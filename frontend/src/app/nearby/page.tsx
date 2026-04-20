"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchNearby, type ShelterVet } from "@/lib/api";

const TYPE_ICONS: Record<string, string> = {
  vet: "🏥",
  shelter: "🏠",
  ngo: "🤝",
};

export default function NearbyPage() {
  const [shelters, setShelters] = useState<ShelterVet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterType, setFilterType] = useState<string>("");
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
          // Default to Mumbai centre if geolocation fails
          setUserLocation({ lat: 19.076, lng: 72.8777 });
        }
      );
    } else {
      setUserLocation({ lat: 19.076, lng: 72.8777 });
    }
  }, []);

  useEffect(() => {
    if (!userLocation) return;

    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchNearby(
          userLocation.lat,
          userLocation.lng,
          10,
          filterType || undefined
        );
        setShelters(data);
      } catch {
        setError("Could not load nearby help. Please try again.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [userLocation, filterType]);

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">
            Find Help Nearby
          </h1>
          <p className="text-sm text-gray-500">
            Vets, shelters &amp; NGOs near you
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {[
          { value: "", label: "All" },
          { value: "vet", label: "🏥 Vets" },
          { value: "shelter", label: "🏠 Shelters" },
          { value: "ngo", label: "🤝 NGOs" },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilterType(f.value)}
            className={`px-4 py-2 rounded-full text-sm whitespace-nowrap ${
              filterType === f.value
                ? "bg-[var(--color-warm-500)] text-white"
                : "bg-white border border-gray-200 text-gray-600"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <div className="text-4xl animate-bounce mb-3">🐾</div>
          <p className="text-gray-500">Finding help near you...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Results */}
      {!loading && shelters.length === 0 && (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">📍</div>
          <p className="text-gray-500">No results found nearby. Try expanding your search area.</p>
        </div>
      )}

      <div className="space-y-3">
        {shelters.map((s) => (
          <div
            key={s.id}
            className="bg-white rounded-xl p-4 shadow-sm border border-gray-100"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span>{TYPE_ICONS[s.type] || "📍"}</span>
                  <h3 className="font-semibold text-gray-800">{s.name}</h3>
                </div>
                <p className="text-sm text-gray-500 mb-2">{s.address}</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="bg-gray-100 rounded-full px-2 py-1">
                    {s.hours}
                  </span>
                  {s.emergency_24hr && (
                    <span className="bg-red-100 text-red-700 rounded-full px-2 py-1 font-semibold">
                      24x7 Emergency
                    </span>
                  )}
                  {s.distance_km != null && (
                    <span className="bg-blue-50 text-blue-600 rounded-full px-2 py-1">
                      {s.distance_km} km away
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 mt-3">
              <a
                href={`tel:${s.phone}`}
                className="flex-1 bg-[var(--color-sage-500)] text-white rounded-lg p-2 text-center text-sm font-medium"
              >
                📞 Call
              </a>
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${s.latitude},${s.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 bg-blue-500 text-white rounded-lg p-2 text-center text-sm font-medium"
              >
                🗺️ Directions
              </a>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
