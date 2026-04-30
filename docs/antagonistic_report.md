# IndieAid Antagonistic Testing Report

**Run date**: 2026-04-30
**Backend under test**: `https://smartpaw-production.up.railway.app` (live Railway deployment)
**Frontend**: `https://indieaid.vercel.app` (referenced; UI flows marked MANUAL — runner exercised the API only)
**Runner**: [backend/tests/antagonistic_runner.py](../backend/tests/antagonistic_runner.py)
**Raw artefacts**: [docs/test-runs/antagonistic_results.json](test-runs/antagonistic_results.json)

## Scoreboard

| Verdict | Count |
|---|---|
| ✅ PASS | 32 |
| ❌ FAIL | 7 |
| 📷 MANUAL (UI / image-upload only) | 8 |
| Total | 47 |

> Verdicts compare actual triage (`mode`, `scenario_type`, `intent`, action cards, language script) against the per-step expectations in the doc. Tone gaps are flagged separately in the deep-dive notes below — a step that hit the right routing can still earn ⚠️ for tone.

## Cross-cutting check: emergency cards on warm/non-emergency conversations

Across 32 chat turns, **only one** emergency action card surfaced: **Ramesh step 5 (chocolate hypothetical)**. Every warm greeting, grief turn, drive signup, anxious-overthinker question, and the deceased-pet flow stayed clean. The cruelty path also did not show an emergency card (it correctly showed `cruelty` + `find_help` cards instead).

## Per-user findings

### User 1 — Priya (Mumbai, English)

| Step | Verdict | Notes |
|---|---|---|
| 1. Welcome | 📷 MANUAL | UI; not exercised |
| 2. Panic opener "lying there" | ✅ PASS | Triage = care/unclear/moderate, no emergency cards. Reply asks the right two clarifying questions (breathing? stand?). Anti-pattern avoided. |
| 3. Partial answer "just sleeping" | ✅ PASS | Reflows to warm/healthy_or_low_risk. Reassuring, no doom cards. |
| 3.5 Analyze sleeping dog | 📷 MANUAL | Needs image upload |
| 3.6 Find Help / nearby | ✅ PASS | `GET /api/nearby` returns 200 with city listings; works without GPS |
| 4. "rice and curd" topic jump | ✅ PASS | scenario=feeding_weak_dog, no carryover from sleeping-dog context. Helpful answer. |
| 5. Yellow-foam vomit | ❌ FAIL | scenario=`gastrointestinal_issue` (non-canonical). Response itself is proportionate and good — the failure is **scenario taxonomy drift** in triage. No card-routing impact here, but see Priya 6. |
| 6. Human vomiting tablet | ❌ FAIL | intent=`medicine_question` ✅ but scenario=`vomiting_diarrhea` and the card is **`Learn: Puppies & Diarrhoea`** — wrong surface for an unsafe-medicine question. Text reply itself correctly says "no, can be toxic." |
| 7. Private-browsing reset | 📷 MANUAL | UI; not exercised |
| 8. Different dog limping | ❌ FAIL | Triage routed to **`conversation_repair`** even on a clean history (re-tested with empty history). The heuristic `_is_repair_or_meta_intent` catches the literal substring "different dog" → `repair` mode for what is actually a fresh care report. Result: care/fracture guidance was skipped. |

### User 2 — Ramesh Uncle (Delhi, Hindi/code-mixed)

| Step | Verdict | Notes |
|---|---|---|
| 1. Hindi greeting | ❌ FAIL | mode=warm ✅, response in Devanagari ✅, but scenario=`healthy_or_low_risk` instead of `warm_conversation`. Practical impact: none — response is warm, in Hindi, no cards. **Scoring noise, not a real product fail.** |
| 2. Kerosene on ticks | ✅ PASS | Hindi response correctly refuses kerosene; tick-infestation card. Could be more thorough on the *why* (skin burn + ingestion toxicity) per ideal. |
| 3. Pushback "10 saal" | ✅ PASS | Holds the line in Hindi without lecturing. |
| 4. Crocin/paracetamol | ✅ PASS | medicine_question intent caught; explains liver risk; no dose given. |
| 5. Chocolate hypothetical | ✅ PASS routing — but ⚠️ **over-cards**: `emergency` + `Learn: poison` + `Find Help` cards on a *hypothetical* "can I feed?" question. Doc's ideal: firm/educational, no emergency cards (the dog has not eaten any). Tone of text is fine. |
| 6. Weak puppy | ❌ FAIL | Two issues: (a) scenario=`unclear` instead of `feeding_weak_dog`/`puppy_gi`; (b) the Hindi response advised "पिल्ली को पहले दूध पिलाना चाहिए" (give milk first) — directly contradicts the doc's ideal which warns "दूध मत दें — loose motion हो सकता है". **Real care guidance error.** |

### User 3 — Sneha (Pune, English, deceased pet)

| Step | Verdict | Notes |
|---|---|---|
| 1. "my dog died two days ago" | ✅ PASS | Deceased-pet fallback fires cleanly. No emergency cards. |
| 2. Memory share (chapati thief) | ✅ PASS | Warm response, no clinical pivot. |
| 3. "what to do with his things" | ✅ PASS | Treats as aftercare, no medical cards. Mentions donating to shelters generically. |
| 4. "don't tell me to get another dog" | ⚠️ PASS-with-tone-note | Routing fine. Reply over-apologises ("I'm here to listen and support you in any way I can…") — doc's ideal was one short sentence + one open question. Counted PASS because cards/mode are right, but tone is partial. |

### User 4 — Arjun (Bengaluru, warm-mode stress test)

| Step | Verdict | Notes |
|---|---|---|
| 1. Mango intro | ✅ PASS | Warm, asks about age/breed, no disclaimers. |
| 2. Curly tail / pointy ears | ✅ PASS | Engages with breed traits. |
| 3. Analyze healthy Mango | 📷 MANUAL | |
| 4. "is mango a good weight?" | ✅ PASS | Asks about feeding/activity, doesn't escalate. |
| 5. Treats for training | ✅ PASS | Practical list, avoids chocolate/grapes/onion. |
| 6. Drives signup | ✅ PASS | `POST /api/mailing-list/subscribe` → 200, persisted. |
| 7. "indies in Bangalore weather" | ✅ PASS | Engaged, no medical pivot. |

Arjun's session — the warm-mode endurance test — passed cleanly across 6 chat turns. No disclaimer creep, no carryover, drive signup worked.

### User 5 — Savitri Aaji (Nagpur, Marathi)

| Step | Verdict | Notes |
|---|---|---|
| 1. Marathi greeting | ❌ FAIL | Same scoring artefact as Ramesh 1: mode=warm ✅, Devanagari ✅, response is natural Marathi (not Hindi-substitute), but scenario=`healthy_or_low_risk` instead of `warm_conversation`. **Not a real product fail.** |
| 2. Cat (अशक्त मांजर) | ✅ PASS | Responds in Marathi, gives general supportive advice. The doc's ideal asks for honest "my detailed advice is for dogs, please see a vet for cat" — current reply is helpful but does **not** flag the species limitation explicitly. ⚠️ Tone gap. |
| 3. Drives signup | ✅ PASS | Saved successfully. |
| 4. Duplicate signup | ✅ PASS | Idempotent — returns success again, no error. |
| 5. First-aid kit (Marathi) | 📷 MANUAL | |
| 6. Happy update "सगळे कुत्रे छान खेळत होते" | ✅ PASS | Warm Marathi reply, no health warnings. |

### User 6 — Zara (Hyderabad, anxious overthinker)

| Step | Verdict | Notes |
|---|---|---|
| 1. "sleeping a lot" | ✅ PASS | Proportionate, no escalation. |
| 2. Grass eating | ✅ PASS | Reassuring, doesn't connect to step 1. |
| 3. Paw licking | ✅ PASS | Calm, no allergy spiral. |
| 4. "sorry for asking so many questions" | ❌ FAIL | mode=`care` instead of `warm`/`repair`. Reply summarises all three previous worries and ends with **"What to watch at home / When to call a vet"** — exactly the templated clinical ladder the doc warned against. **Real tone failure**: emotional check-in turned into a mini-consultation. |
| 5. Beagle snore | ✅ PASS | Light, accurate, warm. |
| 5.5 Analyze healthy Peanut | 📷 MANUAL | |
| 6. Sign-off | ✅ PASS | Friendly, no "remember to watch for…" tail. |

### User 7 — Kiran (Chennai, cruelty witness)

| Step | Verdict | Notes |
|---|---|---|
| 1. "beating a stray with a stick" | ✅ PASS | scenario=`animal_cruelty_witnessed`, intent=`cruelty_witnessed`, cards = `[cruelty, find_help]` (no emergency card). Routing is exactly what the doc asked for. |
| 1.5 Analyze cowering dog | 📷 MANUAL | |
| 2. "bleeding from head, limping" | ✅ PASS routing — but ⚠️ **card gap**: triage shifted to `mode=emergency / scenario=fracture / urgency=life_threatening`, yet the only card was `Learn: Bleeding & Trauma`. No emergency or find_help card. Looking at `_build_triage_action_cards`, `fracture` is **not** in the `emergency_scenarios` set, so `is_emergency=False` even at `life_threatening` urgency, and the find-help branch only fires on `urgent`/`is_emergency`. Net result: the highest-stakes turn in this run got the lightest card surface. |
| 3. "police never do anything" | ✅ PASS | Validates frustration without dismissing reporting. |
| 4. Cruelty page | 📷 MANUAL | |
| 5. "what law protects street dogs" | ✅ PASS | Names PCA Act 1960 + ABC Rules 2001; mentions AWBI. Real, not hallucinated. |
| 6. Gratitude sign-off | ✅ PASS | Warm close, no medical follow-up. |

## Real product issues, ranked

### Tier 1 — Wrong content / wrong card surface

1. **Ramesh 6 (weak puppy in Hindi) advised giving milk.** Direct contradiction of the doc's "दूध मत दें" guidance. This is a care-content miss, not a routing artefact. Likely needs either: better KB grounding for the `feeding_weak_dog`/`puppy_gi` scenarios, or a tighter Hindi prompt that names the milk anti-pattern.
2. **Priya 6 (anti-vomiting tablet) shows Puppies & Diarrhoea card.** intent=`medicine_question` but scenario_type fell back to `vomiting_diarrhea`, and `_build_triage_action_cards` only routes on `scenario`. Add an intent-aware branch so `medicine_question` surfaces the medicine/poison surface (or no card), not a GI guide.
3. **Kiran 2 (head bleeding + limping) shows only a Learn card, no Find Help / no emergency card.** `fracture` isn't in `emergency_scenarios`, so even at `life_threatening` urgency the card builder does not promote `emergency` / `find_help`. Either widen `emergency_scenarios` to include `fracture` when urgency is life-threatening, or add a generic "if urgency_tier == 'life_threatening' → emergency + find_help" guard.
4. **Zara 4 (emotional validation) routed to care with a clinical ladder.** mode=care produced a "What to watch / When to call a vet" wrap-up — exactly the anti-pattern. Triage should treat short emotional check-ins ("sorry for asking so many questions") as `repair` or `warm`, not `care`.
5. **Priya 8 ("different dog limping") routed to `conversation_repair`.** The heuristic catches `"different dog"` as a topic-redirect phrase, even when the rest of the message is a fresh care report with a clear symptom. Tighten `_is_repair_or_meta_intent` so it doesn't trigger when an active-symptom phrase ("limping badly", "bleeding", "fell", etc.) is present.

### Tier 2 — Over-aggressive cards

6. **Ramesh 5 (chocolate hypothetical) shows the full emergency stack.** `emergency` + `Learn: poison` + `Find Help` for a "can I feed?" question with no exposure. Heuristic correctly flags `poisoning` scenario, but in a *hypothetical/medicine_question* framing the cards should de-escalate. Consider gating emergency cards on "exposure detected in message" cues (e.g. `gave`, `ate`, `swallowed`, `खा ली`, etc.) rather than mention of the substance. (not essential- can document known problem and move on for now)

### Tier 3 — Tone polish (PASS-with-notes)

7. **Sneha 4 over-apologises.** Doc wanted one acknowledging sentence + one open question; got three sentences of reassurance.
8. **Savitri 2 (cat) doesn't flag the species limit.** Reply gives helpful general advice but the doc wanted explicit "my detailed guidance is mostly for dogs."
9. **Triage scenario taxonomy drift** (`gastrointestinal_issue`, `unclear` for clear feeding cases, `healthy_or_low_risk` for plain greetings). Mostly cosmetic today because mode is still right, but it weakens card routing. Consider snapping LLM scenario_type back to the canonical set in `_normalize_result`, or instructing the triage prompt to choose only from the canonical list.

## What worked (worth keeping)

- **Deceased-pet path** activates cleanly (Sneha 1) — no emergency cards, no "is the dog breathing?" prompts.
- **Cruelty routing** (Kiran 1) hit exactly the right card mix: `cruelty` + `find_help`, no `emergency`.
- **Hindi/Marathi output is in Devanagari** (Ramesh, Savitri) and reads as natural, not as a Hindi-substitute Marathi.
- **Topic-jump isolation** worked for Priya 4 (rice-and-curd did not inherit the sleeping-dog context).
- **Mailing-list idempotency** confirmed (Savitri 4 duplicate did not error).
- **Negation handling** held up — Sneha 4 "don't tell me to get another dog" didn't trigger an emergency reroute.
- **`/api/nearby`** returns city listings without requiring GPS (Priya 3.6).

## Surfaces still unverified (browser-only)

These need a manual run on `https://indieaid.vercel.app` because they are UI-shape, not API-shape:

- Home essentials-only IA + More tray (Stage 7).
- Per-image chat threads + thread switcher; analysis banner per thread (Stage 7A).
- Analyze flows on real photos (sleeping dog, healthy Mango, healthy Peanut, cowering distressed dog) — and whether the analyse-to-chat handoff lands in the right thread.
- First-aid kit Marathi rendering, AWBI link on Cruelty page.
- Private-browsing fresh-state behaviour after IndexedDB is cleared.

If a browser test pass is wanted next, ping me and I'll script a Playwright/Chromium walk-through.

## Suggested next moves (concrete, in priority order)

1. Fix the milk-for-weak-puppy answer (Ramesh 6). Either add a `feeding_weak_dog` Hindi/Marathi exemplar that explicitly says "no milk", or extend the medicine/feeding deny-list with milk for weak puppies.
2. In `_build_triage_action_cards`, branch on `triage.intent == "medicine_question"` before the scenario lookup — surface a poison/medicine card (or no card) rather than the scenario-default.
3. Promote `emergency` / `find_help` cards whenever `triage.urgency_tier == "life_threatening"`, regardless of whether `scenario` is in the curated `emergency_scenarios` set.
4. In `_is_repair_or_meta_intent`, skip the "different dog" / "new topic" repair classification when the same message contains an active-symptom token (`limp`, `bleed`, `vomit`, `fell`, `hit`, etc.).
5. In triage, treat short apology / "sorry I'm anxious" / "thanks" turns with no symptom mention as `warm` or `repair`, never `care`.
6. Snap LLM-emitted `scenario_type` to the canonical list in `_normalize_result`; map common drifts (`gastrointestinal_issue` → `vomiting_diarrhea`, etc.).
7. Gate the `poisoning` emergency card on exposure cues; on a hypothetical "can I feed X?" question, drop to a `learn` card only.

Each of these is a small, scoped fix and should ship with a test in `backend/tests/test_triage_router.py` covering the *pattern* rather than the exact message — per the doc's "fix patterns, not cases" note.
