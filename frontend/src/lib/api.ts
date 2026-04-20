const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function analyzeImage(
  imageFile: File,
  language: string = "en"
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("language", language);

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(err.detail || "Analysis failed");
  }

  return res.json();
}

export async function fetchNearby(
  lat: number,
  lng: number,
  radiusKm: number = 5,
  type?: string
): Promise<ShelterVet[]> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lng.toString(),
    radius_km: radiusKm.toString(),
  });
  if (type) params.set("type", type);

  const res = await fetch(`${API_BASE}/api/nearby?${params}`);
  if (!res.ok) throw new Error("Failed to fetch nearby shelters");
  return res.json();
}

export async function submitReport(report: ReportInput): Promise<Report> {
  const res = await fetch(`${API_BASE}/api/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!res.ok) throw new Error("Failed to submit report");
  return res.json();
}

export async function fetchReports(
  lat: number,
  lng: number,
  radiusKm: number = 5
): Promise<Report[]> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lng.toString(),
    radius_km: radiusKm.toString(),
  });
  const res = await fetch(`${API_BASE}/api/reports?${params}`);
  if (!res.ok) throw new Error("Failed to fetch reports");
  return res.json();
}

export async function sendChatMessage(
  message: string,
  language: string = "en",
  history: ChatMessage[] = [],
  analysisContext?: string
): Promise<{ response: string }> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      language,
      history,
      context_from_analysis: analysisContext,
    }),
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

// Types
export interface AnalysisResult {
  dog_detected: boolean;
  emotion?: { label: string; confidence: number };
  safety?: { level: string; reason: string };
  condition?: {
    breed_guess: string;
    estimated_age: string;
    physical_condition: string;
    visible_injuries: string[];
    health_concerns: string[];
    body_language: string;
  };
  first_aid: { step_number: number; instruction: string }[];
  empathetic_summary: string;
  disclaimer: string;
  language: string;
}

export interface ShelterVet {
  id: string;
  name: string;
  type: string;
  address: string;
  phone: string;
  latitude: number;
  longitude: number;
  hours: string;
  distance_km?: number;
  emergency_24hr: boolean;
}

export interface ReportInput {
  latitude: number;
  longitude: number;
  description: string;
  urgency: string;
  image_url?: string;
}

export interface Report {
  id: string;
  latitude: number;
  longitude: number;
  description: string;
  urgency: string;
  image_url?: string;
  created_at: string;
  status: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
