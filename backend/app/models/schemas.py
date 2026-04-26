from pydantic import BaseModel
from typing import Optional


class EmotionResult(BaseModel):
    label: str
    confidence: float


class SafetyLevel(BaseModel):
    level: str  # "safe", "caution", "danger"
    reason: str


class ConditionAssessment(BaseModel):
    breed_guess: str
    estimated_age: str
    physical_condition: str
    visible_injuries: list[str]
    health_concerns: list[str]
    body_language: str


class FirstAidStep(BaseModel):
    step_number: int
    instruction: str


class AnalysisResponse(BaseModel):
    dog_detected: bool
    emotion: Optional[EmotionResult] = None
    safety: Optional[SafetyLevel] = None
    condition: Optional[ConditionAssessment] = None
    first_aid: list[FirstAidStep] = []
    empathetic_summary: str = ""
    disclaimer: str = (
        "This is AI-based guidance, not a veterinary diagnosis. "
        "When in doubt, please contact a veterinary professional immediately."
    )
    language: str = "en"


class LanguageContent(BaseModel):
    """Language-specific generated content for one language variant."""
    safety: Optional[SafetyLevel] = None
    empathetic_summary: str = ""
    first_aid: list[FirstAidStep] = []


class MultilingualAnalysisResponse(BaseModel):
    """Full analysis with generated content pre-built for all three languages."""
    dog_detected: bool
    emotion: Optional[EmotionResult] = None
    condition: Optional[ConditionAssessment] = None
    languages: dict[str, LanguageContent] = {}
    disclaimer: str = (
        "This is AI-based guidance, not a veterinary diagnosis. "
        "When in doubt, please contact a veterinary professional immediately."
    )


class ReportCreate(BaseModel):
    latitude: float
    longitude: float
    description: str = ""
    urgency: str = "medium"  # "low", "medium", "high", "critical"
    image_url: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    description: str
    urgency: str
    image_url: Optional[str] = None
    image_filename: Optional[str] = None
    created_at: str
    status: str
    resolved_at: Optional[str] = None
    resolved_note: Optional[str] = None


class ReportStatusUpdate(BaseModel):
    status: str  # "open", "in_progress", "resolved", "closed"
    note: str = ""


class NearbyQuery(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 5.0
    type: Optional[str] = None  # "vet", "shelter", "ngo"


class ShelterVet(BaseModel):
    id: str
    name: str
    type: str
    address: str
    phone: str
    latitude: float
    longitude: float
    hours: str = ""
    distance_km: Optional[float] = None
    emergency_24hr: bool = False


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    history: list[ChatMessage] = []
    context_from_analysis: Optional[str] = None
