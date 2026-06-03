# LinkedIn Post Draft — v2 Update
**Date:** 2026-06-03  
**Audience:** Recruiters / hiring managers seeking a senior PM who can be technical  
**Tone:** Honest, reflective, shows technical depth without losing the PM narrative  
**Reference:** Follows up the original v1 post  

---

## DRAFT

A few months ago I shipped a proof-of-concept aircraft safety tracker and concluded it probably shouldn't be scaled into a real product. I wrote about why.

Then I kept building anyway — but with a different goal. Not "can I scale this into a product?" but "how deep can I go into the data engineering before it stops being interesting?"

Turns out: quite deep.

**What v2 adds**

The original app had one data source: Aviation Safety Network (ASN), scraped and served as-is. v2 adds two official government databases:

- **NTSB** — US accident investigation records. The challenge isn't getting the data; it's that 80%+ of NTSB URLs either point to unreleased investigations, empty JavaScript shells, or foreign-led cases with no public docket. I built an HTTP viability audit that classifies each link before import, so the app only shows a Details link when there's actually something there.

- **FAA AIDS** — the FAA's Accident and Incident Data System, ~6,500 Boeing/Airbus records accessed through the ASIAS portal. The challenge here was different: the portal occasionally goes down site-wide, which would make bulk URL checks silently classify every record as dead. I built a liveness probe that aborts the audit if the homepage itself isn't responding — so a 20-minute CDN outage doesn't corrupt 6,000+ link statuses.

The result: **12,592 incidents across 153 aircraft models**, with sources triple-deduplicated across ASN, NTSB, and FAA, and every outbound link verified before display.

**What I actually learned (the non-obvious parts)**

𝟭) 𝗨𝗥𝗟 𝘃𝗮𝗹𝗶𝗱𝗶𝘁𝘆 𝗶𝘀 𝗮 𝗱𝗮𝘁𝗮 𝗾𝘂𝗮𝗹𝗶𝘁𝘆 𝗽𝗿𝗼𝗯𝗹𝗲𝗺, 𝗻𝗼𝘁 𝗮 𝗰𝗼𝗱𝗲 𝗽𝗿𝗼𝗯𝗹𝗲𝗺
HTTP 200 doesn't mean a link works. NTSB CAROL returns 200 with an empty React shell for many records. FAA ASIAS returns 200 on a search form that requires another click to reach the actual report. Both pass a naive "is the URL reachable?" check and fail a "does a user actually get the data?" check. The fix is classifying responses by content, not status code.

𝟮) 𝗚𝗼𝘃𝗲𝗿𝗻𝗺𝗲𝗻𝘁 𝗱𝗮𝘁𝗮 𝗽𝗼𝗿𝘁𝗮𝗹𝘀 𝗮𝗿𝗲 𝗳𝗿𝗮𝗴𝗶𝗹𝗲 𝗮𝘁 𝘀𝗰𝗮𝗹𝗲
Running 6,500 URL checks concurrently against a government CDN produces 403s and timeouts that look like dead records but aren't. Reducing concurrency from 16 threads to 3, increasing timeouts, and adding jitter between requests turned 49 "not working" records into 49 "working" records — same URLs, same data, just less aggressive. Infrastructure behaviour is a product consideration, not just a backend one.

𝟯) 𝗗𝗲𝗱𝘂𝗽𝗹𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗮𝗰𝗿𝗼𝘀𝘀 𝗮𝗴𝗲𝗻𝗰𝗶𝗲𝘀 𝗿𝗲𝗾𝘂𝗶𝗿𝗲𝘀 𝗳𝘂𝘇𝘇𝘆 𝗺𝗮𝘁𝗰𝗵𝗶𝗻𝗴 — 𝗮𝗻𝗱 𝗰𝗼𝗻𝘀𝗲𝗿𝘃𝗮𝘁𝗶𝘀𝗺
ASN, NTSB, and FAA maintain independent record IDs with no shared key. Matching the same real-world event across three systems means fuzzy-scoring on date, operator, location, and fatality count — with a deliberate high threshold to avoid silently dropping real events. The product tradeoff: occasional redundancy is better than false negatives.

𝟰) 𝗦𝗰𝗼𝗽𝗶𝗻𝗴 𝗶𝘀 𝘀𝘁𝗶𝗹𝗹 𝘁𝗵𝗲 𝗵𝗮𝗿𝗱𝗲𝘀𝘁 𝗽𝗮𝗿𝘁
Each phase had a clear PRD, a gate condition, and an explicit non-goals list. The non-goals list got longer with every sprint. Saying "FAA SDR is out of scope for now" is a product decision, not a technical one — and it's the kind of decision that keeps a project shippable instead of perpetually almost-done.

**New tech (v2 additions)**
- `httpx` + `ThreadPoolExecutor` for concurrent URL auditing with per-request jitter
- JSONL audit pipeline with bucket classification, overlay merge, and retry ladders
- SQLite write-back with `--dry-run` / `--apply` pattern (ask before you write)
- `thefuzz` token-set ratio for cross-source incident deduplication

**Stack unchanged from v1:** Flask, SQLAlchemy, HTMX, Railway, DeepSeek for AI summaries, PostgreSQL in production (SQLite locally).

This is still a technical portfolio demo — same disclaimers as v1 apply. But it's now the kind of demo where the interesting problems were in the data pipeline, not the front end.

---

*Links to code and data sources in comments.*

*Disclaimer: Educational/portfolio demo. Incident data is complex and does not indicate aircraft design quality.*

---

## Notes for editing before posting

- Add a concrete opening hook if the "I kept building anyway" angle feels too soft
- The four bolded lessons are the core PM signal — don't cut these
- Consider trimming §2 (infrastructure fragility) if post feels too technical for the audience
- "Links in comments" — add GitHub repo + ASN/NTSB/FAA source links when posting
- Character count target for LinkedIn: ~1,500–2,000 characters for good engagement; this draft is ~2,800 — trim one lesson section if needed
