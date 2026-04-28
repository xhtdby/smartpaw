# IndieAid — Combined, Self-Audited Architecture Diagnostic

## Executive diagnosis

IndieAid’s current dysfunction is not a single bad prompt, bad fallback, or bad test. It is a systemic collapse caused by six interacting design choices:

1. The product has been reduced to one mode: emergency first aid.
2. English chat often bypasses the LLM and returns hardcoded fallback text.
3. Triage uses previous assistant messages and stale analysis context as classification input, so old bot replies poison new user turns.
4. Keyword priority makes the first matched emergency label dominate even when the user clearly changes topic.
5. Action cards are triggered by the bot’s own warning language, so harmless conversations surface scary emergency guides.
6. The tests mostly reward emergency behaviour and fail to test normal pet-owner interaction, conversational recovery, or repetition.

The result is exactly what the screenshots and chat logs show: the app feels like a dead checklist machine, repeats itself, misclassifies casual messages as emergencies, and cannot gracefully recover when challenged by the user.

The important correction to my earlier analysis is this: hardcoded responses are not inherently bad. For true emergencies such as choking, collapse, severe bleeding, heatstroke, poisoning, road trauma, and rabies exposure, fast deterministic responses are desirable. The failure is that this emergency path expanded into scenarios where conversation, proportionality, and context are essential.

---

## What the user-visible failures prove

### 1. The app cannot handle normal human conversation

Messages like:

* “hi”
* “what’s up”
* “i have a cute dog”
* “all good, he’s just a little sad”

should start warm mode or mild-care mode. Instead they produce fracture, seizure, breathing, trauma, or generic observation checklists. This shows the system lacks a top-level intent router that distinguishes conversation from emergency triage.

### 2. The app gets stuck on previous topics

The screenshot with “just started diarrhoea no dehydration” receiving eye-injury advice is not random. The previous assistant response contained the word “eye,” and the triage classifier searched across the new user message plus previous assistant text. The eye keyword came before diarrhoea in the fixed priority order, so the classifier selected `eye_injury` before it ever reached the diarrhoea logic.

The second buggy chat demonstrates the same class of failure with seizure/collapse. Once the assistant says seizure/collapse-related text, later user messages like “no seizure is happening” and “stop” still trigger the same seizure/collapse fallback. Negation is not understood because the classifier is doing substring matching, not meaning-level classification.

### 3. “Stop repeating yourself” is treated as medical input

A real chatbot should recognize this as a meta-conversation repair request. IndieAid instead routes it back through emergency triage and returns the same canned response. This reveals a missing recovery layer:

* user frustration detection
* contradiction handling
* topic reset handling
* “I got that wrong” acknowledgement
* safe fallback to asking a clarifying question

### 4. The app cannot proportion advice

Mild statements are escalated into emergency structures. Example: “all good, he’s just a little sad” should produce something like:

> Ah, got it — not an emergency. If he’s just a bit quiet, check whether he’s eating, drinking, walking normally, and interested in you. If this is new and lasts more than a day, or you see vomiting, breathing trouble, collapse, pain, or refusal to eat, it’s worth calling a vet.

Instead, the app lists generic warning signs and shows trauma/diarrhoea cards. That is not first aid; it is an overfitted emergency classifier wearing a chat UI.

---

## Root causes

## Root cause 1 — Single-mode product identity

The product copy says “dog first aid & care,” but the backend behaves as if every user is a rescuer in the next few minutes of an emergency. The system prompt, knowledge base, fallback responses, action cards, and tests all assume urgent intervention.

This leaves no legitimate path for:

* pet-owner conversation
* breed curiosity
* healthy-dog reassurance
* nutrition questions
* training questions
* grooming questions
* vaccination planning
* mild symptom monitoring
* post-vet care
* community feeding advice

The app currently has one emotional register: clinical urgency.

## Root cause 2 — Hardcoded fallback expansion beyond true emergencies

The hardcoded fallback system appears to have started as a safety feature. That is sensible for genuine emergencies. But it now covers too many ordinary or moderate scenarios.

Hardcoded emergency responses are appropriate for:

* choking / not breathing
* collapse / seizure in progress
* severe bleeding
* road trauma
* poisoning / toxic ingestion
* heatstroke
* fall/entrapment
* rabies exposure involving a human bite or scratch

They are much less appropriate for:

* mild diarrhoea without dehydration
* tick questions
* mild skin disease
* routine care
* feeding questions
* lost dog questions
* healthy or low-risk dogs
* sad/quiet behaviour
* conversational greetings
* “what breed is this?”

For these, deterministic checklists remove the exact thing the LLM is useful for: asking one good follow-up, matching tone, acknowledging uncertainty, and giving proportional advice.

## Root cause 3 — Triage contamination from previous assistant messages

The current triage design uses some combination of:

* current user message
* analysis context
* previous assistant message or chat history

for keyword matching.

That creates feedback loops because the assistant’s own response contains emergency words. Once those words enter history, the next classification can be dominated by the bot’s previous output instead of the user’s new intent.

This is the direct mechanism behind the repeated eye-injury and seizure/collapse loops.

Important nuance: previous context should not be thrown away completely. It is useful for the LLM’s response. But it should not decide the emergency scenario by raw keyword matching. Classification should heavily privilege the current user message, and use older context only as secondary supporting evidence.

## Root cause 4 — No negation or correction handling

The user said “no seizure is happening.” A robust classifier should downgrade or clear the seizure scenario. The current system likely sees the substring “seizure” and triggers seizure/collapse again.

This is a classic keyword-triage failure. It cannot distinguish:

* “the dog is having a seizure”
* “no seizure is happening”
* “why did you mention seizure?”
* “stop talking about seizure”

All contain the same keyword, but only one is a seizure emergency.

## Root cause 5 — Action cards match against response text

Action cards are triggered by the combined query/response text. Since the assistant includes warnings like “watch for vomiting, wounds, collapse, diarrhoea,” harmless conversations trigger scary guides.

The card layer should be based on:

* current user intent
* selected scenario
* urgency tier
* possibly location

It should not mine the assistant’s own generic warning language for keywords.

## Root cause 6 — Fallback response monoculture

The analysis-page fallback has too few shapes. A happy healthy dog, a nervous stray, a mild skin issue, and an injured dog all get overly similar “approach slowly / offer water / speak softly” advice.

This makes the app feel repetitive even outside chat.

The fallback layer needs at least these response families:

* healthy pet
* healthy stray/community dog
* mild concern / monitor
* unclear but non-urgent
* urgent but stable
* immediate emergency
* no dog visible / bad image

## Root cause 7 — The test suite validates the wrong product

The existing test direction appears to reward emergency correctness while barely testing conversational appropriateness. It is valuable that emergency regressions are tested, but the app is not only an emergency dispatcher. Tests should catch:

* “hi” does not become fracture advice
* “what’s up” does not become emergency advice
* “no seizure is happening” clears seizure context
* “stop repeating” triggers an apology/repair, not another checklist
* “just started diarrhoea no dehydration” routes to mild GI advice, not prior eye advice
* “i have a cute dog” gets warm conversation, not trauma cards
* repeated messages do not produce identical outputs unless a genuine emergency is in progress

---

## Self-audit: where the earlier diagnoses were too strong or incomplete

## Correction 1 — “The LLM is dead code” needs qualification

The stronger version of the claim is: for English users, many recognized scenarios appear to route through deterministic fallback before the LLM can provide a natural response. This makes the LLM effectively absent from the user experience in normal matched scenarios.

But I should not claim absolute dead code without checking the live deployed backend, exact production env vars, and every branch in the actual current commit. Some paths may still reach the LLM, especially unclear scenarios, non-English flows, or branches not covered by the screenshots.

The practical diagnosis remains: the user-visible behaviour is dominated by deterministic fallback and keyword triage, not by a conversational model.

## Correction 2 — Hardcoded responses are not the enemy

Earlier framing risked implying “use the LLM more” as the whole solution. That is incomplete.

The right architecture is hybrid:

* deterministic emergency kernel for time-critical first aid
* LLM conversation layer for normal care, proportional advice, and follow-up questions
* guardrails around the LLM for uncertainty, vet referral, forbidden medication/dosage advice, and escalation triggers

Removing hardcoded emergency advice would be a mistake.

## Correction 3 — The previous warm version may have been unsafe

The user remembers the older chat as warmer and more helpful, but also says it was overconfident and did not direct users to vets enough. That means “restore the old version” is not the answer. The goal is to recover warmth without recovering unsafe confidence.

## Correction 4 — Intent classification is harder than keyword matching

Adding `_classify_intent()` sounds simple, but if implemented with shallow keywords it can reproduce the same fragility. For example:

* “my dog ate chocolate lol” has casual tone but poisoning intent
* “he’s just sleepy” may be benign or collapse depending on context
* “no blood now but he was hit by a bike” is still urgent

Intent routing should use a layered approach, not a single keyword gate.

## Correction 5 — Context should be demoted, not deleted

A naïve fix would classify only the current user message and ignore all history. That solves loops but loses useful continuity. Better:

* current user message decides whether the user is changing topic, negating, correcting, or continuing
* previous context is used only if the current message is explicitly dependent: “more advice,” “what now,” “same dog,” “it got worse”
* assistant messages should never be raw keyword sources for emergency classification
* old analysis context should expire or be tied to a specific conversation/session

## Correction 6 — I did not verify production env or API availability

I cannot confirm from the supplied artifacts whether the Groq key is configured in production, whether rate limits drove the fallback expansion, or whether backend failures cause extra fallback behaviour. Any implementation plan should include verifying production logs and branch behaviour.

---

## Better target architecture

## 1. Three-mode conversational architecture

### Warm mode — default

For greetings, pet introductions, breed curiosity, general questions, normal pet-owner chat.

Example:

> That’s lovely — tell me about him. What’s his name, and is he an indie mix or a breed you know? If you want, I can also help with feeding, grooming, training, or checking whether something looks concerning.

No emergency cards. No numbered first-aid checklist.

### Care mode — mild or uncertain concerns

For non-life-threatening symptoms or routine questions.

Example:

> Mild diarrhoea that just started and no dehydration signs is usually something to monitor closely. Keep water available, avoid rich foods, and watch energy, appetite, vomiting, blood in stool, and gum moisture. If it continues beyond 24 hours, becomes bloody, or the dog seems weak, call a vet.

This mode can ask one or two follow-up questions.

### Emergency mode — true first aid

For obvious danger.

Example:

> This may be urgent. Keep the dog still and away from traffic. Do not give food, water, or medicine. Call a vet/rescue now if breathing is abnormal, the dog cannot stand, there is heavy bleeding, or there was a vehicle impact.

This is where deterministic fallbacks belong.

---

## 2. Layered triage router

Use a four-stage router:

### Stage A — Conversation repair / meta-intent

Detect:

* “stop repeating”
* “why did you say that”
* “that’s wrong”
* “no, not that”
* “new topic”
* “different dog”

These should never be sent through medical emergency keyword matching. They should trigger an apology, reset, or clarifying question.

### Stage B — Negation and correction

Detect negated emergency terms:

* “no seizure”
* “not bleeding”
* “not choking”
* “no dehydration”
* “no vomiting”
* “can walk”
* “breathing fine”

Negated symptoms should reduce or clear urgency instead of triggering it.

### Stage C — Current-message emergency screen

Run deterministic checks only on the current user message for high-risk patterns:

* not breathing / choking / blue gums
* unconscious / collapse / seizure happening
* heavy bleeding / blood pouring
* hit by car / road accident
* poison / toxic ingestion
* heatstroke signs
* trapped in well/pit
* human bite/scratch rabies exposure

### Stage D — LLM or lightweight classifier for mode selection

If not a deterministic emergency, classify as warm/care/informational/unclear. This can be an LLM classifier with a tiny JSON schema, or a careful ruleset plus fallback to LLM.

---

## 3. Context policy

### Do not use raw assistant text for emergency keyword classification

Assistant text can contain generic warnings and should not become evidence of a new emergency.

### Use user history selectively

Previous user messages can matter, but only with recency and role awareness. Suggested priority:

1. current user message
2. previous user message if current message is dependent
3. analysis context if current conversation explicitly came from analysis
4. assistant messages only as conversational context for the LLM, not triage evidence

### Expire analysis context

Photo analysis context should have:

* session ID
* timestamp
* visible “using previous photo” banner
* clear “new dog / new topic” action
* automatic expiry after a short period or after first unrelated query

---

## 4. Prompt design

Use mode-specific prompts rather than one universal emergency prompt.

### Warm prompt

* friendly, curious, dog-loving
* can compliment the dog or user’s care
* can ask about name, age, breed, behaviour
* no emergency template unless symptoms appear
* may gently mention “I can also help check if something seems concerning”

### Care prompt

* proportionate and grounded
* asks one or two useful questions
* distinguishes monitor-at-home vs call-vet vs emergency
* avoids diagnosis
* no medication/dosage advice
* gives specific watch-for signs

### Emergency prompt

* current concise checklist style
* immediate actions first
* contact help clearly
* no long chatty preamble

---

## 5. Action card policy

Cards should be decided from scenario and mode, not from bot response keywords.

### Warm mode cards

* Dog care basics
* Feeding safely
* Breed/indie dog info
* Training basics

### Care mode cards

* Relevant care guide
* Monitor signs
* Find help if escalation signs exist

### Emergency mode cards

* Emergency call
* Find help near you
* One relevant first-aid guide

No more “cute dog” → bleeding/diarrhoea cards.

---

## 6. Test strategy

## Unit tests — no API key

### Triage router tests

* `hi` → warm mode
* `what's up` → warm mode
* `i have a cute dog` → warm mode
* `all good, he's just sad` → care/warm, low urgency
* `just started diarrhoea no dehydration` → care mode, mild GI
* `no seizure is happening` → clears seizure, not emergency
* `stop repeating yourself` → repair mode
* `dog hit by car can't stand` → emergency mode
* `dog ate rat poison` → emergency mode

### Context isolation tests

* previous assistant mentioned eye; current user says diarrhoea → GI, not eye
* previous assistant mentioned seizure; current user says no seizure → no seizure emergency
* previous assistant mentioned bleeding; current user says “what food is safe?” → nutrition, not bleeding

### Action card tests

* warm mode → no emergency cards
* mild diarrhoea → GI care card, no trauma card
* true road trauma → emergency + find help cards

### Fallback variety tests

* healthy pet and healthy stray do not return identical steps
* happy dog does not get “approach slowly / offer water / speak softly” every time
* fallback responses include no first-aid checklist when no first-aid is needed

## Integration tests — mocked LLM

* chat endpoint routes mode correctly
* context passed to LLM but not used for emergency keyword selection
* non-emergency prompts do not force emergency structure
* meta-user corrections trigger repair response

## Quality tests — with API key, smaller and meaningful

Keep emergency quality tests, but reduce duplication. Add:

* warmth score for casual chat
* proportionality score for mild concerns
* escalation correctness for true emergencies
* uncertainty/vet referral score for health advice
* repetition detection across turns

---

## Implementation plan

## Phase 1 — Stop the bleeding

1. Remove assistant messages from heuristic emergency classification.
2. Add repair/meta-intent detection before medical triage.
3. Add negation handling for common emergency keywords.
4. Shrink hardcoded fast path to true emergencies only.
5. Stop matching action cards against bot response text.
6. Add “new conversation / new dog” reset that clears all localStorage analysis and chat context.

This phase should fix the repeated eye/seizure loops and the worst doom-card behaviour.

## Phase 2 — Restore the chatbot

1. Add warm/care/emergency modes.
2. Add mode-specific prompts.
3. Let the LLM handle warm and care modes.
4. Keep deterministic emergency kernel.
5. Replace clinical analysis-to-chat autofill with silent backend context and a natural prompt.

This phase restores the “soul” without reviving unsafe overconfidence.

## Phase 3 — Make it a useful dog app

1. Add non-emergency knowledge base articles.
2. Add Learn page categories beyond emergencies.
3. Add care/nutrition/training/breed action cards.
4. Make Find Help context-aware.
5. Add feedback controls and logging for bad responses.

## Phase 4 — Rebuild tests around the actual product

1. Unit-test router and context isolation.
2. Add tests for negation and repair.
3. Add tests for card relevance.
4. Keep a compact emergency regression suite.
5. Add conversational quality checks.

---

## Minimal code-level sketch

### Request router shape

```python
def route_message(user_message, history, analysis_context):
    repair = detect_repair_or_meta_intent(user_message)
    if repair:
        return Route(mode="repair", urgency="none", scenario="conversation_repair")

    negations = detect_negated_symptoms(user_message)

    emergency = detect_true_emergency(user_message, negations=negations)
    if emergency:
        return Route(mode="emergency", urgency=emergency.urgency, scenario=emergency.scenario)

    mode = classify_non_emergency_intent(user_message)
    return Route(mode=mode.mode, urgency=mode.urgency, scenario=mode.scenario)
```

### Emergency detection rule

```python
# Current user message only.
# Never assistant text.
# Previous user context only if current message is dependent.
text = normalize(user_message)
```

### Negation handling sketch

```python
NEGATED_PATTERNS = {
    "seizure": ["no seizure", "not seizure", "isn't seizing", "not seizing"],
    "bleeding": ["no bleeding", "not bleeding", "blood stopped"],
    "choking": ["not choking", "breathing fine", "can breathe"],
    "dehydration": ["no dehydration", "not dehydrated", "gums moist"],
}
```

### Fast fallback whitelist

```python
FAST_TRIAGE_SCENARIOS = {
    "fall_entrapment",
    "choking_airway",
    "seizure_collapse",
    "severe_bleeding",
    "heatstroke",
    "road_trauma",
    "poisoning",
    "rabies_exposure",
}
```

### Action cards

```python
def build_action_cards(route, user_message):
    if route.mode in {"warm", "repair"}:
        return []

    if route.mode == "care":
        return care_cards_for(route.scenario)

    if route.mode == "emergency":
        return emergency_cards_for(route.scenario)
```

---

## The product vision

IndieAid should not be “a chatbot that panics.” It should be a field-aware dog care assistant that can shift registers:

* warm when the user is just sharing
* curious when the user is unsure
* grounded when the user asks for care advice
* urgent when danger is real
* humble when corrected
* helpful when it was wrong

The current app has emergency content, useful resource links, multilingual ambitions, and a real field use case. The failure is that safety fixes flattened every interaction into the same checklist shape. The next iteration should preserve the deterministic emergency core while allowing the LLM back into the parts of the product where human tone, proportionality, and adaptation matter.

---

## Final repo review — additional dead/bad code and structural risks

This final pass looked specifically for code that is stale, misleading, over-broad, or likely to keep producing the observed failures.

### 1. Emergency fallback sets have become product-routing policy

`LOCAL_DECISION_SCENARIOS` in triage and `FAST_TRIAGE_SCENARIOS` in chat contain nearly the same broad set of scenarios. That means “local decision” and “fast response” are no longer reserved for emergencies; they include healthy/low-risk, lost dog, routine care, feeding, ticks, skin disease, no-dog-visible, and other non-emergency states.

This is bad code not because deterministic paths are always wrong, but because the name and intent of the set no longer match its behaviour. The set is acting as a hidden product router while still being named like an emergency optimisation.

Recommended action: rename and split into explicit groups:

* `DETERMINISTIC_EMERGENCY_SCENARIOS`
* `DETERMINISTIC_SAFETY_SCENARIOS`
* `LLM_CARE_SCENARIOS`
* `LLM_WARM_SCENARIOS`

Only the first group should bypass the LLM.

### 2. The LLM triage path is mostly unreachable by design

`classify_situation()` returns the heuristic result immediately if the heuristic scenario is in `LOCAL_DECISION_SCENARIOS`. Since that set covers most recognised scenarios, the LLM classifier is skipped for the exact cases where nuance is needed.

This is partly dead code: the Groq triage model path exists, but most real recognised inputs do not reach it.

Recommended action: invert the rule. Use deterministic classification only for high-confidence emergencies; use the LLM or a richer classifier for low-risk, ambiguous, negated, or conversational inputs.

### 3. Current chat code passes previous assistant text into triage

The chat router explicitly passes the last assistant message into `classify_situation()`, and the heuristic classifier combines it with the current user message and analysis context before matching. This is the core context-poisoning bug.

Recommended action: remove assistant text from heuristic classification entirely. Assistant text can go into the LLM’s conversational context, but it should not be treated as evidence of a new medical scenario.

### 4. The action-card layer is doing unsafe inference from generated text

Action cards are built from `query + response`. This means warning text in the assistant’s own response can create scary follow-up cards that the user never asked for. It also means every generic warning line increases the probability of irrelevant cards.

Recommended action: build cards only from the route object: mode, scenario, urgency, and optionally current user message. Never mine the assistant’s output for scenario inference.

### 5. The “clear history” action does not fully reset state

The front-end clear button removes message history and legacy chat history but does not clear `analysisContext` state or the analysis-context localStorage keys. Separately, analysis context is cleared only after a successful send. If a send fails, stale analysis context can remain.

Recommended action: `clearHistory()` should clear:

* `messages`
* `sources`
* `lastEmergency`
* `analysisContext`
* chat localStorage keys
* analysis localStorage keys

The `catch` path after failed sends should either clear analysis context or visibly tell the user that previous photo context is still active.

### 6. The analysis-to-chat handoff creates a fake user message

When arriving from image analysis, the chat page auto-fills a long message beginning “I just analyzed a dog photo…” and includes the full context. This makes the user appear to have said a clinical report they did not write.

This is product-bad code: it contaminates the conversation tone and increases the chance that diagnostic words from the analysis become chat intent.

Recommended action: keep analysis context invisible as metadata and show a small banner: “Using previous photo analysis — change / clear.” The input should remain empty or contain a human prompt like “Ask a follow-up about this dog.”

### 7. The analysis page still uses the same fallback monoculture

`generate_fast_empathetic_response()` is explicitly designed to keep upload flows fast by using the local fallback response. That is understandable, but the fallback response itself is too generic. Healthy dogs still get “approach slowly / offer water / speak softly,” and visible injuries merely append two more generic steps.

Recommended action: keep fast local response generation, but branch by visible condition and context:

* healthy pet
* healthy street dog
* sad/quiet dog
* injured but stable
* urgent visible emergency
* unclear image

### 8. Combined vision model fallback preserves legacy multi-call services that are now mostly backup code

The current image pipeline first calls `analyze_vision()` and only falls back to separate `detect_dog()`, `classify_emotion()`, and `analyze_condition()` if the combined call fails. That makes the older dog detector / emotion / condition services mostly backup code.

This is not automatically bad. But it is stale-risk code: if those legacy services are not regularly tested, their prompts and output shapes can drift from the combined vision path.

Recommended action: either remove the legacy multi-call path or add explicit tests for fallback-path parity.

### 9. Dog detection skips detection entirely when Groq is not configured

`detect_dog()` returns `None` if the Groq key is missing. In the legacy fallback path, that means no dog is detected even if the uploaded image contains a dog.

Recommended action: if there is no vision API key, return a controlled “analysis unavailable” state rather than “no dog detected.” Those are different product states.

### 10. The model prompts still describe the assistant as field-first-aid only

The chat system prompt says the assistant helps a rescuer act in the next few minutes. That is useful in emergency mode and wrong in warm/care mode.

Recommended action: split the prompt by mode. Do not try to make one prompt handle first aid, casual pet chat, triage repair, educational care, and emergency dispatch.

### 11. Tests are structurally biased toward emergency checklist behaviour

The emergency triage test requires numbered steps near the beginning of every chat response. That is useful for emergency fixtures but actively harmful if copied into normal chat expectations. The LLM-judge quality test also asks a panic-scripted Bengaluru follow-up sequence for every quick fixture, which means even moderate scenarios are judged inside an emergency conversational frame.

Recommended action: keep a compact emergency suite, but add separate suites for warm mode, care mode, repair mode, negation, stale context, action-card relevance, and response repetition.

### 12. Test infrastructure depends on external image URLs and Groq

The test suite is skipped when the Groq key is missing and downloads fixture images at runtime unless a cache exists. That makes it weak as CI protection, especially for pure routing regressions.

Recommended action: create local deterministic unit tests for the router, triage, context policy, and card builder. Only keep a small number of API-key integration tests.

---

## Final prioritized cleanup list

### Must fix first

1. Stop passing previous assistant replies into heuristic triage.
2. Add negation and correction handling before emergency keyword matching.
3. Shrink deterministic fast responses to true emergencies.
4. Stop action cards from reading assistant-generated response text.
5. Make `clearHistory()` clear analysis context too.
6. Add tests for “no seizure,” “stop repeating,” and “diarrhoea after eye response.”

### Should fix next

1. Split warm/care/emergency prompts.
2. Replace analysis-to-chat autofill with invisible context plus a visible clear banner.
3. Add varied local fallback shapes for analysis results.
4. Make no-key/no-model states explicit instead of pretending analysis succeeded or no dog was found.
5. Add non-emergency Learn content.

### Can fix later

1. Decide whether to keep or remove the legacy multi-call vision pipeline.
2. Add telemetry for repeated identical replies, emergency false positives, and user correction phrases.
3. Make Find Help context-aware by city, scenario, and urgency.
4. Replace the LLM judge with a mixed suite: deterministic assertions plus a smaller semantic-eval layer.

## Closing assessment

The codebase is not fundamentally broken. It has useful pieces: a clear FastAPI/Next split, multilingual ambitions, a combined vision call, resource links, a KB, and deterministic emergency fallbacks. The failure is architectural overreach by safety scaffolding. Emergency machinery is currently serving as product personality, intent router, memory policy, response generator, and UI-card selector.

The right next version should not be “less safe.” It should be safer because it distinguishes real emergencies from normal dog-care interaction, lets users correct the assistant, and prevents stale context from turning every conversation into the last emergency it saw.
