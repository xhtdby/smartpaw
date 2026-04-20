"use client";

import Link from "next/link";

const GUIDES = [
  {
    emoji: "🤝",
    title: "How to Safely Approach a Stray Dog",
    summary:
      "Stay calm, move slowly, turn sideways, and let the dog come to you. Never chase or corner a stray.",
    tips: [
      "Avoid direct eye contact — it can feel threatening",
      "Extend the back of your hand slowly for sniffing",
      "Watch the tail: tucked = fear, stiff = alert",
      "If the dog growls, stop and give space",
    ],
  },
  {
    emoji: "🩹",
    title: "Basic First Aid for Bleeding Wounds",
    summary:
      "Apply gentle pressure with a clean cloth, don't remove embedded objects, and get to a vet.",
    tips: [
      "Wear gloves if available",
      "Do NOT use Dettol or hydrogen peroxide on dogs",
      "Wrap wounds loosely with clean cloth",
      "Rush to vet for heavy, non-stop bleeding",
    ],
  },
  {
    emoji: "🌡️",
    title: "Dehydration & Heatstroke",
    summary:
      "Offer cool (not ice cold) water, move to shade, wet paws and belly with cool water.",
    tips: [
      "Signs: dry gums, sunken eyes, excessive panting",
      "Wet the dog's paws, belly, and neck",
      "Never douse with ice water — it causes shock",
      "Keep water bowls outside your building for strays",
    ],
  },
  {
    emoji: "🦠",
    title: "Mange — What You Can Do",
    summary:
      "Mange is treatable! Contact an NGO for proper treatment. Never apply home remedies like kerosene.",
    tips: [
      "Signs: hair loss patches, red skin, excessive scratching",
      "Do NOT use kerosene, engine oil, or turmeric paste",
      "Provide nutritious food to build immunity",
      "Report to WSD or IDA for treatment",
    ],
  },
  {
    emoji: "💉",
    title: "Rabies Awareness",
    summary:
      "Rabies is 100% fatal but 100% preventable. Wash any bite wound with soap and water for 15 minutes.",
    tips: [
      "ANY bite or scratch breaking skin needs PEP vaccine",
      "Wash wound with soap + running water for 15 min",
      "Go to hospital immediately for anti-rabies shots",
      "Do NOT apply chilli, turmeric, or folk remedies",
    ],
  },
  {
    emoji: "🐶",
    title: "Dog Body Language Guide",
    summary:
      "Understanding body language keeps both you and the dog safe.",
    tips: [
      "Happy: relaxed body, wide tail wags, open mouth smile",
      "Scared: tucked tail, ears flat, crouching, lip licking",
      "Aggressive: stiff body, raised hackles, showing teeth",
      "In pain: whimpering, limping, licking one area obsessively",
    ],
  },
  {
    emoji: "🍖",
    title: "Feeding Strays Safely",
    summary:
      "Feed at the same time and place daily. Avoid chocolate, onions, and cooked bones.",
    tips: [
      "Good: rice + boiled chicken/egg, roti with dal, kibble",
      "Bad: chocolate, onion, garlic, grapes, spicy food",
      "Always provide water alongside food",
      "Clean up leftovers to avoid attracting rats",
    ],
  },
  {
    emoji: "⚖️",
    title: "Legal Rights of Stray Dogs in India",
    summary:
      "Stray dogs are protected by law. Feeding them is legal. Harming them is a criminal offense.",
    tips: [
      "PCA Act 1960: illegal to harm, poison, or kill strays",
      "ABC Rules 2023: only sterilize/vaccinate, no relocation",
      "No society can legally ban feeding strays",
      "Report cruelty: AWBI helpline 1962",
    ],
  },
];

export default function LearnPage() {
  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">
            Learn Dog Care
          </h1>
          <p className="text-sm text-gray-500">
            Essential guides for helping strays
          </p>
        </div>
      </div>

      {/* Offline Notice */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-sm text-blue-700 mb-6">
        📱 These guides are available offline. Bookmark this page for emergencies.
      </div>

      {/* Guides */}
      <div className="space-y-4">
        {GUIDES.map((guide, i) => (
          <details
            key={i}
            className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden"
          >
            <summary className="p-4 cursor-pointer hover:bg-gray-50">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{guide.emoji}</span>
                <div>
                  <h3 className="font-semibold text-gray-800">
                    {guide.title}
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {guide.summary}
                  </p>
                </div>
              </div>
            </summary>
            <div className="px-4 pb-4 border-t border-gray-50 pt-3">
              <ul className="space-y-2">
                {guide.tips.map((tip, j) => (
                  <li
                    key={j}
                    className="flex gap-2 text-sm text-gray-600"
                  >
                    <span className="text-[var(--color-warm-400)]">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        ))}
      </div>

      {/* Emergency Banner */}
      <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-center">
        <div className="font-semibold text-red-700 text-sm mb-1">
          🚨 In an emergency, call now
        </div>
        <a
          href="tel:1962"
          className="text-red-600 font-bold text-lg underline"
        >
          AWBI Helpline: 1962
        </a>
      </div>
    </main>
  );
}
