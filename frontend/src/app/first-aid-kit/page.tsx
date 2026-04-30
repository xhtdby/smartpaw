"use client";

import Link from "next/link";
import { Quiz } from "@/components/Quiz";
import { LanguageSelector, useLanguage } from "@/lib/language";

type PageLanguage = "en" | "hi" | "mr";

type Topic = {
  id: string;
  title: Record<PageLanguage, string>;
  immediate: Record<PageLanguage, string>;
  otc: Record<PageLanguage, string>;
  redFlags: Record<PageLanguage, string>;
  remember: Record<PageLanguage, string>;
};

const COPY = {
  en: {
    title: "First-aid Kit",
    subtitle: "Action-first basics for the animal in front of you",
    immediate: "Immediate steps",
    otc: "Useful kit items",
    redFlags: "Stop and get help if",
    remember: "Remember",
    sourcesTitle: "Clinical sources",
  },
  hi: {
    title: "प्राथमिक चिकित्सा किट",
    subtitle: "आपके सामने मौजूद जानवर के लिए तुरंत काम आने वाली बातें",
    immediate: "तुरंत कदम",
    otc: "किट में उपयोगी चीजें",
    redFlags: "रुकें और मदद लें अगर",
    remember: "याद रखें",
    sourcesTitle: "चिकित्सकीय स्रोत",
  },
  mr: {
    title: "प्रथमोपचार किट",
    subtitle: "समोरच्या प्राण्यासाठी तत्काळ उपयोगी पावले",
    immediate: "तत्काळ पावले",
    otc: "किटमधील उपयोगी वस्तू",
    redFlags: "थांबा आणि मदत घ्या जर",
    remember: "लक्षात ठेवा",
    sourcesTitle: "वैद्यकीय स्रोत",
  },
} as const;

const TOPICS: Topic[] = [
  {
    id: "bleeding",
    title: { en: "Bleeding", hi: "खून बहना", mr: "रक्तस्त्राव" },
    immediate: {
      en: "Press a clean cloth or gauze firmly on the wound and keep pressure during transport.",
      hi: "साफ कपड़ा या gauze घाव पर मजबूती से दबाएं और ले जाते समय दबाव बनाए रखें।",
      mr: "स्वच्छ कापड किंवा gauze जखमेवर घट्ट दाबा आणि नेताना दाब कायम ठेवा.",
    },
    otc: {
      en: "Clean cloth, gauze, elastic bandage, saline for gentle rinsing after bleeding is controlled.",
      hi: "साफ कपड़ा, gauze, elastic bandage, और खून रुकने के बाद हल्की सफाई के लिए saline.",
      mr: "स्वच्छ कापड, gauze, elastic bandage, आणि रक्त थांबल्यावर हलक्या धुण्यासाठी saline.",
    },
    redFlags: {
      en: "bleeding is heavy, spurting, does not slow in 10-15 minutes, or the animal is weak/collapsed.",
      hi: "खून बहुत ज्यादा हो, फव्वारे जैसा निकले, 10-15 मिनट में कम न हो, या जानवर कमजोर/गिरा हुआ हो।",
      mr: "रक्त खूप असेल, उडत असेल, 10-15 मिनिटांत कमी होत नसेल, किंवा प्राणी अशक्त/कोसळलेला असेल.",
    },
    remember: {
      en: "Pressure first; do not peel away soaked cloth.",
      hi: "पहले दबाव; भीगा कपड़ा हटाकर clot न तोड़ें।",
      mr: "आधी दाब; भिजलेले कापड काढून clot तोडू नका.",
    },
  },
  {
    id: "choking",
    title: { en: "Choking", hi: "दम घुटना", mr: "घसा अडकणे" },
    immediate: {
      en: "If air is moving, keep calm and let the animal cough; remove only a visible front-mouth object.",
      hi: "अगर हवा जा रही है तो शांत रखें और खांसने दें; केवल सामने दिखती चीज सावधानी से निकालें।",
      mr: "हवा जात असेल तर शांत ठेवा आणि खोकू द्या; फक्त समोर दिसणारी वस्तू सावधपणे काढा.",
    },
    otc: {
      en: "No medicine. Keep a towel ready for safe handling and transport.",
      hi: "कोई दवा नहीं। सुरक्षित पकड़ और transport के लिए towel रखें।",
      mr: "औषध नाही. सुरक्षित हाताळणी आणि transport साठी towel ठेवा.",
    },
    redFlags: {
      en: "blue gums, silent choking, collapse, or breathing stops.",
      hi: "मसूड़े नीले हों, आवाज न निकले, collapse हो, या सांस रुक जाए।",
      mr: "हिरड्या निळ्या दिसतील, आवाज नसेल, collapse होईल किंवा श्वास थांबेल.",
    },
    remember: {
      en: "Do not push fingers deep into the throat.",
      hi: "उंगलियां गले में अंदर तक न डालें।",
      mr: "बोटे घशात खोलवर घालू नका.",
    },
  },
  {
    id: "heatstroke",
    title: { en: "Heatstroke", hi: "हीटस्ट्रोक", mr: "उष्माघात" },
    immediate: {
      en: "Move to shade, cool belly/groin/paws/neck with room-temperature water, and arrange urgent care.",
      hi: "छांव में ले जाएं, पेट/groin/paws/neck को सामान्य पानी से ठंडा करें और तुरंत care arrange करें।",
      mr: "सावलीत न्या, पोट/groin/paws/neck साध्या पाण्याने थंड करा आणि तातडीची care arrange करा.",
    },
    otc: {
      en: "Water, cloth, fan/airflow. Give tiny sips only if alert and swallowing.",
      hi: "पानी, कपड़ा, fan/airflow. होश में हो और निगल सके तभी छोटे घूंट दें।",
      mr: "पाणी, कापड, fan/airflow. शुद्धीत आणि गिळू शकत असेल तरच छोटे घोट द्या.",
    },
    redFlags: {
      en: "collapse, confusion, repeated vomiting, seizures, or very hot body.",
      hi: "गिरना, confused लगना, बार-बार उल्टी, दौरे, या शरीर बहुत गर्म होना।",
      mr: "कोसळणे, गोंधळलेले दिसणे, वारंवार उलटी, झटके किंवा शरीर खूप गरम असणे.",
    },
    remember: {
      en: "Cool first, but avoid ice-cold shock.",
      hi: "पहले ठंडा करें, लेकिन बर्फ जैसा झटका न दें।",
      mr: "आधी थंड करा, पण बर्फासारखा धक्का देऊ नका.",
    },
  },
  {
    id: "poisoning",
    title: { en: "Poisoning", hi: "ज़हर", mr: "विषबाधा" },
    immediate: {
      en: "Move the animal away from the substance, keep the packet/container, and call vet/poison help.",
      hi: "जानवर को substance से दूर करें, packet/container रखें और vet/poison help को कॉल करें।",
      mr: "प्राण्याला substance पासून दूर करा, packet/container ठेवा आणि vet/poison help ला कॉल करा.",
    },
    otc: {
      en: "No home antidote. Keep water available only if alert; do not force.",
      hi: "घर पर antidote नहीं। होश में हो तो पानी पास रखें; जबरदस्ती न दें।",
      mr: "घरचा antidote नाही. शुद्धीत असेल तर पाणी उपलब्ध ठेवा; जबरदस्ती नको.",
    },
    redFlags: {
      en: "seizure, tremors, collapse, repeated vomiting, breathing trouble, or known toxin.",
      hi: "दौरे, tremors, गिरना, बार-बार उल्टी, सांस की दिक्कत, या known toxin।",
      mr: "झटके, थरथर, कोसळणे, वारंवार उलटी, श्वासाचा त्रास किंवा known toxin.",
    },
    remember: {
      en: "Do not induce vomiting unless a vet/poison expert tells you.",
      hi: "Vet/poison expert न कहे तो उल्टी करवाने की कोशिश न करें।",
      mr: "Vet/poison expert सांगत नाही तोवर उलटी करवू नका.",
    },
  },
  {
    id: "road-trauma",
    title: { en: "Road trauma", hi: "सड़क दुर्घटना", mr: "रस्ता अपघात" },
    immediate: {
      en: "Keep still, move from traffic only if safe, and transport on a board/blanket without twisting.",
      hi: "स्थिर रखें, सुरक्षित हो तो traffic से हटाएं, और board/blanket पर बिना twisting transport करें।",
      mr: "स्थिर ठेवा, सुरक्षित असेल तर traffic मधून हलवा, आणि board/blanket वर twisting न करता transport करा.",
    },
    otc: {
      en: "Blanket, cardboard/board, clean cloth. No painkillers without a vet.",
      hi: "कंबल, cardboard/board, साफ कपड़ा। Vet के बिना painkiller नहीं।",
      mr: "चादर, cardboard/board, स्वच्छ कापड. Vet शिवाय painkiller नाही.",
    },
    redFlags: {
      en: "cannot stand, dragging limbs, heavy bleeding, labored breathing, or unconsciousness.",
      hi: "खड़ा न हो पाना, पैर घसीटना, ज्यादा खून, सांस में मेहनत, या बेहोशी।",
      mr: "उभे राहू न शकणे, पाय ओढणे, जास्त रक्त, श्वासात त्रास किंवा बेशुद्धी.",
    },
    remember: {
      en: "Assume fracture or internal injury even when wounds are not obvious.",
      hi: "बाहरी घाव न दिखे तब भी fracture/internal injury मानकर चलें।",
      mr: "बाहेर जखम न दिसली तरी fracture/internal injury गृहित धरा.",
    },
  },
  {
    id: "skin-ticks",
    title: { en: "Skin and ticks", hi: "त्वचा और ticks", mr: "त्वचा आणि ticks" },
    immediate: {
      en: "Keep flies away, prevent licking, remove ticks straight out with tweezers if safe.",
      hi: "मक्खियां दूर रखें, licking रोकें, और सुरक्षित हो तो tweezers से tick सीधा निकालें।",
      mr: "माशा दूर ठेवा, licking थांबवा, आणि सुरक्षित असल्यास tweezers ने tick सरळ काढा.",
    },
    otc: {
      en: "Tweezers, saline, clean gauze. Use species-labeled flea/tick products only as directed.",
      hi: "Tweezers, saline, साफ gauze. Species-labeled flea/tick product केवल निर्देशानुसार।",
      mr: "Tweezers, saline, स्वच्छ gauze. Species-labeled flea/tick product फक्त निर्देशानुसार.",
    },
    redFlags: {
      en: "pale gums, fever, weakness, foul smell, maggots, bleeding skin, or deep wounds.",
      hi: "मसूड़े pale, fever, weakness, बदबू, maggots, skin bleeding, या deep wounds।",
      mr: "फिकट हिरड्या, fever, weakness, दुर्गंधी, maggots, skin bleeding किंवा deep wounds.",
    },
    remember: {
      en: "Never use kerosene, engine oil, acid, chili, or harsh chemicals.",
      hi: "Kerosene, engine oil, acid, chili या harsh chemicals कभी न लगाएं।",
      mr: "Kerosene, engine oil, acid, chili किंवा harsh chemicals कधीही लावू नका.",
    },
  },
  {
    id: "puppies",
    title: { en: "Puppies", hi: "पिल्ले", mr: "पिल्ले" },
    immediate: {
      en: "Keep warm, dry, quiet, and with the mother if she is safe and present.",
      hi: "गर्म, सूखा, शांत रखें और मां सुरक्षित मौजूद हो तो उसके साथ रखें।",
      mr: "उबदार, कोरडे, शांत ठेवा आणि आई सुरक्षित असेल तर तिच्यासोबत ठेवा.",
    },
    otc: {
      en: "Clean bedding, warmth, shallow water for alert older pups. No random diarrhea medicines.",
      hi: "साफ bedding, warmth, alert बड़े pups के लिए shallow water. Random diarrhea medicines नहीं।",
      mr: "स्वच्छ bedding, warmth, alert मोठ्या pups साठी shallow water. Random diarrhea medicines नाहीत.",
    },
    redFlags: {
      en: "bloody diarrhea, repeated vomiting, chilling, weakness, crying nonstop, or refusal to drink.",
      hi: "खूनी दस्त, बार-बार उल्टी, ठंड लगना, कमजोरी, लगातार रोना, या पानी न पीना।",
      mr: "रक्ताळ जुलाब, वारंवार उलटी, थंडी, कमजोरी, सतत रडणे किंवा पाणी न पिणे.",
    },
    remember: {
      en: "Puppies crash fast; escalate early.",
      hi: "पिल्ले जल्दी बिगड़ते हैं; जल्दी मदद लें।",
      mr: "पिल्ले पटकन खालावतात; लवकर मदत घ्या.",
    },
  },
  {
    id: "deceased-aftercare",
    title: { en: "After death", hi: "मृत्यु के बाद", mr: "मृत्यूनंतर" },
    immediate: {
      en: "If you are certain the animal has died, move the body only if safe and use gloves/cloth.",
      hi: "मृत्यु की पूरी पुष्टि हो तो body सुरक्षित हो तभी हटाएं और gloves/cloth use करें।",
      mr: "मृत्यूची खात्री असेल तर body सुरक्षित असल्यासच हलवा आणि gloves/cloth वापरा.",
    },
    otc: {
      en: "Gloves, sheet, mask, disinfectant for surfaces after handling. No medical treatment is needed.",
      hi: "Gloves, sheet, mask, handling के बाद surface disinfectant. Medical treatment की जरूरत नहीं।",
      mr: "Gloves, sheet, mask, handling नंतर surface disinfectant. Medical treatment लागत नाही.",
    },
    redFlags: {
      en: "you are unsure if the animal is alive, there was a bite exposure, or death may be evidence of cruelty.",
      hi: "जीवित होने पर संदेह हो, bite exposure हो, या death cruelty evidence हो सकती हो।",
      mr: "प्राणी जिवंत आहे का शंका असेल, bite exposure असेल किंवा death cruelty evidence असू शकते.",
    },
    remember: {
      en: "No emergency checklist if death is certain; protect dignity and hygiene.",
      hi: "मृत्यु निश्चित हो तो emergency checklist नहीं; dignity और hygiene रखें।",
      mr: "मृत्यू निश्चित असेल तर emergency checklist नाही; dignity आणि hygiene ठेवा.",
    },
  },
  {
    id: "wound-cleaning",
    title: { en: "Wound cleaning", hi: "घाव साफ करना", mr: "जखम साफ करणे" },
    immediate: {
      en: "After bleeding is controlled, gently rinse dirt with clean water or saline; cover loosely.",
      hi: "खून रुकने के बाद साफ पानी या saline से dirt हल्के से धोएं; ढीला cover करें।",
      mr: "रक्त थांबल्यावर स्वच्छ पाणी किंवा saline ने dirt हलके धुवा; सैल cover करा.",
    },
    otc: {
      en: "Saline; dilute povidone-iodine/chlorhexidine only for minor surface cleaning when vet-suitable.",
      hi: "Saline; minor surface cleaning के लिए dilute povidone-iodine/chlorhexidine जब vet-suitable हो।",
      mr: "Saline; minor surface cleaning साठी dilute povidone-iodine/chlorhexidine जेव्हा vet-suitable असेल.",
    },
    redFlags: {
      en: "deep bite, puncture, exposed tissue, maggots, eye wound, severe pain, or spreading swelling.",
      hi: "deep bite, puncture, exposed tissue, maggots, eye wound, severe pain, या swelling फैलना।",
      mr: "deep bite, puncture, exposed tissue, maggots, eye wound, severe pain किंवा swelling वाढणे.",
    },
    remember: {
      en: "Do not use alcohol, peroxide, tea tree oil, or random ointments.",
      hi: "Alcohol, peroxide, tea tree oil या random ointments न लगाएं।",
      mr: "Alcohol, peroxide, tea tree oil किंवा random ointments लावू नका.",
    },
  },
  {
    id: "fracture",
    title: { en: "Fracture support", hi: "Fracture support", mr: "Fracture support" },
    immediate: {
      en: "Do not straighten the limb. Support the whole body and limit movement.",
      hi: "पैर/हड्डी सीधी करने की कोशिश न करें। पूरे शरीर को support दें और movement कम रखें।",
      mr: "पाय/हाड सरळ करण्याचा प्रयत्न करू नका. संपूर्ण शरीराला support द्या आणि movement कमी ठेवा.",
    },
    otc: {
      en: "Board, blanket, towel padding. Avoid tight splints unless trained.",
      hi: "Board, blanket, towel padding. Training न हो तो tight splint न लगाएं।",
      mr: "Board, blanket, towel padding. Training नसेल तर tight splint लावू नका.",
    },
    redFlags: {
      en: "open bone, limb dragging, severe pain, road trauma, or inability to stand.",
      hi: "हड्डी बाहर दिखे, limb dragging, severe pain, road trauma, या खड़ा न होना।",
      mr: "हाड बाहेर दिसणे, limb dragging, severe pain, road trauma किंवा उभे राहू न शकणे.",
    },
    remember: {
      en: "Stillness helps more than a bad splint.",
      hi: "गलत splint से बेहतर है movement कम रखना।",
      mr: "चुकीच्या splint पेक्षा movement कमी ठेवणे चांगले.",
    },
  },
  {
    id: "dehydration",
    title: { en: "Dehydration / ORS", hi: "Dehydration / ORS", mr: "Dehydration / ORS" },
    immediate: {
      en: "Offer tiny frequent sips only if alert and not vomiting repeatedly.",
      hi: "होश में हो और बार-बार उल्टी न हो तभी छोटे-छोटे घूंट बार-बार दें।",
      mr: "शुद्धीत आणि वारंवार उलटी नसेल तरच छोटे घोट वारंवार द्या.",
    },
    otc: {
      en: "Clean water; plain ORS-style fluid may help mild fluid loss, but do not force fluids.",
      hi: "साफ पानी; mild fluid loss में plain ORS-style fluid मदद कर सकता है, पर जबरदस्ती न दें।",
      mr: "स्वच्छ पाणी; mild fluid loss मध्ये plain ORS-style fluid मदत करू शकतो, पण जबरदस्ती नको.",
    },
    redFlags: {
      en: "puppy, blood, repeated vomiting, collapse, sunken eyes, very weak, or cannot swallow.",
      hi: "पिल्ला, खून, बार-बार उल्टी, collapse, धंसी आंखें, बहुत कमजोरी, या निगल न पाना।",
      mr: "पिल्लू, रक्त, वारंवार उलटी, collapse, खोल गेलेले डोळे, खूप weakness किंवा गिळू न शकणे.",
    },
    remember: {
      en: "Fluids help only when the animal can swallow safely.",
      hi: "Fluid तभी मदद करता है जब जानवर सुरक्षित निगल सके।",
      mr: "Fluid तेव्हाच मदत करते जेव्हा प्राणी सुरक्षित गिळू शकतो.",
    },
  },
  {
    id: "otc-medicine",
    title: { en: "OTC medicine basics", hi: "OTC दवा की मूल बातें", mr: "OTC औषधांची मूलभूत माहिती" },
    immediate: {
      en: "Use simple first-aid items; do not give human painkillers, antibiotics, steroids, or leftovers.",
      hi: "साधारण first-aid items use करें; human painkillers, antibiotics, steroids या leftovers न दें।",
      mr: "साधे first-aid items वापरा; human painkillers, antibiotics, steroids किंवा leftovers देऊ नका.",
    },
    otc: {
      en: "Reasonable basics: saline, gauze, clean cloth, dilute antiseptic for minor surface wounds, ORS-style fluid only when swallowing.",
      hi: "Reasonable basics: saline, gauze, clean cloth, minor surface wounds के लिए dilute antiseptic, और swallowing हो तभी ORS-style fluid.",
      mr: "Reasonable basics: saline, gauze, clean cloth, minor surface wounds साठी dilute antiseptic, आणि swallowing असेल तरच ORS-style fluid.",
    },
    redFlags: {
      en: "paracetamol/acetaminophen, ibuprofen, unknown pills, chocolate, grapes/raisins, xylitol, pesticide, or rat poison exposure.",
      hi: "paracetamol/acetaminophen, ibuprofen, unknown pills, chocolate, grapes/raisins, xylitol, pesticide या rat poison exposure।",
      mr: "paracetamol/acetaminophen, ibuprofen, unknown pills, chocolate, grapes/raisins, xylitol, pesticide किंवा rat poison exposure.",
    },
    remember: {
      en: "If it treats pain or fever in people, assume vet-only for animals.",
      hi: "जो दवा इंसानों में दर्द/बुखार के लिए है, उसे animals के लिए vet-only मानें।",
      mr: "माणसांच्या pain/fever ची औषधे animals साठी vet-only माना.",
    },
  },
];

const SOURCES = [
  {
    label: "VCA: Care of open wounds in dogs",
    href: "https://vcahospitals.com/know-your-pet/care-of-open-wounds-in-dogs",
  },
  {
    label: "VCA: Povidone iodine topical",
    href: "https://vcahospitals.com/know-your-pet/povidone-iodine-topical",
  },
  {
    label: "Merck Veterinary Manual: Wound management",
    href: "https://www.merckvetmanual.com/special-pet-topics/emergencies/wound-management",
  },
  {
    label: "ASPCA Poison Control",
    href: "https://www.aspca.org/pet-care/aspca-poison-control",
  },
];

export default function FirstAidKitPage() {
  const { language } = useLanguage();
  const pageLanguage = (language as PageLanguage) || "en";
  const copy = COPY[pageLanguage];

  return (
    <main className="min-h-screen px-4 py-6 max-w-2xl mx-auto">
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

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TOPICS.map((topic) => (
          <article key={topic.id} id={topic.id} className="bg-white border border-gray-100 rounded-xl p-4 scroll-mt-20">
            <h2 className="font-semibold text-gray-900 mb-3">{topic.title[pageLanguage]}</h2>
            <div className="space-y-3 text-sm">
              <div>
                <h3 className="font-medium text-[var(--color-warm-700)]">{copy.immediate}</h3>
                <p className="text-gray-600 leading-relaxed">{topic.immediate[pageLanguage]}</p>
              </div>
              <div>
                <h3 className="font-medium text-[var(--color-sage-700)]">{copy.otc}</h3>
                <p className="text-gray-600 leading-relaxed">{topic.otc[pageLanguage]}</p>
              </div>
              <div>
                <h3 className="font-medium text-red-700">{copy.redFlags}</h3>
                <p className="text-gray-600 leading-relaxed">{topic.redFlags[pageLanguage]}</p>
              </div>
              <div className="rounded-lg bg-[var(--color-warm-50)] px-3 py-2 text-[var(--color-warm-800)]">
                <span className="font-medium">{copy.remember}: </span>
                {topic.remember[pageLanguage]}
              </div>
            </div>
            <Quiz topicId={topic.id} language={pageLanguage} />
          </article>
        ))}
      </section>

      <section className="bg-slate-50 border border-slate-200 rounded-xl p-4 mt-6">
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
    </main>
  );
}
