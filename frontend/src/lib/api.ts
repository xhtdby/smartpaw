const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithRetry(
  input: RequestInfo,
  init?: RequestInit,
  retries = 2
): Promise<Response> {
  for (let i = 0; i <= retries; i++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);
      const res = await fetch(input, { ...init, signal: controller.signal });
      clearTimeout(timeout);
      if (res.ok || res.status < 500 || i === retries) return res;
    } catch (err) {
      if (i === retries) throw err;
    }
    await new Promise((r) => setTimeout(r, 1000 * (i + 1)));
  }
  throw new Error("Request failed");
}

export async function analyzeImage(
  imageFile: File,
  language: string = "en"
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("language", language);

  const res = await fetchWithRetry(`${API_BASE}/api/analyze`, {
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
  radiusKm: number = 10,
  type?: string
): Promise<ShelterVet[]> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lng.toString(),
    radius_km: radiusKm.toString(),
  });
  if (type) params.set("type", type);

  const res = await fetchWithRetry(`${API_BASE}/api/nearby?${params}`);
  if (!res.ok) throw new Error("Failed to fetch nearby shelters");
  return res.json();
}

export async function submitReport(formData: FormData): Promise<Report> {
  const res = await fetchWithRetry(`${API_BASE}/api/report`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to submit report");
  return res.json();
}

export async function fetchReports(
  lat: number,
  lng: number,
  radiusKm: number = 10,
  urgency?: string,
  status?: string
): Promise<Report[]> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lng.toString(),
    radius_km: radiusKm.toString(),
  });
  if (urgency) params.set("urgency", urgency);
  if (status) params.set("status", status);
  const res = await fetchWithRetry(`${API_BASE}/api/reports?${params}`);
  if (!res.ok) throw new Error("Failed to fetch reports");
  return res.json();
}

export async function updateReportStatus(
  reportId: string,
  status: string,
  note: string = ""
): Promise<Report> {
  const res = await fetchWithRetry(`${API_BASE}/api/reports/${reportId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, note }),
  });
  if (!res.ok) throw new Error("Failed to update report");
  return res.json();
}

export async function sendChatMessage(
  message: string,
  language: string = "en",
  history: ChatMessage[] = [],
  analysisContext?: string
): Promise<ChatResponse> {
  const res = await fetchWithRetry(`${API_BASE}/api/chat`, {
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

export function getReportImageUrl(reportId: string): string {
  return `${API_BASE}/api/reports/${reportId}/image`;
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

export interface Report {
  id: string;
  latitude: number;
  longitude: number;
  description: string;
  urgency: string;
  image_url?: string;
  image_filename?: string;
  created_at: string;
  status: string;
  resolved_at?: string;
  resolved_note?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  response: string;
  sources: string[];
}
