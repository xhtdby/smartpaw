# IndieAid Working Context

Load this with `README.md` before starting a new IndieAid task. `PLAN.md` remains the full staged roadmap; this file is the short handoff context for future agents.

## Product Soul

IndieAid is a dog care and first-aid app for pets, community/street dogs, and people trying to help them. It should feel calm, loving, practical, and trustworthy.

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
- `care`: mild or uncertain symptoms, feeding, skin, ticks, diarrhea without red flags, routine vet planning, community-dog care.
- `emergency`: choking, not breathing, collapse, seizure in progress, heavy bleeding, road trauma, poisoning, heatstroke, entrapment, human rabies exposure.
- `repair`: corrections, "stop repeating," "that's wrong," "new dog," "new topic," negated emergency symptoms.

Code should own safety gates, schemas, context policy, and card routing. The LLM should own nuance, tone, proportionality, and humane explanation when the current message is not a deterministic emergency.

## Safe-Push Workflow

Before editing:

- Check the current behavior for the area being changed.
- Inspect `git status --short --branch`.
- Keep `chatgpt-diagnosis.md` local and uncommitted unless explicitly requested.

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

- Stage 0 first-pass fixes are in draft PR #7 and may not be merged into `main` yet.
- The chat still needs a typed mode architecture; first-pass heuristics are only a bridge.
- Analysis-to-chat still creates a fake prefilled user message.
- Analysis fallback text is too generic across healthy, mild, urgent, and unavailable cases.
- Image analysis output can still sound like a formal clinical report instead of a calm IndieAid observation.
- Fixture labels under `backend/tests/fixtures/` are not trustworthy as visual truth.
- Some tests are still biased toward emergency checklist behavior.
- Railway durability for SQLite and uploaded report images is not proven.
- Production environment, Groq key availability, CORS, Vercel API URL, and deployed branch behavior still need verification.

## Active Task Queue

1. Stage 1: keep this context doc concise, linked to `README.md` and `PLAN.md`, and safe for future agents to load.
2. Stage 2: clean up test truth and fixture categories so tests stop rewarding mislabeled image assumptions.
3. Stage 3: add typed LLM-forward routing with `mode` and `context_used`.
4. Stage 4: add mode-specific response generation across English, Hindi, and Marathi.
5. Stage 5: replace fake analysis-to-chat prefilled messages with a visible structured context banner.
6. Stage 6: improve analysis quality and unavailable/uncertain fallback families.
7. Stage 7: align Learn, cards, resources, and app feel with warm/care/emergency modes.
8. Stage 8: audit report persistence and production durability.
9. Stage 9: complete local and deployed end-to-end human verification.

## Discovered Issues Log

- 2026-04-28: Vercel project metadata exists at `frontend/.vercel/project.json`, but deployment listing through the available connector returned `403 Forbidden` during Stage 0.
- 2026-04-28: Railway production URL was not discoverable from repo metadata during Stage 0, so `/health` could not be checked.
- 2026-04-28: Stage 2 found the old `quick` and `detailed` image fixture suites reused four external image URLs across 165 labels, including emergency scenarios. They are quarantined and should not be used as visual truth.
