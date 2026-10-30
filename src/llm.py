import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

import httpx
from google import genai
from google.genai import errors, types

MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
    os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash"),
    "gemini-3.5-flash-lite",
]
MAX_RETRIES = 2
BASE_DELAY = 2
PER_CALL_TIMEOUT = 90   # seconds, hard limit for one API call

_pool = ThreadPoolExecutor(max_workers=4)


def _noop_trace(event, **details):
    pass


def _call_with_hard_timeout(client, model, prompt, config, seconds):
    """Wait at most `seconds` for the API call, even if the HTTP layer hangs."""
    fut = _pool.submit(
        client.models.generate_content,
        model=model, contents=prompt, config=config,
    )
    try:
        return fut.result(timeout=seconds)
    except FutTimeout:
        raise httpx.ReadTimeout("hard timeout hit")


def _make_client(api_key):
    try:
        opts = types.HttpOptions(
            timeout=60_000,
            retry_options=types.HttpRetryOptions(attempts=1),  # SDK ka apna retry band
        )
    except (AttributeError, TypeError):
        opts = types.HttpOptions(timeout=60_000)               # purane SDK ke liye
    return genai.Client(api_key=api_key, http_options=opts)


def call_llm(prompt, schema=None, trace=_noop_trace, max_total_seconds=240):
    """Retry + fallback model, with a hard per-call timeout and a total time budget."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Check the .env file.")

    client = _make_client(api_key)

    config = None
    if schema:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )

    deadline = time.monotonic() + max_total_seconds
    last_error = None

    for model in MODELS:
        for attempt in range(1, MAX_RETRIES + 1):
            if time.monotonic() > deadline:
                trace("llm_budget_exceeded", budget_seconds=max_total_seconds)
                raise RuntimeError(
                    f"LLM time budget ({max_total_seconds}s) exceeded: "
                    f"{type(last_error).__name__}"
                )
            try:
                resp = _call_with_hard_timeout(
                    client, model, prompt, config, PER_CALL_TIMEOUT
                )
                result = resp.parsed if schema else resp.text
                if result is None or result == "":
                    raise ValueError("empty or malformed model output")
                return result

            except (errors.ServerError, httpx.TimeoutException) as e:
                last_error = e
            except errors.ClientError as e:
                if e.code == 404:
                    last_error = e
                    trace("llm_model_unavailable", model=model, code=404)
                    break
                if e.code == 429:
                    last_error = e
                else:
                    raise
            except ValueError as e:
                last_error = e

            delay = min(BASE_DELAY * 2 ** (attempt - 1) + random.uniform(0, 1), 8)
            trace("llm_retry", model=model, attempt=attempt,
                  error_type=type(last_error).__name__)
            time.sleep(delay)

        trace("llm_fallback", failed_model=model)

    raise RuntimeError(f"All models failed: {type(last_error).__name__}: {last_error}")