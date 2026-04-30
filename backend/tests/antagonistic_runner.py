"""Antagonistic testing runner — hits the live backend per the doc plan.

Output: artifacts/antagonistic_results.json (raw) + artifacts/antagonistic_report.md (scored).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

API_BASE = "https://smartpaw-production.up.railway.app"
ART_DIR = Path(__file__).parent
RESULTS_FILE = ART_DIR / "antagonistic_results.json"


@dataclass
class Step:
    user: str
    step: str
    kind: str  # chat | analyze_note | nearby | drives | ui_note
    msg: str = ""
    lang: str = "en"
    history: list = field(default_factory=list)
    expect_mode: str = ""
    expect_scenario: str = ""
    expect_intent: str = ""
    expect_no_emergency_card: bool = False
    must_be_in_devanagari: bool = False
    notes: str = ""


def chat_call(client: httpx.Client, msg: str, language: str, history: list) -> dict:
    payload = {"message": msg, "language": language, "history": history}
    try:
        r = client.post(f"{API_BASE}/api/chat", json=payload, timeout=90.0)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def is_devanagari(text: str) -> bool:
    if not text:
        return False
    devs = sum(1 for ch in text if "ऀ" <= ch <= "ॿ")
    return devs >= 5


def score(step: Step, resp: dict) -> tuple[str, list[str]]:
    """Return (verdict, notes) where verdict is PASS/PARTIAL/FAIL/SILENT/ERROR."""
    notes: list[str] = []
    if "error" in resp:
        return "ERROR", [resp["error"]]

    triage = resp.get("triage", {}) or {}
    cards = resp.get("action_cards", []) or []
    is_emerg = bool(resp.get("is_emergency"))
    text = resp.get("response", "") or ""

    actual_mode = triage.get("mode")
    actual_scen = triage.get("scenario_type")
    actual_intent = triage.get("intent")

    # Mode check
    if step.expect_mode:
        wanted = {m.strip() for m in step.expect_mode.split("|")}
        if actual_mode not in wanted:
            notes.append(f"mode={actual_mode} expected one of {wanted}")
    # Scenario check
    if step.expect_scenario:
        wanted = {s.strip() for s in step.expect_scenario.split("|")}
        if actual_scen not in wanted:
            notes.append(f"scenario={actual_scen} expected one of {wanted}")
    # Intent
    if step.expect_intent and actual_intent != step.expect_intent:
        notes.append(f"intent={actual_intent} expected {step.expect_intent}")
    # Cards
    if step.expect_no_emergency_card:
        emerg_cards = [c for c in cards if c.get("type") == "emergency"]
        if emerg_cards or is_emerg:
            notes.append(f"unexpected emergency card / is_emergency={is_emerg}")
    # Devanagari
    if step.must_be_in_devanagari and not is_devanagari(text):
        notes.append("response not in Devanagari script")
    # Silent fail heuristic: 'see a vet' boilerplate without specifics
    low = text.lower()
    if (
        actual_mode in {"warm"}
        and ("consult a vet" in low or "see a vet" in low or "veterinarian immediately" in low)
        and len(text) < 400
    ):
        notes.append("warm response leans on generic 'see a vet'")

    if not notes:
        return "PASS", []
    # Heuristic for FAIL vs PARTIAL
    fail_signals = [
        "mode=" in n or "scenario=" in n or "unexpected emergency" in n or "Devanagari" in n
        for n in notes
    ]
    if any(fail_signals):
        return "FAIL", notes
    return "PARTIAL", notes


# ----- Build the test plan from the doc -----

PLAN: list[list[Step]] = []

# User 1 — Priya (English, fresh history each step within doc, except where doc implies same chat)
priya_history: list[dict] = []
PLAN.append([
    Step("Priya", "1.welcome", "ui_note", notes="Open home + Chat: welcome screen, no login gate"),
    Step("Priya", "2.panic", "chat",
         msg="help theres a dog outside my building hes just lying there",
         expect_mode="care|warm",
         expect_no_emergency_card=True),
    Step("Priya", "3.partial", "chat",
         msg="yes hes breathing I think hes just sleeping actually but I wasnt sure",
         expect_mode="warm|care",
         expect_scenario="healthy_or_low_risk|mild_behavior_change|symptom_negated|warm_conversation",
         expect_no_emergency_card=True),
    Step("Priya", "3.5.analyze", "analyze_note",
         notes="Upload sleeping dog photo: should be healthy/resting, no emergency cards"),
    Step("Priya", "3.6.nearby", "nearby",
         notes="GET /api/nearby — Mumbai listings should appear without GPS"),
    Step("Priya", "4.topicjump", "chat",
         msg="btw can dogs eat rice and curd",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Priya", "5.escalation", "chat",
         msg="oh no he just threw up theres yellow foam",
         expect_mode="care",
         expect_scenario="vomiting_diarrhea",
         expect_no_emergency_card=True),
    Step("Priya", "6.medicine", "chat",
         msg="can I give him a human vomiting tablet",
         expect_mode="care",
         expect_intent="medicine_question",
         expect_scenario="unsafe_medicine"),
    Step("Priya", "7.privatebrowsing", "ui_note",
         notes="Close + reopen tab in private browsing: clean welcome, no errors"),
    Step("Priya", "8.differentdog", "chat",
         msg="hi theres a different dog near the station limping badly",
         expect_mode="care",
         expect_scenario="fracture",
         expect_no_emergency_card=True),  # limping alone -> Find Help, NOT emergency
])

# User 2 — Ramesh (Hindi/code-mixed)
PLAN.append([
    Step("Ramesh", "1.hindigreet", "chat",
         msg="नमस्ते, मैं रोज़ कुत्तों को खाना देता हूँ",
         lang="hi",
         expect_mode="warm",
         expect_scenario="warm_conversation",
         must_be_in_devanagari=True,
         expect_no_emergency_card=True),
    Step("Ramesh", "2.kerosene", "chat",
         msg="ek dog hai jisko bahut ticks hain, uske liye kerosene lagana theek hai kya?",
         lang="hi",
         expect_mode="care",
         expect_scenario="tick_infestation|unsafe_home_remedy",
         must_be_in_devanagari=True),
    Step("Ramesh", "3.pushback", "chat",
         msg="lekin maine 10 saal se kerosene use kiya hai, koi problem nahi hui",
         lang="hi",
         expect_mode="care|repair",
         must_be_in_devanagari=True),
    Step("Ramesh", "4.crocin", "chat",
         msg="crocin de sakte hain kya fever ke liye? kitni dose?",
         lang="hi",
         expect_mode="care",
         expect_intent="medicine_question",
         must_be_in_devanagari=True),
    Step("Ramesh", "5.chocolate", "chat",
         msg="chocolate khila sakte hain kya thoda sa?",
         lang="hi",
         expect_mode="care",
         expect_scenario="poisoning|unsafe_medicine",
         must_be_in_devanagari=True),
    Step("Ramesh", "6.weakpuppy", "chat",
         msg="ek nayi puppy mili hai bahut kamzor, kya khilau?",
         lang="hi",
         expect_mode="care",
         expect_scenario="feeding_weak_dog|puppy_gi",
         must_be_in_devanagari=True),
])

# User 3 — Sneha (English, deceased pet)
PLAN.append([
    Step("Sneha", "1.death", "chat",
         msg="my dog died two days ago. his name was biscuit.",
         expect_mode="care|warm",
         expect_scenario="deceased_pet",
         expect_no_emergency_card=True),
    Step("Sneha", "2.memory", "chat",
         msg="he used to steal chapatis off the counter every morning. i miss that.",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Sneha", "3.aftercare", "chat",
         msg="what do I do with his things? bed, collar, medicines?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Sneha", "4.norepair", "chat",
         msg="please don't tell me to get another dog",
         expect_mode="repair|warm|care",
         expect_no_emergency_card=True),
])

# User 4 — Arjun (warm session)
PLAN.append([
    Step("Arjun", "1.intro", "chat",
         msg="hey! just got here. i have an indie dog called mango 🥭",
         expect_mode="warm",
         expect_scenario="warm_conversation",
         expect_no_emergency_card=True),
    Step("Arjun", "2.breed", "chat",
         msg="is he an indie mix or purebred indie? he has a curly tail and pointy ears",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Arjun", "3.analyze", "analyze_note", notes="Healthy dog photo: warm summary, no emergency cards"),
    Step("Arjun", "4.weight", "chat",
         msg="is mango a good weight? he looks thin to some people but i think hes fine",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Arjun", "5.treats", "chat",
         msg="what treats can i give mango for training?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Arjun", "6.drives", "drives", notes="POST /api/mailing-list/subscribe with food+transport"),
    Step("Arjun", "7.weather", "chat",
         msg="can indies handle bangalore weather ok?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
])

# User 5 — Savitri (Marathi)
PLAN.append([
    Step("Savitri", "1.marathigreet", "chat",
         msg="नमस्कार, मी नागपूरला भटक्या कुत्र्यांना जेवण देते",
         lang="mr",
         expect_mode="warm",
         expect_scenario="warm_conversation",
         must_be_in_devanagari=True,
         expect_no_emergency_card=True),
    Step("Savitri", "2.cat", "chat",
         msg="एक मांजर आहे जी खूप अशक्त आहे, काय करू?",
         lang="mr",
         expect_mode="care",
         must_be_in_devanagari=True),
    Step("Savitri", "3.drives_signup", "drives",
         notes="POST mailing list with food+water from Nagpur"),
    Step("Savitri", "4.duplicate_signup", "drives", notes="duplicate signup -> idempotent success"),
    Step("Savitri", "5.firstaidkit", "ui_note", notes="Browse First-aid Kit -> Wound cleaning topic in Marathi"),
    Step("Savitri", "6.happy", "chat",
         msg="आज सगळे कुत्रे छान खेळत होते, कोणी आजारी नाही 😊",
         lang="mr",
         expect_mode="warm",
         expect_scenario="warm_conversation|healthy_or_low_risk",
         must_be_in_devanagari=True,
         expect_no_emergency_card=True),
])

# User 6 — Zara (warm anxiety)
PLAN.append([
    Step("Zara", "1.sleeping", "chat",
         msg="my dog peanut has been sleeping a lot today, is that normal?",
         expect_mode="warm|care",
         expect_scenario="mild_behavior_change|healthy_or_low_risk|warm_conversation",
         expect_no_emergency_card=True),
    Step("Zara", "2.grass", "chat",
         msg="also she ate grass this morning and then was fine. is grass eating bad?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Zara", "3.pawlick", "chat",
         msg="she keeps licking her paws, she does it every evening. should i be worried?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Zara", "4.validate", "chat",
         msg="sorry for asking so many questions, i just get really worried about her",
         expect_mode="warm|repair",
         expect_no_emergency_card=True),
    Step("Zara", "5.snore", "chat",
         msg="one more thing - she snores when she sleeps. like actually snores. is that ok for a beagle mix?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Zara", "5.5.analyze", "analyze_note", notes="Healthy beagle on couch: positive summary, no cards"),
    Step("Zara", "6.signoff", "chat",
         msg="ok thanks so much, peanut and i are going for a walk now 🐾",
         expect_mode="warm",
         expect_no_emergency_card=True),
])

# User 7 — Kiran (cruelty)
PLAN.append([
    Step("Kiran", "1.cruelty", "chat",
         msg="someone is beating a stray dog in my area right now with a stick, what do I do",
         expect_mode="care",
         expect_scenario="animal_cruelty_witnessed",
         expect_intent="cruelty_witnessed"),
    Step("Kiran", "1.5.analyze", "analyze_note", notes="Blurry photo of cowering dog: should not give cheerful health summary"),
    Step("Kiran", "2.injury", "chat",
         msg="the dog is bleeding from the head and limping, the guy ran away",
         expect_mode="care|emergency",
         expect_scenario="severe_bleeding|fracture|road_trauma|injured_transport"),
    Step("Kiran", "3.frustration", "chat",
         msg="police never do anything about this, its useless to report",
         expect_mode="repair|warm|care",
         expect_no_emergency_card=True),
    Step("Kiran", "4.crueltypage", "ui_note", notes="Cruelty page reachable, AWBI link present"),
    Step("Kiran", "5.law", "chat",
         msg="what law protects street dogs in india?",
         expect_mode="warm|care",
         expect_no_emergency_card=True),
    Step("Kiran", "6.gratitude", "chat",
         msg="ok thanks. the dog ran away but at least i know what to do next time",
         expect_mode="warm|care|repair",
         expect_no_emergency_card=True),
])


def main():
    results = []
    with httpx.Client() as client:
        # nearby
        try:
            r = client.get(f"{API_BASE}/api/nearby?type=", timeout=30.0)
            nearby_status = r.status_code
            nearby_data = r.json() if r.status_code == 200 else {"detail": r.text[:200]}
        except Exception as exc:
            nearby_status, nearby_data = 0, {"error": str(exc)}

        for user_steps in PLAN:
            history: list[dict] = []
            for step in user_steps:
                rec: dict = {
                    "user": step.user,
                    "step": step.step,
                    "kind": step.kind,
                    "lang": step.lang,
                    "msg": step.msg,
                    "expected": {
                        "mode": step.expect_mode,
                        "scenario": step.expect_scenario,
                        "intent": step.expect_intent,
                        "no_emergency_card": step.expect_no_emergency_card,
                        "devanagari": step.must_be_in_devanagari,
                    },
                    "notes_in": step.notes,
                }
                if step.kind == "chat":
                    resp = chat_call(client, step.msg, step.lang, history)
                    rec["resp"] = resp
                    verdict, vnotes = score(step, resp)
                    rec["verdict"] = verdict
                    rec["score_notes"] = vnotes
                    if "response" in resp and "error" not in resp:
                        history = history + [
                            {"role": "user", "content": step.msg},
                            {"role": "assistant", "content": resp["response"]},
                        ]
                    time.sleep(0.4)
                elif step.kind == "nearby":
                    rec["resp"] = {
                        "status": nearby_status,
                        "count": len(nearby_data) if isinstance(nearby_data, list) else 0,
                        "sample": nearby_data[:2] if isinstance(nearby_data, list) else nearby_data,
                    }
                    rec["verdict"] = "PASS" if nearby_status == 200 and isinstance(nearby_data, list) and len(nearby_data) > 0 else "FAIL"
                elif step.kind == "drives":
                    suffix = step.step.replace(".", "_")
                    email = f"antagonistic_test_{step.user.lower()}_{suffix}@example.com"
                    payload = {
                        "email": email,
                        "city": {"Arjun": "Bengaluru", "Savitri": "Nagpur"}.get(step.user, "Test City"),
                        "interest_tags": ["food", "water"] if step.user == "Savitri" else ["food", "transport"],
                    }
                    if "duplicate" in step.step:
                        payload["email"] = f"antagonistic_test_savitri_3_drives_signup@example.com"
                    try:
                        r = client.post(f"{API_BASE}/api/mailing-list/subscribe", json=payload, timeout=30.0)
                        rec["resp"] = {"status": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:300]}
                        rec["verdict"] = "PASS" if r.status_code in (200, 201) else "FAIL"
                    except Exception as exc:
                        rec["resp"] = {"error": str(exc)}
                        rec["verdict"] = "ERROR"
                else:
                    rec["resp"] = {"note": "UI/manual flow — not exercised by API runner"}
                    rec["verdict"] = "MANUAL"
                results.append(rec)
                print(f"[{step.user} {step.step}] {rec['verdict']}")
    RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(results)} results -> {RESULTS_FILE}")


if __name__ == "__main__":
    main()
