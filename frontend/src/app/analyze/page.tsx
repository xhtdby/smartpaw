"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { analyzeImageMultilingual, type MultilingualAnalysisResult, type AnalysisResult } from "@/lib/api";
import { useLanguage, LanguageSelector } from "@/lib/language";

const SAFETY_COLORS: Record<string, string> = {
  safe: "bg-green-100 text-green-800 border-green-300",
  caution: "bg-yellow-100 text-yellow-800 border-yellow-300",
  danger: "bg-red-100 text-red-800 border-red-300",
};

const SAFETY_ICONS: Record<string, string> = {
  safe: "✅",
  caution: "⚠️",
  danger: "🚫",
};

const EMOTION_ICONS: Record<string, string> = {
  happy: "😊",
  sad: "😢",
  angry: "😠",
  relaxed: "😌",
  fearful: "😨",
};

export default function AnalyzePage() {
  const { language, t } = useLanguage();
  const router = useRouter();
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [mlResult, setMlResult] = useState<MultilingualAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);

  // Derive display result reactively — language switching is instant with no extra network call
  const result: AnalysisResult | null = mlResult
    ? mlResult.dog_detected
      ? (() => {
          const langData = mlResult.languages[language];
          if (!langData) return null;
          return {
            dog_detected: true,
            emotion: mlResult.emotion,
            condition: mlResult.condition,
            safety: langData.safety,
            first_aid: langData.first_aid,
            empathetic_summary: langData.empathetic_summary,
            disclaimer: langData.disclaimer,
            language,
          } as AnalysisResult;
        })()
      : { dog_detected: false, first_aid: [], empathetic_summary: "", disclaimer: "", language } as AnalysisResult
    : null;

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [preview]);

  const handleFile = (file: File) => {
    if (preview) URL.revokeObjectURL(preview);
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setMlResult(null);
    setError("");
  };

  const startCamera = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      setCameraActive(true);
    } catch {
      setError("Camera access denied. Please upload a photo instead.");
    }
  };

  useEffect(() => {
    if (cameraActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraActive]);

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraActive(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        handleFile(file);
        stopCamera();
      }
    }, "image/jpeg", 0.85);
  };

  const analyze = async () => {
    if (!image) return;
    setLoading(true);
    setError("");
    try {
      // Single endpoint: vision model runs once, text LLM runs 3x in parallel server-side
      const data = await analyzeImageMultilingual(image);
      setMlResult(data);

      // Save English context for chat (condition data always comes from the shared vision pass)
      const enLang = data.languages?.["en"];
      const ctx = data.dog_detected ? [
        data.emotion ? `Emotion: ${data.emotion.label}` : "",
        data.condition?.breed_guess ? `Breed: ${data.condition.breed_guess}` : "",
        data.condition?.physical_condition || "",
        data.condition?.visible_injuries?.length ? `Injuries: ${data.condition.visible_injuries.join(", ")}` : "",
        data.condition?.health_concerns?.length ? `Concerns: ${data.condition.health_concerns.join(", ")}` : "",
        enLang?.safety ? `Safety: ${enLang.safety.level} - ${enLang.safety.reason}` : "",
      ].filter(Boolean).join("\n") : null;

      if (ctx) localStorage.setItem("smartpaw-analysis-context", ctx);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const goToChat = () => router.push("/chat?from=analysis");

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview("");
    setImage(null);
    setMlResult(null);
    setError("");
  };

  const safetyLabel = (level: string) => {
    if (level === "safe") return t("analyze.safety.safe");
    if (level === "danger") return t("analyze.safety.danger");
    return t("analyze.safety.caution");
  };

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">
            {t("analyze.title")}
          </h1>
          <p className="text-sm text-gray-500">{t("analyze.subtitle")}</p>
        </div>
        <LanguageSelector compact />
      </div>

      {/* Camera / Upload */}
      {!preview && !cameraActive && (
        <div className="space-y-4">
          <button
            onClick={startCamera}
            className="w-full bg-[var(--color-warm-500)] text-white rounded-xl p-5 text-center"
          >
            <div className="text-3xl mb-2">📷</div>
            <div className="font-semibold">{t("analyze.camera")}</div>
          </button>

          <button
            onClick={() => fileRef.current?.click()}
            className="w-full bg-white border-2 border-dashed border-gray-300 rounded-xl p-5 text-center text-gray-600 hover:border-[var(--color-warm-400)]"
          >
            <div className="text-3xl mb-2">🖼️</div>
            <div className="font-semibold">{t("analyze.upload")}</div>
            <div className="text-xs text-gray-400 mt-1">JPEG, PNG — max 10 MB</div>
          </button>

          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
        </div>
      )}

      {/* Camera Preview */}
      {cameraActive && (
        <div className="space-y-4">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full rounded-xl"
          />
          <div className="flex gap-3">
            <button
              onClick={capturePhoto}
              className="flex-1 bg-[var(--color-warm-500)] text-white rounded-xl p-4 font-semibold"
            >
              📸 Capture
            </button>
            <button
              onClick={stopCamera}
              className="px-4 bg-gray-100 rounded-xl text-gray-600"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Image Preview */}
      {preview && (
        <div className="space-y-4">
          <img
            src={preview}
            alt="Dog photo"
            className="w-full rounded-xl shadow-md max-h-80 object-cover"
          />

          {!result && (
            <div className="flex gap-3">
              <button
                onClick={analyze}
                disabled={loading}
                className="flex-1 bg-[var(--color-warm-500)] text-white rounded-xl p-4 font-semibold disabled:opacity-50"
              >
                {loading ? t("analyze.analyzing") : `🔍 ${t("analyze.analyze")}`}
              </button>
              <button onClick={reset} className="px-4 bg-gray-100 rounded-xl text-gray-600">
                ✕
              </button>
            </div>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="mt-6 text-center p-8 bg-white rounded-xl shadow-sm">
          <div className="text-4xl animate-bounce mb-4">🐾</div>
          <p className="text-[var(--color-warm-600)] font-medium">
            {t("analyze.analyzing")}
          </p>
          <p className="text-sm text-gray-400 mt-2">
            {t("analyze.loading.desc")}
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="mt-6 space-y-4">
          {/* No dog detected */}
          {!result.dog_detected && (
            <div className="bg-white rounded-xl p-6 shadow-sm text-center">
              <div className="text-4xl mb-3">🔍</div>
              <p className="text-gray-600">{result.empathetic_summary}</p>
            </div>
          )}

          {/* Dog detected — full results */}
          {result.dog_detected && (
            <>
              {/* Safety Badge */}
              {result.safety && (
                <div
                  className={`rounded-xl p-4 border-2 ${
                    SAFETY_COLORS[result.safety.level] || SAFETY_COLORS.caution
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold text-lg mb-1">
                    <span>{SAFETY_ICONS[result.safety.level] || "⚠️"}</span>
                    <span>{safetyLabel(result.safety.level)}</span>
                  </div>
                  <p className="text-sm">{result.safety.reason}</p>
                </div>
              )}

              {/* Emotion */}
              {result.emotion && (
                <div className="bg-white rounded-xl p-4 shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">
                      {EMOTION_ICONS[result.emotion.label] || "🐕"}
                    </span>
                    <div>
                      <div className="font-semibold capitalize">
                        {result.emotion.label}
                      </div>
                      <div className="text-xs text-gray-400">
                        {t("analyze.emotion.confidence")}: {Math.round(result.emotion.confidence * 100)}%
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Empathetic Summary */}
              {result.empathetic_summary && (
                <div className="bg-[var(--color-warm-100)] rounded-xl p-4">
                  <p className="text-[var(--color-warm-800)] leading-relaxed">
                    {result.empathetic_summary}
                  </p>
                </div>
              )}

              {/* Condition Details */}
              {result.condition && (
                <div className="bg-white rounded-xl p-4 shadow-sm space-y-3">
                  <h3 className="font-bold text-gray-700">{t("analyze.condition.title")}</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-400">{t("analyze.condition.breed")}:</span>{" "}
                      <span className="font-medium">{result.condition.breed_guess}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">{t("analyze.condition.age")}:</span>{" "}
                      <span className="font-medium">{result.condition.estimated_age}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    {result.condition.physical_condition}
                  </p>

                  {result.condition.visible_injuries.length > 0 && (
                    <div>
                      <div className="text-sm font-semibold text-red-600 mb-1">
                        {t("analyze.condition.injuries")}:
                      </div>
                      <ul className="text-sm text-red-600 list-disc list-inside">
                        {result.condition.visible_injuries.map((inj, i) => (
                          <li key={i}>{inj}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.condition.health_concerns.length > 0 && (
                    <div>
                      <div className="text-sm font-semibold text-yellow-700 mb-1">
                        {t("analyze.condition.concerns")}:
                      </div>
                      <ul className="text-sm text-yellow-700 list-disc list-inside">
                        {result.condition.health_concerns.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* First Aid Steps */}
              {result.first_aid.length > 0 && (
                <div className="bg-white rounded-xl p-4 shadow-sm">
                  <h3 className="font-bold text-[var(--color-sage-700)] mb-3">
                    🩹 {t("analyze.firstaid.title")}
                  </h3>
                  <ol className="space-y-2">
                    {result.first_aid.map((step) => (
                      <li key={step.step_number} className="flex gap-3 text-sm">
                        <span className="bg-[var(--color-sage-100)] text-[var(--color-sage-700)] rounded-full w-6 h-6 flex items-center justify-center font-bold text-xs shrink-0">
                          {step.step_number}
                        </span>
                        <span className="text-gray-700">{step.instruction}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <Link
                  href="/nearby"
                  className="bg-[var(--color-sage-500)] text-white rounded-xl p-3 text-center text-sm font-semibold"
                >
                  🏥 {t("home.nearby")}
                </Link>
                <button
                  onClick={goToChat}
                  className="bg-[var(--color-warm-500)] text-white rounded-xl p-3 text-center text-sm font-semibold"
                >
                  💬 {t("analyze.followup")}
                </button>
              </div>

              {/* Disclaimer */}
              <div className="bg-gray-50 rounded-xl p-3 text-xs text-gray-400 text-center">
                ⚕️ {t("disclaimer")}
              </div>
            </>
          )}

          {/* New Analysis Button */}
          <button
            onClick={reset}
            className="w-full bg-gray-100 text-gray-600 rounded-xl p-3 font-medium"
          >
            {t("analyze.new")}
          </button>
        </div>
      )}
    </main>
  );
}
