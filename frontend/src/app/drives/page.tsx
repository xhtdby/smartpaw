"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { subscribeToMailingList } from "@/lib/api";
import { LanguageSelector, useLanguage } from "@/lib/language";

type PageLanguage = "en" | "hi" | "mr";
type Tag = "food" | "water" | "medicine" | "transport";

const TAGS: Tag[] = ["food", "water", "medicine", "transport"];

const COPY = {
  en: {
    title: "Drives",
    subtitle: "Opt in for food, water, medicine, and transport coordination",
    body:
      "This is an early manual coordination list. No analytics, no third-party email service, and no spam in this stage.",
    email: "Email",
    city: "City",
    interests: "Interests",
    submit: "Join list",
    submitting: "Joining...",
    success: "You're on the list. Duplicate signups update the same email.",
    invalid: "Use a valid email address.",
    error: "Could not save this signup. Please try again.",
    tags: {
      food: "Food",
      water: "Water",
      medicine: "Medicine",
      transport: "Transport",
    },
  },
  hi: {
    title: "ड्राइव्स",
    subtitle: "खाना, पानी, दवा और परिवहन समन्वय के लिए जुड़ें",
    body:
      "यह अभी शुरुआती मैनुअल समन्वय सूची है। इस चरण में कोई एनालिटिक्स, कोई थर्ड-पार्टी ईमेल सेवा और कोई स्पैम नहीं है।",
    email: "ईमेल",
    city: "शहर",
    interests: "रुचियां",
    submit: "सूची में जुड़ें",
    submitting: "जुड़ रहा है...",
    success: "आप सूची में जुड़ गए हैं। उसी ईमेल से दोबारा जुड़ने पर जानकारी अपडेट होती है।",
    invalid: "सही ईमेल पता डालें।",
    error: "यह signup सेव नहीं हो सका। कृपया फिर कोशिश करें।",
    tags: {
      food: "खाना",
      water: "पानी",
      medicine: "दवा",
      transport: "परिवहन",
    },
  },
  mr: {
    title: "ड्राइव्ह्स",
    subtitle: "अन्न, पाणी, औषध आणि वाहतूक समन्वयासाठी सहभागी व्हा",
    body:
      "ही सध्या सुरुवातीची मॅन्युअल समन्वय सूची आहे. या टप्प्यात अॅनालिटिक्स नाही, तृतीय-पक्ष ईमेल सेवा नाही आणि स्पॅम नाही.",
    email: "ईमेल",
    city: "शहर",
    interests: "रुची",
    submit: "सूचीत जोडा",
    submitting: "जोडत आहे...",
    success: "तुम्ही सूचीत आहात. त्याच ईमेलने पुन्हा नोंद केल्यास माहिती अपडेट होते.",
    invalid: "योग्य ईमेल पत्ता वापरा.",
    error: "ही नोंद सेव्ह झाली नाही. कृपया पुन्हा प्रयत्न करा.",
    tags: {
      food: "अन्न",
      water: "पाणी",
      medicine: "औषध",
      transport: "वाहतूक",
    },
  },
} as const;

export default function DrivesPage() {
  const { language } = useLanguage();
  const copy = COPY[(language as PageLanguage) || "en"];
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
  const [selectedTags, setSelectedTags] = useState<Tag[]>(["food", "water"]);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState("");

  const toggleTag = (tag: Tag) => {
    setSelectedTags((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]
    );
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if (!email.includes("@")) {
      setError(copy.invalid);
      return;
    }
    setStatus("loading");
    try {
      await subscribeToMailingList({
        email,
        city: city.trim() || undefined,
        interest_tags: selectedTags,
      });
      setStatus("success");
    } catch {
      setStatus("error");
      setError(copy.error);
    }
  };

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">{copy.title}</h1>
          <p className="text-sm text-gray-500">{copy.subtitle}</p>
        </div>
        <LanguageSelector compact />
      </div>

      <section className="bg-white border border-gray-100 rounded-xl p-4 mb-4">
        <p className="text-sm text-gray-700 leading-relaxed">{copy.body}</p>
      </section>

      <form onSubmit={submit} className="bg-white border border-gray-100 rounded-xl p-4 space-y-4">
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">{copy.email}</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-[var(--color-warm-400)]"
            required
          />
        </label>

        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">{copy.city}</span>
          <input
            value={city}
            onChange={(event) => setCity(event.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-[var(--color-warm-400)]"
          />
        </label>

        <div>
          <div className="text-sm font-medium text-gray-700 mb-2">{copy.interests}</div>
          <div className="grid grid-cols-2 gap-2">
            {TAGS.map((tag) => (
              <label key={tag} className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedTags.includes(tag)}
                  onChange={() => toggleTag(tag)}
                />
                <span>{copy.tags[tag]}</span>
              </label>
            ))}
          </div>
        </div>

        {(error || status === "success") && (
          <div className={`rounded-lg px-3 py-2 text-sm ${status === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            {status === "success" ? copy.success : error}
          </div>
        )}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full rounded-xl bg-[var(--color-warm-500)] px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {status === "loading" ? copy.submitting : copy.submit}
        </button>
      </form>
    </main>
  );
}
