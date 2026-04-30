"use client";

import Link from "next/link";
import { LanguageSelector, useLanguage } from "@/lib/language";

type PageLanguage = "en" | "hi" | "mr";

const COPY = {
  en: {
    title: "Cruelty Help",
    subtitle: "For dogs, cats, cows, and other stray or community animals",
    safetyTitle: "Do not confront if it can escalate",
    safetyBody:
      "Keep yourself safe, keep distance, and collect details only from a safe place. If a person is in danger or violence is active, call 112 first.",
    recognizeTitle: "Recognize",
    recognize: [
      "beating, kicking, poisoning, burning, throwing stones, or deliberate injury",
      "abandonment, animals tied without food/water, overcrowding, or denial of basic care",
      "illegal relocation or harassment of community animals and caregivers",
    ],
    documentTitle: "Document safely",
    document: [
      "note exact location, date, time, species, number of animals, and what happened",
      "take photos/video from a safe distance; include landmarks when possible",
      "save witness names, vehicle numbers, shop/building names, and prior complaint numbers",
    ],
    reportTitle: "Where to report",
    report: [
      "Use the AWBI cruelty complaint portal for a written record.",
      "For urgent danger to people, traffic, fire, or violence, call 112.",
      "Use Find Help for local rescue/vet contacts if the animal is injured right now.",
    ],
    dontTitle: "Do not",
    dont: [
      "do not threaten, trespass, or seize an animal yourself",
      "do not post personal details publicly before filing a safe complaint",
      "do not move an injured animal unless staying there is more dangerous",
    ],
    sourcesTitle: "Sources",
  },
  hi: {
    title: "क्रूरता में मदद",
    subtitle: "कुत्ते, बिल्ली, गाय और अन्य आवारा/सामुदायिक जानवरों के लिए",
    safetyTitle: "स्थिति बिगड़ सकती हो तो सामने से न भिड़ें",
    safetyBody:
      "अपनी सुरक्षा रखें, दूरी बनाए रखें और सुरक्षित जगह से ही जानकारी जुटाएं। अगर किसी व्यक्ति को खतरा है या हिंसा चल रही है, पहले 112 पर कॉल करें।",
    recognizeTitle: "पहचानें",
    recognize: [
      "मारना, लात मारना, ज़हर देना, जलाना, पत्थर मारना या जानबूझकर चोट पहुंचाना",
      "छोड़ देना, बिना खाना/पानी बांधकर रखना, भीड़ में रखना या बुनियादी देखभाल न देना",
      "सामुदायिक जानवरों या देखभाल करने वालों को अवैध रूप से हटाना या परेशान करना",
    ],
    documentTitle: "सुरक्षित तरीके से दस्तावेज़ बनाएं",
    document: [
      "सटीक स्थान, तारीख, समय, प्रजाति, जानवरों की संख्या और घटना लिखें",
      "सुरक्षित दूरी से फोटो/वीडियो लें; संभव हो तो आसपास की पहचान दिखे",
      "गवाह, वाहन नंबर, दुकान/बिल्डिंग नाम और पुराने complaint नंबर सेव करें",
    ],
    reportTitle: "कहां रिपोर्ट करें",
    report: [
      "लिखित रिकॉर्ड के लिए AWBI cruelty complaint portal का उपयोग करें।",
      "लोगों, ट्रैफिक, आग या हिंसा का तुरंत खतरा हो तो 112 पर कॉल करें।",
      "जानवर अभी घायल है तो स्थानीय rescue/vet संपर्कों के लिए Find Help खोलें।",
    ],
    dontTitle: "यह न करें",
    dont: [
      "धमकी न दें, गैरकानूनी तरीके से अंदर न जाएं, और खुद जानवर जब्त न करें",
      "सुरक्षित शिकायत से पहले किसी की निजी जानकारी सार्वजनिक न करें",
      "जब तक वहीं रहना ज्यादा खतरनाक न हो, घायल जानवर को न हिलाएं",
    ],
    sourcesTitle: "स्रोत",
  },
  mr: {
    title: "क्रूरतेसाठी मदत",
    subtitle: "कुत्रे, मांजरी, गायी आणि इतर भटके/समुदायातील प्राणी",
    safetyTitle: "स्थिती बिघडू शकत असेल तर सामना करू नका",
    safetyBody:
      "स्वतःची सुरक्षितता ठेवा, अंतर ठेवा आणि सुरक्षित जागेतूनच तपशील घ्या. व्यक्ती धोक्यात असेल किंवा हिंसा सुरू असेल तर आधी 112 वर कॉल करा.",
    recognizeTitle: "ओळखा",
    recognize: [
      "मारणे, लाथ मारणे, विष देणे, जाळणे, दगड मारणे किंवा जाणूनबुजून इजा करणे",
      "सोडून देणे, अन्न/पाणी न देता बांधून ठेवणे, गर्दीत ठेवणे किंवा मूलभूत काळजी न देणे",
      "समुदायातील प्राणी किंवा काळजीवाहूंना बेकायदेशीरपणे हटवणे किंवा त्रास देणे",
    ],
    documentTitle: "सुरक्षितपणे नोंद ठेवा",
    document: [
      "अचूक ठिकाण, तारीख, वेळ, प्रजाती, प्राण्यांची संख्या आणि काय झाले ते लिहा",
      "सुरक्षित अंतरावरून फोटो/व्हिडिओ घ्या; शक्य असल्यास ओळख पटणारी खूण दिसू द्या",
      "साक्षीदार, वाहन क्रमांक, दुकान/इमारत नावे आणि आधीचे complaint नंबर सेव्ह करा",
    ],
    reportTitle: "कुठे नोंद करावी",
    report: [
      "लिखित नोंदीसाठी AWBI cruelty complaint portal वापरा.",
      "लोक, वाहतूक, आग किंवा हिंसेचा तातडीचा धोका असेल तर 112 वर कॉल करा.",
      "प्राणी सध्या जखमी असेल तर स्थानिक rescue/vet संपर्कांसाठी Find Help उघडा.",
    ],
    dontTitle: "हे करू नका",
    dont: [
      "धमकी देऊ नका, बेकायदेशीर प्रवेश करू नका किंवा प्राणी स्वतः जप्त करू नका",
      "सुरक्षित तक्रार करण्यापूर्वी कोणाची वैयक्तिक माहिती सार्वजनिक करू नका",
      "तिथे राहणे अधिक धोकादायक नसेल तर जखमी प्राणी हलवू नका",
    ],
    sourcesTitle: "स्रोत",
  },
} as const;

const SOURCES = [
  {
    label: "AWBI cruelty complaint portal",
    href: "https://awbi.gov.in/cruelty-complaint",
  },
  {
    label: "AWBI law-enforcement handbook",
    href: "https://awbi.gov.in/uploads/regulations/167712687486Law%20Enforcement%20on%20animal%20welfare%20%28IO%20handbook%29_comp.pdf",
  },
  {
    label: "India emergency response 112",
    href: "https://www.112.gov.in/about",
  },
];

function ListSection({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <section className="bg-white border border-gray-100 rounded-xl p-4">
      <h2 className="font-semibold text-gray-800 mb-3">{title}</h2>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex gap-2 text-sm text-gray-600 leading-relaxed">
            <span className="text-[var(--color-warm-500)]">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function CrueltyPage() {
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
        <LanguageSelector compact />
      </div>

      <section className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
        <h2 className="font-semibold text-red-700 mb-2">{copy.safetyTitle}</h2>
        <p className="text-sm text-red-700 leading-relaxed">{copy.safetyBody}</p>
      </section>

      <div className="space-y-4">
        <ListSection title={copy.recognizeTitle} items={copy.recognize} />
        <ListSection title={copy.documentTitle} items={copy.document} />
        <ListSection title={copy.reportTitle} items={copy.report} />
        <ListSection title={copy.dontTitle} items={copy.dont} />

        <section className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <h2 className="font-semibold text-slate-800 mb-3">{copy.sourcesTitle}</h2>
          <div className="space-y-2">
            {SOURCES.map((source) => (
              <a
                key={source.href}
                href={source.href}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-blue-700 underline"
              >
                {source.label}
              </a>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
