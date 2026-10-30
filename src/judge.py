import json

from llm import call_llm
from schemas import JudgeResult


def judge_and_guard(answer, evidence, trace):
    """Check each claim against its cited sources, then apply confidence guardrails."""
    by_id = {s["id"]: s for s in evidence}

    claims = []
    for i, f in enumerate(answer.key_findings):
        claims.append({
            "claim_index": i,
            "claim": f.claim,
            "cited_sources": [
                {"id": sid, "content": by_id[sid]["content"][:1500]}
                for sid in f.source_ids if sid in by_id
            ],
        })

    prompt = f"""
You are a strict fact-checking judge.
For each claim, decide if the cited source text clearly supports it.
supported = true only if the source text directly states or clearly implies the claim.
If cited_sources is empty or the text does not contain the claim, supported = false.
Give a one-sentence note per claim.

<claims>
{json.dumps(claims, ensure_ascii=False)}
</claims>
"""

    try:
        result = call_llm(prompt, schema=JudgeResult, trace=trace, max_total_seconds=120)
        unsupported = {c.claim_index for c in result.checks if not c.supported}
    except Exception as exc:
        trace("judge_failed", error_type=type(exc).__name__)
        answer.limitations_and_assumptions.append(
            "Automatic claim verification was unavailable for this run."
        )
        if answer.confidence == "high":
            answer.confidence = "medium"
        unsupported = set()

    total = len(answer.key_findings)

    if unsupported:
        kept = [f for i, f in enumerate(answer.key_findings) if i not in unsupported]
        verified = len(kept)

        answer.limitations_and_assumptions.append(
            f"{len(unsupported)} of {total} claim(s) were removed because the cited sources did not support them."
        )
        answer.key_findings = kept

        answer.short_answer = (
            f"Only {verified} of {total} initial findings could be verified "
            f"against the sources, so this answer is partial and should not be "
            f"treated as complete."
        )
        answer.confidence_reason = (
            f"{len(unsupported)} of {total} claims were not supported by their "
            f"cited sources and were removed. Remaining evidence is thin."
        )

        if answer.confidence == "high":
            answer.confidence = "medium"
        if total and len(unsupported) / total > 0.5:
            answer.confidence = "low"

    # Guardrail: kam sources = low confidence
    if len(evidence) < 2:
        answer.confidence = "low"
        answer.confidence_reason = (
            "Fewer than 2 reliable sources survived filtering. " + answer.confidence_reason
        )

    trace("judge_done", unsupported=len(unsupported), total=total,
          final_confidence=answer.confidence)
    return answer