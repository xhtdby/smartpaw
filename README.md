# IndieAid

IndieAid is a dog care and first-aid app for pets, street dogs, and the people trying to help them. It should feel calm, practical, and kind: robust when a situation is urgent, and friendly when someone just wants to understand or care for a dog better.

The app is not meant to be a panic machine. It should know how to shift between warm conversation, proportionate care guidance, and true emergency first aid.

## Product Soul

IndieAid is built from love for animals and respect for the humans who stop to help them. Every change should preserve that:

- Warm by default when the user is greeting, sharing, learning, or asking a normal care question.
- Grounded when symptoms are mild, unclear, or need monitoring.
- Fast and direct when the dog or a person may be in danger.
- Humble when corrected by the user.
- Clear about uncertainty and professional help, without hiding behind disclaimers.
- Especially careful with community-dog realities: traffic, crowds, rescue access, language, and human safety.

## Current Shape

- `frontend/`: Next.js app deployed on Vercel.
- `backend/`: FastAPI app deployed on Railway.
- `backend/app/services/triage.py`: classifies chat turns before response generation.
- `backend/app/routers/chat.py`: chat endpoint, retrieval, fallbacks, action cards, Groq text calls.
- `backend/app/routers/analyze.py`: image upload and analysis flow.
- `backend/app/services/vision_analyzer.py`: combined vision analysis.
- `backend/data/first_aid_kb.json`: built-in first-aid retrieval content.
- `backend/data/help_resources.json`: local rescue/help resources.
- `backend/tests/fixtures/`: image and chat quality fixtures.

## Local Development

Backend:

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
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

- `GROQ_API_KEY`: enables vision, chat, triage, and judge-model tests.
- `HF_API_TOKEN`: optional legacy fallback for condition analysis.
- `SUPABASE_URL` and `SUPABASE_KEY`: optional.
- `CORS_ORIGINS`: configure if deployments move away from the current Vercel domains.

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
- Log discovered inconsistencies instead of chasing every side issue mid-fix.
- Avoid adding new files, dependencies, generated artifacts, or test data unless they clearly pay for themselves.
- Test both safety and warmth. A correct emergency checklist is not enough if normal users feel punished for normal questions.

## Current High-Value Risks

These are confirmed from the current repo and should steer upcoming work:

- Chat triage uses previous assistant text as classification input, which can make old bot warnings poison new user turns.
- The deterministic fast path includes many non-emergency scenarios, so warm and care conversations often bypass the LLM.
- Action cards are inferred from the assistant response text, so generic warnings can create irrelevant scary cards.
- Clearing chat history does not clear all analysis context state.
- Analysis-to-chat handoff auto-fills a clinical message as if the user typed it.
- The image test fixtures reuse a few external image URLs across many unrelated labels. Some fixtures tagged as bleeding, fracture, choking, heatstroke, or eye injury use generic dog photos, so they do not prove visual truth. This should be replaced with locally controlled, accurately labeled fixtures or split into text-only routing tests and real image-analysis tests.
- Groq-dependent tests are useful but cannot be the only regression protection. Router, context, card, and fallback tests should run without network or API keys.

## Target Product Modes

- Warm mode: greetings, dog introductions, breed curiosity, learning, and healthy-dog reassurance.
- Care mode: mild or uncertain symptoms, routine care, feeding, skin, ticks, diarrhea without red flags, and follow-up questions.
- Emergency mode: choking, not breathing, collapse, seizure in progress, heavy bleeding, road trauma, poisoning, heatstroke, entrapment, and human rabies exposure.
- Repair mode: user corrections such as "no seizure", "stop repeating", "that's wrong", or "new topic".

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

For UI or user-flow changes, start the dev server and check the actual screen, not just the compiler. The app should be useful, readable, and emotionally appropriate for the situation.
