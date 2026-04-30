"use client";

import Link from "next/link";
import { LanguageSelector, useLanguage } from "@/lib/language";

type PageLanguage = "en" | "hi" | "mr";

const COPY = {
  en: {
    title: "Settings",
    subtitle: "Language and device storage controls",
    language: "Language",
    storageTitle: "Storage",
    storageBody:
      "Chat threads and analyzed photos are stored on this device. Use Clear all from the chat screen to remove them.",
  },
  hi: {
    title: "सेटिंग्स",
    subtitle: "भाषा और डिवाइस स्टोरेज नियंत्रण",
    language: "भाषा",
    storageTitle: "स्टोरेज",
    storageBody:
      "चैट थ्रेड और जांची गई फोटो इस डिवाइस पर सेव होती हैं। उन्हें हटाने के लिए चैट स्क्रीन में सब साफ़ करें का उपयोग करें।",
  },
  mr: {
    title: "सेटिंग्ज",
    subtitle: "भाषा आणि डिव्हाइस स्टोरेज नियंत्रण",
    language: "भाषा",
    storageTitle: "स्टोरेज",
    storageBody:
      "चॅट थ्रेड आणि तपासलेले फोटो या डिव्हाइसवर सेव्ह होतात. ते हटवण्यासाठी चॅट स्क्रीनवरील सर्व साफ करा वापरा.",
  },
} as const;

export default function SettingsPage() {
  const { language } = useLanguage();
  const copy = COPY[(language as PageLanguage) || "en"];

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
      </div>

      <section className="bg-white border border-gray-100 rounded-xl p-4 mb-4">
        <h2 className="font-semibold text-gray-800 mb-3">{copy.language}</h2>
        <LanguageSelector />
      </section>

      <section className="bg-white border border-gray-100 rounded-xl p-4">
        <h2 className="font-semibold text-gray-800 mb-2">{copy.storageTitle}</h2>
        <p className="text-sm text-gray-600 leading-relaxed">{copy.storageBody}</p>
      </section>
    </main>
  );
}
