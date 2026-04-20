"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

type Language = "en" | "hi" | "mr";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const translations: Record<Language, Record<string, string>> = {
  en: {
    "app.name": "SmartPaw",
    "app.tagline": "Helping Mumbai's stray dogs, one photo at a time",
    "app.subtitle": "AI-powered first aid guidance, emotion assessment, and rescue coordination",
    "home.help": "Help a Dog",
    "home.help.desc": "Take a photo to assess condition & get first aid guidance",
    "home.nearby": "Find Help",
    "home.nearby.desc": "Vets & shelters near you",
    "home.report": "Report",
    "home.report.desc": "Log a stray needing help",
    "home.chat": "Ask SmartPaw",
    "home.chat.desc": "First aid chat assistant",
    "home.learn": "Learn",
    "home.learn.desc": "Dog care & first aid guides",
    "home.emergency": "Emergency? Call now",
    "analyze.title": "Help a Dog",
    "analyze.subtitle": "Take or upload a photo for assessment",
    "analyze.camera": "Open Camera",
    "analyze.upload": "Upload Photo",
    "analyze.analyze": "Analyze",
    "analyze.analyzing": "Analyzing...",
    "analyze.new": "Analyze Another Photo",
    "nearby.title": "Find Help Nearby",
    "nearby.subtitle": "Vets, shelters & NGOs near you",
    "nearby.finding": "Finding help near you...",
    "nearby.empty": "No results found nearby. Try expanding your search area.",
    "report.title": "Community Reports",
    "report.subtitle": "Stray dogs needing help near you",
    "report.form.title": "Report a Dog in Need",
    "report.form.placeholder": "Describe the dog and situation...",
    "report.form.urgency": "Urgency:",
    "report.form.photo": "Attach Photo (optional)",
    "report.form.submit": "Submit Report",
    "report.form.submitting": "Submitting...",
    "report.loading": "Loading nearby reports...",
    "report.empty": "No reports nearby yet.",
    "report.empty.cta": "Be the first to report a dog in need!",
    "chat.title": "SmartPaw Chat",
    "chat.subtitle": "Ask about dog first aid & care",
    "chat.welcome": "Hi, I'm SmartPaw!",
    "chat.welcome.desc": "I can help you with first aid for stray dogs, understanding dog behavior, and finding resources in Mumbai.",
    "chat.placeholder": "Ask about dog care or first aid...",
    "chat.disclaimer": "Not a vet. Always consult a professional for serious cases.",
    "common.back": "←",
    "common.call": "Call",
    "common.directions": "Directions",
    "disclaimer": "Not a substitute for veterinary care. Always consult a professional.",
  },
  hi: {
    "app.name": "SmartPaw",
    "app.tagline": "मुंबई के आवारा कुत्तों की मदद, एक फोटो से",
    "app.subtitle": "AI-संचालित प्राथमिक चिकित्सा मार्गदर्शन और बचाव समन्वय",
    "home.help": "कुत्ते की मदद करें",
    "home.help.desc": "स्थिति जांचने के लिए फोटो लें",
    "home.nearby": "मदद खोजें",
    "home.nearby.desc": "आस-पास के पशु चिकित्सक",
    "home.report": "रिपोर्ट करें",
    "home.report.desc": "मदद चाहने वाले कुत्ते की सूचना दें",
    "home.chat": "SmartPaw से पूछें",
    "home.chat.desc": "प्राथमिक चिकित्सा चैट",
    "home.learn": "सीखें",
    "home.learn.desc": "कुत्ते की देखभाल गाइड",
    "home.emergency": "आपातकाल? अभी कॉल करें",
    "analyze.title": "कुत्ते की मदद करें",
    "analyze.subtitle": "जांच के लिए फोटो लें या अपलोड करें",
    "analyze.camera": "कैमरा खोलें",
    "analyze.upload": "फोटो अपलोड करें",
    "analyze.analyze": "जांच करें",
    "analyze.analyzing": "जांच हो रही है...",
    "analyze.new": "दूसरी फोटो जांचें",
    "nearby.title": "पास में मदद खोजें",
    "nearby.subtitle": "आस-पास के डॉक्टर और शेल्टर",
    "nearby.finding": "मदद खोज रहे हैं...",
    "nearby.empty": "पास में कोई परिणाम नहीं मिला।",
    "report.title": "सामुदायिक रिपोर्ट",
    "report.subtitle": "आपके पास मदद चाहने वाले कुत्ते",
    "report.form.title": "ज़रूरतमंद कुत्ते की रिपोर्ट करें",
    "report.form.placeholder": "कुत्ते और स्थिति का वर्णन करें...",
    "report.form.urgency": "तात्कालिकता:",
    "report.form.photo": "फोटो लगाएं (वैकल्पिक)",
    "report.form.submit": "रिपोर्ट जमा करें",
    "report.form.submitting": "जमा हो रही है...",
    "report.loading": "रिपोर्ट लोड हो रहीं हैं...",
    "report.empty": "पास में कोई रिपोर्ट नहीं।",
    "report.empty.cta": "पहली रिपोर्ट दर्ज करें!",
    "chat.title": "SmartPaw चैट",
    "chat.subtitle": "कुत्ते की देखभाल के बारे में पूछें",
    "chat.welcome": "नमस्ते, मैं SmartPaw हूं!",
    "chat.welcome.desc": "मैं आवारा कुत्तों की प्राथमिक चिकित्सा, व्यवहार समझने और मुंबई में संसाधन खोजने में मदद कर सकता हूं।",
    "chat.placeholder": "कुत्ते की देखभाल के बारे में पूछें...",
    "chat.disclaimer": "पशु चिकित्सक नहीं। गंभीर मामलों में हमेशा पेशेवर से सलाह लें।",
    "common.back": "←",
    "common.call": "कॉल",
    "common.directions": "दिशानिर्देश",
    "disclaimer": "यह पशु चिकित्सा का विकल्प नहीं है। हमेशा पेशेवर से परामर्श करें।",
  },
  mr: {
    "app.name": "SmartPaw",
    "app.tagline": "मुंबईच्या भटक्या कुत्र्यांना मदत, एका फोटोतून",
    "app.subtitle": "AI-चालित प्रथमोपचार मार्गदर्शन आणि बचाव समन्वय",
    "home.help": "कुत्र्याला मदत करा",
    "home.help.desc": "स्थिती तपासण्यासाठी फोटो काढा",
    "home.nearby": "मदत शोधा",
    "home.nearby.desc": "जवळचे पशुवैद्य",
    "home.report": "कळवा",
    "home.report.desc": "मदत हव्या असलेल्या कुत्र्याची माहिती द्या",
    "home.chat": "SmartPaw ला विचारा",
    "home.chat.desc": "प्रथमोपचार चॅट",
    "home.learn": "शिका",
    "home.learn.desc": "कुत्र्यांची काळजी मार्गदर्शक",
    "home.emergency": "आणीबाणी? आत्ता कॉल करा",
    "analyze.title": "कुत्र्याला मदत करा",
    "analyze.subtitle": "तपासणीसाठी फोटो काढा किंवा अपलोड करा",
    "analyze.camera": "कॅमेरा उघडा",
    "analyze.upload": "फोटो अपलोड करा",
    "analyze.analyze": "तपासा",
    "analyze.analyzing": "तपासणी सुरू...",
    "analyze.new": "दुसरा फोटो तपासा",
    "nearby.title": "जवळ मदत शोधा",
    "nearby.subtitle": "जवळचे डॉक्टर आणि शेल्टर",
    "nearby.finding": "मदत शोधत आहे...",
    "nearby.empty": "जवळ काही आढळले नाही.",
    "report.title": "समुदाय अहवाल",
    "report.subtitle": "तुमच्या जवळ मदत हव्या असलेले कुत्रे",
    "report.form.title": "गरजू कुत्र्याचा अहवाल द्या",
    "report.form.placeholder": "कुत्रा आणि परिस्थितीचे वर्णन करा...",
    "report.form.urgency": "तातडी:",
    "report.form.photo": "फोटो जोडा (पर्यायी)",
    "report.form.submit": "अहवाल सादर करा",
    "report.form.submitting": "सादर होत आहे...",
    "report.loading": "अहवाल लोड होत आहेत...",
    "report.empty": "जवळ अहवाल नाहीत.",
    "report.empty.cta": "पहिला अहवाल नोंदवा!",
    "chat.title": "SmartPaw चॅट",
    "chat.subtitle": "कुत्र्यांच्या काळजीबद्दल विचारा",
    "chat.welcome": "नमस्कार, मी SmartPaw आहे!",
    "chat.welcome.desc": "मी भटक्या कुत्र्यांसाठी प्रथमोपचार, वर्तन समजून घेणे आणि मुंबईत संसाधने शोधण्यात मदत करू शकतो.",
    "chat.placeholder": "कुत्र्यांच्या काळजीबद्दल विचारा...",
    "chat.disclaimer": "पशुवैद्य नाही. गंभीर प्रकरणांसाठी नेहमी व्यावसायिकांचा सल्ला घ्या.",
    "common.back": "←",
    "common.call": "कॉल",
    "common.directions": "दिशानिर्देश",
    "disclaimer": "हे पशुवैद्यकीय काळजीचा पर्याय नाही. नेहमी व्यावसायिकांचा सल्ला घ्या.",
  },
};

const LanguageContext = createContext<LanguageContextType | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLang] = useState<Language>("en");

  useEffect(() => {
    const saved = localStorage.getItem("smartpaw-lang") as Language | null;
    if (saved && (saved === "en" || saved === "hi" || saved === "mr")) {
      setLang(saved);
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLang(lang);
    localStorage.setItem("smartpaw-lang", lang);
  };

  const t = (key: string): string => {
    return translations[language][key] || translations.en[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}

export function LanguageSelector({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage } = useLanguage();
  const options = [
    { code: "en" as Language, label: compact ? "EN" : "English" },
    { code: "hi" as Language, label: compact ? "हि" : "हिन्दी" },
    { code: "mr" as Language, label: compact ? "म" : "मराठी" },
  ];

  return (
    <div className="flex gap-1.5">
      {options.map((o) => (
        <button
          key={o.code}
          onClick={() => setLanguage(o.code)}
          className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
            language === o.code
              ? "bg-[var(--color-warm-500)] text-white"
              : "bg-gray-100 text-gray-500 hover:bg-gray-200"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
