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

const HOME_MORE_COPY = {
  en: {
    more: "More",
    report: "Report a stray",
    learn: "Learn",
    firstAid: "First-aid kit",
    cruelty: "Cruelty help",
    drives: "Drives",
    settings: "Settings",
  },
  hi: {
    more: "और",
    report: "आवारा जानवर की रिपोर्ट",
    learn: "सीखें",
    firstAid: "प्राथमिक चिकित्सा किट",
    cruelty: "क्रूरता में मदद",
    drives: "ड्राइव्स",
    settings: "सेटिंग्स",
  },
  mr: {
    more: "आणखी",
    report: "भटक्या प्राण्याची नोंद",
    learn: "शिका",
    firstAid: "प्रथमोपचार किट",
    cruelty: "क्रूरतेसाठी मदत",
    drives: "ड्राइव्ह्स",
    settings: "सेटिंग्ज",
  },
} as const;

export default function Home() {
  const { t, language } = useLanguage();
  const emergencyCopy = HOME_EMERGENCY_COPY[language as keyof typeof HOME_EMERGENCY_COPY] || HOME_EMERGENCY_COPY.en;
  const moreCopy = HOME_MORE_COPY[language as keyof typeof HOME_MORE_COPY] || HOME_MORE_COPY.en;

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

      <div className="w-full max-w-sm grid grid-cols-1 gap-3 mb-6">
        <Link
          href="/analyze"
          className="bg-[var(--color-warm-500)] hover:bg-[var(--color-warm-600)] text-white rounded-xl p-5 text-center shadow-md transition-colors block"
        >
          <div className="text-xl font-semibold mb-1">{t("home.help")}</div>
          <div className="text-sm opacity-90">{t("home.help.desc")}</div>
        </Link>

        <div className="grid grid-cols-2 gap-3">
          <Link
            href="/chat"
            className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
          >
            <div className="text-sm font-semibold text-gray-700">{t("home.chat")}</div>
            <div className="text-xs text-gray-500">{t("home.chat.desc")}</div>
          </Link>

          <Link
            href="/nearby"
            className="bg-white border-2 border-[var(--color-sage-100)] hover:border-[var(--color-sage-500)] rounded-xl p-4 text-center transition-all block"
          >
            <div className="text-sm font-semibold text-gray-700">{t("home.nearby")}</div>
            <div className="text-xs text-gray-500">{t("home.nearby.desc")}</div>
          </Link>
        </div>
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

      <details className="w-full max-w-sm bg-white border border-gray-200 rounded-xl mb-6 overflow-hidden">
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-gray-700">
          {moreCopy.more}
        </summary>
        <div className="grid grid-cols-2 gap-2 p-3 border-t border-gray-100">
          {[
            { href: "/learn", label: moreCopy.learn },
            { href: "/first-aid-kit", label: moreCopy.firstAid },
            { href: "/report", label: moreCopy.report },
            { href: "/cruelty", label: moreCopy.cruelty },
            { href: "/drives", label: moreCopy.drives },
            { href: "/settings", label: moreCopy.settings },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm text-gray-700 hover:border-[var(--color-warm-300)] hover:bg-[var(--color-warm-50)]"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </details>

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
