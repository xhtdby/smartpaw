"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Quiz } from "@/components/Quiz";
import { SpeciesScopeSelect } from "@/components/SpeciesScopeSelect";
import { useLanguage, LanguageSelector } from "@/lib/language";
import {
  SPECIES_FILTER_OPTIONS,
  getFirstAidHref,
  getNearbyHref,
  getSpeciesLabel,
  getSpeciesSearchQuery,
  normalizeSpeciesFilter,
  type SpeciesFilter,
} from "@/lib/species";

type PageLanguage = "en" | "hi" | "mr";

type Guide = {
  id: string;
  species: SpeciesFilter[];
  icon: string;
  title: Record<PageLanguage, string>;
  summary: Record<PageLanguage, string>;
  bullets: Record<PageLanguage, string[]>;
};

type ResourceLink = {
  href: string;
  label: string;
  note: Record<PageLanguage, string>;
};

const COPY = {
  en: {
    title: "Learn",
    subtitle: "High-confidence first aid basics for pets and community animals",
    truthTitle: "How to use this page",
    truthBody:
      "IndieAid is AI guidance, not a veterinary diagnosis. This page sticks to safer, high-confidence first-aid basics. It avoids made-up dosing and tells you when to escalate.",
    quickTitle: "Quick Actions",
    quickFindHelp: "Open Find Help",
    quickFirstAid: "First-aid Kit",
    quickVet: "Emergency Vet Search",
    quickRabies: "WHO Rabies Guidance",
    redFlagsTitle: "Get urgent professional help if you see",
    redFlags: [
      "trouble breathing, collapse, repeated seizures, or the animal cannot stand",
      "heavy bleeding, obvious fracture, severe road trauma, or deep bite wounds",
      "suspected poisoning, heatstroke, bloated belly with retching, or severe eye injury",
      "maggot wounds, rapidly worsening skin disease, or a weak young animal with bloody diarrhoea",
    ],
    uncertaintyTitle: "When the problem is not clear",
    uncertaintyBody:
      "Do not guess a single diagnosis too early. Compare the main possibilities, check breathing, ability to stand, bleeding, body temperature, vomiting, swelling, and pain level, then choose the safest action that fits all likely causes.",
    resourcesTitle: "Verified Resources",
    emergencyTitle: "Human safety first",
    emergencyBody:
      "If a person is in danger or may have rabies exposure, use local emergency care immediately. In India, call 112.",
  },
  hi: {
    title: "सीखें",
    subtitle: "पालतू और सामुदायिक जानवरों के लिए उच्च-विश्वास प्राथमिक उपचार के मूल कदम",
    truthTitle: "इस पेज का उपयोग कैसे करें",
    truthBody:
      "IndieAid AI-आधारित मार्गदर्शन है, पशु-चिकित्सीय निदान नहीं। यह पेज सुरक्षित और अधिक भरोसेमंद प्राथमिक-उपचार कदमों पर केंद्रित है। यह मनगढ़ंत दवा-डोज़ से बचता है और स्पष्ट बताता है कि कब पेशेवर मदद लेनी चाहिए।",
    quickTitle: "त्वरित कार्रवाइयाँ",
    quickFindHelp: "Find Help खोलें",
    quickFirstAid: "प्राथमिक चिकित्सा किट",
    quickVet: "इमरजेंसी वेट खोजें",
    quickRabies: "WHO रेबीज़ मार्गदर्शन",
    redFlagsTitle: "इन स्थितियों में तुरंत पेशेवर मदद लें",
    redFlags: [
      "साँस लेने में दिक्कत, गिर जाना, बार-बार दौरे, या जानवर खड़ा न हो पा रहा हो",
      "बहुत खून बहना, हड्डी टूटना दिखना, गंभीर सड़क दुर्घटना, या गहरे काटने के घाव",
      "ज़हर की आशंका, हीटस्ट्रोक, पेट फूलना और उल्टी जैसा प्रयास, या गंभीर आँख की चोट",
      "कीड़ों वाले घाव, तेजी से बिगड़ती त्वचा की बीमारी, या खून वाले दस्त के साथ कमजोर पिल्ला",
    ],
    uncertaintyTitle: "जब समस्या स्पष्ट न हो",
    uncertaintyBody:
      "बहुत जल्दी एक ही निदान मानकर न चलें। मुख्य संभावनाओं की तुलना करें, जानवर की साँस, खड़े होने की क्षमता, खून, शरीर का तापमान, उल्टी, सूजन और दर्द का स्तर देखें, फिर वह कदम चुनें जो सभी संभावित कारणों में सुरक्षित हो।",
    resourcesTitle: "सत्यापित संसाधन",
    emergencyTitle: "पहले मानव सुरक्षा",
    emergencyBody:
      "अगर कोई व्यक्ति खतरे में है या रेबीज़ एक्सपोज़र की आशंका है, तो तुरंत स्थानीय आपातकालीन सहायता लें। भारत में 112 पर कॉल करें।",
  },
  mr: {
    title: "शिका",
    subtitle: "पालीव आणि समुदायातील प्राण्यांसाठी उच्च-विश्वास प्रथमोपचाराची मूलभूत माहिती",
    truthTitle: "हे पान कसे वापरावे",
    truthBody:
      "IndieAid हे AI-आधारित मार्गदर्शन आहे, पशुवैद्यकीय निदान नाही. हे पान अधिक सुरक्षित आणि विश्वासार्ह प्रथमोपचाराच्या मूलभूत गोष्टींवरच लक्ष केंद्रित करते. हे बनावट डोस देत नाही आणि कधी व्यावसायिक मदत घ्यावी हे स्पष्ट सांगते.",
    quickTitle: "झटपट कृती",
    quickFindHelp: "Find Help उघडा",
    quickFirstAid: "प्रथमोपचार किट",
    quickVet: "आपत्कालीन वेट शोधा",
    quickRabies: "WHO रेबीज मार्गदर्शन",
    redFlagsTitle: "या परिस्थितीत त्वरित व्यावसायिक मदत घ्या",
    redFlags: [
      "श्वास घेण्यास त्रास, कोसळणे, वारंवार झटके, किंवा प्राणी उभा राहू शकत नसणे",
      "जोरदार रक्तस्त्राव, स्पष्ट फ्रॅक्चर, गंभीर रस्ते अपघात, किंवा खोल चाव्याच्या जखमा",
      "विषबाधेची शक्यता, उष्माघात, फुगलेले पोट आणि ओकारीचे प्रयत्न, किंवा गंभीर डोळ्याची दुखापत",
      "अळ्यांचे घाव, झपाट्याने बिघडणारा त्वचारोग, किंवा रक्ताळ जुलाब असलेले अशक्त पिल्लू",
    ],
    uncertaintyTitle: "समस्या स्पष्ट नसल्यास",
    uncertaintyBody:
      "खूप लवकर एकच निदान ठरवू नका. मुख्य शक्यता तुलना करा, प्राण्याचा श्वास, उभे राहण्याची क्षमता, रक्तस्त्राव, शरीराचे तापमान, उलटी, सूज आणि वेदना तपासा, आणि मग सर्व शक्य कारणांमध्ये सुरक्षित ठरणारी कृती निवडा.",
    resourcesTitle: "पडताळलेली संसाधने",
    emergencyTitle: "आधी मानवी सुरक्षितता",
    emergencyBody:
      "एखादी व्यक्ती धोक्यात असेल किंवा रेबीज एक्स्पोजरची शक्यता असेल, तर त्वरित स्थानिक आपत्कालीन मदत घ्या. भारतात 112 वर कॉल करा.",
  },
} as const;

const SPECIES_ALERTS: Record<
  SpeciesFilter,
  Record<PageLanguage, { title: string; body: string }>
> = {
  all: {
    en: {
      title: "Universal scope",
      body: "These guides show low-risk stabilization steps first. Pick an animal below for species-specific emergency cues.",
    },
    hi: {
      title: "Universal scope",
      body: "These guides show low-risk stabilization steps first. Pick an animal below for species-specific emergency cues.",
    },
    mr: {
      title: "Universal scope",
      body: "These guides show low-risk stabilization steps first. Pick an animal below for species-specific emergency cues.",
    },
  },
  dog: {
    en: {
      title: "Dog-specific cues",
      body: "Dog behavior, puppy diarrhoea, heat stress, road trauma, and maggot-wound guidance will stay visible with the universal basics.",
    },
    hi: {
      title: "Dog-specific cues",
      body: "Dog behavior, puppy diarrhoea, heat stress, road trauma, and maggot-wound guidance will stay visible with the universal basics.",
    },
    mr: {
      title: "Dog-specific cues",
      body: "Dog behavior, puppy diarrhoea, heat stress, road trauma, and maggot-wound guidance will stay visible with the universal basics.",
    },
  },
  cat: {
    en: {
      title: "Cat emergency cues",
      body: "Straining to urinate without urine, repeated litter-box trips, collapse, or any possible lily exposure needs immediate veterinary or poison-support help. Do not use dog flea products or human painkillers.",
    },
    hi: {
      title: "Cat emergency cues",
      body: "Straining to urinate without urine, repeated litter-box trips, collapse, or any possible lily exposure needs immediate veterinary or poison-support help. Do not use dog flea products or human painkillers.",
    },
    mr: {
      title: "Cat emergency cues",
      body: "Straining to urinate without urine, repeated litter-box trips, collapse, or any possible lily exposure needs immediate veterinary or poison-support help. Do not use dog flea products or human painkillers.",
    },
  },
  cow: {
    en: {
      title: "Cow and livestock cues",
      body: "Left-sided belly swelling, repeated retching, collapse, calving trouble, or inability to stand needs livestock veterinary help. Keep the animal standing and calm if safe; avoid invasive procedures.",
    },
    hi: {
      title: "Cow and livestock cues",
      body: "Left-sided belly swelling, repeated retching, collapse, calving trouble, or inability to stand needs livestock veterinary help. Keep the animal standing and calm if safe; avoid invasive procedures.",
    },
    mr: {
      title: "Cow and livestock cues",
      body: "Left-sided belly swelling, repeated retching, collapse, calving trouble, or inability to stand needs livestock veterinary help. Keep the animal standing and calm if safe; avoid invasive procedures.",
    },
  },
  other: {
    en: {
      title: "Unknown species",
      body: "Use only universal steps: protect people, reduce movement, keep the animal away from hazards, avoid medicines, and contact a relevant rescue or veterinarian.",
    },
    hi: {
      title: "Unknown species",
      body: "Use only universal steps: protect people, reduce movement, keep the animal away from hazards, avoid medicines, and contact a relevant rescue or veterinarian.",
    },
    mr: {
      title: "Unknown species",
      body: "Use only universal steps: protect people, reduce movement, keep the animal away from hazards, avoid medicines, and contact a relevant rescue or veterinarian.",
    },
  },
};

const GUIDES: Guide[] = [
  {
    id: "approach",
    species: ["all"],
    icon: "🤝",
    title: {
      en: "Approach Safely",
      hi: "सुरक्षित तरीके से पास जाएँ",
      mr: "सुरक्षितपणे जवळ जा",
    },
    summary: {
      en: "Human safety comes first. A scared or painful animal can bite, kick, or scratch even if it needs help.",
      hi: "मानव सुरक्षा पहले है। डरा हुआ या दर्द में जानवर मदद की ज़रूरत होने पर भी काट, खरोंच या लात मार सकता है।",
      mr: "मानवी सुरक्षितता आधी आहे. घाबरलेला किंवा वेदनेत असलेला प्राणी मदतीची गरज असूनही चावू, ओरखडे देऊ किंवा लाथ मारू शकतो.",
    },
    bullets: {
      en: [
        "Approach sideways, move slowly, and avoid direct eye contact.",
        "Do not corner the animal or reach straight for the head.",
        "If the animal growls, lunges, snaps, kicks, or panics, back away and call for help.",
        "Use food, water, or a calm voice only if that does not put you at risk.",
      ],
      hi: [
        "बगल से जाएँ, धीरे चलें, और सीधे आँखों में न देखें।",
        "जानवर को घेरें नहीं और सिर की ओर सीधे हाथ न बढ़ाएँ।",
        "अगर जानवर गुर्राए, झपटे, काटने या लात मारने की कोशिश करे, पीछे हटें और मदद बुलाएँ।",
        "खाना, पानी, या शांत आवाज़ तभी उपयोग करें जब उससे आपकी सुरक्षा प्रभावित न हो।",
      ],
      mr: [
        "बाजूने जा, हळू हालचाल करा, आणि थेट डोळ्यात पाहू नका.",
        "प्राण्याला कोपऱ्यात अडकवू नका आणि थेट डोक्याकडे हात नेऊ नका.",
        "प्राणी गुरगुरत असेल, झेपावत असेल, चावत किंवा लाथ मारत असेल तर मागे या आणि मदत मागा.",
        "अन्न, पाणी किंवा शांत आवाज यांचा वापर फक्त तुमची सुरक्षितता धोक्यात येत नसेल तरच करा.",
      ],
    },
  },
  {
    id: "trauma",
    species: ["all"],
    icon: "🩹",
    title: {
      en: "Bleeding, Road Trauma, and Fractures",
      hi: "खून बहना, सड़क दुर्घटना और फ्रैक्चर",
      mr: "रक्तस्त्राव, रस्ते अपघात आणि फ्रॅक्चर",
    },
    summary: {
      en: "Control what you safely can, but minimize movement and escalate quickly.",
      hi: "जो सुरक्षित रूप से कर सकते हैं वह करें, लेकिन हिलाना-डुलाना कम रखें और जल्दी मदद लें।",
      mr: "जे सुरक्षितपणे शक्य आहे ते करा, पण हालचाल कमी ठेवा आणि लवकर मदत घ्या.",
    },
    bullets: {
      en: [
        "Use direct pressure with a clean cloth for active bleeding.",
        "Do not remove embedded objects and do not force a bent limb straight.",
        "If spinal injury is possible, move the animal as little as possible on a flat support.",
        "Any heavy bleeding, obvious fracture, or vehicle trauma needs urgent veterinary care.",
      ],
      hi: [
        "सक्रिय खून बहने पर साफ कपड़े से सीधा दबाव दें।",
        "घुसी हुई वस्तु न निकालें और मुड़े हुए पैर को सीधा करने की कोशिश न करें।",
        "अगर रीढ़ की चोट की आशंका हो, तो जानवर को समतल सहारे पर बहुत कम हिलाएँ।",
        "बहुत खून, स्पष्ट फ्रैक्चर, या वाहन दुर्घटना की स्थिति में तुरंत पशु-चिकित्सक की जरूरत है।",
      ],
      mr: [
        "सक्रिय रक्तस्त्राव असेल तर स्वच्छ कापडाने थेट दाब द्या.",
        "घुसलेली वस्तू काढू नका आणि वाकलेला पाय जबरदस्तीने सरळ करू नका.",
        "मणक्याच्या दुखापतीची शक्यता असेल तर प्राण्याला सपाट आधारावर कमीत कमी हलवा.",
        "जोरदार रक्तस्त्राव, स्पष्ट फ्रॅक्चर, किंवा वाहन अपघातात तातडीची पशुवैद्यकीय मदत आवश्यक आहे.",
      ],
    },
  },
  {
    id: "heat",
    species: ["all"],
    icon: "🌡️",
    title: {
      en: "Heatstroke and Dehydration",
      hi: "हीटस्ट्रोक और डिहाइड्रेशन",
      mr: "उष्माघात आणि निर्जलीकरण",
    },
    summary: {
      en: "Cool the animal steadily, not aggressively. Ice-water shock is not the goal.",
      hi: "जानवर को धीरे-धीरे ठंडा करें, बहुत आक्रामक तरीके से नहीं। बर्फीले पानी का झटका देना सही नहीं है।",
      mr: "प्राण्याला हळूहळू थंड करा, आक्रमकपणे नाही. बर्फाच्या पाण्याचा धक्का देणे योग्य नाही.",
    },
    bullets: {
      en: [
        "Move the animal to shade and offer water if it can swallow normally.",
        "Use cool water on the paws, belly, and body; avoid ice baths.",
        "Heavy panting, collapse, vomiting, confusion, or very high body heat is an emergency.",
        "If the animal does not improve quickly, get professional care immediately.",
      ],
      hi: [
        "जानवर को छाया में ले जाएँ और अगर वह सामान्य रूप से निगल पा रहा है तो पानी दें।",
        "पंजों, पेट और शरीर पर ठंडा पानी डालें; बर्फ वाले स्नान से बचें।",
        "बहुत हाँफना, गिर जाना, उल्टी, भ्रम, या बहुत अधिक शरीर-गर्मी आपातकाल है।",
        "अगर सुधार जल्दी न हो, तो तुरंत पेशेवर मदद लें।",
      ],
      mr: [
        "प्राण्याला सावलीत न्या आणि तो व्यवस्थित गिळू शकत असेल तर पाणी द्या.",
        "पंजे, पोट आणि शरीरावर थंड पाणी वापरा; बर्फाच्या अंघोळीपासून दूर रहा.",
        "खूप धाप लागणे, कोसळणे, उलटी, गोंधळ, किंवा शरीर खूप गरम असणे ही आपत्कालीन चिन्हे आहेत.",
        "लवकर सुधारणा न झाल्यास त्वरित व्यावसायिक मदत घ्या.",
      ],
    },
  },
  {
    id: "poison",
    species: ["all"],
    icon: "☠️",
    title: {
      en: "Poisoning or Unknown Ingestion",
      hi: "ज़हर या अज्ञात चीज़ खाने की आशंका",
      mr: "विषबाधा किंवा अज्ञात वस्तू खाल्ल्याची शक्यता",
    },
    summary: {
      en: "Do not guess a home antidote. Time and accurate history matter most.",
      hi: "घर का कोई अनुमानित इलाज न करें। समय और सही जानकारी सबसे ज़्यादा महत्वपूर्ण है।",
      mr: "घरगुती उतारा अंदाजाने देऊ नका. वेळ आणि अचूक माहिती सर्वात महत्त्वाची आहे.",
    },
    bullets: {
      en: [
        "Keep the animal away from the suspected toxin and bring the packet or photo if possible.",
        "Do not force vomiting unless a veterinary professional specifically tells you to do so.",
        "Drooling, tremors, seizures, repeated vomiting, collapse, or breathing trouble need urgent help.",
        "Use poison hotlines or an emergency veterinarian as quickly as possible.",
      ],
      hi: [
        "जानवर को संदिग्ध ज़हरीली चीज़ से दूर रखें और संभव हो तो पैकेट या फोटो साथ रखें।",
        "जब तक कोई पशु-चिकित्सक विशेष रूप से न कहे, उल्टी कराने की कोशिश न करें।",
        "लार टपकना, कंपकंपी, दौरे, बार-बार उल्टी, गिरना, या साँस की दिक्कत में तुरंत मदद लें।",
        "ज़हर हेल्पलाइन या इमरजेंसी पशु-चिकित्सक से जितनी जल्दी हो सके संपर्क करें।",
      ],
      mr: [
        "प्राण्याला संशयित विषारी वस्तूपासून दूर ठेवा आणि शक्य असल्यास पॅकेट किंवा फोटो सोबत ठेवा.",
        "पशुवैद्यकाने स्पष्ट सांगितल्याशिवाय उलटी करवण्याचा प्रयत्न करू नका.",
        "लाळ गळणे, थरथर, झटके, वारंवार उलटी, कोसळणे, किंवा श्वासाचा त्रास असल्यास तातडीची मदत घ्या.",
        "विषबाधा हेल्पलाइन किंवा आपत्कालीन पशुवैद्य यांच्याशी शक्य तितक्या लवकर संपर्क साधा.",
      ],
    },
  },
  {
    id: "skin",
    species: ["all"],
    icon: "🪰",
    title: {
      en: "Maggot Wounds and Severe Skin Disease",
      hi: "कीड़ों वाले घाव और गंभीर त्वचा रोग",
      mr: "अळ्यांचे घाव आणि गंभीर त्वचारोग",
    },
    summary: {
      en: "These are painful, quickly worsening problems and usually need repeated treatment.",
      hi: "ये दर्दनाक और तेजी से बिगड़ने वाली समस्याएँ हैं, और अक्सर बार-बार इलाज की जरूरत होती है।",
      mr: "ही वेदनादायक आणि झपाट्याने बिघडणारी समस्या असते, आणि बहुतेकदा पुन्हा पुन्हा उपचार लागतात.",
    },
    bullets: {
      en: [
        "Keep flies away as much as possible and transport for treatment quickly.",
        "If you must rinse the surface, use clean saline only.",
        "Never pour kerosene, turpentine, engine oil, acid, or other chemicals into the wound or onto diseased skin.",
        "Whole-body hair loss, foul smell, open sores, or maggots are not minor problems.",
      ],
      hi: [
        "जहाँ तक संभव हो मक्खियों को दूर रखें और जल्दी इलाज के लिए ले जाएँ।",
        "अगर सतह धोनी ही पड़े, तो केवल साफ सेलाइन का उपयोग करें।",
        "घाव या खराब त्वचा पर कभी भी केरोसिन, टर्पेन्टाइन, इंजन ऑयल, एसिड, या दूसरे रसायन न डालें।",
        "पूरे शरीर में बाल झड़ना, बदबू, खुले घाव, या कीड़े होना छोटी समस्या नहीं है।",
      ],
      mr: [
        "शक्य तितक्या माशा दूर ठेवा आणि लवकर उपचारासाठी घेऊन जा.",
        "वरचा भाग धुवावाच लागला तर फक्त स्वच्छ सलाईन वापरा.",
        "जखमेवर किंवा आजारी त्वचेवर कधीही रॉकेल, टर्पेन्टाइन, इंजिन ऑइल, आम्ल, किंवा इतर रसायने टाकू नका.",
        "संपूर्ण शरीरावर केस गळणे, दुर्गंधी, उघडी जखम, किंवा अळ्या असणे ही किरकोळ समस्या नाही.",
      ],
    },
  },
  {
    id: "cat-urgent",
    species: ["cat"],
    icon: "!",
    title: {
      en: "Cats: Urinary Blockage and Lily Exposure",
      hi: "Cats: Urinary Blockage and Lily Exposure",
      mr: "Cats: Urinary Blockage and Lily Exposure",
    },
    summary: {
      en: "Cats have a few time-critical emergencies where waiting can be dangerous.",
      hi: "Cats have a few time-critical emergencies where waiting can be dangerous.",
      mr: "Cats have a few time-critical emergencies where waiting can be dangerous.",
    },
    bullets: {
      en: [
        "Repeatedly trying to urinate with little or no urine is an emergency, especially in male cats.",
        "Possible lily exposure is urgent even if the cat only licked pollen or drank vase water.",
        "Do not give human painkillers, dog flea products, or home antidotes.",
        "Keep the cat contained, reduce stress, bring plant/packet details, and contact a vet or poison-support line.",
      ],
      hi: [
        "Repeatedly trying to urinate with little or no urine is an emergency, especially in male cats.",
        "Possible lily exposure is urgent even if the cat only licked pollen or drank vase water.",
        "Do not give human painkillers, dog flea products, or home antidotes.",
        "Keep the cat contained, reduce stress, bring plant/packet details, and contact a vet or poison-support line.",
      ],
      mr: [
        "Repeatedly trying to urinate with little or no urine is an emergency, especially in male cats.",
        "Possible lily exposure is urgent even if the cat only licked pollen or drank vase water.",
        "Do not give human painkillers, dog flea products, or home antidotes.",
        "Keep the cat contained, reduce stress, bring plant/packet details, and contact a vet or poison-support line.",
      ],
    },
  },
  {
    id: "cow-bloat",
    species: ["cow"],
    icon: "!",
    title: {
      en: "Cows: Bloat and Down Animals",
      hi: "Cows: Bloat and Down Animals",
      mr: "Cows: Bloat and Down Animals",
    },
    summary: {
      en: "Bloat and inability to stand can become life-threatening and need livestock help.",
      hi: "Bloat and inability to stand can become life-threatening and need livestock help.",
      mr: "Bloat and inability to stand can become life-threatening and need livestock help.",
    },
    bullets: {
      en: [
        "Left-sided belly swelling with repeated retching or distress is urgent livestock-vet territory.",
        "If safe, keep the cow standing or sternal, calm, shaded, and away from traffic.",
        "Do not puncture the rumen, force oils, or try invasive procedures unless trained and directed.",
        "For a down cow, protect from sun/traffic, avoid dragging by limbs, and call livestock support early.",
      ],
      hi: [
        "Left-sided belly swelling with repeated retching or distress is urgent livestock-vet territory.",
        "If safe, keep the cow standing or sternal, calm, shaded, and away from traffic.",
        "Do not puncture the rumen, force oils, or try invasive procedures unless trained and directed.",
        "For a down cow, protect from sun/traffic, avoid dragging by limbs, and call livestock support early.",
      ],
      mr: [
        "Left-sided belly swelling with repeated retching or distress is urgent livestock-vet territory.",
        "If safe, keep the cow standing or sternal, calm, shaded, and away from traffic.",
        "Do not puncture the rumen, force oils, or try invasive procedures unless trained and directed.",
        "For a down cow, protect from sun/traffic, avoid dragging by limbs, and call livestock support early.",
      ],
    },
  },
  {
    id: "puppies",
    species: ["dog"],
    icon: "🐶",
    title: {
      en: "Puppies, Vomiting, and Diarrhoea",
      hi: "पिल्ले, उल्टी और दस्त",
      mr: "पिल्ले, उलटी आणि जुलाब",
    },
    summary: {
      en: "Young puppies deteriorate fast. Weakness, chilling, and bloody diarrhoea can become life-threatening quickly.",
      hi: "छोटे पिल्ले बहुत जल्दी बिगड़ सकते हैं। कमजोरी, ठंड लगना और खून वाले दस्त जल्दी जानलेवा हो सकते हैं।",
      mr: "लहान पिल्ले झपाट्याने खालावू शकतात. अशक्तपणा, अंग गार पडणे, आणि रक्ताळ जुलाब पटकन जीवघेणे ठरू शकतात.",
    },
    bullets: {
      en: [
        "Keep weak puppies warm, dry, and away from larger animals.",
        "Do not give random human medicines for diarrhoea or pain.",
        "Bloody diarrhoea, repeated vomiting, or refusal to drink are urgent signs.",
        "If the mother is present and safe, keeping puppies with her is usually better than separating them too early.",
      ],
      hi: [
        "कमज़ोर पिल्लों को गर्म, सूखा, और बड़े जानवरों से अलग रखें।",
        "दस्त या दर्द के लिए मनमानी मानव दवाएँ न दें।",
        "खून वाले दस्त, बार-बार उल्टी, या पानी न पीना गंभीर संकेत हैं।",
        "अगर माँ मौजूद और सुरक्षित है, तो पिल्लों को बहुत जल्दी अलग करने के बजाय उसके साथ रखना अक्सर बेहतर होता है।",
      ],
      mr: [
        "अशक्त पिल्लांना उबदार, कोरडे, आणि मोठ्या प्राण्यांपासून दूर ठेवा.",
        "जुलाब किंवा वेदनेसाठी मनमानी मानवी औषधे देऊ नका.",
        "रक्ताळ जुलाब, वारंवार उलटी, किंवा पाणी न पिणे ही गंभीर चिन्हे आहेत.",
        "आई उपस्थित आणि सुरक्षित असेल तर पिल्लांना फार लवकर वेगळे करण्यापेक्षा तिच्यासोबत ठेवणे साधारणपणे चांगले असते.",
      ],
    },
  },
];

const RESOURCE_LINKS: ResourceLink[] = [
  {
    href: "https://awbi.gov.in/view/index/contact-us",
    label: "AWBI Contact",
    note: {
      en: "Official Animal Welfare Board of India contact details.",
      hi: "भारतीय पशु कल्याण बोर्ड के आधिकारिक संपर्क विवरण।",
      mr: "भारतीय प्राणी कल्याण मंडळाचे अधिकृत संपर्क तपशील.",
    },
  },
  {
    href: "https://awbi.gov.in/view/index/list-of-awo",
    label: "AWBI Recognized Organizations",
    note: {
      en: "Directory of recognized organizations for local India-wide help.",
      hi: "भारत भर में स्थानीय मदद के लिए मान्यता प्राप्त संस्थाओं की निर्देशिका।",
      mr: "भारतभरातील स्थानिक मदतीसाठी मान्यताप्राप्त संस्थांची यादी.",
    },
  },
  {
    href: "https://www.who.int/news-room/fact-sheets/detail/rabies%EF%BB%BF",
    label: "WHO Rabies Fact Sheet",
    note: {
      en: "Primary guidance for human rabies exposure and wound washing.",
      hi: "मानव रेबीज़ एक्सपोज़र और घाव धोने के लिए प्राथमिक मार्गदर्शन।",
      mr: "मानवी रेबीज एक्स्पोजर आणि जखम धुण्याबाबतचे प्राथमिक मार्गदर्शन.",
    },
  },
  {
    href: "https://www.aspca.org/pet-care/aspca-poison-control",
    label: "ASPCA Poison Control",
    note: {
      en: "Useful poison-support resource where available.",
      hi: "जहाँ उपलब्ध हो, ज़हर संबंधी उपयोगी सहायता संसाधन।",
      mr: "जिथे उपलब्ध असेल तिथे विषबाधेसाठी उपयोगी सहाय्य संसाधन.",
    },
  },
  {
    href: "https://www.fda.gov/animal-veterinary/animal-health-literacy/lovely-lilies-and-curious-cats-dangerous-combination",
    label: "FDA: Lilies and cats",
    note: {
      en: "Official cat lily-toxicity guidance and emergency context.",
      hi: "Official cat lily-toxicity guidance and emergency context.",
      mr: "Official cat lily-toxicity guidance and emergency context.",
    },
  },
  {
    href: "https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics/feline-lower-urinary-tract-disease",
    label: "Cornell: Feline urinary emergencies",
    note: {
      en: "University veterinary guidance for lower urinary tract signs and obstruction.",
      hi: "University veterinary guidance for lower urinary tract signs and obstruction.",
      mr: "University veterinary guidance for lower urinary tract signs and obstruction.",
    },
  },
  {
    href: "https://www.merckvetmanual.com/digestive-system/diseases-of-the-ruminant-forestomach/bloat-in-ruminants",
    label: "Merck Veterinary Manual: Ruminant bloat",
    note: {
      en: "Clinical reference for cattle and ruminant bloat.",
      hi: "Clinical reference for cattle and ruminant bloat.",
      mr: "Clinical reference for cattle and ruminant bloat.",
    },
  },
  {
    href: "https://www.petpoisonhelpline.com/contact/",
    label: "Pet Poison Helpline",
    note: {
      en: "Another poison-support option for urgent ingestion cases.",
      hi: "अचानक कुछ खा लेने वाले मामलों में ज़हर सहायता का एक और विकल्प।",
      mr: "अकस्मात काही खाल्ल्याच्या तातडीच्या प्रकरणांसाठी विष सहाय्याचा आणखी एक पर्याय.",
    },
  },
  {
    href: "https://www.112.gov.in/about",
    label: "India Emergency Response Support System",
    note: {
      en: "Official information for India emergency response.",
      hi: "भारत की आपातकालीन प्रतिक्रिया प्रणाली की आधिकारिक जानकारी।",
      mr: "भारताच्या आपत्कालीन प्रतिसाद व्यवस्थेची अधिकृत माहिती.",
    },
  },
];

export default function LearnPage() {
  const { language } = useLanguage();
  const pageLanguage = (language as PageLanguage) || "en";
  const copy = COPY[pageLanguage];
  const [speciesFilter, setSpeciesFilter] = useState<SpeciesFilter>("all");

  useEffect(() => {
    setSpeciesFilter(normalizeSpeciesFilter(new URLSearchParams(window.location.search).get("species")));
  }, []);

  const updateSpeciesFilter = (species: SpeciesFilter) => {
    setSpeciesFilter(species);
    const params = new URLSearchParams(window.location.search);
    if (species === "all") params.delete("species");
    else params.set("species", species);
    const query = params.toString();
    window.history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
  };

  const visibleGuides = useMemo(
    () =>
      GUIDES.filter(
        (guide) =>
          speciesFilter === "all" ||
          guide.species.includes("all") ||
          guide.species.includes(speciesFilter)
      ),
    [speciesFilter]
  );
  const speciesAlert = SPECIES_ALERTS[speciesFilter][pageLanguage];

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">
            {copy.title}
          </h1>
          <p className="text-sm text-gray-500">{copy.subtitle}</p>
        </div>
        <LanguageSelector compact />
      </div>

      <section className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
        <h2 className="font-semibold text-amber-800 mb-2">{copy.truthTitle}</h2>
        <p className="text-sm text-amber-800 leading-relaxed">{copy.truthBody}</p>
      </section>

      <section className="bg-white border border-gray-100 rounded-xl p-4 mb-4">
        <SpeciesScopeSelect
          value={speciesFilter}
          onChange={updateSpeciesFilter}
          options={SPECIES_FILTER_OPTIONS}
          label="Animal"
        />
        <div className="mt-3 rounded-lg bg-[var(--color-warm-50)] px-3 py-2">
          <h2 className="text-sm font-semibold text-[var(--color-warm-800)]">{speciesAlert.title}</h2>
          <p className="text-sm text-[var(--color-warm-800)] leading-relaxed mt-1">
            {speciesAlert.body}
          </p>
        </div>
      </section>

      <section className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
        <h2 className="font-semibold text-red-700 mb-2">{copy.emergencyTitle}</h2>
        <p className="text-sm text-red-700 leading-relaxed">{copy.emergencyBody}</p>
      </section>

      <section className="mb-6">
        <h2 className="text-lg font-bold text-[var(--color-warm-700)] mb-3">
          {copy.quickTitle}
        </h2>
        <div className="grid grid-cols-1 gap-3">
          <Link
            href={getNearbyHref(speciesFilter)}
            className="bg-white border border-gray-200 rounded-xl p-4 text-sm font-medium text-gray-700"
          >
            🏥 {copy.quickFindHelp}
          </Link>
          <Link
            href={getFirstAidHref(speciesFilter)}
            className="bg-white border border-gray-200 rounded-xl p-4 text-sm font-medium text-gray-700"
          >
            🩹 {copy.quickFirstAid}
          </Link>
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(getSpeciesSearchQuery(speciesFilter))}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white border border-gray-200 rounded-xl p-4 text-sm font-medium text-gray-700"
          >
            📍 {copy.quickVet}
          </a>
          <a
            href="https://www.who.int/news-room/fact-sheets/detail/rabies%EF%BB%BF"
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white border border-gray-200 rounded-xl p-4 text-sm font-medium text-gray-700"
          >
            📘 {copy.quickRabies}
          </a>
        </div>
      </section>

      <section className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
        <h2 className="font-semibold text-red-700 mb-3">{copy.redFlagsTitle}</h2>
        <ul className="space-y-2">
          {copy.redFlags.map((item) => (
            <li key={item} className="flex gap-2 text-sm text-red-700">
              <span>•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-4 mb-6">
        {visibleGuides.map((guide) => (
          <div
            key={guide.id}
            id={guide.id}
            className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 scroll-mt-20"
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl">{guide.icon}</span>
              <div className="min-w-0">
                <h3 className="font-semibold text-gray-800">
                  {guide.title[pageLanguage]}
                </h3>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {guide.species.map((species) => (
                    <span
                      key={species}
                      className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600"
                    >
                      {species === "all" ? "All animals" : getSpeciesLabel(species)}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                  {guide.summary[pageLanguage]}
                </p>
              </div>
            </div>
            <ul className="mt-4 space-y-2">
              {guide.bullets[pageLanguage].map((bullet) => (
                <li key={bullet} className="flex gap-2 text-sm text-gray-600">
                  <span className="text-[var(--color-warm-500)]">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
            <Quiz topicId={guide.id} language={pageLanguage} />
          </div>
        ))}
      </section>

      <section className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-6">
        <h2 className="font-semibold text-slate-800 mb-2">{copy.uncertaintyTitle}</h2>
        <p className="text-sm text-slate-700 leading-relaxed">{copy.uncertaintyBody}</p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-[var(--color-warm-700)] mb-3">
          {copy.resourcesTitle}
        </h2>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {RESOURCE_LINKS.map((resource) => (
            <a
              key={resource.href}
              href={resource.href}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50"
            >
              <div className="flex items-center justify-between gap-4">
                <span className="font-medium text-gray-800">{resource.label}</span>
                <span className="text-gray-400">↗</span>
              </div>
              <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                {resource.note[pageLanguage]}
              </p>
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}
