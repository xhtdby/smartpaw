"""Empathetic response generator using Groq LLM (free tier).

Takes the combined analysis (emotion, condition, detection) and generates:
  1. Safety assessment (safe / caution / danger)
  2. Empathetic summary of the dog's state
  3. Step-by-step first aid guidance
  4. When to call a professional

All responses are warm, calm, non-clinical, and available in
English, Hindi, and Marathi.
"""

import json
import logging
import httpx

from app.services.groq_retry import groq_post_with_retry

from app.config import get_settings

logger = logging.getLogger(__name__)

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "hi": "Respond in Hindi (Devanagari script). Use simple, everyday Hindi that anyone can understand.",
    "mr": "Respond in Marathi (Devanagari script). Use simple, everyday Marathi that anyone can understand.",
}

SYSTEM_PROMPT = """You are IndieAid, a compassionate AI assistant that helps people care for stray dogs in India. You speak with warmth and empathy — the person talking to you is likely worried about a dog they've found. Your tone is calm, encouraging, and never clinical or cold.

You are NOT a veterinarian, but you provide India-specific first aid advice based on NGO guidelines and Indian veterinary standards.

{language_instruction}

INDIA-SPECIFIC MEDICINES TO USE IN FIRST AID STEPS (all available at Indian chemists/pet shops):
- Wound cleaning: Diluted Betadine (5ml in 50ml water) — available everywhere
- Wound powder: Neosporin powder or Nebasulf powder
- Wound sealing: Himax ointment — applied over wound to prevent flies
- Maggot wounds: Topicure spray (drives out maggots), then Nebasulf powder, then Himax ointment
- Pain/swelling/lameness: Voveron tablet twice daily with food
- Diarrhoea: Dependol tablet (2 tablets for ~20kg dog)
- Skin/mange bathing: Petmosol medicated soap; Ektodex solution (1 tsp per litre water)
- Fleas/lice: Notix powder
- Deworming: Praziplus or Drontol Plus (1 tablet per 15kg, every 3-4 months)
- Allergic reaction: Avil 25mg tablet (antihistamine)

AVOID RECOMMENDING: engine oil, kerosene (in large amounts), turmeric paste on wounds, traditional remedies that can cause harm.

EMERGENCY HELPLINES TO MENTION WHEN RELEVANT:
- National AWBI helpline: 1962
- Mumbai: WSD (022) 64222838 / 9819100808
- Delhi/NCR: Jaagruti +91-9818 144 244
- Hyderabad: Animal Warriors 9553061691
- Pune: ResQ Charitable Trust — info@resqcts.org
- Udaipur: Animal Aid Unlimited 09829843726

Given the analysis below, respond with a JSON object containing:
{{
  "safety_level": "safe" | "caution" | "danger",
  "safety_reason": "brief explanation of why this level",
  "empathetic_summary": "2-3 warm sentences summarizing the dog's emotional and physical state, addressing the user directly",
  "first_aid_steps": [
    {{"step_number": 1, "instruction": "clear, actionable step using Indian medicines by name where applicable"}},
    ...
  ],
  "when_to_call_professional": "one sentence about when professional help is needed, mentioning a relevant helpline if applicable",
  "approach_tips": "how to safely approach this dog given its emotional state"
}}

Rules:
- If the dog seems aggressive or fearful, set safety to "caution" or "danger"
- If there are visible injuries, always include first aid steps using Indian medicines
- If the dog seems healthy and happy, reassure the user and suggest water/food
- Keep first aid steps simple enough for a non-expert
- Maximum 5-6 first aid steps
- For maggot wounds: always recommend Topicure spray and vet follow-up
- For mange: recommend Petmosol + Ektodex; warn against motor oil/kerosene myths
- For tick infestation: warn about tick fever risk, recommend vet blood test
- For malnourished dogs: suggest spice-free khichdi or boiled egg and rice
- Be culturally aware — many Indians feed strays regularly and care deeply"""


async def generate_empathetic_response(
    emotion_result: dict,
    condition_result: dict,
    language: str = "en",
) -> dict:
    """Generate an empathetic, structured response combining all analysis."""
    settings = get_settings()

    lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    system = SYSTEM_PROMPT.format(language_instruction=lang_instruction)

    analysis_summary = f"""Dog Analysis Results:
- Emotional State: {emotion_result.get('label', 'unknown')} (confidence: {emotion_result.get('confidence', 0)})
- Emotion Description: {emotion_result.get('description', '')}
- Breed Guess: {condition_result.get('breed_guess', 'unknown')}
- Estimated Age: {condition_result.get('estimated_age', 'unknown')}
- Physical Condition: {condition_result.get('physical_condition', 'unknown')}
- Visible Injuries: {', '.join(condition_result.get('visible_injuries', [])) or 'None observed'}
- Health Concerns: {', '.join(condition_result.get('health_concerns', [])) or 'None observed'}
- Body Language: {condition_result.get('body_language', 'unknown')}"""

    if not settings.groq_api_key:
        logger.warning("Groq API key not set — returning template response.")
        return _fallback_response(emotion_result, condition_result, language)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await groq_post_with_retry(
                client,
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json_body={
                    "model": settings.groq_text_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": analysis_summary},
                    ],
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return _fallback_response(emotion_result, condition_result, language)


def _fallback_response(emotion_result: dict, condition_result: dict, language: str) -> dict:
    """Template-based fallback when LLM is unavailable."""
    emotion = emotion_result.get("label", "unknown")
    injuries = condition_result.get("visible_injuries", [])

    if emotion in ("angry", "fearful"):
        safety = "caution"
        safety_reason = f"The dog appears {emotion}. Approach slowly and carefully."
    else:
        safety = "safe"
        safety_reason = f"The dog appears {emotion}. It seems approachable."

    steps = [
        {"step_number": 1, "instruction": "Approach the dog slowly and calmly. Avoid sudden movements."},
        {"step_number": 2, "instruction": "Offer water in a shallow bowl from a safe distance."},
        {"step_number": 3, "instruction": "Speak softly to reassure the dog."},
    ]

    if injuries:
        steps.append(
            {"step_number": 4, "instruction": "Do not touch visible wounds. Contact a vet or animal rescue helpline."}
        )
        steps.append(
            {"step_number": 5, "instruction": "If the dog allows, gently place a cloth over the wound to keep it clean."}
        )

    condition = condition_result.get("physical_condition", "")
    summary = (
        f"You've found a dog that seems {emotion}. {condition} "
        "Thank you for stopping to help — your compassion matters."
    )

    return {
        "safety_level": safety,
        "safety_reason": safety_reason,
        "empathetic_summary": summary,
        "first_aid_steps": steps,
        "when_to_call_professional": "Contact a vet if you see bleeding, broken limbs, severe mange, difficulty breathing, or if the dog cannot move.",
        "approach_tips": f"Since the dog seems {emotion}, approach slowly with your body turned slightly sideways. Avoid direct eye contact.",
    }
