# Hermes Agent Creative Hackathon Proposal (Codex)

## Context
- Hackathon window is 16 days with a May 3 deadline and prizes focused on creative Hermes-agent projects in video/image/audio/3D/interactive media.
- This repo already has strong aviation-data plumbing plus AI analysis hooks, so the best play is to build a high-polish creative layer instead of another ingestion pipeline.

## What Exists Today (Repo Analysis)
- Multi-source incident ingestion: NTSB, FAA AIDS, FAA SDR with retry-safe bulk import patterns.
- Canonical merge logic and source-priority model (`NTSB > FAA_AIDS > FAA_SDR > ASN`) for incident truth.
- System tagging pipeline using JASC normalization and mapped/unmapped system tracking.
- Rich incident model graph: `Incident`, `IncidentSource`, `SystemTag`, `ReportAnalysis`, `ImportLog`, and dedupe decision trails.
- Existing AI endpoint `/api/analyze-report` with model adapters, caching, rate limiting, URL/PDF extraction, and structured JSON parsing.
- HTMX/Jinja UI for search, filtering, incidents timeline, and aircraft detail pages.

## Proposed Concept: **Black Box Studio**
An interactive “cinematic safety replay” product for one hero crash that turns raw investigation data into a synchronized:
- 3D flight scene
- narrated incident storyline
- systems-failure timeline
- evidence panel linked to source records

### Why This Wins
- Creative + useful: transforms hard-to-read reports into understandable safety narratives.
- Visually strong: perfect for a 45-60s Twitter/X demo reel.
- Technically credible: clearly demonstrates autonomous agent orchestration, model handoff, and deterministic rendering output.
- Scope-safe: one hero incident yields quality and reliability inside 16 days.

## Hermes + Kimi Role Design
### Hermes Agents (Primary Judging Signal)
- **Investigator Agent:** extracts event timeline from `IncidentSource.source_data` + report text.
- **Causality Agent:** identifies root cause, contributing factors, and confidence tiers.
- **Storyboard Agent:** outputs a scene script (beats, camera intent, text overlays, voiceover script).
- **Verifier Agent:** cross-checks generated claims against source snippets and flags low-confidence claims.

### Kimi 2.5 Coding Model (Dual-Track Signal)
- Converts storyboard JSON into concrete scene config and animation logic for Three.js/React Three Fiber.
- Generates helper components quickly (timeline scrubber, caption overlays, scene state machine).
- Accelerates front-end iteration while Hermes owns reasoning and narrative quality.

## Integration Plan (Concrete Repo Touchpoints)
- Add `app/services/hermes_story_engine.py`:
  - orchestrates multi-agent prompts
  - emits strict JSON contracts (`timeline`, `causes`, `storyboard`, `citations`)
- Add `app/services/kimi_scene_generator.py`:
  - translates storyboard to render config and keyframe tracks
- Add route `POST /api/creative/replay/<incident_id>` in `app/routes.py`:
  - returns assembled replay payload
- Add page `app/templates/creative_replay.html`:
  - split view: 3D scene + narrative/evidence panel
- Reuse existing models:
  - `Incident`, `IncidentSource`, `SystemTag`, `ReportAnalysis` for provenance and display
- Optional persisted table (if needed): `CreativeReplay` for cached agent outputs/versioning

## MVP Scope (16-Day Feasible)
- Single hero incident only.
- One polished replay mode (not full scenario builder).
- One visual style pack (day/night, weather fixed).
- Voiceover optional; subtitle-first is acceptable.

## Day-by-Day Delivery Plan
1. **Days 1-2:** Select hero incident, lock data quality, define JSON schemas.
2. **Days 3-5:** Build Hermes Story Engine with citation-first output.
3. **Days 6-8:** Build replay API and payload assembler.
4. **Days 9-11:** Implement 3D scene + timeline sync UI.
5. **Days 12-13:** Integrate Kimi-assisted scene code generation/refinement.
6. **Day 14:** QA pass, latency tuning, fallback handling.
7. **Day 15:** Record final demo, produce screenshots/GIF clips.
8. **Day 16:** Publish Twitter thread + repo walkthrough.

## Demo Script for Twitter Submission
- 0-5s: “From dense crash records to cinematic safety replay.”
- 5-20s: Show raw source snippets and Hermes generating structured timeline live.
- 20-40s: 3D replay runs with synchronized narrative and system-failure overlays.
- 40-55s: Evidence click-through proving claims are source-grounded.
- 55-60s: “Built with Hermes Agents (+ Kimi 2.5 coding assist) in 16 days.”

## Technical Risk Register + Mitigation
- Risk: hallucinated narrative details.
  - Mitigation: verifier agent + mandatory citation fields + confidence badges.
- Risk: malformed model JSON.
  - Mitigation: schema validation + repair pass + safe fallback summary.
- Risk: front-end polish time sink.
  - Mitigation: one-incident scope + one visual style + fixed camera templates.
- Risk: rendering complexity.
  - Mitigation: deterministic keyframe-based animation, avoid physics simulation.

## Success Criteria
- End-to-end replay generation under 30s for cached incident context.
- Replay payload is schema-valid and citation-complete.
- Demo video clearly showcases Hermes agent orchestration, not just UI effects.
- Twitter post includes short clip + architecture graphic + open repo link.

## Stretch Goals (Only If Ahead of Schedule)
- Add “what-if safety intervention” branch playback.
- Add optional TTS narration.
- Add second incident preset for replay comparison.

---

## 📝 Peer Review: Technical & Strategic Critique

**Reviewer:** Senior Engineering Manager / Tech Lead
**Date:** April 18, 2026

### Executive Summary
The "Black Box Studio" concept is an exceptionally strong hackathon submission. It perfectly targets the judging criteria (creative use of Hermes, interactive 3D, dual-model eligibility) and smartly scopes the execution down to a single "hero incident." The 4-agent orchestration pattern (Investigator -> Causality -> Storyboard -> Verifier) is technically impressive and highly marketable. However, the timeline between Days 9-13 introduces significant integration risk by separating the 3D scene implementation from the Kimi code generation phase. 

### 1. Solution Architecture
*   **Strengths:** The multi-agent pipeline is well-designed. The inclusion of a "Verifier Agent" to cross-check claims against source snippets is a standout architectural choice that solves the LLM hallucination problem elegantly. Reusing the existing data plumbing (`IncidentSource`, etc.) saves days of work.
*   **Weaknesses:** The proposal lacks detail on how state is passed between the 4 Hermes agents. If the context window blows up or JSON schemas mismatch between agent handoffs, the pipeline will break. Furthermore, relying on Kimi 2.5 to generate Three.js logic *after* the UI is built (Days 12-13) is an anti-pattern. Kimi should be generating the foundational Three.js components first.

### 2. Requirements & Deliverables
*   **Strengths:** The Twitter demo script is excellent. Working backward from the 60-second video ensures the team builds only what is visible. The MVP scope is appropriately ruthless (no physics, one weather style).
*   **Weaknesses:** The proposal mentions "evidence click-through" in the demo script, but doesn't define how the frontend will map 3D timeline events back to specific text highlights in the UI. The data contract for `citations` needs strict definition immediately.

### 3. Methodology & Implementation
*   **Strengths:** The Day-by-Day plan is clear and sequential. The risk register correctly identifies the front-end polish time sink and rendering complexity as the primary threats.
*   **Weaknesses:** Days 9-11 (Implement 3D scene) and Days 12-13 (Integrate Kimi-assisted scene generation) are out of order. Kimi should be used in Days 9-11 to generate the scene config, which is then manually refined and integrated. If Kimi fails to produce usable Three.js code on Day 12, the project fails.

### 4. Team Capabilities & Resource Allocation
*   **Strengths:** Leveraging existing Flask/SQLAlchemy knowledge means zero time is wasted on database setup.
*   **Weaknesses:** 3D web rendering (Three.js/React Three Fiber) has a steep learning curve. If the team lacks strong WebGL experience, relying on Kimi to generate *complex* animations (like banking, pitching, or terrain mapping) is a high risk. 

### 5. Technical Challenges & Mitigations
*   **Challenge:** Agent handoff latency. Running 4 sequential LLM calls might take 60-90 seconds, breaking the "under 30s" success criteria.
    *   *Mitigation:* The `CreativeReplay` caching table mentioned as "optional" must be **mandatory**. The demo should run entirely from cached JSON payloads, with the live generation shown asynchronously or sped up for the video.
*   **Challenge:** 3D Asset Sourcing.
    *   *Mitigation:* The plan needs a Day 1 task to secure a low-poly glTF/OBJ model of the hero aircraft. Do not attempt to generate or build 3D assets from scratch.

### 6. Prioritized Recommendations for Enhancement
1.  **Mandatory Caching (P0):** Make the `CreativeReplay` table mandatory. Pre-generate the 4-agent output for the hero incident so the frontend demo is instantaneous and immune to API timeouts during judging.
2.  **Reorder Kimi Integration (P1):** Move Kimi 2.5 scene generation to Days 8-9. Have Kimi write the raw Three.js components first, then spend Days 10-12 manually integrating and polishing them.
3.  **Define the Handoff Schema (P1):** Explicitly define the JSON schema that passes between the Storyboard Agent and the Kimi Coding Model. This contract is the linchpin of the entire project.
4.  **Secure 3D Assets Early (P2):** Add "Acquire low-poly aircraft 3D model" to Day 1.
5.  **Drop "Evidence Click-Through" Complexity (P3):** Instead of interactive click-throughs in the 3D scene, have the Verifier Agent simply output static citation text boxes that appear alongside the timeline.
