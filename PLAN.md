Progress: Stages 0-6 complete. Current implementation pass completed Stage 7 IA, Stage 7A client-side per-image threads, Stage 7B tone/action-card routing, Stage 7G drives mailing-list storage, and partial Stage 7C first-aid/cruelty surfaces. Remaining major work: quiz depth, medicine KB-backed chat/image surfacing, multi-species kernels, login/IP persistence, Railway durability, and full E2E verification.

# IndieAid Revival Plan

## 1. Intent

IndieAid is a care and first-aid app for pets, street animals, and the people who stop to help them. The product should feel calm, loving, practical, and trustworthy. It should be robust when an animal or person may be in danger, and warm when someone is learning, checking on a healthy animal, or asking a normal care question.

The goal is not to make the app "less safe." The goal is to make it safer by distinguishing real emergencies from normal care interaction, by letting users correct the assistant, and by preventing stale context from turning every conversation into the last emergency it saw.

Product modes:

- `warm`: greetings, animal introductions, breed/species curiosity, learning, healthy-animal reassurance.
- `care`: mild or uncertain symptoms, feeding, skin, ticks, diarrhea without red flags, routine vet planning, community-animal care, deceased/passed-away pet aftercare.
- `emergency`: choking, not breathing, collapse, seizure in progress, heavy bleeding, road trauma, poisoning, heatstroke, entrapment, human rabies exposure.
- `repair`: user corrections, "stop repeating," "that's wrong," "new animal," "new topic," or "no, not that."

Within `emergency` and high-urgency `care`, the assistant uses a tighter "lock-in / fixer" register: action first, rationale second, escalation third, no chatty preamble.

Species scope:

- Dogs are the primary, fully-supported species (current state).
- Cats and cows are first-class targets for Stage 7E.
- All other species fall back to a conservative "general animal" path with strong vet deferral.

Core principle: LLM-forward does not mean LLM-only. Code owns safety boundaries, context policy, schemas, and UI routing. The LLM owns nuance, tone, proportionality, and humane explanation when the situation is not a deterministic emergency.

Language principle: English, Hindi, and Marathi are equal priorities for this plan. Multilingual access is not a final translation pass. Routing, prompts, UI copy, tests, cards, fallbacks, and verification must all treat these three languages as first-class product surfaces. Additional Indian languages, voice input/output, and a design overhaul to make the app unique and memorable are explicitly the **next** features after this plan closes — keep contracts and IA clean enough that they don't require rework.

## 2. Current Ground Truth

Already implemented (Stages 0–6):

- Assistant replies removed from heuristic triage evidence.
- Mode router with `warm` / `care` / `emergency` / `repair` and `context_used` audit field.
- Mode-specific prompts for English, Hindi, Marathi.
- Analysis-to-chat handoff replaced with a visible banner; structured `analysis_context` schema with 30-min expiry.
- Scenario-family fallbacks for image analysis (healthy, mild, urgent, unavailable, no-animal-visible).
- Deceased pet handling in triage and chat responses.
- Clear-history clears analysis context.
- Router/card tests for warm, repair, negation, stale context, mild care, and emergency cases (dog-only).

Confirmed remaining work and risks:

- Single global chat with one optional analysis-context slot — old photo context leaks across topics or evaporates after one pass. Per-image chat threads + a real chat/image storage model are missing.
- Tone within modes is correct but flat: warm replies lack human acknowledgements; emergency replies still hedge.
- Home screen mixes essentials and secondary features. Essentials must remain frictionless (no login, no geolocation gate).
- Earlier versions of the app surfaced OTC medicine guidance in chat and image analysis; that information was removed in error and must be restored behind a sourced KB.
- No first-aid-kit screen — first aid is currently only inline action cards.
- No animal-cruelty path — cruelty reports get treated as medical emergencies.
- App is dog-only end-to-end (triage, prompts, vision, resources, guides). Cat photos are analyzed as dogs.
- No login, no forums, no verified-report concept. Anonymous users lose context across devices/private windows.
- Learn page is static; no quizzes.
- No drives / mailing-list coordination surface.
- Railway durability for SQLite and uploaded report images is not yet proven; new tables (mailing list, users, threads) will compound this risk.
- Production env, Groq key availability, rate limits, CORS, Vercel API URL, and deployed branch behavior still need verification.

## 3. Operating Rules

Work in small, push-safe stages. Every stage should be safe to stop, commit, push, and resume.

Rules for every stage:

- Check current behavior before changing it.
- Keep changes scoped to the stage.
- Do not chase side issues unless they block the stage or create obvious user harm.
- Log discovered inconsistencies in `docs/indieaid-working-context.md` instead of expanding scope mid-fix.
- Avoid new dependencies, generated assets, large fixture blobs, and broad rewrites unless the stage explicitly calls for them.
- Do not hardcode a growing tree of ordinary chat responses. Hardcode only safety gates, schema fallbacks, and true emergency kernels.
- Do not treat unverified internet images as labels for bleeding, fracture, seizure, choking, eye injury, or other visual diagnoses.
- Do not add English-only user-facing text in a user-facing surface. English, Hindi, and Marathi copy should land together unless the text is internal-only.
- Do not make Hindi or Marathi feel like stiff word-for-word translations of English.
- Do not hide uncertainty behind generic disclaimers. Say what is known, what is uncertain, and what the human should do next.
- Do not put friction (login, geolocation gate, language confirmation) in front of essentials: Chat, Analyze, Find Help, emergency CTA.

Verification rhythm:

- Before edit: run the smallest useful baseline check for the area.
- After edit: run targeted tests plus `npm run build` for frontend-impacting work.
- Before push: inspect `git diff`, avoid unrelated files, and stage paths explicitly.
- After push: check GitHub, Vercel preview, and Railway health/API behavior where accessible.

Multilingual access requirements:

- Support English, Hindi, Marathi, and common code-mixed forms.
- Keep safety classification canonical: language-specific text maps into shared fields (`mode`, `scenario_type`, `urgency_tier`, `negated_symptoms`, `species`, `intent`).
- Use reviewed, stable emergency wording for all three languages. The LLM can adapt tone, but emergency meaning must not drift.
- Tests must include all three languages for core safety and product-mode behavior before a stage is considered done.

## 4. Execution Stages

### Stages 0–6: Complete

Foundation, persistent context doc, test truth cleanup, typed mode routing, mode-specific prompts, analysis-to-chat handoff, and analysis quality + vision fallbacks. See git history (`git log`) and `docs/indieaid-working-context.md` for details.

### Stage 7: App Feel & Information Architecture

Purpose: Make the app feel like one product. Hide non-essential features from the main screen; keep essentials frictionless and visible.

Actions:

- Audit `frontend/src/app/page.tsx`. Define essentials as Chat, Analyze, Find Help, and a single emergency CTA. Surface only these on home.
- Move secondary surfaces (Learn, Report, First-Aid Kit, Drives, Cruelty, Quizzes, Settings) into a "More" tray.
- Essentials must never require login, geolocation grant, or language confirmation. Language selector stays available but does not block entry.
- Keep nav consistent across home, chat, analyze, learn, nearby, report.
- Action cards in `backend/app/routers/chat.py` (`_build_triage_action_cards`) routed from `mode + urgency + scenario_type + intent`. Warm/care cards visually lighter than emergency cards.
- Verify English/Hindi/Marathi parity across surfaces.

Definition of done:

- Home shows only essentials; non-essentials reachable but tucked.
- Warm/care chats never render emergency-styled cards.
- UI feels like one product across pages.

### Stage 7A: Chat & Image Storage Model + Per-Image Threads

Purpose: Replace the broken global-chat / single-analysis-slot model with per-image chat threads and a real local storage model.

Actions:

- Define `ChatThread`: `{ id, kind: "general" | "image", image_id?, created_at, last_used_at, messages[], analysis_context? }`.
- Define `ImageRecord`: `{ id, blob (compressed), thumbnail_blob, created_at, analysis_status, analysis_context }`.
- Storage: IndexedDB (via `idb-keyval` or a tiny helper) for blobs and large arrays; small index in localStorage for fast list rendering.
- Migrate legacy `indieaid-chat-history` and `indieaid-analysis-context` keys into the general thread, then remove.
- Compress images client-side before storing: max 1280px long edge, JPEG q≈0.8. Keep a smaller thumbnail.
- When a user analyzes a photo, open or focus that image's thread. Analysis context is stored on the thread, not on a global slot.
- Chat list UI: compact thread switcher showing general thread + recent image threads with thumbnails. Cap at 20; evict oldest.
- "Clear chat" clears the **current** thread only; a separate "Clear all" option clears storage.
- Backend: `analysis_context` continues to flow per-request as today. No backend chat persistence in this stage.
- Tests: thread isolation; legacy-key migration; eviction.

Definition of done:

- Every image gets its own thread with persistent context.
- General chat is separate and clean.
- Old context-leak-then-evaporate behavior is gone.
- Storage stays under a sane cap.

### Stage 7B: Tone Polish — Warmth and Lock-In

Purpose: Refine the human feel within each mode. No new hardcoded ordinary-chat strings.

Actions:

- Update warm-mode prompt to invite small genuine compliments and human acknowledgements ("she sounds adorable", "good of you to check"). Forbid sycophancy lists or templated openers.
- Update emergency and high-urgency care prompts to a "lock-in / fixer" register: action first, rationale second, escalation third. Apply only when `mode == emergency` or (`mode == care` AND `urgency_tier >= high`).
- Care-mid and warm modes keep the proportionate, gentle register from Stage 4.
- Repair-mode prompt stays tight; correction acknowledgement is enough.
- All four mode prompts updated for English, Hindi, Marathi together.
- Tone tests: warm reply has a human acknowledgement and no numbered checklist; emergency reply leads with an imperative within the first sentence; care reply lists monitor / call-vet / red-flags clearly.

Definition of done:

- Warm replies feel kind without being hardcoded.
- Emergencies feel locked-in and direct.
- Tone tests cover all three languages.
- No hardcoded warm strings introduced.

### Stage 7C: First-Aid Kit Screen & Animal-Cruelty Section

Purpose: Provide a real first-aid surface — first aid is first aid, whatever it takes to help an animal in front of the user. Distinct from Learn (which teaches). Add a cruelty path covering all strays.

Key correction: The first-aid kit is **not** a "no new clinical claims" surface. Earlier versions surfaced OTC medicine guidance directly in chat and in the image analyser; that was removed in error and must be restored here and in Stage 7F.

Actions:

- New route `frontend/src/app/first-aid-kit/page.tsx`. Browsable grid: bleeding, choking, heatstroke, poisoning, road trauma, skin/ticks, puppies, deceased pet aftercare, wound cleaning, fracture stabilization, dehydration / oral rehydration, OTC medicine basics.
- Each topic includes: immediate steps, OTC items reasonable to use (per Stage 7F medicine KB), red flags meaning stop and go to vet, and a one-line "if you remember nothing else" line.
- Reuse `_GUIDE_LABELS` from `backend/app/routers/chat.py` so kit topics and chat action cards share IDs.
- Restore OTC medicine surfacing in chat replies and image-analysis output where appropriate, gated by Stage 7F medicine KB so claims stay sourced and species-checked.
- New route `frontend/src/app/cruelty/page.tsx`. Covers cruelty against **all strays** — dogs, cats, cows, other animals. Sections: how to recognize, how to document safely, where to report (city-specific verified contacts), what **not** to do.
- Add `animal_cruelty_witnessed` scenario to triage so chat routes here instead of treating cruelty as medical emergency.
- Add cruelty + general-stray resources to `backend/data/help_resources.json` with verified, dated sources.
- All copy and resources in English/Hindi/Marathi together.
- Both screens reachable from "More" tray.

Definition of done:

- Kit screen actively helps a user act, including OTC guidance, instead of redirecting them away.
- Cruelty page covers all strays with verified contacts and clear non-medical framing.
- Triage routes cruelty reports to the cruelty surface, not the emergency action-card row.

### Stage 7D: Learn Mode Quizzes

Purpose: Add light quizzes covering both Learn guides and first-aid teachings.

Actions:

- Quiz data file `backend/data/learn_quizzes.json`. Topics: existing Learn guides (approach, trauma, heat, poison, skin, puppies) **and** first-aid kit topics (bleeding, choking, dehydration/ORS, OTC medicine basics, wound care, fracture stabilization, deceased pet aftercare). 3–5 multiple-choice items per topic. English/Hindi/Marathi from the start.
- Frontend quiz component embedded under each Learn guide and on each first-aid-kit topic page. State held in component; no scoreboards, no telemetry.
- Each item has a correct answer + a baseline one-sentence explanation in JSON.
- Optional LLM-fresh feedback: when an API key is available and the user answers wrong, a small grounded LLM call may regenerate the explanation in a fresh, encouraging way. Falls back to static explanation on failure or missing key. Correctness is never decided by the LLM.
- Tests: quiz JSON shape; component renders all three languages; correct/incorrect feedback path with key absent (static) and present (LLM-fresh, grounded).

Definition of done:

- Every Learn guide and major first-aid topic has an inline quiz in three languages.
- Quizzes work fully offline / no-key.
- LLM-fresh feedback enhances but never decides correctness.

### Stage 7E: Multi-Species Support (cats, cows, general animal fallback)

Purpose: Extend beyond dog-only. Cats and cows become first-class targets; everything else uses a conservative general-animal fallback.

Actions:

- Research and select first-aid sources for cats and cows. Capture source URL + date in `docs/indieaid-working-context.md`. Prefer Indian veterinary sources where available.
- Add `species: "dog" | "cat" | "cow" | "other"` to triage and analysis schemas. Default `dog` for backward compatibility.
- Vision: add a species-detection step. If `species == other`, switch to a conservative general-animal prompt that says what is observed and defers strongly to a vet.
- Triage prompts and emergency kernels: dog kernels stay; cat and cow get their own narrow kernel sets (only high-confidence emergencies). `other` species → care/repair routing only, no species-specific emergency claims.
- Resources: add `species` filter to `help_resources.json`. Cat clinics, livestock helplines, etc.
- Action cards and Learn guides: add cat-specific and cow-specific entries; keep dog content untouched.
- All multilingual.
- Tests: species detection on labeled fixtures; cat-emergency routing; cow injury → livestock contacts; unknown species → general advice with explicit deferral.

Definition of done:

- A cat photo is not analyzed as a dog.
- Cow injury routes to livestock contacts.
- Unknown species gets honest "I can't be sure, here is general guidance" rather than fabricated dog advice.
- Emergency claims are only made for species where kernels exist.

### Stage 7F: Medicine Guidance & Safer-Alternative Counters

Purpose: Restore positive OTC guidance that earlier versions provided, and add counters for unsafe human medicines. Highest safety risk in the plan; requires the most explicit guardrails.

Two complementary directions, both needed:

1. **Restore OTC guidance** — what is reasonable to use at home (diluted antiseptic for minor wounds, ORS-style rehydration, species-appropriate OTC items where vet-sourced guidance supports it). Surfaced in chat, image analyser, and first-aid-kit screen.
2. **Counter unsafe human medicines** — clearly flag dangerous misuses with safer alternatives (paracetamol → cats, ibuprofen → dogs/cats, etc.).

Actions:

- Medicine knowledge file `backend/data/medicine_kb.json`. Each entry: `{ name, species_safe[], species_unsafe[], typical_use, common_misuse, safer_alternatives[], home_use_ok: bool, requires_vet: bool, dose_guidance: "vet_only" | "general_range_with_caveats", sources: [{ url, accessed_on }] }`. Every entry must cite a veterinary source.
- Triage: add `intent: "medicine_question"`. Route to a dedicated medicine prompt that:
  - states whether the medicine is generally safe, conditional, or unsafe for that species,
  - if safe and `home_use_ok`, gives practical guidance grounded in the KB entry (do not invent doses; defer numeric dosing to a vet unless the KB explicitly captures a general range),
  - if unsafe, names safer alternatives and recommends a vet,
  - always names red flags meaning stop and go to vet.
- Hardcoded deny-list for the most dangerous misuses (paracetamol → cats, ibuprofen → dogs/cats, chocolate, grapes, xylitol, etc.) so a model outage cannot return permissive advice.
- Image analyser: when analysis surfaces a treatable condition with an OTC option in the KB, include the OTC suggestion in the analysis output (subject to KB grounding).
- Frontend: medicine answers and image-analysis OTC suggestions render with a distinct callout (not an ordinary chat bubble) carrying the source citation.
- All multilingual.
- Tests: unsafe-medicine question always triggers refusal + safer alternative, even with no API key; safe OTC question returns KB-grounded guidance with citation; image analyser includes OTC suggestion when KB matches the analysis condition.

Definition of done:

- The app once again gives practical OTC guidance where the KB supports it, in chat and in image analysis.
- Unsafe-medicine asks always counter with safer alternatives.
- Everything is sourced and works with or without an API key.

### Stage 7G: Drives / Collaboration Mailing List

Purpose: Let people opt in to food/water/medicine drive coordination without building a full social product.

Actions:

- Backend: new endpoint `POST /api/mailing-list/subscribe` in a new router `backend/app/routers/community_drives.py`. Accepts email, optional city, optional interest tags (food, water, medicine, transport). Stores in a new SQLite table `mailing_list` in the existing DB. Idempotent on email.
- Rate-limit and basic email-format validation. No verification email yet.
- Frontend: new route `frontend/src/app/drives/page.tsx`. Explains the list (coordination only, no spam, easy unsubscribe), single-screen signup form. Reachable from "More" tray.
- Unsubscribe via tokenized link deferred to Stage 7H or later.
- Privacy note: no analytics, no third-party email service in this stage; just stored locally.
- Tests: subscription persists; duplicate email is idempotent; bad email is rejected.

Definition of done:

- Users can sign up for drive coordination.
- Data is stored in SQLite.
- Page is honest about being early and manually-coordinated.

### Stage 7H: Login, IP-Based Anonymous Persistence, & Database Expansion

Purpose: Login is genuinely important — the gate for in-app forums, inter-user interactions, and trust-checking before any user is allowed to file or endorse "verified reports." Essentials must remain login-free. Anonymous users still deserve to keep precious context across sessions, so use IP-based server persistence as a fallback.

Two-tier persistence model:

- **Logged-in users**: full server-side sync — chat threads, image records, report ownership, forum posts, verified-report endorsements.
- **Anonymous users**: IP-keyed lightweight server persistence (chat threads + image records only) so a user returning from the same network keeps context. IndexedDB on the client remains primary; IP-keyed cache is a fallback for device loss / private windows. Clearly disclosed; expires within ~30 days; never shown to anyone else; never used for any social feature.

Actions:

- Constraint: nothing on the home essentials path may require login. Login is a button in More/Settings, never a wall on essentials.
- Login is **required** for: forum/community surfaces, endorsing or filing verified reports, replying to other users, drive coordination beyond simple subscribe.
- Backend auth: choose magic-link email (reuses SMTP from Stage 7G) or Supabase. Magic-link preferred for simplicity.
- Database: extend `backend/app/database.py` with `users`, `chat_threads`, `chat_messages`, `image_records`, plus `anonymous_sessions` keyed by hashed IP + coarse user-agent. Reuse the existing migration pattern.
- Reports: add `user_id` (optional) and `verified` (bool) columns. Anonymous reports continue to work but cannot be marked verified. Verified-report eligibility requires a logged-in account that has cleared a basic trust check (email confirmed, account age ≥ N days, optional phone verification — design captured but ramped after Stage 9).
- Frontend: Stage 7A chat threads sync to server when logged in, IP-cache when anonymous, IndexedDB always. No silent upload of anonymous history into a user account on login — explicit "import this device's history into your account?" prompt.
- Privacy: explicit consent screen on first login + clear note on the anonymous IP-cache (what is stored, how long, how to clear).
- Tests: anonymous IP-cache round-trip; logged-in sync; anonymous → login claim flow with explicit consent; logout wipes server-cached state on the client; verified-report gate.

Definition of done:

- Login exists and gates community/verified-report features.
- Essentials stay login-free.
- Anonymous users keep precious context across sessions via IP-keyed cache.
- No silent data takeover when a user logs in for the first time.

### Stage 8: Report and Production Durability

Purpose: Ensure community reporting and any new persisted state are not silently lossy.

Actions:

- Audit Railway storage for SQLite database and uploaded report images.
- Confirm whether `DB_PATH` and `UPLOADS_DIR` point to durable volume paths in production.
- Verify durability of new tables from Stages 7G and 7H (`mailing_list`, `users`, `chat_threads`, `chat_messages`, `image_records`, `anonymous_sessions`).
- If durable storage exists, document the env/volume contract.
- If durable storage does not exist, either configure durable paths or downgrade affected features in UI/docs until storage is added. In particular, gate Stage 7H sync behind explicit env config rather than shipping partial sync.
- Do not add a full new database provider unless durability cannot be handled with the existing Railway setup.

Definition of done:

- The app no longer silently implies persistence that production cannot guarantee.
- Railway durability is documented for `reports`, `mailing_list`, and any user/thread tables.
- At least one report create/read flow is verified end-to-end if production access allows.

### Stage 9: End-to-End Human Verification

Purpose: Confirm the app works as a human would experience it.

Test matrix:

- Greeting; cute/healthy dog; deceased pet correction without emergency cards; mild diarrhea with no dehydration; vaccine or feeding question; image analysis to chat follow-up; "no, not bleeding"; "stop repeating"; poisoning; road trauma; no API key / model unavailable; failed chat send.
- Per-image thread isolation (Stage 7A).
- Tone shift: warm vs lock-in feel by mode (Stage 7B).
- First-aid kit and cruelty surfaces reachable, correct, multilingual (Stage 7C).
- Quiz interactions, with and without API key (Stage 7D).
- Cat photo, cow photo, unknown-species photo (Stage 7E).
- Dangerous-medicine question — no dose returned, safer alternative shown; safe OTC question — KB-grounded guidance with citation (Stage 7F).
- Mailing-list subscribe + duplicate (Stage 7G).
- Login on/off paths; essentials never gated; anonymous → login claim with consent (Stage 7H).
- Home screen surfaces only essentials; secondary tray contains the rest.
- Each core flow checked in English, Hindi, and Marathi, with a small code-mixed pass.

Definition of done:

- The final PR has a concise verification note.
- Known non-blocking issues are logged, not hidden.
- The app feels warm when safe, grounded when uncertain, and urgent only when urgency is real.

## 5. Public Interface Decisions

Backend schema additions:

- `TriageResult.mode: Literal["warm", "care", "emergency", "repair"]` (already present).
- `TriageResult.context_used: bool` (already present).
- `TriageResult.species: Literal["dog", "cat", "cow", "other"]` (Stage 7E).
- `TriageResult.intent: Literal["general", "medicine_question", "cruelty_witnessed", ...]` (Stages 7C, 7F).
- `AnalysisResponse.species` and `AnalysisResponse.otc_suggestion` (Stages 7E, 7F).
- `ChatRequest.thread_id` and `ChatRequest.image_id` for per-image threads (Stage 7A; backend currently treats these as opaque pass-through until Stage 7H adds server persistence).
- `ChatRequest.analysis_context` and legacy `context_from_analysis` remain as today.

Frontend decisions:

- Type changes in `frontend/src/lib/api.ts` land in the same stage as backend schema changes.
- Chat UI uses a thread switcher; analysis context displays as a banner per thread, not as user text.
- IndexedDB is the primary client store from Stage 7A onward; legacy localStorage keys are migrated and removed.
- Language selector remains visible and reliable on home, chat, analyze, learn, nearby, report, first-aid-kit, cruelty, drives.
- Any new user-facing copy lands for English, Hindi, and Marathi in the same commit.

Suggested structured analysis context shape (unchanged from Stage 5):

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

## 6. Test Matrix

Always-on tests, no API key:

- Mode classification for warm, care, emergency, repair in English, Hindi, Marathi.
- Negation and correction handling.
- Context isolation from previous assistant text and across image threads (Stage 7A).
- Tone-by-mode register checks (Stage 7B).
- Action-card relevance.
- Fallback response families.
- Image-analysis tone for healthy, mild-care, emergency, no-animal, and unavailable.
- Species detection and species-specific routing (Stage 7E).
- Medicine deny-list and safe-OTC KB grounding (Stage 7F).
- Mailing-list idempotency (Stage 7G).
- Anonymous IP-cache and login claim flows (Stage 7H).
- Quiz JSON shape and static feedback path (Stage 7D).
- API schema compatibility.

Optional tests, API key required:

- Small vision sanity suite with verified fixtures.
- Small LLM quality suite for warmth, proportionality, escalation, uncertainty, repetition, image-analysis tone, and naturalness in all three languages.
- LLM-fresh quiz feedback grounding (Stage 7D).

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

- Mode architecture and tone polish.
- Context policy and per-image storage model.
- Analysis handoff and per-image threads.
- First-aid kit and cruelty surfaces.
- Multi-species support.
- Medicine guidance with safer-alternative counters.
- Drives mailing list.
- Optional login with IP-keyed anonymous fallback.
- Information-architecture cleanup.
- Test truth and learn/card relevance.
- Deployment verification and report durability.

Avoid over-scoping:

- Do not redesign the whole UI before the core flows work.
- Do not build a global rescue directory.
- Do not add telemetry, analytics, or feedback collection until privacy and storage expectations are clear.
- Do not migrate databases unless Railway durability cannot be solved with current infrastructure.
- Do not replace all model providers in this pass.
- Do not add large image datasets.
- Do not hardcode a long list of friendly responses to imitate warmth.
- Do not expand beyond English, Hindi, Marathi in this plan.
- Do not build voice input/output in this plan.
- Do not invest in heavy bespoke visual design during this plan; a design overhaul is the next initiative.

Immediately next, after this plan closes:

- Voice input/output. Keep chat and analysis contracts clean enough to wrap with a voice layer without redesign.
- Additional Indian languages. Keep language plumbing free of hardcoded three-language assumptions deeper than necessary.
- Design overhaul to make the app unique and memorable. Stage 7 IA cleanup prepares the ground.

Later backlog, only after core revival:

- Response feedback controls.
- Repetition telemetry.
- City-aware Find Help.
- Better resource source tracking.
- Broader multilingual QA.
- Provider fallback strategy beyond Groq.

## 8. Stage-by-Stage Commit Guidance

Recommended branch sequence for the active stages:

- `revive-app-feel-ia` (Stage 7)
- `revive-image-threads` (Stage 7A)
- `revive-tone-polish` (Stage 7B)
- `revive-first-aid-cruelty` (Stage 7C)
- `revive-quizzes` (Stage 7D)
- `revive-multi-species` (Stage 7E)
- `revive-medicine-kb` (Stage 7F)
- `revive-drives` (Stage 7G)
- `revive-login-and-db` (Stage 7H)
- `revive-report-durability` (Stage 8)
- `revive-e2e-polish` (Stage 9)

Each PR should include: what changed, why it matters for IndieAid's product soul, tests run, deployment checks run, known follow-up issues.

Do not stage unrelated dirty files. If a file has user changes unrelated to the stage, work around them or ask before touching that file.

## 9. Assumptions

- The README product values are authoritative.
- The app remains focused on animals India users actually meet — pets and community/street animals.
- Dogs are the fully-supported species today; cats and cows are next; everything else is general-animal fallback.
- The app gives guidance, not veterinary diagnosis.
- Emergency determinism is desirable only for true emergencies.
- Normal care and warm conversation should use the LLM where available.
- English, Hindi, and Marathi are equal priorities for implementation and verification.
- More languages, voice, and a design overhaul are the immediate next initiatives after this plan.
- Production access may be partial; record what was actually verified rather than implying full verification.
