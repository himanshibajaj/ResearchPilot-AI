# ResearchPilot-AI

# ResearchPilot AI

An evidence-first research agent: plan → search → fetch → filter → synthesize → judge, with retries, timeouts and full tracing. CLI only, by design (the brief prioritizes system design over UI).

## Setup
1. Python 3.11+
2. `python -m venv .venv` and activate it (`.venv\Scripts\activate` on Windows)
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`
5. `python src/main.py` and type a research question

Output: terminal + `outputs/research_<timestamp>.md`. Metrics: `outputs/metrics.json`. Trace: `logs/agent.jsonl`.

## Architecture
Question → Planner (LLM) → Search (DDGS, multi-query, dedup) → Fetch (httpx + trafilatura) → Filter (score + injection strip + ad-link drop) → Synthesizer (LLM, Pydantic schema) → Judge (LLM claim check + guardrails) → Citation-ID check → Markdown report + metrics + JSONL trace

Files: `src/main.py` (orchestration, tools), `llm.py` (retry/fallback/timeout), `filtering.py`, `judge.py`, `schemas.py`. Evaluation: `eval/EVALUATION.md`. Samples: `outputs/sample_*.md`.

## Why an agentic approach?
The number of searches needed is not known in advance, and source quality varies. A planner splits the question into queries, tools gather evidence, and a judge checks the result. A single LLM call cannot browse or verify.

## Tools and why
- **Web search (DDGS):** free, no key, finds candidate sources.
- **Page fetch (httpx + trafilatura):** reads full pages, not just snippets.
- **LLM (Gemini):** planning, synthesis, claim judging.

## How bad tool results are handled
| Failure | Behavior |
|---|---|
| Search fails | Logged, other queries continue |
| Page fetch fails/blocked | Skipped, snippet used if available |
| Planner fails | Falls back to the raw question |
| LLM 503/429/timeout | Retry with backoff, then fallback model |
| LLM hangs | Hard per-call timeout (90s) + total time budget per step |
| Wrong model name (404) | Skips straight to next model |
| Malformed LLM JSON | Pydantic schema; retry |
| Judge fails | Confidence capped at medium, limitation noted |
| No usable sources | Returns "insufficient evidence" |

## How hallucinations are reduced
- Answer only from supplied evidence; every finding must cite source IDs (schema enforces at least one).
- Sources section is built by code, not the model.
- Judge removes claims the cited sources do not support, then code overwrites the short answer and confidence reason so the report cannot contradict itself.
- Fewer than 2 surviving sources forces confidence = low.
- Prompt rule: if the entity is not in the evidence, return no findings.

## Prompt injection
Source text is wrapped as untrusted data, and a regex filter strips lines like "ignore previous instructions". Limitation: regex catches only known patterns.

## Key tradeoffs
- Custom orchestration instead of LangGraph, for clarity.
- Judge adds one LLM call (latency/cost) but removes unsupported claims.
- Evidence capped per source and number of pages to control latency.
- Free DDGS search is non-deterministic: same query can return different sources.

## Known limitations
- Citation-ID check validates IDs only, not semantic support (the judge covers this partly).
- Judge is the same model family as the writer.
- Hard timeout abandons a hung thread rather than killing it.
- Source quality scoring is heuristic (domain hints, keyword overlap, length).
- Sequential page fetching.

## Production readiness
Wrap `run_research` in FastAPI with a job queue, async/parallel fetching, caching, secrets manager, CI running the eval set, Docker.

## What I would monitor
Latency per step, cost per query, LLM retry/timeout rate, tool error rate, % low-confidence answers, claims removed by judge, injection flags, user feedback.

## AI Tool Usage
**Tools:** Claude (design discussion, code drafts, debugging help), Google Gemini API (runtime LLM inside the product).

**AI-assisted:** first drafts of `llm.py`, `schemas.py`, `filtering.py`, `judge.py`, the planner, and README/eval drafts.

**My own work:** running and testing every query, diagnosing failures from the logs (hung call, wrong fallback model, citation bug), model benchmarking, choosing tradeoffs.

I have run and can explain every file.
