# IndieAid Working Context

Load this with `README.md` before starting a new IndieAid task. `PLAN.md` remains the full staged roadmap; this file is the short handoff context for future agents.

## Product Soul

IndieAid is a care and first-aid app for pets, street animals, and the people who stop to help them. It should feel calm, loving, practical, and trustworthy.

The app should be warm for greetings, learning, healthy-dog questions, and normal care. It should be grounded and proportionate for mild or uncertain symptoms. It should become short, direct, and action-first only for true emergencies. When the user corrects it, it should acknowledge the correction and narrow or reset context instead of repeating an old emergency script.

IndieAid gives guidance, not veterinary diagnosis. It must say what is known, what is uncertain, and what the person should do next.

## Language Contract

English, Hindi, and Marathi are equal product surfaces for this phase.

- Routing, prompts, UI copy, cards, fallbacks, and tests should treat all three languages as first-class.
- Safety classification should map language-specific text into shared canonical fields such as `mode`, `scenario_type`, `urgency_tier`, and future negation/context fields.
- Emergency wording can be adapted by the LLM, but the safety meaning must not drift between languages.
- Hindi and Marathi copy should be natural and simple, not stiff word-for-word English translations.
- Do not add new user-facing copy in only one language unless it is internal-only.
- Additional languages and voice flows are out of scope until English, Hindi, and Marathi are reliable.

## Architecture Map

- `frontend/`: Next.js app deployed on Vercel.
- `frontend/src/app/chat/page.tsx`: chat UI, history, analysis-context handoff, action cards.
- `frontend/src/app/analyze/page.tsx`: image-analysis UI and handoff into chat.
- `frontend/src/lib/api.ts`: frontend API types and backend URL handling.
- `frontend/src/lib/language.tsx`: UI language state and translations.
- `backend/`: FastAPI app deployed on Railway.
- `backend/app/main.py`: app setup, CORS, health endpoint.
- `backend/app/models/schemas.py`: API schemas shared by routers.
- `backend/app/services/triage.py`: pre-response triage and safety routing.
- `backend/app/routers/chat.py`: chat endpoint, retrieval, response fallbacks, Groq text calls, action cards.
- `backend/app/routers/analyze.py`: image upload and analysis response assembly.
- `backend/app/services/vision_analyzer.py`: combined vision model path.
- `backend/app/services/response_generator.py`: multilingual analysis response generation and fallback text.
- `backend/data/first_aid_kb.json`: local first-aid retrieval content.
- `backend/data/help_resources.json`: local help/resource contacts.
- `backend/tests/fixtures/`: currently mixed fixture labels; do not assume image labels are visual truth.

## Current Mode Target

Target modes:

- `warm`: greeting, dog introduction, breed curiosity, learning, healthy-dog reassurance.
- `care`: mild or uncertain symptoms, feeding, skin, ticks, diarrhea without red flags, routine vet planning, community-dog care, deceased/passed-away pet aftercare.
- `emergency`: choking, not breathing, collapse, seizure in progress, heavy bleeding, road trauma, poisoning, heatstroke, entrapment, human rabies exposure.
- `repair`: corrections, "stop repeating," "that's wrong," "new dog," "new topic," negated emergency symptoms.

Code should own safety gates, schemas, context policy, and card routing. The LLM should own nuance, tone, proportionality, and humane explanation when the current message is not a deterministic emergency.

## Safe-Push Workflow

Before editing:

- Check the current behavior for the area being changed.
- Inspect `git status --short --branch`.
- Keep `docs/archive/chatgpt-diagnosis.md` archived and uncommitted unless explicitly requested.

During edits:

- Keep changes scoped to the current stage in `PLAN.md`.
- Avoid broad rewrites, new dependencies, generated assets, or large fixture blobs unless the stage explicitly needs them.
- Log non-blocking inconsistencies in this file instead of expanding scope mid-fix.

Before pushing:

- Run focused backend tests for the touched area.
- Run `npm run build` for frontend-impacting work.
- Inspect `git diff` and stage explicit paths only.
- Push the branch and update or open a draft PR with checks and deployment notes.

Deployment checks:

- Vercel uses `frontend/vercel.json`; preview verification may require Vercel access.
- Railway uses `backend/railway.json`; `/health` verification requires the production backend URL.
- Record what was actually checked instead of implying unavailable access.

## Known Risks

- Railway durability for SQLite and uploaded report images is not proven beyond the volume mount at `/app/data` (commit `5bf0122`). Needs verification (Stage 8).
- Production environment, Groq key availability, CORS, Vercel API URL, and deployed branch behavior still need verification.
- Triage scenario taxonomy drift: LLM sometimes emits non-canonical scenario types (`gastrointestinal_issue`, `unclear`) — snapping in `_normalize_result` is needed.
- Medicine guidance (milk for weak puppy, paracetamol dosing) lacks KB grounding — active care-content risk until Stage 7F ships.
- Species limitation: cat photos analyzed as dogs, cow injuries get dog-specific advice. Needs Stage 7E.
- Fixture labels under `backend/tests/fixtures/` are not trustworthy as visual truth.

## Active Task Queue

Stages 0–6, 7 IA, 7A, 7B, 7C, 7G complete. Remaining:

1. Antagonistic test fixes (Step 0 in `.claude/plans/plan-strategy-and-find-tidy-parnas.md`) — land before new features.
2. Stage 7F: Medicine KB-backed chat/image surfacing.
3. Stage 7E: Multi-species support (cats, cows, general fallback).
4. Stage 7D: Learn mode quizzes.
5. Stage 8: Railway durability verification.
6. Stage 7H: Login, IP-keyed anonymous persistence, DB expansion.
7. Stage 9: End-to-end verification (Playwright browser matrix).

Execution plan with resources and schema drafts: `.claude/plans/plan-strategy-and-find-tidy-parnas.md`.

## Discovered Issues Log

- 2026-04-28: Vercel project metadata exists at `frontend/.vercel/project.json`, but deployment listing through the available connector returned `403 Forbidden` during Stage 0.
- 2026-04-28: Railway production URL was not discoverable from repo metadata during Stage 0, so `/health` could not be checked.
- 2026-04-28: Stage 2 found the old `quick` and `detailed` image fixture suites reused four external image URLs across 165 labels, including emergency scenarios. They are quarantined and should not be used as visual truth.
- 2026-04-28: Example chat showed "dead / she's dead / not an emergency, she's just dead" bouncing back into emergency or active-triage questions. Added `deceased_pet` as a stable non-emergency care scenario with quiet cards and aftercare/grief wording.
- 2026-04-28: Stage 6 added `analysis_status` (`complete`, `uncertain`, `no_dog_visible`, `unavailable`) so model outages no longer masquerade as "no dog visible"; local fallback families now distinguish healthy, mild, urgent, no-dog, and unavailable paths.
- 2026-04-30: Railway persistent volume is now mounted at `/app/data`; backend defaults now auto-prefer `/app/data` for SQLite and uploads when present, with `.env` overrides still supported.
- 2026-04-30: Antagonistic testing (7 personas, 47 steps) identified 7 failures: milk-for-weak-puppy care error, wrong card on medicine question, missing Find Help on life-threatening fracture, repair misclassification of "different dog limping", care mode on emotional check-ins, scenario taxonomy drift. Results in `docs/antagonistic_report.md`.
- 2026-04-30: `chatgpt-diagnosis.md` archived to `docs/archive/` — all 6 systemic failures it identified are now fixed. Future agents should not reference it for current state.

## Documentation Map

- `README.md` — product overview, tech stack, setup.
- `PLAN.md` — canonical staged roadmap (source of truth for stage definitions).
- `docs/indieaid-working-context.md` — this file; agent handoff context.
- `docs/antagonistic_testing.md` — persona-driven testing doc (7 users, interaction sequences, ideal responses).
- `docs/antagonistic_report.md` — results from the first antagonistic test run.
- `docs/test-runs/` — raw test data (JSON).
- `docs/archive/chatgpt-diagnosis.md` — historical architecture diagnostic (pre-Stage-0, all issues now fixed).
- `.claude/plans/plan-strategy-and-find-tidy-parnas.md` — active execution plan for remaining stages with resources and schema drafts.
