import re
from urllib.parse import urlparse

INJECTION_RE = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+"
    r"(instructions|prompts?|rules)"
    r"|reveal\s+(your\s+)?(system\s+)?(prompt|instructions)"
    r"|new\s+instructions\s*:"
    r"|do\s+not\s+(cite|mention)\s+(any\s+)?sources",
    re.IGNORECASE,
)

TRUSTED_HINTS = ("github.com", "arxiv.org", "docs.", ".edu", ".gov", "wikipedia.org")
WEAK_HINTS = ("pinterest.", "quora.com", "facebook.com", "instagram.com", "tiktok.com")
AD_HINTS = ("bing.com/aclick", "doubleclick.net", "googleadservices.com")

STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "and", "or", "is", "are", "with",
    "on", "how", "what", "which", "best", "top", "compare", "research", "find",
    "using", "about", "their", "from", "that", "this", "be", "by", "as",
}

THRESHOLD = 0.35


def _keywords(text):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _domain_score(url):
    host = urlparse(url).netloc.lower()
    if any(h in url.lower() for h in WEAK_HINTS):
        return 0.2
    if any(h in host for h in TRUSTED_HINTS):
        return 1.0
    return 0.6


def sanitize(text):
    """Remove lines that look like prompt-injection. Returns (clean_text, removed_count)."""
    kept, removed = [], 0
    for line in text.splitlines():
        if INJECTION_RE.search(line):
            removed += 1
        else:
            kept.append(line)
    return "\n".join(kept), removed


def filter_evidence(evidence, question, queries, trace):
    """Score sources, drop weak ones, strip injection text. Returns (kept, dropped)."""
    kw = _keywords(question + " " + " ".join(queries))
    kept, dropped = [], []

    for src in evidence:
        # Sponsored / ad links are always dropped
        if any(h in src["url"].lower() for h in AD_HINTS):
            dropped.append({
                "title": src["title"],
                "url": src["url"],
                "score": 0,
                "reason": "sponsored/ad link",
                "injection_lines_removed": 0,
            })
            continue

        clean, removed = sanitize(src["content"])
        if removed:
            trace("injection_detected", url=src["url"], lines_removed=removed)

        haystack = _keywords(src["title"] + " " + clean)
        relevance = len(kw & haystack) / max(len(kw), 1)
        length_score = min(len(clean) / 1500, 1.0)
        score = round(
            0.5 * min(relevance * 1.5, 1.0)
            + 0.3 * _domain_score(src["url"])
            + 0.2 * length_score,
            2,
        )

        info = {
            "title": src["title"],
            "url": src["url"],
            "score": score,
            "injection_lines_removed": removed,
        }

        if score < THRESHOLD or len(clean) < 200:
            info["reason"] = "low score or too little text"
            dropped.append(info)
            continue

        kept.append({**src, "content": clean, "score": score,
                     "injection_flagged": removed > 0})

    # IDs dobara S1, S2, S3... sequence mein
    for i, src in enumerate(kept, start=1):
        src["id"] = f"S{i}"

    trace("filtering_done", kept=len(kept), dropped=len(dropped), dropped_detail=dropped)
    return kept, dropped