"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { analyzeImage, type AnalysisResult } from "@/lib/api";

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
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [language, setLanguage] = useState("en");
  const fileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraActive, setCameraActive] = useState(false);

  const handleFile = (file: File) => {
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError("");
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch {
      setError("Camera access denied. Please upload a photo instead.");
    }
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
        // Stop camera
        const stream = videoRef.current?.srcObject as MediaStream;
        stream?.getTracks().forEach((t) => t.stop());
        setCameraActive(false);
      }
    }, "image/jpeg", 0.85);
  };

  const analyze = async () => {
    if (!image) return;
    setLoading(true);
    setError("");
    try {
      const data = await analyzeImage(image, language);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">
            Help a Dog
          </h1>
          <p className="text-sm text-gray-500">
            Take or upload a photo for assessment
          </p>
        </div>
      </div>

      {/* Camera / Upload */}
      {!preview && !cameraActive && (
        <div className="space-y-4">
          <button
            onClick={startCamera}
            className="w-full bg-[var(--color-warm-500)] text-white rounded-xl p-5 text-center"
          >
            <div className="text-3xl mb-2">📷</div>
            <div className="font-semibold">Open Camera</div>
          </button>

          <button
            onClick={() => fileRef.current?.click()}
            className="w-full bg-white border-2 border-dashed border-gray-300 rounded-xl p-5 text-center text-gray-600 hover:border-[var(--color-warm-400)]"
          >
            <div className="text-3xl mb-2">🖼️</div>
            <div className="font-semibold">Upload Photo</div>
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
            className="w-full rounded-xl"
          />
          <button
            onClick={capturePhoto}
            className="w-full bg-[var(--color-warm-500)] text-white rounded-xl p-4 font-semibold"
          >
            📸 Capture Photo
          </button>
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

          {/* Language Selection */}
          <div className="flex gap-2 justify-center">
            {[
              { code: "en", label: "English" },
              { code: "hi", label: "हिन्दी" },
              { code: "mr", label: "मराठी" },
            ].map((lang) => (
              <button
                key={lang.code}
                onClick={() => setLanguage(lang.code)}
                className={`px-3 py-1 rounded-full text-sm ${
                  language === lang.code
                    ? "bg-[var(--color-warm-500)] text-white"
                    : "bg-gray-100 text-gray-600"
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>

          {!result && (
            <div className="flex gap-3">
              <button
                onClick={analyze}
                disabled={loading}
                className="flex-1 bg-[var(--color-warm-500)] text-white rounded-xl p-4 font-semibold disabled:opacity-50"
              >
                {loading ? "Analyzing..." : "🔍 Analyze"}
              </button>
              <button
                onClick={() => {
                  setPreview("");
                  setImage(null);
                  setResult(null);
                }}
                className="px-4 bg-gray-100 rounded-xl text-gray-600"
              >
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
            Analyzing the photo...
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Let&apos;s see how we can help this pup
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
                    <span className="capitalize">{result.safety.level} to Approach</span>
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
                        Confidence: {Math.round(result.emotion.confidence * 100)}%
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
                  <h3 className="font-bold text-gray-700">Condition Assessment</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-400">Breed:</span>{" "}
                      <span className="font-medium">{result.condition.breed_guess}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Age:</span>{" "}
                      <span className="font-medium">{result.condition.estimated_age}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    {result.condition.physical_condition}
                  </p>

                  {result.condition.visible_injuries.length > 0 && (
                    <div>
                      <div className="text-sm font-semibold text-red-600 mb-1">
                        Visible Injuries:
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
                        Health Concerns:
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
                    🩹 First Aid Steps
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
                  🏥 Find Nearest Help
                </Link>
                <Link
                  href="/chat"
                  className="bg-[var(--color-warm-500)] text-white rounded-xl p-3 text-center text-sm font-semibold"
                >
                  💬 Ask Follow-up
                </Link>
              </div>

              {/* Disclaimer */}
              <div className="bg-gray-50 rounded-xl p-3 text-xs text-gray-400 text-center">
                ⚕️ {result.disclaimer}
              </div>
            </>
          )}

          {/* New Analysis Button */}
          <button
            onClick={() => {
              setPreview("");
              setImage(null);
              setResult(null);
            }}
            className="w-full bg-gray-100 text-gray-600 rounded-xl p-3 font-medium"
          >
            Analyze Another Photo
          </button>
        </div>
      )}
    </main>
  );
}
