"use client";

import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-8">
      {/* Hero */}
      <div className="text-center max-w-md mx-auto mb-8">
        <div className="text-6xl mb-4">🐾</div>
        <h1 className="text-3xl font-bold text-[var(--color-warm-700)] mb-2">
          SmartPaw
        </h1>
        <p className="text-lg text-[var(--color-warm-600)]">
          Helping Mumbai&apos;s stray dogs, one photo at a time
        </p>
        <p className="text-sm text-gray-500 mt-2">
          AI-powered first aid guidance, emotion assessment, and rescue
          coordination
        </p>
      </div>

      {/* Main Action */}
      <Link
        href="/analyze"
        className="w-full max-w-sm bg-[var(--color-warm-500)] hover:bg-[var(--color-warm-600)] text-white rounded-2xl p-6 text-center shadow-lg transition-all hover:shadow-xl hover:scale-[1.02] block mb-6"
      >
        <div className="text-4xl mb-3">📷</div>
        <div className="text-xl font-semibold mb-1">Help a Dog</div>
        <div className="text-sm opacity-90">
          Take a photo to assess condition &amp; get first aid guidance
        </div>
      </Link>

      {/* Secondary Actions */}
      <div className="w-full max-w-sm grid grid-cols-2 gap-4 mb-6">
        <Link
          href="/nearby"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">🏥</div>
          <div className="text-sm font-semibold text-gray-700">Find Help</div>
          <div className="text-xs text-gray-500">Vets &amp; shelters near you</div>
        </Link>

        <Link
          href="/report"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">📍</div>
          <div className="text-sm font-semibold text-gray-700">Report</div>
          <div className="text-xs text-gray-500">Log a stray needing help</div>
        </Link>

        <Link
          href="/chat"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">💬</div>
          <div className="text-sm font-semibold text-gray-700">Ask SmartPaw</div>
          <div className="text-xs text-gray-500">First aid chat assistant</div>
        </Link>

        <Link
          href="/learn"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">📖</div>
          <div className="text-sm font-semibold text-gray-700">Learn</div>
          <div className="text-xs text-gray-500">Dog care &amp; first aid guides</div>
        </Link>
      </div>

      {/* Emergency Banner */}
      <div className="w-full max-w-sm bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
        <div className="flex items-start gap-3">
          <span className="text-xl">🚨</span>
          <div>
            <div className="font-semibold text-red-700 text-sm">
              Emergency? Call now
            </div>
            <div className="text-xs text-red-600 mt-1">
              AWBI Helpline:{" "}
              <a href="tel:1962" className="underline font-bold">
                1962
              </a>
            </div>
            <div className="text-xs text-red-600">
              RESQ 24x7:{" "}
              <a href="tel:+919820233633" className="underline">
                +91 98202 33633
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Language Selector */}
      <div className="flex gap-2 text-sm text-gray-500">
        <button className="px-3 py-1 rounded-full bg-[var(--color-warm-100)] text-[var(--color-warm-700)] font-medium">
          English
        </button>
        <button className="px-3 py-1 rounded-full hover:bg-gray-100">
          हिन्दी
        </button>
        <button className="px-3 py-1 rounded-full hover:bg-gray-100">
          मराठी
        </button>
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-gray-400">
        <p>SmartPaw — AI for compassion</p>
        <p className="mt-1">
          Not a substitute for veterinary care. Always consult a professional.
        </p>
      </footer>
    </main>
  );
}
