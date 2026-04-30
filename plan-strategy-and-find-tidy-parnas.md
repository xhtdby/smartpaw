# Plan — Strategy + resources for the unfinished IndieAid stages

## Context

`PLAN.md` declares Stages 7D (quizzes), 7E (multi-species), 7F (sourced medicine KB), 7H (login + IP-keyed anonymous persistence + DB expansion), 8 (Railway durability), and 9 (E2E verification) as outstanding. Antagonistic-test results in `artifacts/antagonistic_report.md` already surfaced linked gaps (medicine card routing, milk-for-weak-puppy advice, life-threatening fracture not promoting Find Help). This plan answers two asks: **(a) the strategy and order to finish those stages**, and **(b) a curated list of resources sorted into three separate categories — creative, open source, trustworthy.**

---

## Product philosophy to preserve while building

The implementation plan below assumes IndieAid is **warm and helpful at all costs**: it should feel like a capable friend who knows first aid, not like a cold symptom form. This does not mean being permissive with unsafe actions. It means every refusal, emergency escalation, privacy notice, quiz correction, and error state must leave the user with a concrete next step and a feeling that the app stayed with them.

Practical rules for every remaining stage:

- **Friend first, then structure**: start with a human acknowledgement when the user is scared, guilty, confused, or apologetic. Then give the safest action. Avoid clinical ladders for emotional check-ins with no active symptom.
- **Never dead-end a user**: if a medicine is unsafe, name a safer alternative or the exact information to gather for a vet; if a source is uncertain, say what can be done safely while waiting.
- **No scolding**: use "don't give cow milk here; keep warm and offer tiny safe amounts only if alert" instead of "you should not have done that."
- **Urgency without panic**: emergencies should be direct and locked-in, but still companionable: "This is serious. Do this now."
- **Privacy copy is care copy**: login, anonymous persistence, IP hashing, and consent screens should explain benefits plainly, not sound like legal boilerplate.
- **Multilingual warmth is part of safety**: Hindi and Marathi copy must be natural and reassuring, not stiff translations of English. Code-mixed messages should still route to canonical safety fields.
- **Clinical claims need sources; tone needs taste**: source every medical/medicine claim, but do not let citation-heavy prose crowd out concise help in the UI.

---

## Research method and source hierarchy

Use this hierarchy when implementing new content:

1. **Primary clinical / legal / platform sources**: official veterinary manuals, FDA/Cornell/AVMA, Indian DAHD/AWBI/eGazette, Railway/Playwright/Better Auth/Resend docs.
2. **Secondary practical sources**: established NGOs and animal-welfare guides, used for user-facing steps and local reporting workflow, not for drug dosing.
3. **Creative/test sources**: datasets, directories, and tone references. These can shape evaluation, UX, or discovery, but must not create clinical claims.

Each user-facing medical content file should track `source_url`, `accessed_on`, and a short `claim_scope` ("toxin deny-list", "cat emergency", "first-aid kit item", etc.). A source can justify only the claim it actually supports.

---

## Current ground truth (from Phase-1 code exploration)

| Stage | Exists | Missing |
|---|---|---|
| 7D quizzes | 12 first-aid kit topic IDs in [first-aid-kit/page.tsx](frontend/src/app/first-aid-kit/page.tsx); 6 Learn guide IDs in `_GUIDE_LABELS` at [chat.py:250-257](backend/app/routers/chat.py#L250-L257) | `backend/data/learn_quizzes.json`, frontend Quiz component, LLM-fresh feedback hook |
| 7E multi-species | Nothing | `species` field in `TriageResult`, `AnalysisResponse`, `AnalysisContext`; vision species step; cat/cow KB entries; species filter in `help_resources.json`; species tests |
| 7F medicine KB | Triage already routes `intent=medicine_question` → scenario `unsafe_medicine` ([triage.py:493-504](backend/app/services/triage.py#L493-L504)); poison-card path in [chat.py:319-330](backend/app/routers/chat.py#L319-L330) | `backend/data/medicine_kb.json`, `_PROMPT_MEDICINE`, `AnalysisResponse.otc_suggestion`, image-analyser OTC emission, frontend citation callout, expanded deny-list |
| 7H login + IP cache | aiosqlite migration pattern in [database.py:40-78](backend/app/database.py); IP-based rate-limit dict in [community_drives.py](backend/app/routers/community_drives.py) | `users` / `chat_threads` / `chat_messages` / `image_records` / `anonymous_sessions` tables; magic-link flow + SMTP; auth router; consent screen; thread-sync endpoints |
| 8 Railway durability | `_default_persistent_root()` auto-detects `/app/data` in [config.py:7-14](backend/app/config.py); legacy `smartpaw.db` migration in [database.py:19-29](backend/app/database.py) | volume mount declared in `railway.json`, diagnostic endpoint reporting resolved paths, durability proof note |
| 9 E2E | 7 backend pytest files in `backend/tests/` covering modes/cards/triage; root-level `test_*.py` files are 0-byte stubs | Frontend E2E framework (no Playwright/Cypress in `package.json`), GitHub Actions CI, production smoke test |

---

## Strategy — recommended order

The order minimises rework and respects the doc's "small, push-safe stages" rule. Each stage stays branchable per `PLAN.md §8`.

### Step 0 — Antagonistic-test fixes first (completed 2026-04-30; branch `triage-fixes-from-antagonistic`)

This has now landed before the remaining stages, so future work should build on the fixed routing/card behavior rather than re-solving these issues. The core principle from this pass is still important: fix routing **patterns**, not individual adversarial messages. From `artifacts/antagonistic_report.md`:

1. In [chat.py `_build_triage_action_cards`](backend/app/routers/chat.py#L278-L359), branch on `triage.intent == "medicine_question"` **before** the scenario-driven card map. Surface `Learn: Poisoning` (or a new `medicine_basics` card once 7C kit ID is wired through `_GUIDE_LABELS`) instead of `Learn: Puppies & Diarrhoea`.
2. Promote `find_help` (and `emergency` when life-threatening) whenever `urgency_tier == "life_threatening"`, regardless of whether scenario is in the curated `emergency_scenarios` set. Fixes Kiran step 2.
3. In [triage.py `_is_repair_or_meta_intent`](backend/app/services/triage.py#L226-L259), short-circuit to `False` when the same message contains an active-symptom token (`limp`, `bleed`, `vomit`, `fell`, `hit`, `not breathing`).
4. In `_normalize_result`, snap LLM `scenario_type` back to the canonical set; map known drifts (`gastrointestinal_issue` → `vomiting_diarrhea`, free-form `unclear` overriding a heuristic match → keep heuristic).
5. Gate the chocolate/poisoning emergency card on exposure cues (`gave|ate|swallowed|खा ली|खाया`); on hypothetical "can I feed?" questions drop to a `learn` card only.
6. Treat short emotional turns ("sorry for asking", "thanks") with no symptom mention as `warm`/`repair`, never `care`. Tightens Zara 4.

Implemented pattern tests live in [test_triage_router.py](backend/tests/test_triage_router.py). Keep these as regression anchors for Stage 7F/7E changes, because medicine KB and multi-species routing will otherwise be tempted to reintroduce over-specific phrase matching.

### Step 1 — Stage 7F medicine KB (~2 days, `revive-medicine-kb`)

Sequenced before quizzes because (a) the antagonistic report flagged real medicine errors (milk to weak puppy, wrong card on anti-vomit tablet) and (b) the kit screen already references medicine basics — KB grounds it.

**Research upgrade for this stage**:

- Source the toxin/unsafe-medicine deny-list from high-authority pages first: FDA's pet-danger list explicitly flags human medicines, NSAIDs, acetaminophen, onions, grapes/raisins, chocolate, and xylitol; Merck's analgesic toxicosis page covers acetaminophen/ibuprofen risks and xylitol-containing formulations; Cornell's cat hazards page adds cat-specific toxin framing.
- Treat weak-puppy milk guidance as a first-aid feeding claim, not just a toxin claim. It belongs in `medicine_kb.json` only if the schema can mark it as `claim_type: "feeding_first_aid"` or similar; otherwise it should live in the first-aid KB with a citation and be linked by medicine chat.
- The friend-first behavior for medicine asks is: **answer the fear, block the unsafe action, offer a safe substitute, and ask only the facts needed for escalation**. Example shape: "Don't give Crocin. Keep them quiet and note the tablet strength, amount, and time; call a vet/poison service with those details."
- Every medicine entry should have `home_use_ok`, `requires_vet`, `dose_guidance`, `safer_alternatives`, `red_flags`, `source_url`, `accessed_on`, and `source_claim`. Do not let a general toxin page justify a dose.
- For Hindi/Marathi, store safety-critical medicine names and "do not give" copy statically where feasible. Let the LLM add warmth and phrasing, not decide the safety claim.

- Create `backend/data/medicine_kb.json` with the schema in `PLAN.md §7F` (species_safe/unsafe, home_use_ok, dose_guidance, sources). First entries: ORS rehydration, diluted povidone-iodine, paracetamol, ibuprofen, aspirin, chocolate, grapes/raisins, xylitol, milk-to-puppy, kerosene/turpentine. Each entry cites a vet source (see Resources below).
- Add `_PROMPT_MEDICINE` in [chat.py](backend/app/routers/chat.py) that loads the matched KB entry into context and forbids invented doses.
- Hardcoded deny-list expansion in [triage.py](backend/app/services/triage.py) for paracetamol-cat, ibuprofen-dog/cat, chocolate, grapes, xylitol, onion, garlic — works without API key.
- Extend `AnalysisResponse` in [schemas.py](backend/app/models/schemas.py) with `otc_suggestion: Optional[OTCEntry]` and emit it from [analyze.py](backend/app/routers/analyze.py) when KB matches the analysis condition.
- Frontend: distinct `MedicineCallout` React component carrying source citation; render in chat and on Analyze page.
- Tests: deny-list works without key; safe-OTC returns KB-grounded text + citation; image OTC emitted on a matching analysis fixture.

### Step 2 — Stage 7E multi-species (~2-3 days, `revive-multi-species`)

After 7F because medicine entries already need `species_safe[]` / `species_unsafe[]` (cleanly extends to cat/cow once species exists).

**Research upgrade for this stage**:

- Cat kernels should be narrower than dog kernels. Cornell and FDA support treating lilies and acetaminophen as cat-specific urgent poison hazards; Cornell supports urinary obstruction as a true emergency. Do not generalize dog-safe advice to cats.
- Cow/livestock kernels should lean on DAHD/FAO's 2024 Standard Veterinary Treatment Guidelines for India-specific disease/treatment context and Merck for bloat/snakebite emergency framing. Cow guidance should mostly be "keep safe, do not move, call livestock/veterinary help" rather than home treatment.
- The `other` species fallback should be emotionally warm and epistemically strict: "I can't safely identify species-specific first aid from this. Keep them safe, avoid feeding/medicating, and contact a vet/rescue."
- Resources must have `species` and `resource_type` (`clinic`, `livestock_helpline`, `rescue`, `cruelty_reporting`) so a cow injury does not surface dog-only NGOs as the primary action.
- Add a test fixture note for each species test: source of image/message, what label is trusted, and what is intentionally *not* being asserted (for example, do not assert fracture from an unverified internet photo).

- Add `species: Literal["dog", "cat", "cow", "other"] = "dog"` to `TriageResult`, `AnalysisResponse`, `AnalysisContext` (defaulting to dog keeps current tests green).
- Vision: small species-detection step in [analyze.py](backend/app/routers/analyze.py) (LLM-only; no new model dependency). On `species == "other"` swap to the conservative general-animal prompt.
- Add narrow cat + cow emergency kernels to [triage.py](backend/app/services/triage.py) (only the ones with high-confidence guidance; no aggressive dog-emergency reuse).
- Add `species` filter to entries in [help_resources.json](backend/data/help_resources.json); seed cat clinics + livestock helplines.
- Update Learn guides (e.g. `frontend/src/app/learn/page.tsx`) so cat/cow entries appear without rewriting dog content.
- Tests: cat photo isn't classified as dog; cow injury → livestock contacts; unknown species → general-deferral text.

### Step 3 — Stage 7D quizzes (~1.5 days, `revive-quizzes`)

After 7E so quiz IDs can include cat/cow topics from day one (no later migration).

**Research and tone upgrade for this stage**:

- Quizzes should teach safe reflexes, not test obedience. Each wrong-answer explanation should start with reassurance ("That is an easy mistake") and then correct the action.
- Each distractor should represent a real unsafe myth already present in the KB or adversarial tests: milk for weak puppies, human painkillers, kerosene on wounds, forcing water, moving fractures, waiting on lilies/cat poisons.
- The canonical source for a quiz item is the same KB entry or first-aid article that renders on the page. Store `source_entry_id` per question so future content audits can trace every explanation.
- Keep questions short for mobile and for Hindi/Marathi. Avoid "all of the above" because translated option logic gets brittle.
- LLM-fresh feedback may soften tone, but it must quote the static `correct_index` and `explanation` as immutable inputs.

- `backend/data/learn_quizzes.json` keyed by guide_id (reuses `_GUIDE_LABELS` keys + first-aid-kit topic IDs). 3-5 MCQs per topic, each with `{q, options, correct_index, explanation}` blocks for `en` / `hi` / `mr`.
- React `<Quiz />` component, no scoreboard, no telemetry. State local. Embed under each Learn guide and first-aid-kit topic.
- Optional LLM-fresh feedback path: when key present + answer wrong, regenerate explanation grounded in the static answer; never decides correctness.
- Tests: JSON shape validation; static-only path works; LLM-fresh path is gated on `groq_api_key`.

### Step 4 — Stage 8 durability (~½ day, `revive-report-durability`)

Cheap and unblocks Stage 7H. Most logic already landed in commit `5bf0122`.

**Research upgrade for this stage**:

- Railway's current volume docs describe volumes as persistent service storage and expose a mount-path concept (`RAILWAY_VOLUME_MOUNT_PATH`). The app should not assume `/app/data` blindly if Railway provides a different mount path; prefer env-configured paths, with `/app/data` as the known deployment convention.
- `/health` should answer the question a scared operator has at 2am: "Will reports and uploaded images survive a restart?" It should report resolved data paths and writability, but never API keys, database contents, emails, or user identifiers.
- If production cannot prove writable durable storage, the friendly behavior is to downgrade persistence claims in the UI. Do not tell users "saved" when the deployment cannot keep data.

- Add a `volumes` block to [railway.json](backend/railway.json) so the `/app/data` mount is declared in code, not Railway UI only.
- Extend `/health` in [main.py](backend/app/main.py) to return `{ db_path, uploads_dir, db_writable, uploads_writable }` so smoke tests can assert on durability without leaking secrets.
- Add a one-shot pytest that creates a report, restarts the in-process app, and verifies the row survives — reuses `tmp_path` plumbing from [test_community_drives.py](backend/tests/test_community_drives.py).
- Optional: Litestream sidecar config (see Resources) — *only* if the Railway volume turns out to be ephemeral on the current plan. Skip otherwise.

### Step 5 — Stage 7H login + IP-keyed cache + DB expansion (~3-4 days, `revive-login-and-db`)

Hardest stage; goes last so all schemas (medicine, species, quizzes) are stable before tables ship. Hard rule from `PLAN.md §3`: essentials must stay login-free.

**Auth architecture decision**: Better Auth / NextAuth runs on the Next.js side for the magic-link flow (send email → verify click → issue session cookie). FastAPI does NOT run its own auth server. Instead, FastAPI receives a signed JWT (via `itsdangerous` or a shared HMAC secret) in the `Authorization` header and verifies it. This keeps Python-side auth to ~50 lines of middleware, not a full auth framework.

**SMTP provider**: Resend (free tier: 100 emails/day) or Railway SMTP addon. Same channel that 7G mailing-list will eventually use for unsubscribe links.

**Research and privacy upgrade for this stage**:

- Better Auth's magic-link plugin supports `signIn.magicLink` and a `sendMagicLink` callback; its docs also expose token storage options. Use hashed magic-link tokens, short TTLs, neutral responses ("If that email can sign in, we sent a link"), and rate limits. Do not store magic-link tokens in plain text.
- Resend's current free account limits are 100 transactional emails/day and 3,000/month, which is enough for early magic links but not enough for public launch spikes. Add an env-driven provider interface so the app can swap SMTP later.
- The DPDP Act's official Gazette text requires notice for personal-data processing and consent that is free, specific, informed, unambiguous, and limited to necessary data. It also says notices should be available in English or an Eighth Schedule language. For IndieAid, that means the anonymous persistence notice must exist in English, Hindi, and Marathi at minimum.
- Treat IP-keyed persistence as a trust-sensitive feature, not a clever cache. The consent copy should explain benefit first ("so you don't lose rescue context"), then retention, then clear/delete controls.
- Do not let login become emotionally punitive. If a user hits a login-gated community action, the UI should say what remains available without login and return them to the rescue task.

**Two-tier persistence (per PLAN.md §7H)**:

| Tier | Who | What's stored server-side | Disclosure |
|---|---|---|---|
| Logged-in | Email-verified user | Full sync: threads, messages, images, report ownership, verified-report endorsements | Standard account terms |
| Anonymous | IP-keyed fallback | `anonymous_sessions(hashed_ip_ua, thread_blob, expires_at)` — 30-day expiry | Consent banner on first chat message: "We save your chat on our server using your network info so you don't lose it. It expires in 30 days. Nobody else can see it." |

**What requires login** (per PLAN.md): forum/community surfaces, endorsing or filing verified reports, replying to other users, advanced drive coordination. **What never requires login**: Chat, Analyze, Find Help, First-Aid Kit, Cruelty page, Learn, basic Drives subscribe.

- Add tables `users`, `chat_threads`, `chat_messages`, `image_records`, `anonymous_sessions` in [database.py](backend/app/database.py) using the existing `CREATE TABLE IF NOT EXISTS` pattern.
- New router `backend/app/routers/auth.py`. Endpoints: `POST /api/auth/magic-link`, `GET /api/auth/verify`, `POST /api/auth/logout`.
- IP hashing: `sha256(client_ip + coarse_ua_family)` — no raw IP stored. Compliant with DPDP Act 2023 "data minimisation" principle. `anonymous_sessions.hashed_key` column is NOT reversible to IP.
- Frontend: settings page gains "Sign in with email" button. On first login: explicit consent screen ("Import this device's chat history into your account?"). No silent upload.
- Reports: add nullable `user_id` and `verified` columns. Verified-report eligibility: email confirmed + account age ≥ 7 days. Phone verification designed but ramped after Stage 9 (per PLAN.md).
- Tests: anonymous IP-cache round-trip; logged-in sync; anonymous → login claim with explicit consent; logout wipes server-cached state; verified-report gate; essentials reachable without login.

### Step 6 — Stage 9 E2E browser matrix (~1-2 days, `revive-e2e-polish`)

Last because every prior stage adds a row to the matrix.

- Adopt **Playwright** because the official docs support Chromium, Firefox, and WebKit testing, CI usage, parallel/sharded test execution, and Trace Viewer debugging with DOM/network/console detail. Avoid unverified "faster than Cypress" or NPM-download claims in the plan; the defensible reason is browser coverage plus debuggability. Add `@playwright/test` to [frontend/package.json](frontend/package.json), config `playwright.config.ts`, tests under `frontend/e2e/`.
- Walk-throughs covering each user from `antagonistic_testing.md` **plus** the additional items from `PLAN.md §9` not covered by antagonistic users: failed chat send, no-API-key full browsing, per-image thread isolation, image-to-chat handoff, vaccine question.
- Add a "friendliness assertion" to each persona: the test should not only check cards/status codes, it should assert that the UI did not strand the user. Examples: medicine refusal includes a safer next step; login gate offers a no-login path back; no-API fallback still gives a useful safe action; quiz wrong answer is encouraging.
- Browser matrix: Chromium (desktop), WebKit (Safari/iPhone — Priya's session), Firefox (desktop — Sneha's session), Android WebView (Savitri's session). Shard by browser in CI; run full matrix only on `main`, PRs run Chromium-only.
- GitHub Actions: `.github/workflows/ci.yml` running `pytest` + `npm run build` + `npx playwright test` on PR. Keep PR runs Chromium-only to control CI minutes; run the full browser matrix on `main`.
- Delete the 0-byte stubs (`backend/test_browser_sim.py`, `test_chunks.py`, `test_frontend.py`, `test_image_formats.py`, `test_live.py`) — they confuse new contributors and add nothing.
- **Before declaring Stage 9 done**: regenerate `antagonistic_testing.md` per the [regeneration prompt](regeneration_prompt.md) to cover all newly-shipped features at full depth. The v1 testing doc is renamed `docs/antagonistic_testing_v1.md`.

---

## Resources — three separate categories

### 🟦 Trustworthy — for grounding clinical claims, citations, and verified contacts

These are the sources that should appear in `medicine_kb.json` `sources[]` arrays, in `help_resources.json`, and in cruelty-page copy.

- **[Standard Veterinary Treatment Guidelines for Livestock and Poultry (DAHD + FAO + USAID, 2024 PDF)](https://dahd.gov.in/sites/default/files/2024-10/StandardVeterinaryTreatment.pdf)** — 274 diseases across 12 species including cattle, buffalo, sheep, goat, poultry, horse, donkey, camel. Indian-government, FAO-co-developed. Direct fit for Stage 7E cow + general-livestock kernels and 7F medicine KB. Note the PDF's own caveat: advocacy, not legally binding.
- **[Merck Veterinary Manual — Toxicology overview](https://www.merckvetmanual.com/toxicology/toxicology-introduction/overview-of-veterinary-toxicology)** — gold standard for the unsafe-medicine deny-list (paracetamol, ibuprofen, chocolate, xylitol, grapes). Free public access; cite per entry.
- **[Merck Veterinary Manual — Toxicoses From Human Analgesics](https://www.merckvetmanual.com/toxicology/toxicoses-from-human-analgesics/toxicoses-from-human-analgesics-in-animals)** — specific grounding for acetaminophen/paracetamol, ibuprofen, aspirin/NSAID risk, monitoring language, and "do not invent home dosing" prompts.
- **[FDA — Potentially Dangerous Items for Your Pet](https://www.fda.gov/animal-veterinary/animal-health-literacy/potentially-dangerous-items-your-pet)** — source for broad household deny-list: human medicines, NSAIDs, acetaminophen fatal to cats, onions, xylitol, chocolate, grapes/raisins. Good for `claim_scope: toxin_deny_list`.
- **[AVMA — Pet First Aid PDF](https://ebusiness.avma.org/files/productdownloads/LR_COM_FirstAid_010816.pdf)** — source for first-aid-kit basics: direct pressure for bleeding, cool-water heatstroke steps, poison-call information to gather, "do not induce vomiting or give medication unless directed." Use for quizzes and kit pages.
- **[Plumb's Veterinary Drug Handbook](https://plumbs.com/buy-the-handbook/)** — use only if the team has lawful access. Do not scrape or copy paywalled dose tables. Per `PLAN.md §7F`, default `dose_guidance: "vet_only"` unless a free authoritative source gives a clear general range.
- **[Cornell Feline Health Center — Health Topics](https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics)** — cat-specific authority for Stage 7E. Free articles, brochures, behaviour guides. Use for cat first-aid copy.
- **[Cornell Feline Health Center — Feline Lower Urinary Tract Disease](https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics/feline-lower-urinary-tract-disease)** — supports cat urinary obstruction as a true emergency; useful for Stage 7E cat kernel tests.
- **[FDA — Lovely Lilies and Curious Cats](https://www.fda.gov/animal-veterinary/animal-health-literacy/lovely-lilies-and-curious-cats-dangerous-combination)** — cat-specific lily emergency source; use for cat poison kernel and medicine/toxin KB.
- **[Merck Veterinary Manual — Bloat in Ruminants](https://www.merckvetmanual.com/digestive-system/diseases-of-the-ruminant-forestomach/bloat-in-ruminants)** — supports cow bloat as life-threatening and requiring veterinary/emergency intervention. Good for cow triage kernel.
- **[Merck Veterinary Manual — Snakebites in Animals](https://www.merckvetmanual.com/toxicology/snakebite/snakebites-in-animals)** — supports snakebite as emergency across domestic species; for cows, the user action should be "avoid movement and call livestock vet," not home treatment.
- **[Pet Poison Helpline (855-764-7661)](https://www.petpoisonhelpline.com)** — fee-based phone service; cite as escalation, not as a free contact for Indian users.
- **[Animal Welfare Board of India (AWBI)](https://awbi.gov.in/)** — official complaint portal, statutory body under PCA Act 1960. Already referenced from Cruelty page; add the formal email + grievance-portal URL to `help_resources.json` cruelty entries.
- **[Digital Personal Data Protection Act, 2023 — official Gazette PDF](https://egazette.gov.in/WriteReadData/2023/247847.pdf)** — source for consent/notice language in Stage 7H. Implementation relevance: notices must name personal data + purpose; consent must be specific/informed/unambiguous and limited to necessary data; notices should be available in English or an Eighth Schedule language.
- **[VOSD — How Citizens Can Legally Report Animal Cruelty in India (step-by-step)](https://www.vosd.in/how-to-report-animal-cruelty-in-india-vosd-guide/)** — practical, citizen-readable companion to AWBI. Use as a "what to do next" link from Cruelty page.
- **[People for Animals (PFA), Friendicoes, Blue Cross of India, Visakha SPCA](https://vspca.org/)** — established city-level rescue NGOs. Cross-check phone numbers against city helpline pages quarterly; today's `_CITY_EMERGENCY_CONTACTS` dict in [chat.py](backend/app/routers/chat.py#L126-L138) is the canonical place to update.
- **[OpenFDA Animal & Veterinary Adverse Events API](https://open.fda.gov/apis/animalandveterinary/event/)** — free JSON, government-issued. Useful for a future "known adverse events for this drug + species" lookup; not blocking for 7F.

### 🟧 Open-source — code, schemas, and frameworks to reuse rather than rewrite

- **[Better Auth — Magic Link plugin](https://better-auth.com/docs/plugins/magic-link)** — recommended first pass for Stage 7H because the official plugin exposes the exact flow we need: user submits email, `sendMagicLink` sends the URL, verification authenticates the user. Implementation note: configure hashed token storage and short TTL; never store magic-link tokens plain.
- **[Auth.js / NextAuth Email provider](https://next-auth.js.org/providers/email)** and **[Auth.js Resend provider guide](https://authjs.dev/guides/configuring-resend)** — fallback if Better Auth integration with FastAPI cookies becomes rough. Use official docs, not comparison blog posts, for final implementation decisions.
- **[Resend account quotas](https://resend.com/docs/knowledge-base/account-quotas-and-limits)** — current free limits are 100 transactional emails/day and 3,000/month. Good for dev/early beta; add provider abstraction before launch.
- **[Litestream](https://litestream.io/)** — streaming SQLite WAL replication to S3 / R2 / GCS. Activate for Stage 8 only if Railway's volume turns out to be ephemeral. Sidecar process; no schema change required. [Repo](https://github.com/benbjohnson/litestream).
- **[Railway Volumes docs](https://docs.railway.com/volumes)** — official source for persistent volume behavior and mount-path expectations. Stage 8 health checks should validate the path actually used by the deployed service.
- **[Playwright](https://playwright.dev)** — Stage 9 E2E. Use official docs as the basis: browser coverage for Chromium/Firefox/WebKit, CI support, parallelism/sharding, and Trace Viewer with DOM/network/console inspection. Avoid unverified benchmark/download claims.
- **[react-quiz-component (npm: react-quiz-component)](https://www.npmjs.com/package/react-quiz-component)** — Stage 7D scaffold. Light, JSON-driven; we'd vendor or fork to add Devanagari rendering + LLM-fresh feedback hook rather than depend on it long-term.
- **[GETMARKED Quiz JSON schema](https://digitaliser.getmarked.ai/docs/api/question_schema/)** — open MCQ schema reference; shape `learn_quizzes.json` to match so future tooling (auto-graders, exporters) plugs in.
- **[itsdangerous](https://itsdangerous.palletsprojects.com)** — signed tokens for Stage 7H magic-link verification. Already in FastAPI dependency tree.
- **[Hugging Face cats_vs_dogs (microsoft/cats_vs_dogs)](https://huggingface.co/datasets/microsoft/cats_vs_dogs)** + **[Animals-10 (Rapidata/Animals-10)](https://huggingface.co/datasets/Rapidata/Animals-10)** — open-licensed test fixtures for Stage 7E species-detection tests. Animals-10 includes cat / cow / dog labels.
- **[Oxford-IIIT Pet Dataset (timm/oxford-iiit-pet)](https://huggingface.co/datasets/timm/oxford-iiit-pet)** — 37 breed classes; useful when a future stage adds breed-aware Learn guidance.
- **[YOLOv5n / v8n / v11n (Ultralytics)](https://docs.ultralytics.com)** — only if a future stage wants on-device species detection without an LLM round trip. Out of scope today, but worth noting.

### 🟢 Creative — non-obvious sources that punch above their weight

- **[Hugging Face SAVSNET/PetBERT](https://huggingface.co/SAVSNET/PetBERT)** — vet-tuned BERT trained on real UK clinical notes. Could classify free-text owner descriptions ("loose stools two days") into ICD-style categories — unconventional but useful for triage taxonomy snap-back, the Antagonistic-report Tier-3 issue.
- **[Hugging Face karenwky/pet-health-symptoms-dataset](https://huggingface.co/datasets/karenwky/pet-health-symptoms-dataset)** — 2,000 LLM-generated owner-language symptom samples. Use as held-out evaluation fixtures for the triage classifier; it's not vet-authoritative, but it's a great cheap test set.
- **[Animal Humane Society — First Aid for Pet Parents](https://www.animalhumanesociety.org/resource/first-aid-tips-pet-parents)** + **[RSPCA Education](https://education.rspca.org.uk/)** — mine for *tone*, not facts. The phrasing here is closer to IndieAid's warm/care register than Plumb's clinical voice.
- **[Open Trivia Database](https://opentdb.com/)** — not vet content, but the *delivery format* (categories + difficulty + JSON) is a clean inspiration for `learn_quizzes.json` shape.
- **[iNaturalist Species Classification & Detection Dataset (CVPR 2018)](https://arxiv.org/abs/1707.06642)** — community-sourced 859k images / 5k+ species. Overkill for cat/dog/cow but indicates the upper bound of what an "everything-else fallback" could become if Stage 7E "other" species ever needs to actually identify, not just defer.
- **[Maharashtra Animal Welfare Board](https://dahd.maharashtra.gov.in/en/organization/maharashtra-animal-welfare-board/)** — regional authority not commonly cited in app directories. Worth seeding into `help_resources.json` for Pune / Mumbai / Nagpur (which is exactly the city set the antagonistic users live in).
- **[GausutaAnjaliJi — Top Animal Welfare Organisations in Delhi list](https://www.gausutaanjaliji.org/blog/top-animal-welfare-organizations-in-delhi)** + **[HelpLocal animal-rescue NGOs Delhi](https://helplocal.in/blog/animal-rescue-ngos-delhi/)** — community-curated NGO directories that complement the more-famous PFA/Friendicoes contacts. Cross-validate before adding to verified contacts.
- **[Down To Earth — coverage of the SVTG release](https://www.downtoearth.org.in/health/centre-releases-standard-veterinary-treatment-guidelines-for-livestock-and-poultry)** — secondary-source explainer of the DAHD/FAO guidelines; useful when summarising the "what does this guideline cover" line for our own Cruelty/About copy in a way that's readable rather than legalese.

---

## Research-to-implementation map

| Product area | Primary source constraint | IndieAid behavior |
|---|---|---|
| Unsafe human medicines | FDA dangerous-items list + Merck analgesic toxicosis | Block the drug, name why at a high level, give safer immediate steps, collect name/amount/time for vet call |
| Poison exposure | AVMA first aid + FDA/Merck toxin pages | If exposure happened: ask substance/amount/time, preserve packet, no vomiting/medication unless directed; if hypothetical: friendly prevention answer only |
| Weak puppy feeding | First-aid KB + puppy/neonatal sources | Warmth first; tiny safe intake only if alert; no cow milk/force feeding; encourage rescue/vet help when cold, limp, crying, or non-suckling |
| Cat emergencies | Cornell + FDA cat-specific hazards | Cat urinary obstruction, lily exposure, acetaminophen/paracetamol, collapse, seizure, heavy bleeding are narrow emergency kernels |
| Cow emergencies | DAHD/FAO SVTG + Merck bloat/snakebite | Mostly dispatch and safe containment: bloat, dystocia, snakebite, immobility/fracture, severe infectious signs |
| First-aid kit | AVMA first-aid checklist | Kit copy teaches safe stabilisation, not definitive treatment; every topic has "if you remember nothing else" plus escalation |
| Cruelty reporting | AWBI + PCA Act + practical NGO guides | Document safely, do not escalate into human confrontation, report through official/verified channels |
| Anonymous persistence | DPDP Act official Gazette | Clear notice, specific purpose, minimum data, consent in English/Hindi/Marathi, expiry and deletion controls |
| Magic-link login | Better Auth/Auth.js + Resend docs | Friendly email sign-in, neutral enumeration-safe responses, hashed tokens, rate limits, no login wall for essentials |
| Railway durability | Railway Volumes docs | Health endpoint proves writable persistent paths before UI promises saved reports/history |
| E2E verification | Playwright official docs | Cross-browser checks plus trace artifacts; tests assert usefulness/warmth, not just DOM presence |

---

## Schema Drafts

Concrete examples so Codex doesn't guess at shapes.

### Sample `learn_quizzes.json` entry (one topic, trilingual)

```json
{
  "wound_cleaning": [
    {
      "q": {
        "en": "What should you use to clean a minor wound on a street dog?",
        "hi": "एक स्ट्रीट डॉग के छोटे घाव को साफ़ करने के लिए क्या इस्तेमाल करना चाहिए?",
        "mr": "रस्त्यावरच्या कुत्र्याच्या लहान जखमेवर स्वच्छतेसाठी काय वापरावे?"
      },
      "options": {
        "en": ["Dettol / undiluted antiseptic", "Diluted povidone-iodine (Betadine)", "Kerosene", "Turmeric paste"],
        "hi": ["डेटॉल / बिना पतला एंटीसेप्टिक", "पतला पोविडोन-आयोडीन (बीटाडीन)", "मिट्टी का तेल", "हल्दी का पेस्ट"],
        "mr": ["डेटॉल / न पातळ केलेले अँटिसेप्टिक", "पातळ केलेले पोविडोन-आयोडीन (बीटाडीन)", "रॉकेल", "हळदीचा लेप"]
      },
      "correct_index": 1,
      "explanation": {
        "en": "Diluted povidone-iodine is safe for wound cleaning. Undiluted antiseptics can irritate tissue. Kerosene burns skin and is toxic if licked. Turmeric paste can trap bacteria.",
        "hi": "पतला पोविडोन-आयोडीन घाव साफ़ करने के लिए सुरक्षित है। बिना पतला एंटीसेप्टिक tissue को irritate कर सकता है। केरोसिन skin जला सकता है और चाटने पर toxic है। हल्दी बैक्टीरिया को अंदर बंद कर सकती है।",
        "mr": "पातळ केलेले पोविडोन-आयोडीन जखम स्वच्छ करण्यासाठी सुरक्षित आहे. बिनपातळ अँटिसेप्टिक tissue ला irritate करू शकतो. रॉकेल skin भाजवू शकते. हळद बॅक्टेरिया आत अडकवू शकते."
      }
    }
  ]
}
```

### Sample `medicine_kb.json` entry

```json
{
  "paracetamol": {
    "names": ["paracetamol", "acetaminophen", "crocin", "dolo", "tylenol"],
    "species_safe": [],
    "species_unsafe": ["dog", "cat"],
    "species_notes": {
      "cat": "Extremely toxic — even one tablet can be fatal. Cats lack the enzyme (glucuronyl transferase) to metabolise it.",
      "dog": "Toxic at doses commonly used by owners. Can cause liver failure and methemoglobinemia."
    },
    "typical_use": "Human fever and pain relief",
    "common_misuse": "Given to dogs/cats for fever or pain by well-meaning owners",
    "safer_alternatives": ["cold water compress for fever", "shade and rest", "vet-prescribed meloxicam (dogs only, vet dosing)"],
    "home_use_ok": false,
    "requires_vet": true,
    "dose_guidance": "vet_only",
    "red_flags": ["known ingestion", "vomiting", "pale or blue gums", "weakness", "fast breathing", "collapse"],
    "friendly_next_step": "Do not give another tablet. Keep the animal quiet and note the tablet strength, amount, and time for the vet.",
    "sources": [
      { "title": "Merck Vet Manual — Toxicoses From Human Analgesics", "url": "https://www.merckvetmanual.com/toxicology/toxicoses-from-human-analgesics/toxicoses-from-human-analgesics-in-animals", "accessed_on": "2026-04-30", "claim_scope": "analgesic_toxicosis" },
      { "title": "FDA — Potentially Dangerous Items for Your Pet", "url": "https://www.fda.gov/animal-veterinary/animal-health-literacy/potentially-dangerous-items-your-pet", "accessed_on": "2026-04-30", "claim_scope": "acetaminophen_fatal_to_cats_and_human_medicine_warning" }
    ]
  }
}
```

### Cat and cow emergency kernels (high-confidence only, sourced)

**Cat emergencies** (sources: [Cornell Feline Health Center](https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics), [Cornell FLUTD](https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics/feline-lower-urinary-tract-disease), [FDA lilies + cats](https://www.fda.gov/animal-veterinary/animal-health-literacy/lovely-lilies-and-curious-cats-dangerous-combination)):
1. **Not breathing / collapse** — same urgency as dogs
2. **Urinary blockage** (male cats straining, crying at litter box) — life-threatening within 24-48 hours
3. **Poisoning** (lily, paracetamol, antifreeze) — lilies are uniquely fatal to cats, not dogs
4. **Seizure in progress** — same protocol as dogs
5. **Heavy bleeding / road trauma** — same protocol as dogs

**Cow emergencies** (sources: [DAHD/FAO SVTG 2024](https://dahd.gov.in/sites/default/files/2024-10/StandardVeterinaryTreatment.pdf), [Merck bloat in ruminants](https://www.merckvetmanual.com/digestive-system/diseases-of-the-ruminant-forestomach/bloat-in-ruminants), [Merck snakebites in animals](https://www.merckvetmanual.com/toxicology/snakebite/snakebites-in-animals)):
1. **Bloat** (distended left flank, difficulty breathing) — can be fatal within hours
2. **Dystocia** (calving difficulty) — requires immediate intervention
3. **Haemorrhagic septicaemia** (sudden high fever, swelling) — endemic in India
4. **Fracture / road trauma with immobility** — livestock helpline + do not move
5. **Snakebite** (sudden swelling, distress) — common in rural India

All other cat/cow situations → `care` mode with strong vet deferral. No species-specific emergency claims for `other` species. Keep the tone friendly: "I can't safely treat this like a dog case, but here is how to keep them safe while you contact the right help."

---

## Multilingual Implementation Notes

| Content Type | Translation Strategy | Rationale |
|---|---|---|
| `learn_quizzes.json` | **Static** — authored in 3 languages in JSON | Correctness must be human-verified; LLM translation of medical MCQs risks subtle errors |
| `medicine_kb.json` | **Static** for `names[]`, `species_notes`, `safer_alternatives[]` | Safety-critical content; "paracetamol बिलकुल मत दें" must be exact, not LLM-improvised |
| Chat responses | **Dynamic** — LLM generates in detected language | Already works; triage detects language |
| Quiz LLM-fresh feedback | **Hybrid** — static base explanation always available; LLM may rephrase in detected language when key present | Falls back to static on failure |
| Cat/cow triage heuristics | **Static** — add Hindi/Marathi species terms to heuristic patterns | `मांजर`, `बिल्ली`, `गाय`, `गोवंश`, `मांजरी` etc. must be in the triage regex |
| UI labels (new pages) | **Static** — authored in 3 languages in the component | Same pattern as existing pages |
| Privacy/consent copy | **Static** — English/Hindi/Marathi authored together | DPDP-grounded notices must be clear and friendly; do not rely on LLM for consent wording |
| Emotional repair/warm copy | **Prompted + tested** — LLM phrasing, deterministic mode routing | Friend philosophy depends on not treating apologies, guilt, or thanks as symptoms |

---

## Risk and Dependency Table

| Stage | Key Risk | Mitigation |
|---|---|---|
| **Step 0** | Antagonistic fixes break existing passing tests | Run full `pytest` before and after; each fix gets a pattern test |
| **All stages** | Warm/helpful philosophy gets lost under safety/legal copy | Add friend-first acceptance checks: acknowledgement, concrete next step, no scolding, no dead-end |
| **7F** | Groq rate limits on medicine prompts during high usage | Hardcoded deny-list works without key; KB fallback text always present |
| **7F** | Medicine KB cites a source for a claim the source does not support | Store `claim_scope`; review every entry source-by-source; default to `vet_only` dosing |
| **7E** | Vision species step adds ~1s latency to every analysis | Parallelize species detection with condition analysis (both are LLM calls) |
| **7E** | Cat/cow first-aid advice lacks Indian vet review | All entries cite Cornell/DAHD sources; mark as "sourced, not vet-reviewed" in the UI |
| **7D** | Quiz content quality in Hindi/Marathi | Have a native speaker review before merge — not an LLM translation pass |
| **8** | Railway volume is ephemeral on free/hobby tier | Add Litestream sidecar config to Cloudflare R2 (free: 10GB); daily backup cron |
| **7H** | No SMTP provider configured for magic links | Use Resend (free: 100 emails/day) or Railway SMTP addon |
| **7H** | DPDP Act 2023 compliance for IP-keyed sessions | Hash IP+UA, never store raw; 30-day auto-expiry; consent banner; deletion on request |
| **7H** | Login feels like a wall during rescue | Essentials stay login-free; gated pages include a path back to Chat/Find Help |
| **9** | Playwright CI takes too long on full matrix | Shard by browser; full matrix on `main` only, PRs run Chromium-only |
| **9** | Antagonistic testing doc is stale after features ship | Regenerate per `regeneration_prompt.md` before declaring Stage 9 done |

---

## Critical files this plan touches

- [backend/app/services/triage.py](backend/app/services/triage.py) — Step 0 (1, 3, 4, 6), Step 1 (deny-list), Step 2 (species)
- [backend/app/routers/chat.py](backend/app/routers/chat.py) — Step 0 (1, 2, 5), Step 1 (`_PROMPT_MEDICINE`)
- [backend/app/routers/analyze.py](backend/app/routers/analyze.py) — Step 1 (otc_suggestion), Step 2 (species detection)
- [backend/app/models/schemas.py](backend/app/models/schemas.py) — Step 1 (`OTCEntry`), Step 2 (`species`)
- [backend/app/database.py](backend/app/database.py) — Step 5 (new tables)
- [backend/app/main.py](backend/app/main.py) — Step 4 (diagnostic `/health`)
- [backend/app/config.py](backend/app/config.py) — Step 5 (auth secrets)
- [backend/data/help_resources.json](backend/data/help_resources.json) — Step 2 (species filter), trustworthy-source seeding
- [backend/data/medicine_kb.json](backend/data/medicine_kb.json) (new) — Step 1
- [backend/data/learn_quizzes.json](backend/data/learn_quizzes.json) (new) — Step 3
- [backend/railway.json](backend/railway.json) — Step 4 (volumes block)
- [backend/tests/test_triage_router.py](backend/tests/test_triage_router.py) — Step 0 pattern tests
- [frontend/src/app/learn/page.tsx](frontend/src/app/learn/page.tsx) — Step 2 (cat/cow), Step 3 (quiz mount)
- [frontend/src/app/first-aid-kit/page.tsx](frontend/src/app/first-aid-kit/page.tsx) — Step 1 (citation callout), Step 3 (quiz mount)
- [frontend/src/app/settings/page.tsx](frontend/src/app/settings/page.tsx) — Step 5 (sign-in button)
- [frontend/src/lib/api.ts](frontend/src/lib/api.ts) — Step 1 (`OTCEntry` type), Step 2 (`species` type), Step 5 (auth endpoints)
- [frontend/package.json](frontend/package.json) — Step 6 (`@playwright/test`)
- `.github/workflows/ci.yml` (new) — Step 6
- `frontend/playwright.config.ts` + `frontend/e2e/` (new) — Step 6

## Verification

End-to-end after each step:

- **Every step**: run a short "friendliness review" on changed user-facing paths. Check: does the user get a concrete next step, does the copy avoid scolding, does a refusal include a safer alternative, and does the screen keep essentials reachable?
- **Step 0**: `cd backend && pytest -k "antagonistic or pattern"` plus a re-run of `python artifacts/antagonistic_runner.py` against the deployed Railway URL — fail count should drop from 7 to ≤1.
- **Step 1**: `pytest backend/tests/test_medicine_kb.py` (new) and a manual chat call: `curl -X POST .../api/chat -d '{"message": "can I give crocin", ...}'` should return a `MedicineCallout`-shaped block with a citation; image-analysis fixture for a wound returns `otc_suggestion`.
- **Step 2**: feed a cat photo to `/api/analyze`; expect `species: "cat"` and species-aware copy; expect `species: "other"` fallback for an unknown image to *not* claim dog-specific emergencies.
- **Step 3**: `npm run build` clean; render Learn `/approach`, click through one quiz, verify Hindi + Marathi rendering and that the LLM-fresh path falls back to static text when `GROQ_API_KEY` is unset.
- **Step 4**: hit `/health` on Railway; expect resolved paths and `db_writable: true`. Run the report-survives-restart pytest.
- **Step 5**: magic-link round-trip in Playwright (request → click email link → land authenticated → log out → server-side state cleared). Anonymous IP-cache round-trip with same hashed IP returns prior thread; with different IP, no leakage.
- **Step 6**: `npx playwright test` green locally and in CI; the GitHub Actions run uploads a Trace Viewer artefact on failure. Antagonistic browser walk-through (re-implementing `antagonistic_testing.md` users 1-7) passes.
