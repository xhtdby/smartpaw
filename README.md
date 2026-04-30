# IndieAid

IndieAid is a care and first-aid app for pets, street animals, and the people who stop to help them. It should feel calm, practical, and kind: robust when a situation is urgent, and friendly when someone just wants to understand or care for an animal better.

The app is not meant to be a panic machine. It should know how to shift between warm conversation, proportionate care guidance, and true emergency first aid — and act, not just redirect, when first aid is what the situation needs.

## Product Soul

IndieAid is built from love for animals and respect for the humans who stop to help them. Every change should preserve that:

- Warm by default when the user is greeting, sharing, learning, or asking a normal care question.
- Grounded when symptoms are mild, unclear, or need monitoring.
- Fast and direct — "lock-in / fixer" register — when an animal or person may be in danger.
- Humble when corrected by the user.
- Clear about uncertainty and professional help, without hiding behind disclaimers.
- Especially careful with community-animal realities: traffic, crowds, rescue access, language, and human safety.
- Honest about what the user can do at home: practical OTC guidance where reputable veterinary sources support it, clear refusals + safer alternatives where they don't.
- Frictionless on essentials: Chat, Analyze, Find Help, and the emergency CTA must never sit behind a login or a permission gate.

## Species Scope

- **Dogs** — fully supported today (triage, prompts, vision, resources, guides).
- **Cats and cows** — first-class targets for the active plan (Stage 7E).
- **Other species** — conservative general-animal fallback that says what is observed and defers strongly to a vet.

Cruelty surfaces cover **all strays**, not just dogs.

## Current Shape

- `frontend/`: Next.js app deployed on Vercel.
- `backend/`: FastAPI app deployed on Railway.
- `backend/app/services/triage.py`: classifies chat turns into `mode` (warm/care/emergency/repair), `urgency_tier`, `scenario_type`, `species`, `intent`, with a `context_used` audit field.
- `backend/app/routers/chat.py`: chat endpoint, retrieval, fallbacks, action cards, Groq text calls. Action cards routed from `mode + urgency + scenario_type + intent`.
- `backend/app/routers/analyze.py`: image upload and analysis flow, including the multilingual analysis path.
- `backend/app/services/vision_analyzer.py`: combined vision analysis with scenario-family fallbacks.
- `backend/app/database.py`: SQLite (async via `aiosqlite`) holding community reports today; planned to hold mailing list, users, and chat threads in later stages.
- `backend/data/first_aid_kb.json`: built-in first-aid retrieval content (TF-IDF).
- `backend/data/help_resources.json`: rescue, official, and advice contacts.
- `backend/data/medicine_kb.json` *(planned, Stage 7F)*: sourced OTC + unsafe-medicine KB.
- `backend/data/learn_quizzes.json` *(planned, Stage 7D)*: quiz items per Learn guide and first-aid topic.
- `backend/tests/fixtures/`: image and chat quality fixtures.
- `frontend/src/app/`: home, chat, analyze, learn, nearby, report. Planned additions: `first-aid-kit/`, `cruelty/`, `drives/`.
- `docs/indieaid-working-context.md`: persistent context doc (architecture map, language contract, discovered-issues log, source/date tracking for resources).
- `PLAN.md`: revival plan and current stage tracker.

## Local Development

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` for the app. The backend serves on `http://localhost:8000`.

## Environment

Backend environment variables:

- `GROQ_API_KEY`: enables vision, chat, triage, and judge-model tests. Without it, the app falls back to deterministic, sourced content (no fabricated advice).
- `HF_API_TOKEN`: optional legacy fallback for condition analysis.
- `SUPABASE_URL` and `SUPABASE_KEY`: optional. Candidate provider for Stage 7H login if magic-link is not chosen.
- `CORS_ORIGINS`: configure if deployments move away from the current Vercel domains.
- `DB_PATH`, `UPLOADS_DIR`: must point to durable Railway volume paths in production (audited in Stage 8).

Frontend environment variables depend on `frontend/src/lib/api.ts`. Keep production API URLs aligned with the Railway backend.

## Deployment

- Railway uses `backend/railway.json` and starts the API with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Vercel uses `frontend/vercel.json` and builds with `npm run build`.
- After each meaningful change, verify locally first, then push, then check the deployed Vercel and Railway behavior from a human user's point of view.

## Working Principles

- Check the current behavior before fixing it.
- Keep fixes scoped to the feature or defect being handled.
- Prefer one small, verified improvement over broad rewrites.
- Do not let emergency safety code become the whole product personality.
- Do not put friction in front of essentials. Login is the gate for forums, inter-user interaction, and verified reports — never for chat, analyze, find-help, or the emergency CTA.
- First aid is first aid. Where reputable veterinary sources support an OTC option, the app should surface it (with citation). Suppressing useful guidance in the name of caution has been a real regression.
- Log discovered inconsistencies in `docs/indieaid-working-context.md` instead of chasing every side issue mid-fix.
- Avoid adding new files, dependencies, generated artifacts, or test data unless they clearly pay for themselves.
- Test both safety and warmth. A correct emergency checklist is not enough if normal users feel punished for normal questions.

## Target Product Modes

- **Warm** mode: greetings, animal introductions, breed/species curiosity, learning, healthy-animal reassurance. Prompt invites small genuine human acknowledgements.
- **Care** mode: mild or uncertain symptoms, routine care, feeding, skin, ticks, diarrhea without red flags, follow-up questions, deceased pet aftercare.
- **Emergency** mode: choking, not breathing, collapse, seizure in progress, heavy bleeding, road trauma, poisoning, heatstroke, entrapment, human rabies exposure. Uses a tighter "lock-in / fixer" register: action first, rationale second, escalation third.
- **Repair** mode: user corrections such as "no seizure", "stop repeating", "that's wrong", "new animal", "new topic".

Within `care`, high-urgency turns also use the lock-in register.

## Languages

English, Hindi, and Marathi are equal priorities. Routing, prompts, UI copy, tests, cards, and fallbacks treat all three as first-class. Common code-mixed forms are supported. Additional Indian languages and voice input/output are the immediate next initiatives once the active plan closes — the contracts are kept clean enough to wrap with a voice layer or extend with more languages without redesign.

## Active Plan Snapshot

Stages 0–6 are complete: mode routing, mode-specific prompts, analysis-to-chat banner handoff, scenario-family fallbacks for image analysis, deceased pet handling, and clear-history cleanup.

Active stages (in `PLAN.md`):

- **Stage 7** — App feel and information-architecture cleanup; essentials-only home, secondary "More" tray.
- **Stage 7A** — Per-image chat threads, IndexedDB storage, image compression. Fixes the broken global-chat / single-analysis-slot model.
- **Stage 7B** — Tone polish: warmth in warm mode, lock-in register in emergency / high-urgency care.
- **Stage 7C** — First-aid kit screen and cruelty section covering all strays. Restores OTC medicine surfacing.
- **Stage 7D** — Learn-mode and first-aid-kit quizzes with optional grounded LLM-fresh feedback.
- **Stage 7E** — Multi-species support: cats and cows first-class, other species via general-animal fallback.
- **Stage 7F** — Medicine knowledge base: sourced OTC guidance + safer-alternative counters and a hardcoded deny-list.
- **Stage 7G** — Drives / mailing-list signup for food, water, and medicine coordination.
- **Stage 7H** — Magic-link login + IP-keyed anonymous server cache. Login gates forums and verified reports; essentials stay login-free.
- **Stage 8** — Report and production durability audit, including any new tables.
- **Stage 9** — End-to-end human verification across all three languages.

After this plan closes: voice input/output, additional Indian languages, and a design overhaul to make the app unique and memorable.

## Current Risks Worth Knowing

- Single global chat with one optional analysis-context slot — old photo context leaks across topics or evaporates after one pass. Fixed by Stage 7A.
- OTC medicine guidance was previously stripped from chat and the image analyser; restoring it is a goal of Stages 7C and 7F.
- App is dog-only end-to-end. Cat photos are analyzed as dogs. Fixed by Stage 7E.
- Cruelty reports get treated as medical emergencies. Fixed by Stage 7C.
- No login means anonymous users lose context across devices and private windows. Mitigated by Stage 7H's IP-keyed fallback.
- Railway durability for SQLite and uploaded report images is not yet proven. Audited in Stage 8 before any new persisted feature is shipped.
- Groq-dependent tests are useful but cannot be the only regression protection. Router, context, card, fallback, species, and medicine-deny-list tests all run without network or API keys.

## Before Shipping A Fix

Run the smallest meaningful checks:

```powershell
cd backend
pytest
```

```powershell
cd frontend
npm run build
```

For UI or user-flow changes, start the dev server and check the actual screen, not just the compiler. The app should be useful, readable, and emotionally appropriate for the situation — warm when safe, grounded when uncertain, urgent only when urgency is real.
