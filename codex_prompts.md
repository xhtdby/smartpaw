# Codex Prompts — IndieAid Remaining Development

Run these **in order**. Each prompt assumes the previous one was committed. Do not skip ahead — the ordering minimises rework (medicine entries need species fields, quizzes need cat/cow topics, persistence needs all schemas stable).

> [!IMPORTANT]
> After each Codex run, **review the diff yourself** before committing. Check that fixes address patterns, not just the specific test cases mentioned. If a fix uses `if message.contains("specific phrase")` instead of a general heuristic, reject it.

---

## Prompt 0 — Antagonistic Test Fixes

```
Read these files before starting:
- PLAN.md (§3 operating rules, §7 scope controls)
- docs/indieaid-working-context.md (current risks, active task queue)
- docs/antagonistic_report.md (the 7 failures to fix)
- docs/antagonistic_testing.md (§ Codex Implementation Guidelines — read section 1 "Fix Patterns, Not Cases" carefully)
- backend/app/services/triage.py
- backend/app/routers/chat.py
- backend/tests/test_triage_router.py

Fix the 5 Tier-1 product issues from docs/antagonistic_report.md. The fixes must be PATTERN-LEVEL, not message-specific. Here is what to fix and how:

1. In `_build_triage_action_cards` in chat.py: branch on `triage.intent == "medicine_question"` BEFORE the scenario-driven card map. Surface the poison/medicine learn card, not the scenario-default card. This fixes Priya step 6 (anti-vomiting tablet showing "Puppies & Diarrhoea" card).

2. Add a guard in `_build_triage_action_cards`: if `urgency_tier == "life_threatening"`, always include `emergency` + `find_help` cards regardless of whether `scenario_type` is in the curated `emergency_scenarios` set. This fixes Kiran step 2 (head bleeding + fracture got only a Learn card).

3. In `_is_repair_or_meta_intent` in triage.py: short-circuit to False when the same message contains an active-symptom token (limp, bleed, vomit, fell, hit, not breathing, fracture, seizure). This fixes Priya step 8 ("different dog limping badly" classified as repair).

4. In `_normalize_result` in triage.py: snap LLM-emitted `scenario_type` to the canonical set. Map known drifts: `gastrointestinal_issue` → `vomiting_diarrhea`, free-form `unclear` when heuristic already matched → keep the heuristic match. This fixes the scenario taxonomy drift (Tier 3 item 9).

5. In triage.py: treat short emotional turns ("sorry for asking", "thanks", "sorry I'm anxious") that contain no symptom tokens as `warm` or `repair`, never `care`. This fixes Zara step 4 (emotional check-in routed to care with a clinical ladder).

For each fix, add a PATTERN test in backend/tests/test_triage_router.py. The test must use a PARAPHRASE of the antagonistic message, not the exact message. For example, don't test "sorry for asking so many questions" — test "I feel bad for bothering you" to prove the pattern works generally.

Do NOT fix Tier 2 item 6 (chocolate hypothetical over-carding) — document it as a known issue in docs/indieaid-working-context.md instead.

Run `cd backend && pytest` before and after. All existing tests must stay green.
Branch: `triage-fixes-from-antagonistic`
```

---

## Prompt 1 — Stage 7F: Medicine KB

```
Read these files before starting:
- PLAN.md §7F (Medicine Guidance & Safer-Alternative Counters) — this is the authoritative spec
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Step 1" section AND "Schema Drafts" section (has a concrete medicine_kb.json sample entry for paracetamol)
- docs/antagonistic_report.md — Ramesh step 6 (milk-for-weak-puppy) and Priya step 6 (wrong card on medicine)
- backend/app/services/triage.py (existing medicine_question intent, deny-list patterns)
- backend/app/routers/chat.py (existing _PROMPT_CARE, _build_triage_action_cards)
- backend/app/models/schemas.py (AnalysisResponse)
- backend/app/routers/analyze.py

Implement Stage 7F: Medicine KB-backed chat and image surfacing.

Deliverables:
1. Create `backend/data/medicine_kb.json`. Use the schema from the plan's Schema Drafts section. First entries (minimum 10): paracetamol, ibuprofen, aspirin, ORS/electrolyte rehydration, diluted povidone-iodine (Betadine), chocolate, grapes/raisins, xylitol, milk-for-weak-puppy, kerosene/turpentine. Every entry must have a `sources[]` array with real veterinary URLs (Merck Vet Manual, Cornell, FDA, DAHD). Do NOT invent sources.

2. Add `_PROMPT_MEDICINE` in chat.py — a mode-specific prompt for medicine questions that loads the matched KB entry into context and explicitly forbids inventing doses. If no KB match, defer to a vet.

3. Expand the hardcoded deny-list in triage.py for: paracetamol→cat, ibuprofen→dog/cat, aspirin→cat, chocolate, grapes, xylitol, onion, garlic, milk-for-neonatal-puppy. These must work WITHOUT an API key.

4. Add `otc_suggestion: Optional[dict]` to AnalysisResponse in schemas.py. In analyze.py, when analysis surfaces a treatable condition that matches a `home_use_ok: true` KB entry, include the OTC suggestion. Keep it simple — a dict with `name`, `guidance`, `source_url`.

5. Frontend: add a `MedicineCallout` component that renders distinctly from normal chat bubbles, carrying a source citation line. Use it in the chat page when the response includes medicine KB data. Keep it minimal — a colored callout box with an icon, not a full redesign.

6. Tests in `backend/tests/test_medicine_kb.py` (new file):
   - Deny-list works without API key (paracetamol for cat → refusal)
   - Safe OTC query returns KB-grounded text with citation
   - KB JSON schema validation (every entry has required fields + valid source URLs)
   - Medicine intent routes to _PROMPT_MEDICINE, not _PROMPT_CARE

All medicine KB content must be in English. Hindi/Marathi translations of the KB entries are static and authored now — do not rely on LLM translation for safety-critical content. Chat responses in Hindi/Marathi are still LLM-generated (already works via language detection).

Run `cd backend && pytest` and `cd frontend && npm run build`. Branch: `revive-medicine-kb`
```

---

## Prompt 2 — Stage 7E: Multi-Species

```
Read these files before starting:
- PLAN.md §7E (Multi-Species Support)
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Step 2" section AND "Schema Drafts → Cat and cow emergency kernels" (lists the 5 high-confidence emergencies per species with sources)
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Multilingual Implementation Notes" (Hindi/Marathi species terms for triage regex)
- backend/app/services/triage.py
- backend/app/models/schemas.py
- backend/app/routers/analyze.py
- backend/app/routers/chat.py
- backend/data/help_resources.json
- backend/data/medicine_kb.json (just created in previous step — medicine entries already have species_safe/species_unsafe)

Implement Stage 7E: Multi-species support for cats, cows, and a general-animal fallback.

Deliverables:
1. Add `species: Literal["dog", "cat", "cow", "other"] = "dog"` to TriageResult, AnalysisResponse, and AnalysisContext in schemas.py. Default "dog" keeps all existing tests green.

2. Vision species detection: in analyze.py, add a species-detection step to the vision prompt. This is an LLM-only step (no new model dependency). If species is "other", use a conservative general-animal prompt that describes what is observed and defers strongly to a vet. Do NOT reuse dog emergency kernels for unknown species.

3. Triage: add cat and cow emergency kernels to triage.py. ONLY the high-confidence ones from the plan:
   - Cat: not breathing/collapse, urinary blockage, poisoning (lily/paracetamol/antifreeze), seizure, heavy bleeding/road trauma
   - Cow: bloat, dystocia, haemorrhagic septicaemia, fracture/road trauma, snakebite
   All other cat/cow situations → care mode with strong vet deferral. "other" species → care/repair only, zero species-specific emergency claims.

4. Add Hindi/Marathi species terms to triage heuristic patterns: मांजर, बिल्ली, गाय, गोवंश, मांजरी (and their common variations). These must be in the regex so Hindi/Marathi species mentions are detected.

5. Add `species` filter to entries in help_resources.json. Seed with: 2-3 cat clinics (major cities), livestock helplines (state-level), DAHD national helpline. Mark existing entries as `species: ["dog"]` or `species: ["dog", "cat"]` as appropriate.

6. Update Learn page (frontend/src/app/learn/page.tsx) so cat-specific and cow-specific entries appear. Do NOT rewrite or remove existing dog content — this is additive.

7. Tests in backend/tests/test_species_routing.py (new):
   - Cat message → species="cat", cat emergency kernels fire correctly
   - Cow injury → species="cow", livestock contacts surfaced
   - Unknown species → species="other", general deferral text, NO dog-specific emergency claims
   - Hindi "मेरी बिल्ली बीमार है" → species="cat"
   - Dog messages still work exactly as before (regression check)

CRITICAL: multi-species routing must be ADDITIVE. Do not restructure the existing dog logic. Dog pathways are proven — treat cat/cow as plugins that extend, not replace.

Run `cd backend && pytest` and `cd frontend && npm run build`. Branch: `revive-multi-species`
```

---

## Prompt 3 — Stage 7D: Quizzes

```
Read these files before starting:
- PLAN.md §7D (Learn Mode Quizzes)
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Step 3" section AND "Schema Drafts → Sample learn_quizzes.json" (has a concrete trilingual example entry)
- frontend/src/app/learn/page.tsx (current Learn page)
- frontend/src/app/first-aid-kit/page.tsx (current first-aid kit page)
- backend/app/routers/chat.py (look at _GUIDE_LABELS for the canonical guide IDs)

Implement Stage 7D: Learn mode quizzes.

Deliverables:
1. Create `backend/data/learn_quizzes.json`. Use the trilingual schema from the plan's Schema Drafts. Keys match `_GUIDE_LABELS` guide IDs + first-aid-kit topic IDs. 3-5 MCQ items per topic. Each item has `q`, `options`, `correct_index`, `explanation` — all with `en`, `hi`, `mr` sub-keys. Cover at minimum: approach, trauma, heat, poison, skin, puppies, bleeding, wound_cleaning, dehydration. Include at least one cat-specific and one cow-specific question (Stage 7E is now done).

2. Create a React `<Quiz />` component. Requirements:
   - Takes a topic ID, loads questions from a static JSON import or API fetch
   - No scoreboard, no telemetry, no persistent state
   - Shows one question at a time, reveals explanation on answer
   - Respects the current language setting (reads from the language context)
   - Feels conversational and encouraging, not like an exam
   - On wrong answer: shows the static explanation. If GROQ_API_KEY is available (check via an optional API call), may regenerate a fresh encouraging explanation grounded in the static one. Falls back to static on any failure. The LLM NEVER decides correctness.

3. Embed the Quiz component under each Learn guide on the Learn page and on each first-aid-kit topic page.

4. Tests:
   - JSON schema validation (every entry has required fields, all 3 languages, correct_index in range)
   - Frontend: `npm run build` succeeds
   - Static-only quiz path works when API key is absent (test by verifying the component renders explanations without any API call)

Do NOT add: scoreboards, progress tracking, telemetry, share buttons, or gamification. This is a learning tool, not a quiz app.

Run `cd frontend && npm run build`. Branch: `revive-quizzes`
```

---

## Prompt 4 — Stage 8: Railway Durability

```
Read these files before starting:
- PLAN.md §Stage 8 (Report and Production Durability)
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Step 4" section
- backend/app/config.py (look at _default_persistent_root and how db_path/uploads_dir resolve)
- backend/app/database.py (current tables, migration pattern)
- backend/app/main.py (existing /health endpoint)
- backend/railway.json
- docs/indieaid-working-context.md (Railway volume note from April 30)

Implement Stage 8: Railway durability verification.

Deliverables:
1. In railway.json: add a `volumes` block declaring the `/app/data` mount so the volume config lives in code, not just the Railway UI dashboard.

2. Extend the `/health` endpoint in main.py to return:
   ```json
   {
     "status": "ok",
     "db_path": "/app/data/indieaid.db",
     "uploads_dir": "/app/data/uploads",
     "db_exists": true,
     "db_writable": true,
     "uploads_writable": true
   }
   ```
   Do NOT leak secrets, API keys, or internal paths beyond the data directory. This is a diagnostic endpoint for verifying the volume mount in production.

3. Add a pytest in backend/tests/test_durability.py:
   - Create a report via the community router, verify it persists in the DB
   - Simulate an app restart (re-call init_db), verify the row is still there
   - Reuse the tmp_path pattern from test_community_drives.py

4. Update docs/indieaid-working-context.md: add a note under Discovered Issues Log confirming whether /health returns writable=true on the deployed Railway URL (if you have access) or mark it as "needs manual verification on deploy".

This is a small stage. Do NOT add Litestream, database migrations, or new tables here — those belong to Stage 7H.

Run `cd backend && pytest`. Branch: `revive-report-durability`
```

---

## Prompt 5 — Stage 7H: Login + Persistence + DB Expansion

```
Read these files before starting:
- PLAN.md §7H (Login, IP-Based Anonymous Persistence, & Database Expansion) — read this FULLY, it is 30 lines of detailed requirements
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Step 5" section (has auth architecture decision, two-tier persistence table, DPDP compliance notes, login/no-login boundary)
- backend/app/database.py (existing migration pattern)
- backend/app/config.py
- backend/app/routers/community_drives.py (existing IP rate-limiting pattern + SMTP setup to reuse)
- frontend/src/app/settings/page.tsx
- frontend/src/app/chat/page.tsx (IndexedDB thread storage from Stage 7A)

Implement Stage 7H: Login, IP-keyed anonymous persistence, and database expansion.

HARD CONSTRAINT: Nothing on the home essentials path (Chat, Analyze, Find Help, First-Aid Kit, Cruelty, Learn, basic Drives subscribe) may require login. Login is a button in Settings, never a wall on essentials.

Deliverables:

1. Database expansion in database.py — add tables using existing CREATE TABLE IF NOT EXISTS pattern:
   - `users(id, email, email_verified_at, created_at)`
   - `chat_threads(id, user_id NULLABLE, thread_kind, image_id NULLABLE, created_at, last_used_at)`
   - `chat_messages(id, thread_id, role, content, created_at)`
   - `image_records(id, user_id NULLABLE, analysis_status, analysis_context_json, created_at)`
   - `anonymous_sessions(hashed_key TEXT PRIMARY KEY, thread_blob TEXT, created_at, expires_at)`
   - Add nullable `user_id` and `verified BOOLEAN DEFAULT FALSE` columns to `reports` table

2. Auth router — new file `backend/app/routers/auth.py`:
   - `POST /api/auth/magic-link` — accepts email, generates a signed token (use `itsdangerous` URLSafeTimedSerializer), stores in users table, returns success. For now, log the magic link URL to console instead of actually sending email — SMTP integration can be wired later with Resend.
   - `GET /api/auth/verify?token=...` — verifies the signed token, sets email_verified_at, returns a session JWT
   - `POST /api/auth/logout` — invalidates session
   - Middleware: extract and verify JWT from Authorization header on protected routes only

3. Anonymous IP-keyed persistence:
   - Hash: `sha256(client_ip + coarse_ua_family)` — never store raw IP
   - Store thread_blob (JSON of thread IDs + messages) in anonymous_sessions with 30-day expiry
   - New endpoints: `GET /api/anonymous/threads` (returns threads for hashed key), `POST /api/anonymous/threads` (saves)
   - Auto-cleanup: delete expired sessions on app startup via init_db

4. Frontend:
   - Settings page: add "Sign in with email" button and magic-link flow UI
   - Chat page: sync threads to server when logged in, IP-cache when anonymous, IndexedDB always (three-tier: IndexedDB primary, server sync secondary, IP-cache fallback)
   - On first login: explicit consent screen — "Import this device's chat history into your account?" with Yes/No. No silent upload.
   - Consent banner on first anonymous chat: "We save your chat using your network info so you don't lose it. It expires in 30 days. Only you can see it."

5. Tests in backend/tests/test_auth.py:
   - Magic-link generation + verification round-trip
   - Expired token rejection
   - Anonymous IP-cache: save and retrieve with same hash
   - Anonymous IP-cache: different hash returns nothing (no leakage)
   - Essentials endpoints (chat, analyze, nearby) accessible without auth header
   - Protected endpoints (verified reports) require auth

Do NOT build: forums, social features, phone verification, Resend email integration (just console-log the link for now), or verified-report UI. Those come after Stage 9.

Run `cd backend && pytest` and `cd frontend && npm run build`. Branch: `revive-login-and-db`
```

---

## Prompt 6 — Stage 9: E2E Verification

```
Read these files before starting:
- PLAN.md §Stage 9 (End-to-End Human Verification) — has the 12-item test matrix
- .claude/plans/plan-strategy-and-find-tidy-parnas.md — "Step 6" section
- docs/antagonistic_testing.md (7 personas with interaction sequences)
- docs/antagonistic_report.md (the 7 failures — verify they are now fixed)
- frontend/package.json

Implement Stage 9: E2E browser verification with Playwright.

Deliverables:

1. Add `@playwright/test` to frontend devDependencies. Create `frontend/playwright.config.ts` targeting Chromium + WebKit + Firefox. Configure to run against `http://localhost:3000` (dev server).

2. Create `frontend/e2e/` directory with test files:
   - `home.spec.ts` — home screen shows only essentials (Chat, Analyze, Find Help, emergency CTA); secondary items in More tray; no login gate
   - `chat-warm.spec.ts` — Arjun's warm-mode session: greeting → breed chat → no emergency cards across 3+ turns
   - `chat-care.spec.ts` — Priya's care session: panic opener → sleeping dog de-escalation → topic jump to feeding
   - `chat-emergency.spec.ts` — Kiran's cruelty→medical transition: cruelty report → bleeding report → verify emergency + find_help cards appear
   - `analyze.spec.ts` — upload a test image, verify analysis response renders, verify thread is created
   - `language.spec.ts` — switch to Hindi, send a message, verify Devanagari response; switch to Marathi, verify Marathi response
   - `drives.spec.ts` — navigate to drives, subscribe with email, verify success; duplicate subscribe, verify no error
   - `quiz.spec.ts` — navigate to Learn, open a quiz, answer a question, verify explanation renders
   - `first-aid-kit.spec.ts` — browse first-aid kit topics, verify content renders in selected language
   - `no-api-key.spec.ts` — with backend running but GROQ_API_KEY unset, verify warm/care fallbacks still work (no raw errors)
   - `thread-isolation.spec.ts` — create two chat threads, verify messages don't leak between them

3. GitHub Actions CI — create `.github/workflows/ci.yml`:
   - Trigger: on PR to main
   - Jobs: (a) `cd backend && pytest`, (b) `cd frontend && npm run build`, (c) `npx playwright test --project=chromium` (Chromium only on PRs)
   - On push to main: run full matrix (Chromium + WebKit + Firefox)
   - Upload Playwright trace on failure as artifact

4. Clean up:
   - Verify all 7 antagonistic test failures from docs/antagonistic_report.md are now fixed by running the relevant E2E tests
   - Update docs/indieaid-working-context.md with a final Stage 9 note

5. Do NOT skip: run `npx playwright test` locally and confirm it passes before committing.

Branch: `revive-e2e-polish`
```

---

## After All 7 Prompts

Once all stages are committed and merged:

1. **Regenerate the antagonistic testing doc** using the prompt in the Gemini artifacts at `regeneration_prompt.md` — it covers how to expand the testing doc to include all 6 new features at full depth.

2. **Manual verification pass**: walk through the app yourself in English, Hindi, and Marathi. The E2E tests cover structure but not *feel* — only a human can judge whether the app feels warm vs clinical.

3. **Update PLAN.md progress line** (line 1) to reflect all stages complete.
