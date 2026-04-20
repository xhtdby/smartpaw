"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  submitReport,
  fetchReports,
  updateReportStatus,
  getReportImageUrl,
  type Report,
} from "@/lib/api";
import { useLanguage, LanguageSelector } from "@/lib/language";

const URGENCY_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const STATUS_COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-700",
  "in-progress": "bg-purple-100 text-purple-700",
  resolved: "bg-green-100 text-green-700",
};

export default function ReportPage() {
  const { t } = useLanguage();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [description, setDescription] = useState("");
  const [urgency, setUrgency] = useState("medium");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [filterUrgency, setFilterUrgency] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => setUserLocation({ lat: 19.076, lng: 72.8777 })
      );
    } else {
      setUserLocation({ lat: 19.076, lng: 72.8777 });
    }
  }, []);

  useEffect(() => {
    if (!userLocation) return;
    loadReports();
  }, [userLocation, filterUrgency, filterStatus]);

  const loadReports = async () => {
    if (!userLocation) return;
    setLoading(true);
    try {
      const data = await fetchReports(
        userLocation.lat,
        userLocation.lng,
        10,
        filterUrgency || undefined,
        filterStatus || undefined
      );
      setReports(data);
    } catch { /* empty */ } finally {
      setLoading(false);
    }
  };

  const handleImageSelect = (file: File) => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleSubmit = async () => {
    if (!userLocation || !description.trim()) return;
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("latitude", userLocation.lat.toString());
      formData.append("longitude", userLocation.lng.toString());
      formData.append("description", description.trim());
      formData.append("urgency", urgency);
      if (imageFile) formData.append("image", imageFile);

      await submitReport(formData);
      setDescription("");
      setImageFile(null);
      if (imagePreview) URL.revokeObjectURL(imagePreview);
      setImagePreview("");
      setShowForm(false);
      await loadReports();
    } catch {
      alert("Failed to submit report. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusUpdate = async (id: string, status: string) => {
    const note = status === "resolved" ? prompt("Add a resolution note (optional):") || "" : "";
    try {
      await updateReportStatus(id, status, note);
      await loadReports();
    } catch {
      alert("Failed to update status.");
    }
  };

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">←</Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">{t("report.title")}</h1>
          <p className="text-sm text-gray-500">{t("report.subtitle")}</p>
        </div>
        <LanguageSelector compact />
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-[var(--color-warm-500)] text-white rounded-full w-10 h-10 flex items-center justify-center text-xl"
        >
          +
        </button>
      </div>

      {/* Report Form */}
      {showForm && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mb-6">
          <h3 className="font-bold text-gray-700 mb-3">{t("report.form.title")}</h3>

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("report.form.placeholder")}
            className="w-full border border-gray-200 rounded-lg p-3 text-sm h-24 resize-none focus:outline-none focus:border-[var(--color-warm-400)]"
          />

          {/* Image Upload */}
          <div className="mt-3">
            {imagePreview ? (
              <div className="relative">
                <img src={imagePreview} alt="Preview" className="w-full h-32 object-cover rounded-lg" />
                <button
                  onClick={() => { setImageFile(null); URL.revokeObjectURL(imagePreview); setImagePreview(""); }}
                  className="absolute top-1 right-1 bg-black/50 text-white rounded-full w-6 h-6 text-xs"
                >✕</button>
              </div>
            ) : (
              <button
                onClick={() => fileRef.current?.click()}
                className="w-full border-2 border-dashed border-gray-200 rounded-lg p-3 text-sm text-gray-400 hover:border-[var(--color-warm-300)]"
              >
                📷 {t("report.form.photo")}
              </button>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImageSelect(f); }}
            />
          </div>

          <div className="mt-3">
            <div className="text-sm text-gray-500 mb-2">Urgency:</div>
            <div className="flex gap-2">
              {["low", "medium", "high", "critical"].map((u) => (
                <button
                  key={u}
                  onClick={() => setUrgency(u)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize ${
                    urgency === u
                      ? URGENCY_COLORS[u] + " ring-2 ring-offset-1 ring-gray-300"
                      : "bg-gray-50 text-gray-400"
                  }`}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-3 text-xs text-gray-400">
            📍 Your current location will be attached automatically
          </div>

          <button
            onClick={handleSubmit}
            disabled={submitting || !description.trim()}
            className="mt-3 w-full bg-[var(--color-warm-500)] text-white rounded-lg p-3 font-semibold disabled:opacity-50"
          >
            {submitting ? t("report.form.submitting") : t("report.form.submit")}
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
        <select
          value={filterUrgency}
          onChange={(e) => setFilterUrgency(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-xs bg-white"
        >
          <option value="">All urgency</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-xs bg-white"
        >
          <option value="">All status</option>
          <option value="open">Open</option>
          <option value="in-progress">In Progress</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <div className="text-4xl animate-bounce mb-3">🐾</div>
          <p className="text-gray-500">{t("report.loading")}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && reports.length === 0 && (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">📍</div>
          <p className="text-gray-500 mb-2">{t("report.empty")}</p>
          <p className="text-sm text-gray-400">{t("report.empty.cta")}</p>
        </div>
      )}

      {/* Reports */}
      <div className="space-y-3">
        {reports.map((r) => (
          <div key={r.id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-start justify-between mb-2">
              <div className="flex gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${URGENCY_COLORS[r.urgency] || URGENCY_COLORS.medium}`}>
                  {r.urgency}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[r.status] || STATUS_COLORS.open}`}>
                  {r.status}
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(r.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>

            {r.image_filename && (
              <img
                src={getReportImageUrl(r.id)}
                alt="Report"
                className="w-full h-32 object-cover rounded-lg mb-2"
                loading="lazy"
              />
            )}

            <p className="text-sm text-gray-700">{r.description}</p>

            {r.resolved_note && (
              <p className="text-xs text-green-600 mt-1 italic">✓ {r.resolved_note}</p>
            )}

            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <a
                href={`https://www.google.com/maps?q=${r.latitude},${r.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 underline"
              >
                📍 View on map
              </a>
              {r.status === "open" && (
                <>
                  <span className="text-xs text-gray-300">|</span>
                  <button onClick={() => handleStatusUpdate(r.id, "in-progress")} className="text-xs text-purple-500 underline">
                    Mark In-Progress
                  </button>
                </>
              )}
              {r.status === "in-progress" && (
                <>
                  <span className="text-xs text-gray-300">|</span>
                  <button onClick={() => handleStatusUpdate(r.id, "resolved")} className="text-xs text-green-500 underline">
                    Mark Resolved
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
