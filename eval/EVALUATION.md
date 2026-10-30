# Evaluation

Queries were run through `python src/main.py`. Timings are from `outputs/metrics.json`; traces are in `logs/agent.jsonl`.

| # | Query | Expected | Actual | Worked | Didn't |
|---|---|---|---|---|---|
| 1 | Compare top 3 open-source vector DBs for RAG | Structured comparison with sources | Qdrant/Weaviate/Milvus report from 6-7 sources | Real benchmark numbers; contradiction between sources noted in limitations | Long citation lists on findings; confidence "high" in an early run before the judge existed |
| 2 | Research Zorvanta Quantum Labs (fake company) | Admit no evidence | Low confidence, "evidence contains no info on this company" | No invented funding or product details | Unrelated entities (ZeroVanta, QuantX) appeared in findings; fixed with prompt rule 7b |
| 3 | Find 5 Indian B2B HR-tech startups | 5 startups with positioning | 1 verified startup, confidence low | Judge removed 4 unsupported claims, no invented startups | Sources were listicles, not startup directories; summary contradicted findings and said "5 of 5" (fixed in judge.py); results vary run to run |
| 4 | Pros and cons of multi-agent for customer support | Balanced pros/cons with sources | 4 supported findings, 38.5s, confidence high | Clean structure, every finding cited, judge removed nothing | Cost claim (15x tokens) rests on a few similar blog sources, so "high" is generous |
| 5 | Which is the best database? (vague) | State assumptions, avoid a single "best" | Medium confidence, SQL vs NoSQL by use case, no single winner, 44.8s | Did not pick a winner; limitations explain "best" depends on use case; judge removed 1 of 3 claims | Short answer is only the verification notice (no actual answer) because the judge overwrites it; agent did not ask a clarifying question |


## Metrics

| Run | Time | Sources kept / dropped | Confidence |
|---|---|---|---|
| Vector DB | 538s (Google 503/slow period) | 7 / 1 | high |
| Zorvanta (fake) | 1017s (before timeout fix) | 5 / 3 | low |
| HR startups (before timeout fix) | 1041s | 3 / 4 | low |
| HR startups (after fix) | 176s | 4 / 4 | low |
| Multi-agent | 38.5s | 8 / 0 | high |
| Vague DB query | 44.8s | 5 / 3 | medium |

## Failures found and fixed

1. **Google 503:** added retry with backoff and a fallback model.
2. **Wrong fallback model name:** caught via a 404 in the logs; verified with `models.list()`.
3. **17-minute hang:** trace timestamps showed one LLM call hanging with no retry logged. The SDK timeout did not fire. Fixed with a hard per-call timeout plus a total time budget per step.
4. **Model benchmark ("Say hi"):** gemini-3.8-flash 503, 3.5-flash-lite 34s, 3.6-flash 20s, 3.1-flash-lite 2.3s. Chose 3.1-flash-lite as primary. The HR query went from 1041s to 176s.
5. **Citation check bug:** it scanned the Sources section, so every source looked cited. Now it scans only the report body.
6. **Judge consistency bug:** the short answer contradicted removed findings. Code now overwrites it.
7. **Run-to-run variance:** the vector DB query produced a 6-finding report in one run and a 1-finding low-confidence report in another. Search results are non-deterministic and the judge removed unsupported claims. An ad link (bing.com/aclick) also slipped into the sources; added ad domains to the weak-source list.

## Not done / known limitations

- No baseline (no-tools LLM) comparison.
- No caching or async page fetching.
- Citation check validates IDs only; the judge covers semantic support partly, using the same model family as the writer.
- No hosted malicious-page test for prompt injection (regex filter exists but was not demoed).
- No clarifying question for vague queries; short answer drops the actual answer when claims are removed.
- DuckDuckGo search is non-deterministic: the same query can return different sources.