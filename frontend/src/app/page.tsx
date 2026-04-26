"use client";

import Image from "next/image";
import Link from "next/link";
import { useLanguage, LanguageSelector } from "@/lib/language";

const HOME_EMERGENCY_COPY = {
  en: {
    human: "If a person is in danger or may have rabies exposure, use local emergency care immediately. In India, call 112.",
    animal: "For animal-specific next steps and verified contacts, open Find Help.",
    cta: "Open Find Help",
  },
  hi: {
    human: "अगर कोई व्यक्ति खतरे में है या रेबीज़ एक्सपोज़र की आशंका है, तो तुरंत स्थानीय आपातकालीन सहायता लें। भारत में 112 पर कॉल करें।",
    animal: "जानवर से जुड़ी अगली कार्रवाई और सत्यापित संपर्कों के लिए Find Help खोलें।",
    cta: "Find Help खोलें",
  },
  mr: {
    human: "एखादी व्यक्ती धोक्यात असेल किंवा रेबीज एक्स्पोजरची शक्यता असेल, तर त्वरित स्थानिक आपत्कालीन मदत घ्या. भारतात 112 वर कॉल करा.",
    animal: "प्राण्यांसाठी पुढची पावले आणि पडताळलेले संपर्क पाहण्यासाठी Find Help उघडा.",
    cta: "Find Help उघडा",
  },
} as const;

export default function Home() {
  const { t, language } = useLanguage();
  const emergencyCopy = HOME_EMERGENCY_COPY[language as keyof typeof HOME_EMERGENCY_COPY] || HOME_EMERGENCY_COPY.en;

  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-8">
      {/* Hero */}
      <div className="text-center max-w-md mx-auto mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Image
            src="/logo.png"
            alt="IndieAid logo"
            width={48}
            height={48}
            priority
          />
          <h1 className="text-3xl font-bold text-[var(--color-warm-700)]">
            {t("app.name")}
          </h1>
        </div>
        <p className="text-lg text-[var(--color-warm-600)]">
          {t("app.tagline")}
        </p>
        <p className="text-sm text-gray-500 mt-2">
          {t("app.subtitle")}
        </p>
      </div>

      {/* Main Action */}
      <Link
        href="/analyze"
        className="w-full max-w-sm bg-[var(--color-warm-500)] hover:bg-[var(--color-warm-600)] text-white rounded-2xl p-6 text-center shadow-lg transition-all hover:shadow-xl hover:scale-[1.02] block mb-6"
      >
        <div className="text-4xl mb-3">📷</div>
        <div className="text-xl font-semibold mb-1">{t("home.help")}</div>
        <div className="text-sm opacity-90">
          {t("home.help.desc")}
        </div>
      </Link>

      {/* Secondary Actions */}
      <div className="w-full max-w-sm grid grid-cols-2 gap-4 mb-6">
        <Link
          href="/nearby"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">🏥</div>
          <div className="text-sm font-semibold text-gray-700">{t("home.nearby")}</div>
          <div className="text-xs text-gray-500">{t("home.nearby.desc")}</div>
        </Link>

        <Link
          href="/report"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">📍</div>
          <div className="text-sm font-semibold text-gray-700">{t("home.report")}</div>
          <div className="text-xs text-gray-500">{t("home.report.desc")}</div>
        </Link>

        <Link
          href="/chat"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">💬</div>
          <div className="text-sm font-semibold text-gray-700">{t("home.chat")}</div>
          <div className="text-xs text-gray-500">{t("home.chat.desc")}</div>
        </Link>

        <Link
          href="/learn"
          className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
        >
          <div className="text-2xl mb-2">📖</div>
          <div className="text-sm font-semibold text-gray-700">{t("home.learn")}</div>
          <div className="text-xs text-gray-500">{t("home.learn.desc")}</div>
        </Link>
      </div>

      {/* Emergency Banner */}
      <div className="w-full max-w-sm bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
        <div className="flex items-start gap-3">
          <span className="text-xl">🚨</span>
          <div>
            <div className="font-semibold text-red-700 text-sm">
              {t("home.emergency")}
            </div>
            <div className="text-xs text-red-700 mt-1 leading-relaxed">
              {emergencyCopy.human}
            </div>
            <div className="text-xs text-red-700 mt-2 leading-relaxed">
              {emergencyCopy.animal}
            </div>
            <Link
              href="/nearby"
              className="inline-block mt-3 text-xs font-semibold text-red-700 underline"
            >
              {emergencyCopy.cta}
            </Link>
          </div>
        </div>
      </div>

      {/* Language Selector */}
      <LanguageSelector />

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-gray-400">
        <p>{t("app.footer")}</p>
        <p className="mt-1">{t("disclaimer")}</p>
      </footer>
    </main>
  );
}
