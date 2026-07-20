# PRD 0013 — Flight Lookup, Shareable Safety Card & PH Launch Readiness

**Status:** Draft  
**Date:** 2026-06-27 (revised 2026-06-28)  
**Goal:** Make the Aircraft Safety Tracker credible and launchable on Product Hunt by giving consumers an immediate "is my plane safe?" answer, contextualised safety data, a side-by-side compare mode, and a positioning hook strong enough to survive PH comments.

---

## 0. Strategic Context

This PRD exists because the current product is a database browser — useful, but not PH-launchable. Three gaps block a credible launch:

1. **No entry point.** There's nothing to *do* in the first 5 seconds. A search box fixes this.
2. **No context on the numbers.** Raw incident counts without fleet-size context can mislead. A "per aircraft in service" denominator fixes this.
3. **No positioning hook.** "Browse aviation incidents" is not a headline. "The safety data airlines hope you don't look up" is.

There are also two distinct potential markets. This PRD deliberately chooses one:

| Market | Fit for PH? | Decision |
|---|---|---|
| **B2C — nervous flyers, curious consumers** | ✅ Yes | **Build this for PH** |
| **B2B — airline fleet procurement managers** | ❌ No (enterprise sales, wrong funnel) | Backlog — post-traction |

Insight from an ex-Airbus employee: airlines actively avoid making safety data consumer-accessible because it "spooks" passengers. That's the hook. We're building the thing they'd rather you didn't have.

---

## 1. Introduction / Overview

This PRD delivers three things for PH launch readiness, plus one stretch feature:

1. **Homepage search** — the first thing a visitor sees is "Search your aircraft model". Search-first, not browse-first.
2. **Shareable aircraft result page** (`/aircraft/<slug>`) — contextualised safety stats, an AI summary, and rich Open Graph metadata so a shared link unfurls on WhatsApp/Twitter/iMessage.
3. **Rate context** — incident counts shown alongside fleet-size denominator ("X incidents per 100 aircraft in service") so the numbers are meaningful, not alarming.
4. **Side-by-side compare mode** *(stretch)* — `/compare/boeing-737-800/airbus-a320` — one URL, two aircraft, shareable. This is the viral screenshot that gets upvoted on PH.

No new data pipelines are needed. All data already exists in the database.

---

## 2. Goals

1. A visitor can land on the homepage and within 10 seconds have a meaningful, contextualised safety answer about a specific aircraft type.
2. Each aircraft result page has a stable, shareable URL with an OG preview that works on WhatsApp, Twitter/X, iMessage, and LinkedIn.
3. Safety statistics include enough context (fleet size or rate) that a non-expert user is informed, not misled or unnecessarily alarmed.
4. The product survives the three most predictable PH sceptic comments (see Section 10).
5. The "Boeing & Airbus only" scope is owned confidently, not apologised for.

---

## 3. User Stories

**Core (must-have for PH):**
- **As a nervous flyer**, I want to search "737 MAX" and immediately see a contextualised safety record so I can make an informed decision about my booking — not just a raw number I can't interpret.
- **As someone who just booked a flight**, I want to paste a link in a group chat that unfurls into a readable safety card, so my friends can see the same information without signing up for anything.
- **As a first-time visitor from Product Hunt**, I want to understand what this tool does and try it within 5 seconds of landing, without reading any instructions.
- **As a curious consumer**, I want to compare the 737-800 and A320 side by side so I know which aircraft I'd prefer on a given route.

**Secondary (post-PH):**
- As a journalist or researcher, I want a direct link to an aircraft's safety page that I can cite in an article.
- As an airline fleet manager, I want to evaluate incident profiles across aircraft families when preparing a procurement analysis. *(Backlog — B2B)*

---

## 4. Functional Requirements

### 4.1 Homepage — search-first layout

1. The homepage must display a prominent search input as the **primary above-the-fold element**, with placeholder text: *"Search your aircraft — e.g. 737-800, A320, 777…"*
2. A single-line positioning tagline must appear above or below the search box. Suggested copy: *"The safety record airlines hope you don't look up."* (Final copy TBD — see Open Questions.)
3. As the user types (minimum 2 characters), the input must show live autocomplete suggestions drawn from the `Aircraft` table.
4. Each suggestion must show: aircraft name + a short stat (e.g. "Boeing 737-800 · 2,847 incidents · 153 fatal").
5. Selecting a suggestion or submitting navigates to `/aircraft/<slug>`.
6. The search box must support keyboard navigation (arrows, Enter, Escape).
7. The existing aircraft list/grid must remain accessible below the fold — the search is an addition, not a removal.

### 4.2 Aircraft result page — `/aircraft/<slug>`

8. Each aircraft must have a stable, human-readable URL slug (e.g. `/aircraft/boeing-737-800`). Slugs stored as a column on the `Aircraft` model.
9. The page must display **above the fold**:
   - Aircraft name and manufacturer
   - **Total incidents (all time)** — with fleet-size rate context (e.g. "2,847 incidents · ~14 per 100 aircraft in service")
   - **Fatal incidents** — same rate context if data allows
   - **Incidents in the last 5 years** — recency signal, shown as a trend indicator
   - **AI safety summary** — 1–2 sentences from the existing DeepSeek integration (TTL-cached)
10. Tone of all copy must be calm and factual. "2,847 incidents recorded" not "2,847 CRASHES". Users are already anxious.
11. The existing incident detail list must remain visible below the fold.
12. The page must include a **"Share" button** that copies the full URL to the clipboard, with a brief confirmation ("Link copied!").
13. A **"Compare with another aircraft"** prompt/link must appear on the result page, linking to the compare feature (req. 4.3). Even if compare is not built in v1, the prompt seeds the behaviour.

### 4.3 Side-by-side compare mode *(stretch goal — build if time allows before PH)*

14. A compare page at `/compare/<slug-a>/<slug-b>` must show both aircraft's stats side by side in a two-column layout.
15. Each column shows the same stat tiles as the individual result page (req. 9).
16. A "Winner" or "Lower incident rate" indicator highlights which aircraft has the better rate — shown neutrally (e.g. a subtle green dot), not sensationally.
17. The page must have its own OG metadata (title: "737-800 vs A320 — Safety Comparison").
18. A search/swap input on the compare page must allow replacing either aircraft without navigating away.
19. The compare URL must be shareable and stable — anyone with the link sees the same comparison.

### 4.4 Rate context — "per aircraft in service"

20. Every incident count displayed must be accompanied by a rate denominator where data is available. Preferred: incidents per 100 aircraft in the active global fleet. Acceptable fallback: a static footnote ("Fleet size data sourced from [source], [year]").
21. If rate data is unavailable for a specific aircraft, the raw count is shown with a disclaimer: *"Rate data unavailable — incident count shown without fleet-size context."*
22. The rate calculation methodology must be documented on a `/methodology` or `/about` page linked from the footer.

### 4.5 Open Graph / social sharing

23. Every aircraft result page and compare page must include `<meta property="og:*">` and `<meta name="twitter:card">` tags:
    - `og:title`: "Boeing 737-800 Safety Record — Aircraft Safety Tracker"
    - `og:description`: AI summary (truncated to 200 chars) or fallback stats sentence
    - `og:url`: canonical page URL
    - `og:image`: static branded placeholder for v1 (dynamic per-aircraft image is a stretch goal)
24. The homepage must have OG tags describing the product with the positioning tagline as `og:description`.

### 4.6 Scope / empty state

25. If a user searches for an aircraft outside the current scope (e.g. Embraer E175), the result must show a **confident, non-apologetic** empty state: *"We currently cover the Boeing and Airbus commercial fleets — the two largest aircraft families in the world. Embraer, Bombardier, and ATR are not yet included."*
26. The empty state must not be a generic 404. It must link back to the homepage search.
27. No "coming soon" language unless expansion is concretely planned — use "not yet included" instead.

### 4.7 Positioning copy — homepage and about page

28. The homepage must clearly answer "why use this instead of aviation-safety.net?" within the first scroll. Suggested framing: unified FAA + NTSB + ASN data in one place, with an AI summary that interprets it for a non-expert.
29. An `/about` page (or section) must explain: what data sources are used, what Boeing + Airbus scope means, and how the rate methodology works. This is the credibility anchor for journalists and PH commenters.

---

## 5. Non-Goals (Out of Scope for PH Launch)

- **Flight number lookup** (e.g. "SQ321") — requires live flight-to-aircraft API; deferred to backlog.
- **Route lookup / heat maps** (e.g. "SYD → LHR") — interesting consumer feature, but requires route-to-aircraft mapping; backlog.
- **Aircraft "perks" / amenity data** (seat pitch, Wi-Fi, etc.) — product direction diverges from safety focus; backlog.
- **Embraer, Bombardier, ATR ingestion** — data pipeline work; backlog.
- **Downloadable PNG safety card** — OG sharing covers the MVP need; backlog.
- **Email capture / waitlist** — valid, but not a launch blocker; backlog.
- **Safety score / letter grade** — requires a defensible actuarial methodology to avoid misleading users; backlog.
- **B2B / airline fleet procurement features** — enterprise sales motion, wrong funnel for PH; backlog.
- **Dynamic per-aircraft OG images** — static placeholder is fine for v1; backlog.

---

## 6. Design Considerations

- **Homepage above the fold:** Search box dominates. Minimal chrome — think Google homepage. Tagline above the box. Existing content moves below the fold.
- **Result page layout:** Stat tiles (large numbers) → AI summary card → "Compare" prompt → incident table. Clean, not busy. 3–4 tiles max above the fold.
- **Compare page layout:** Two-column on desktop, stacked on mobile. Identical stat tiles in each column for easy scanning. A single "Share this comparison" button at the top.
- **Tone throughout:** Calm, factual, journalistic. Never alarmist. The product is informative, not sensational — that's what makes it credible to both nervous flyers and PH commenters.
- **Mobile:** Search box, stat tiles, and compare layout must all work on a 375px phone screen. Many users will look this up at the gate.
- **OG image v1:** Static branded card (site name + tagline) is acceptable. Ideal v2: dynamic card with aircraft name + top 3 stats as text.

---

## 7. Technical Considerations

- **Autocomplete endpoint:** `GET /api/aircraft/search?q=<query>` → JSON `[{name, slug, incident_count, fatal_count}]`. Simple `ILIKE` on `Aircraft.name`. No new infrastructure.
- **Slug generation:** Migration to add `slug` column to `Aircraft`, populated from `name` (lowercase, hyphens, manufacturer prefix). Must be unique. Existing ID-based URLs get 301 redirects.
- **Rate data source:** Options in priority order: (a) ACAS/ascend fleet database if accessible, (b) static JSON file of fleet sizes sourced from Wikipedia/manufacturer data, (c) skip rate and show disclaimer. A static JSON file seeded from public data is the fastest path for PH.
- **`incidents_last_5_years`:** Likely needs to be computed. Either: a DB column updated on each ingest run, or a computed property at render time from `Incident.event_date`. Render-time is simpler for v1.
- **OG tags:** Rendered server-side in the Jinja `<head>` block. `aircraft.ai_summary` already cached — use directly, truncate to 200 chars.
- **Compare page:** No new data needed — the same endpoint as the result page, called twice. The route `/compare/<slug-a>/<slug-b>` renders a single template with two aircraft objects.
- **No new data pipelines needed for any of the above.**

---

## 8. Success Metrics

- A visitor can search, land on a result page, and understand the safety picture in under 10 seconds from a cold homepage load.
- OG preview renders correctly on WhatsApp, Twitter/X, and iMessage when a link is pasted.
- On PH launch day: zero top-5 comments go unanswered because the product/about page pre-empts them.
- Compare URLs are shared in PH comments (organic virality signal).
- Bounce rate on homepage decreases vs. pre-launch baseline.

---

## 9. Open Questions

1. **Tagline finalisation:** "The safety record airlines hope you don't look up" — too provocative, or exactly right for PH? Needs a call before front-end copy is locked.
2. **Rate data source:** Static JSON (fastest, build in a day) vs. a real fleet-size API (accurate, slower). Decision gates the rate context requirement.
3. **Slug migration:** Do current aircraft pages use DB IDs or clean URLs? If IDs, 301 redirects are needed to avoid breaking any existing inbound links.
4. **`incidents_last_5_years`:** Computed at render time (simple, slower) or stored column updated on ingest (faster, needs migration)?
5. **Autocomplete threshold:** All aircraft in DB, or only those with ≥5 incidents (avoids surfacing sparse records with misleading "0 incidents")?
6. **Compare as v1 or stretch:** Does compare ship with PH launch, or is it added in the week after based on early feedback?
7. **OG image:** Static placeholder (1 day) or dynamic per-aircraft image (3–5 days)? Decision affects PH screenshot quality.

---

## 10. PH Sceptic Survival Guide

The three comments that will appear within the first hour on PH, and how to pre-empt them:

| Predicted comment | Pre-emption |
|---|---|
| *"This is just aviation-safety.net with a nicer UI"* | About page: explain unified FAA+NTSB+ASN view, AI summary for non-experts, rate context. Make the differentiator the headline, not a footnote. |
| *"Where's Embraer / Bombardier?"* | Confident empty state (req. 25) + about page scope explanation. "We cover the two largest commercial fleets" is a position, not an apology. |
| *"312 incidents — is that a lot or a little? You're scaring people."* | Rate context on every stat tile (req. 20–22) + methodology page. Calm tone throughout (req. 10). |

---

## 11. Backlog (Post-PH, post-traction)

These ideas are valid but explicitly deferred. Revisit if PH traction validates the consumer angle:

- **Flight number lookup** (SQ321 → aircraft type → safety record)
- **Route heat maps** (common routes, incident geography)
- **Aircraft amenity data** (seat pitch, Wi-Fi, age of fleet)
- **Embraer / Bombardier / ATR ingestion**
- **Dynamic OG image cards** (per-aircraft stats rendered as image)
- **Email capture / alerts** (notify me of new incidents on my aircraft type)
- **B2B / fleet procurement view** — incident profiles, trend analysis, export. Only if enterprise interest emerges post-launch.
- **Downloadable PNG safety card**
- **Safety score / letter grade** — only after a defensible methodology is established
