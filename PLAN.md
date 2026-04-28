Progress: Stage 0 complete - draft PR #7 opened; next task is Stage 1 context doc.

# IndieAid Revival Plan

## 1. Intent

IndieAid is a dog care and first-aid app for pets, street dogs, and the people who stop to help them. The product should feel calm, loving, practical, and trustworthy. It should be robust when a dog or person may be in danger, and warm when someone is learning, checking on a healthy dog, or asking a normal care question.

The goal is not to make the app "less safe." The goal is to make it safer by distinguishing real emergencies from normal dog-care interaction, by letting users correct the assistant, and by preventing stale context from turning every conversation into the last emergency it saw.

Product modes:

- `warm`: greetings, dog introductions, breed curiosity, learning, healthy-dog reassurance.
- `care`: mild or uncertain symptoms, feeding, skin, ticks, diarrhea without red flags, routine vet planning, community-dog care.
- `emergency`: choking, not breathing, collapse, seizure in progress, heavy bleeding, road trauma, poisoning, heatstroke, entrapment, human rabies exposure.
- `repair`: user corrections, "stop repeating," "that's wrong," "new dog," "new topic," or "no, not that."

Core principle: LLM-forward does not mean LLM-only. Code owns safety boundaries, context policy, schemas, and UI routing. The LLM owns nuance, tone, proportionality, and humane explanation when the situation is not a deterministic emergency.

Language principle: English, Hindi, and Marathi are equal priorities for this plan. Multilingual access is not a final translation pass. Routing, prompts, UI copy, tests, cards, fallbacks, and verification must all treat these three languages as first-class product surfaces. Additional Indian languages, voice input/output, and broad localization infrastructure are out of scope for this phase.

## 2. Current Ground Truth

This plan is grounded in the diagnosis document, the README values, and the current repo.

Already implemented locally in the first pass:

- Assistant replies were removed from heuristic triage evidence.
- Repair/meta intent, negation, stale analysis-context handling, and safer card routing were started.
- Clear-history behavior now clears analysis context.
- Route/card tests were added for warm, repair, negation, stale context, mild care, and emergency cases.
- `README.md` was added to document the app soul, deployment shape, risks, and working principles.

Confirmed remaining risks:

- `PLAN.md`, `README.md`, and `backend/tests/test_triage_router.py` are still untracked until Stage 0 is pushed.
- `chatgpt-diagnosis.md` should remain local and uncommitted unless explicitly requested.
- The chat still needs a real mode architecture, not only first-pass heuristics.
- The analysis-to-chat handoff still uses a fake prefilled user message.
- Analysis fallback text is still too generic across healthy, mild, urgent, and unavailable cases.
- Fixture image labels are not trustworthy as visual truth.
- Some tests are still biased toward emergency checklist behavior.
- Railway persistence for SQLite and report image uploads is not yet proven durable.
- Production env, Groq key availability, rate limits, CORS, Vercel API URL, and deployed branch behavior still need verification.

## 3. Operating Rules

Work in small, push-safe stages. Every stage should be safe to stop, commit, push, and resume with GPT-5.5 medium.

Rules for every stage:

- Check current behavior before changing it.
- Keep changes scoped to the stage.
- Do not chase side issues unless they block the stage or create obvious user harm.
- Log discovered inconsistencies in `docs/indieaid-working-context.md` instead of expanding scope mid-fix.
- Avoid new dependencies, generated assets, large fixture blobs, and broad rewrites unless the stage explicitly calls for them.
- Do not hardcode a growing tree of ordinary chat responses. Hardcode only safety gates, schema fallbacks, and true emergency kernels.
- Do not treat unverified internet images as labels for bleeding, fracture, seizure, choking, eye injury, or other visual diagnoses.
- Do not add English-only user-facing text in a user-facing surface. English, Hindi, and Marathi copy should land together unless the text is internal-only.
- Do not make Hindi or Marathi feel like stiff word-for-word translations of English. They should be simple, natural, and safe, with the same product mode as the English response.
- Do not hide uncertainty behind generic disclaimers. Say what is known, what is uncertain, and what the human should do next.

Verification rhythm:

- Before edit: run the smallest useful baseline check for the area.
- After edit: run targeted tests plus `npm run build` for frontend-impacting work.
- Before push: inspect `git diff`, avoid unrelated files, and stage paths explicitly.
- After push: check GitHub, Vercel preview, and Railway health/API behavior where accessible.

Multilingual access requirements:

- Support English, Hindi, Marathi, and common code-mixed forms across those languages.
- Keep safety classification canonical: language-specific text should map into shared fields such as `mode`, `scenario_type`, `urgency_tier`, and `negated_symptoms`.
- Use reviewed, stable emergency wording for English, Hindi, and Marathi. The LLM can adapt tone, but emergency meaning must not drift.
- Warm and care responses should be natural in the selected language, not rigid translations.
- Tests must include all three languages for core safety and product-mode behavior before a stage is considered done.
- Broader language expansion is explicitly deferred until the current three-language experience is reliable.

## 4. Execution Stages

### Stage 0: First-Pass Checkpoint

Purpose: Preserve the already-made safety and README improvements before deeper work.

Actions:

- Re-run focused backend tests and full frontend build.
- Confirm current first-pass chat behavior for greeting, mild diarrhea, correction, stale context, poisoning, and road trauma.
- Stage only `README.md`, `backend/app/routers/chat.py`, `backend/app/services/triage.py`, `frontend/src/app/chat/page.tsx`, and `backend/tests/test_triage_router.py`.
- Do not stage `chatgpt-diagnosis.md`.
- Commit, push a branch, and open a draft PR.

Definition of done:

- Backend tests pass locally.
- Frontend build passes locally.
- Draft PR exists with a concise summary and verification note.
- Vercel preview and Railway `/health` are checked if credentials/tools allow.

### Stage 1: Persistent Context and Task Ledger

Purpose: Prevent context drift and make future agents productive quickly.

Actions:

- Add `docs/indieaid-working-context.md`.
- Include product soul, architecture map, current mode target, safe-push workflow, known risks, and active task queue.
- Include the equal-priority language contract for English, Hindi, and Marathi.
- Add a short "discovered issues log" section for non-blocking inconsistencies found during later work.
- Link to `PLAN.md` and `README.md`.
- Keep the doc concise enough to load at the start of future tasks.

Definition of done:

- A future agent can read README plus the context doc and know what IndieAid is, what not to break, and what task is next.
- No private diagnosis text is copied wholesale into committed docs.

### Stage 2: Test Truth Cleanup

Purpose: Stop tests from rewarding the wrong product or trusting mislabeled images.

Actions:

- Audit `backend/tests/fixtures/**/labels.json`.
- Split fixtures into three categories:
  - text/router fixtures for intent and triage,
  - mocked vision fixtures for API shape and analysis behavior,
  - verified local image fixtures only when the image content is actually known.
- Remove or quarantine random external image URLs as visual truth.
- Update emergency tests so numbered first-aid checklist expectations apply only to true emergency fixtures.
- Ensure key router, card, context, and fallback tests run without Groq or network access.

Definition of done:

- CI-safe tests catch warm/care/repair regressions without API keys.
- No test claims a visual emergency from an unverified cute dog photo.
- Emergency tests remain, but they no longer define the whole product.

### Stage 3: Typed LLM-Forward Routing

Purpose: Replace emergency-biased product routing with an explicit mode router.

Actions:

- Add `mode` to triage output: `warm`, `care`, `emergency`, or `repair`.
- Add `context_used: bool` to triage output so stale-context decisions are auditable.
- Keep existing urgency and scenario fields for compatibility.
- Keep deterministic code only for:
  - repair/meta intent,
  - negation/correction handling,
  - high-confidence current-message emergencies,
  - no-key/no-model fallback,
  - action-card policy.
- Add an LLM classifier for non-emergency or ambiguous mode selection with a small JSON schema.
- Ensure the classifier handles English, Hindi, Marathi, and common code-mixed English-Hindi-Marathi inputs through the same canonical output fields.
- If the LLM classifier fails, degrade to a conservative non-emergency clarification unless a deterministic emergency gate fired.

Definition of done:

- `hi` routes warm.
- Equivalent Hindi and Marathi greetings route warm.
- `i have a cute dog` routes warm.
- `just started diarrhea no dehydration` routes care, not emergency.
- Equivalent Hindi, Marathi, and code-mixed mild-symptom messages route care, not emergency.
- `no seizure is happening` does not route seizure emergency.
- Equivalent Hindi, Marathi, and code-mixed negations clear the emergency scenario.
- `stop repeating yourself` routes repair.
- `dog hit by car and cannot stand` routes emergency.
- Equivalent Hindi, Marathi, and code-mixed emergency messages route emergency.
- Tests prove assistant history is not raw emergency evidence.

### Stage 4: Mode-Specific Response Generation

Purpose: Let IndieAid change emotional register without losing emergency clarity.

Actions:

- Replace the single emergency-first chat prompt with mode-specific prompts.
- Maintain mode-specific prompt guidance for English, Hindi, and Marathi as equal paths.
- Emergency prompt:
  - short, direct, action-first,
  - no chatty preamble,
  - contact help clearly,
  - avoid unsafe medication/dosing advice.
- Care prompt:
  - proportionate,
  - asks one or two useful follow-up questions when needed,
  - separates monitor, call-vet, and emergency red flags,
  - avoids diagnosis certainty.
- Warm prompt:
  - friendly, curious, and dog-loving,
  - no checklist unless symptoms appear,
  - can invite care, training, feeding, grooming, or breed questions.
- Repair prompt:
  - acknowledges correction,
  - resets or narrows context,
  - does not repeat the previous emergency script.
- Remove hardcoded warm/care prose once model-backed prompts safely cover those paths.

Definition of done:

- Warm and care replies are not deterministic checklist clones.
- Warm and care replies are natural in English, Hindi, and Marathi, not stiff English-shaped translations.
- True emergency replies stay fast and concrete.
- True emergency replies preserve the same safety meaning across English, Hindi, and Marathi.
- No response path returns irrelevant scary cards because of its own warning text.
- API-key-missing behavior is honest and useful rather than fake-confident.

### Stage 5: Analysis-to-Chat Handoff

Purpose: Stop pretending the user typed a clinical report, while preserving useful photo context.

Actions:

- Remove the fake prefilled chat input after image analysis.
- Add a visible chat banner: "Using previous photo analysis" with clear/new-dog controls.
- Localize the banner and controls in English, Hindi, and Marathi in the same change.
- Keep the input empty or use only a neutral placeholder.
- Add optional structured `analysis_context` to `ChatRequest`.
- Keep `context_from_analysis` temporarily for backward compatibility.
- If both are present, structured context wins.
- Add timestamp/source metadata so old analysis context can expire or be ignored when the user changes topic.

Definition of done:

- Coming from analysis does not create a fake user message.
- Clearing chat, new dog, failed send, and unrelated standalone questions clear or ignore stale analysis context.
- Frontend API types and backend schemas change together.
- The handoff UI is understandable in English, Hindi, and Marathi.

### Stage 6: Analysis Quality and Vision Fallbacks

Purpose: Make image analysis feel observant and honest instead of repetitive.

Actions:

- Replace the generic fallback family with scenario families:
  - healthy pet,
  - healthy stray/community dog,
  - sad/quiet but no red flags,
  - mild concern/monitor,
  - urgent but stable,
  - immediate emergency,
  - no dog visible,
  - analysis unavailable.
- Add an explicit analysis status such as `complete`, `uncertain`, `no_dog_visible`, or `unavailable`.
- Provide equivalent fallback response families in English, Hindi, and Marathi.
- If no vision key/model is configured, return `unavailable`, not "no dog detected."
- Decide on the legacy multi-call vision path:
  - either remove it if it is unmaintained,
  - or add parity tests showing it matches the combined vision path's contract.

Definition of done:

- A healthy dog does not get the same advice as an injured dog.
- A model outage does not pretend to know what is in the image.
- Analysis results still give clear next steps for real emergencies.
- Analysis summaries, safety wording, and fallback families are mode-appropriate in English, Hindi, and Marathi.

### Stage 7: Learn, Cards, Resources, and App Feel

Purpose: Make the whole app feel like IndieAid, not just a patched chat endpoint.

Actions:

- Add non-emergency Learn/resource content for:
  - mild symptom monitoring,
  - food and water basics,
  - vaccination and vet planning,
  - indie dog temperament,
  - community/street dog care,
  - grooming and skin basics,
  - training and socialization basics.
- Add or update this content in English, Hindi, and Marathi together.
- Keep medical claims conservative and practical.
- Route action cards from mode, urgency, scenario, and current user intent only.
- Add warm/care cards without emergency visual weight.
- Verify home, chat, analyze, learn, nearby, and report read as one product.
- When changing resource contacts or claims, verify current source pages and record source/date in the context doc or data note.

Definition of done:

- Warm mode can suggest useful learning paths without escalating.
- Care mode suggests relevant care content and escalation signs.
- Emergency mode surfaces Find Help and one relevant guide.
- UI copy feels calm and kind in normal flows, direct in urgent flows.
- Learn/cards/resources are not English-first with Hindi/Marathi lagging behind.

### Stage 8: Report and Production Durability

Purpose: Ensure community reporting is not presented as reliable if deployment storage is temporary.

Actions:

- Audit Railway storage for SQLite database and uploaded report images.
- Confirm whether `DB_PATH` and `UPLOADS_DIR` point to durable volume paths in production.
- If durable storage exists, document the env/volume contract.
- If durable storage does not exist, either:
  - configure durable paths, or
  - clearly downgrade the report feature in UI/docs until proper storage is added.
- Do not add a full new database provider in this stage unless durability cannot be handled with the existing Railway setup.

Definition of done:

- The app no longer silently implies report persistence that production cannot guarantee.
- Railway health and at least one report create/read flow are verified if production access allows.

### Stage 9: End-to-End Human Verification

Purpose: Confirm the app works as a human would experience it, not just as tests see it.

Actions:

- Test local and deployed flows:
  - greeting,
  - cute/healthy dog,
  - mild diarrhea with no dehydration,
  - vaccine or feeding question,
  - image analysis to chat follow-up,
  - "no, not bleeding",
  - "stop repeating",
  - poisoning,
  - road trauma,
  - no API key/model unavailable,
  - failed chat send.
- Check each core flow in English, Hindi, and Marathi.
- Include at least a small code-mixed pass for common English-Hindi-Marathi usage.
- Use browser automation if available; otherwise run a manual browser pass and record what was checked.
- Confirm no in-app text overlaps, scary cards appear only when appropriate, and normal users are not punished for normal questions.

Definition of done:

- The final PR has a concise verification note.
- Known non-blocking issues are logged, not hidden.
- The app feels warm when safe, grounded when uncertain, and urgent only when urgency is real.

## 5. Public Interface Decisions

Backend schema changes:

- `TriageResult.mode: Literal["warm", "care", "emergency", "repair"]`.
- `TriageResult.context_used: bool`.
- Preserve `language` as an explicit request/response concern. Do not infer language only from UI state when the message text clearly differs.
- Keep `urgency_tier`, `scenario_type`, `info_sufficient`, `missing_facts`, `needs_helpline_first`, and `rationale`.
- `ChatRequest.analysis_context` is optional and structured.
- `ChatRequest.context_from_analysis` remains optional for compatibility during migration.
- `ChatResponse.triage` exposes `mode` and `context_used`.
- `AnalysisResponse.analysis_status` is added if needed for unavailable/uncertain model states.

Suggested structured analysis context shape:

```json
{
  "source": "image_analysis",
  "created_at": "ISO-8601 timestamp",
  "scenario_type": "healthy_or_low_risk",
  "urgency_signals": [],
  "unknown_factors": [],
  "emotion": { "label": "relaxed", "confidence": 0.72 },
  "condition": {
    "physical_condition": "appears healthy",
    "visible_injuries": [],
    "health_concerns": [],
    "body_language": "relaxed"
  },
  "user_context": "optional human note"
}
```

Frontend decisions:

- Type changes in `frontend/src/lib/api.ts` must land in the same stage as backend schema changes.
- Chat UI should show analysis context as a banner, not as user text.
- Existing localStorage keys should be migrated or cleared intentionally. Do not leave hidden legacy context behind.
- Language selector behavior must remain visible and reliable on home, chat, analyze, learn, nearby, and report.
- Any new user-facing copy must be added for English, Hindi, and Marathi in the same commit.

## 6. Test Matrix

Always-on tests, no API key:

- Router mode classification for warm, care, emergency, repair in English, Hindi, and Marathi.
- Negation and correction handling in English, Hindi, Marathi, and common code-mixed forms.
- Context isolation from previous assistant text.
- Analysis context expiry/clear behavior.
- Action-card relevance.
- Fallback response families.
- API schema compatibility.

Optional tests, API key required:

- Small vision sanity suite with verified fixtures.
- Small LLM quality suite for warmth, proportionality, escalation, uncertainty, repetition, and naturalness in English, Hindi, and Marathi.
- Do not let API-key tests be the only protection against routing regressions.

Minimum commands before pushing code:

```powershell
cd backend
pytest
```

```powershell
cd frontend
npm run build
```

For frontend or flow changes, also start the app and inspect the actual UI.

## 7. Scope Controls

Keep in scope:

- Mode architecture.
- Context policy.
- Analysis handoff.
- Fallback variety.
- Test truth.
- Learn/card relevance.
- Deployment verification.
- Report durability audit.

Avoid over-scoping:

- Do not redesign the whole UI before the core flows work.
- Do not build a global rescue directory.
- Do not add telemetry, analytics, or feedback collection until privacy and storage expectations are clear.
- Do not migrate databases unless Railway durability cannot be solved with current infrastructure.
- Do not replace all model providers in this pass.
- Do not add large image datasets.
- Do not hardcode a long list of friendly responses to imitate warmth.
- Do not expand beyond English, Hindi, and Marathi in this plan.
- Do not build voice input/output in this plan.
- Do not treat the diagnosis doc as a spec to copy blindly; use it as evidence, then verify against repo behavior.

Later backlog, only after core revival:

- Response feedback controls.
- Repetition telemetry.
- City-aware Find Help.
- Better resource source tracking.
- Broader multilingual QA.
- Additional Indian languages after the English-Hindi-Marathi experience is stable.
- Voice input/output after text flows are reliable and privacy implications are understood.
- Provider fallback strategy beyond Groq.

## 8. Stage-by-Stage Commit Guidance

Recommended branch sequence:

- `revive-foundation`
- `revive-context-doc`
- `revive-test-fixtures`
- `revive-mode-routing`
- `revive-mode-prompts`
- `revive-analysis-handoff`
- `revive-analysis-quality`
- `revive-learn-cards`
- `revive-report-durability`
- `revive-e2e-polish`

Each PR or push should include:

- What changed.
- Why it matters for IndieAid's product soul.
- Tests run.
- Deployment checks run.
- Known follow-up issues.

Do not stage unrelated dirty files. If a file has user changes unrelated to the stage, work around them or ask before touching that file.

## 9. Assumptions

- The diagnosis document remains local and uncommitted.
- The README product values are authoritative.
- The app remains focused on dogs, especially pets and community/street dogs.
- The app gives guidance, not veterinary diagnosis.
- Emergency determinism is desirable only for true emergencies.
- Normal care and warm conversation should use the LLM where available.
- English, Hindi, and Marathi are equal priorities for implementation and verification.
- More languages are out of scope until these three are good.
- Production access may be partial; record what was actually verified rather than implying full verification.
