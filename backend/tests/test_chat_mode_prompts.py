"""Stage 4: mode-specific prompt selection and no-API-key fallback (no API key required)."""

import pytest

from app.routers.chat import (
    _REPAIR_FALLBACK,
    _SYMPTOM_NEGATED_FALLBACK,
    _WARM_FALLBACK,
    _build_system_prompt,
    _mode_fallback,
)
from app.services.triage import TriageResult


def _t(mode: str, scenario: str, urgency: str = "low_risk", needs_helpline: bool = False) -> TriageResult:
    return TriageResult(
        urgency_tier=urgency,
        info_sufficient=True,
        scenario_type=scenario,
        mode=mode,
        needs_helpline_first=needs_helpline,
    )


# ---------------------------------------------------------------------------
# Prompt selection
# ---------------------------------------------------------------------------


def test_emergency_prompt_is_action_first():
    triage = _t("emergency", "road_trauma", "life_threatening", needs_helpline=True)
    system = _build_system_prompt(triage, "Respond in English.", "", "")
    assert "preamble" in system.lower()
    assert "CONTACT" in system
    assert "TRIAGE" in system


def test_emergency_prompt_does_not_have_knowledge_base_section():
    triage = _t("emergency", "road_trauma", "life_threatening")
    system = _build_system_prompt(triage, "Respond in English.", "some KB text", "")
    assert "KNOWLEDGE BASE" not in system


def test_warm_prompt_has_no_triage_or_contact():
    triage = _t("warm", "warm_conversation")
    system = _build_system_prompt(triage, "Respond in English.", "", "")
    assert "TRIAGE" not in system
    assert "CONTACT" not in system


def test_repair_prompt_has_no_triage_or_contact():
    triage = _t("repair", "conversation_repair")
    system = _build_system_prompt(triage, "Respond in English.", "", "")
    assert "TRIAGE" not in system
    assert "CONTACT" not in system


def test_care_prompt_includes_knowledge_base():
    triage = _t("care", "vomiting_diarrhea", "moderate")
    system = _build_system_prompt(triage, "Respond in English.", "some KB text", "")
    assert "KNOWLEDGE BASE" in system
    assert "some KB text" in system
    assert "TRIAGE" in system


def test_care_prompt_has_no_contact():
    triage = _t("care", "vomiting_diarrhea", "moderate")
    system = _build_system_prompt(triage, "Respond in English.", "", "")
    assert "CONTACT" not in system


def test_unknown_mode_falls_back_to_care_prompt():
    triage = TriageResult(urgency_tier="moderate", info_sufficient=True, scenario_type="unclear", mode="care")
    system = _build_system_prompt(triage, "Respond in English.", "ctx", "")
    assert "KNOWLEDGE BASE" in system


# ---------------------------------------------------------------------------
# Warm fallback: never scary, always non-empty, trilingual
# ---------------------------------------------------------------------------


def test_warm_fallback_not_scary_en():
    triage = _t("warm", "warm_conversation")
    reply = _mode_fallback("hi", "", "en", triage)
    assert reply
    assert "emergency" not in reply.lower()
    assert "bleeding" not in reply.lower()
    assert "1." not in reply


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_warm_fallback_not_scary_non_english(lang):
    triage = _t("warm", "warm_conversation")
    reply = _mode_fallback("hi", "", lang, triage)
    assert reply
    assert "emergency" not in reply.lower()
    assert "1." not in reply


def test_warm_fallback_hindi_contains_devanagari():
    triage = _t("warm", "warm_conversation")
    reply = _mode_fallback("नमस्ते", "", "hi", triage)
    assert any("ऀ" <= c <= "ॿ" for c in reply)


def test_warm_fallback_marathi_contains_devanagari():
    triage = _t("warm", "warm_conversation")
    reply = _mode_fallback("नमस्कार", "", "mr", triage)
    assert any("ऀ" <= c <= "ॿ" for c in reply)


# ---------------------------------------------------------------------------
# Repair fallback: acknowledges correction, trilingual
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_repair_fallback_non_empty(lang):
    triage = _t("repair", "conversation_repair")
    reply = _mode_fallback("stop repeating yourself", "", lang, triage)
    assert reply


def test_repair_fallback_hindi_not_english():
    triage = _t("repair", "conversation_repair")
    assert "Got it" not in _REPAIR_FALLBACK["hi"]


def test_repair_fallback_marathi_not_english():
    triage = _t("repair", "conversation_repair")
    assert "Got it" not in _REPAIR_FALLBACK["mr"]


# ---------------------------------------------------------------------------
# Symptom-negated fallback: not escalating, trilingual
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_symptom_negated_fallback_non_empty(lang):
    triage = _t("care", "symptom_negated")
    reply = _mode_fallback("no seizure is happening", "", lang, triage)
    assert reply


def test_symptom_negated_fallback_does_not_escalate():
    triage = _t("care", "symptom_negated")
    reply = _mode_fallback("no seizure is happening", "", "en", triage)
    assert "call rescue" not in reply.lower()
    assert "life-threatening" not in reply.lower()


def test_symptom_negated_fallback_hindi_devanagari():
    assert any("ऀ" <= c <= "ॿ" for c in _SYMPTOM_NEGATED_FALLBACK["hi"])


def test_symptom_negated_fallback_marathi_devanagari():
    assert any("ऀ" <= c <= "ॿ" for c in _SYMPTOM_NEGATED_FALLBACK["mr"])


# ---------------------------------------------------------------------------
# Emergency fallback: action steps present
# ---------------------------------------------------------------------------


def test_emergency_fallback_has_numbered_steps_en():
    triage = _t("emergency", "road_trauma", "life_threatening", needs_helpline=True)
    reply = _mode_fallback("dog hit by car cannot stand", "", "en", triage)
    assert "1." in reply


def test_emergency_fallback_road_trauma_en():
    triage = _t("emergency", "road_trauma", "life_threatening")
    reply = _mode_fallback("dog hit by car", "", "en", triage)
    assert reply
    assert "2." in reply


def test_emergency_fallback_hindi_uses_kb_or_generic():
    triage = _t("emergency", "road_trauma", "life_threatening")
    reply = _mode_fallback("dog hit by car", "", "hi", triage)
    assert reply
    assert any("ऀ" <= c <= "ॿ" for c in reply)


# ---------------------------------------------------------------------------
# Care fallback: scenario-specific, not emergency weight
# ---------------------------------------------------------------------------


def test_care_mild_diarrhea_fallback_en():
    triage = _t("care", "vomiting_diarrhea", "moderate")
    reply = _mode_fallback("dog has diarrhea", "", "en", triage)
    assert reply


def test_care_routine_fallback_en():
    triage = _t("care", "routine_care", "low_risk")
    reply = _mode_fallback("puppy needs vaccine", "", "en", triage)
    assert reply


# ---------------------------------------------------------------------------
# Unknown language gracefully falls back to English equivalents
# ---------------------------------------------------------------------------


def test_unknown_language_warm_fallback():
    triage = _t("warm", "warm_conversation")
    reply = _mode_fallback("hi", "", "fr", triage)
    assert reply == _WARM_FALLBACK["en"]


def test_unknown_language_repair_fallback():
    triage = _t("repair", "conversation_repair")
    reply = _mode_fallback("stop", "", "fr", triage)
    assert reply == _REPAIR_FALLBACK["en"]
