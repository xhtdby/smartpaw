"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { submitReport, fetchReports, type Report } from "@/lib/api";

const URGENCY_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export default function ReportPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [description, setDescription] = useState("");
  const [urgency, setUrgency] = useState("medium");
  const [userLocation, setUserLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setUserLocation({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          });
        },
        () => {
          setUserLocation({ lat: 19.076, lng: 72.8777 });
        }
      );
    } else {
      setUserLocation({ lat: 19.076, lng: 72.8777 });
    }
  }, []);

  useEffect(() => {
    if (!userLocation) return;
    loadReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userLocation]);

  const loadReports = async () => {
    if (!userLocation) return;
    setLoading(true);
    try {
      const data = await fetchReports(userLocation.lat, userLocation.lng, 10);
      setReports(data);
    } catch {
      // Silently fail — reports may be empty
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!userLocation || !description.trim()) return;
    setSubmitting(true);
    try {
      await submitReport({
        latitude: userLocation.lat,
        longitude: userLocation.lng,
        description: description.trim(),
        urgency,
      });
      setDescription("");
      setShowForm(false);
      await loadReports();
    } catch {
      alert("Failed to submit report. Please try again.");
    } finally {
      setSubmitting(false);
    }
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
            Community Reports
          </h1>
          <p className="text-sm text-gray-500">
            Stray dogs needing help near you
          </p>
        </div>
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
          <h3 className="font-bold text-gray-700 mb-3">Report a Dog in Need</h3>

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the dog and situation... (e.g., 'Injured dog near bus stop, limping on left front leg, appears to have a wound')"
            className="w-full border border-gray-200 rounded-lg p-3 text-sm h-24 resize-none focus:outline-none focus:border-[var(--color-warm-400)]"
          />

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
            {submitting ? "Submitting..." : "Submit Report"}
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <div className="text-4xl animate-bounce mb-3">🐾</div>
          <p className="text-gray-500">Loading nearby reports...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && reports.length === 0 && (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">📍</div>
          <p className="text-gray-500 mb-2">No reports nearby yet.</p>
          <p className="text-sm text-gray-400">
            Be the first to report a dog in need!
          </p>
        </div>
      )}

      {/* Reports List */}
      <div className="space-y-3">
        {reports.map((r) => (
          <div
            key={r.id}
            className="bg-white rounded-xl p-4 shadow-sm border border-gray-100"
          >
            <div className="flex items-start justify-between mb-2">
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                  URGENCY_COLORS[r.urgency] || URGENCY_COLORS.medium
                }`}
              >
                {r.urgency}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(r.created_at).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
            <p className="text-sm text-gray-700">{r.description}</p>
            <div className="mt-2 flex gap-2">
              <a
                href={`https://www.google.com/maps?q=${r.latitude},${r.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 underline"
              >
                📍 View on map
              </a>
              <span className="text-xs text-gray-300">|</span>
              <span className="text-xs text-gray-400 capitalize">
                Status: {r.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
