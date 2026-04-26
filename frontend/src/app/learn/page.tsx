"use client";

import Link from "next/link";
import { useLanguage, LanguageSelector } from "@/lib/language";

interface Guide {
  emoji: string;
  title: Record<string, string>;
  summary: Record<string, string>;
  tips: Record<string, string[]>;
}

const GUIDES: Guide[] = [
  {
    emoji: "🤝",
    title: {
      en: "How to Safely Approach a Stray Dog",
      hi: "आवारा कुत्ते को सुरक्षित रूप से कैसे पहुंचें",
      mr: "भटक्या कुत्र्याजवळ सुरक्षितपणे कसे जावे",
    },
    summary: {
      en: "Stay calm, move slowly, turn sideways, and let the dog come to you. Never chase or corner a stray.",
      hi: "शांत रहें, धीरे चलें, बग़ल में मुड़ें, और कुत्ते को आपके पास आने दें। कभी पीछा न करें।",
      mr: "शांत राहा, हळू चाला, बाजूला वळा, आणि कुत्र्याला तुमच्याकडे येऊ द्या. कधीही पाठलाग करू नका.",
    },
    tips: {
      en: [
        "Avoid direct eye contact — it can feel threatening",
        "Extend the back of your hand slowly for sniffing",
        "Watch the tail: tucked = fear, stiff = alert",
        "If the dog growls, stop and give space",
      ],
      hi: [
        "सीधी नज़र से बचें — यह धमकी जैसा लगता है",
        "सूंघने के लिए धीरे-धीरे हाथ का पिछला हिस्सा बढ़ाएं",
        "पूंछ देखें: दबी = डर, तनी = सतर्क",
        "अगर कुत्ता गुर्राए तो रुकें और जगह दें",
      ],
      mr: [
        "सरळ डोळ्यांत पाहणे टाळा — ती धमकी वाटू शकते",
        "हुंगण्यासाठी हळूवारपणे हाताचा मागचा भाग पुढे करा",
        "शेपूट पहा: दाबलेली = भीती, ताठ = सतर्क",
        "कुत्रा गुरगुरल्यास थांबा आणि जागा द्या",
      ],
    },
  },
  {
    emoji: "🩹",
    title: {
      en: "Basic First Aid for Bleeding Wounds",
      hi: "रक्तस्राव वाले घावों के लिए प्राथमिक चिकित्सा",
      mr: "रक्तस्रावी जखमांसाठी प्रथमोपचार",
    },
    summary: {
      en: "Apply gentle pressure with a clean cloth, don't remove embedded objects, and get to a vet.",
      hi: "साफ कपड़े से हल्का दबाव लगाएं, घुसी वस्तुएं न निकालें, और पशु चिकित्सक के पास जाएं।",
      mr: "स्वच्छ कपड्याने हळूवार दाब द्या, रुतलेल्या वस्तू काढू नका, आणि पशुवैद्यकाकडे जा.",
    },
    tips: {
      en: [
        "Wear gloves if available",
        "Do NOT use Dettol or hydrogen peroxide on dogs",
        "Wrap wounds loosely with clean cloth",
        "Rush to vet for heavy, non-stop bleeding",
      ],
      hi: [
        "उपलब्ध हो तो दस्ताने पहनें",
        "कुत्तों पर डेटॉल या हाइड्रोजन पेरोक्साइड का उपयोग न करें",
        "घाव को साफ कपड़े से ढीला लपेटें",
        "भारी, लगातार रक्तस्राव के लिए तुरंत पशु चिकित्सक के पास जाएं",
      ],
      mr: [
        "उपलब्ध असल्यास हातमोजे घाला",
        "कुत्र्यांवर डेटॉल किंवा हायड्रोजन पेरॉक्साइड वापरू नका",
        "स्वच्छ कापडाने जखम सैल गुंडाळा",
        "जोरदार, सतत रक्तस्रावासाठी ताबडतोब पशुवैद्यकाकडे जा",
      ],
    },
  },
  {
    emoji: "🌡️",
    title: {
      en: "Dehydration & Heatstroke",
      hi: "निर्जलीकरण और हीटस्ट्रोक",
      mr: "निर्जलीकरण आणि उष्माघात",
    },
    summary: {
      en: "Offer cool (not ice cold) water, move to shade, wet paws and belly with cool water.",
      hi: "ठंडा (बर्फ जैसा नहीं) पानी दें, छाया में ले जाएं, पंजों और पेट को ठंडे पानी से गीला करें।",
      mr: "थंड (बर्फासारखे नाही) पाणी द्या, सावलीत न्या, पंजे आणि पोट थंड पाण्याने ओले करा.",
    },
    tips: {
      en: [
        "Signs: dry gums, sunken eyes, excessive panting",
        "Wet the dog's paws, belly, and neck",
        "Never douse with ice water — it causes shock",
        "Keep water bowls outside your building for strays",
      ],
      hi: [
        "लक्षण: सूखे मसूड़े, धंसी आंखें, अत्यधिक हांफना",
        "कुत्ते के पंजे, पेट और गर्दन को गीला करें",
        "कभी बर्फ के पानी से न भिगोएं — शॉक हो सकता है",
        "अपनी बिल्डिंग के बाहर आवारा कुत्तों के लिए पानी रखें",
      ],
      mr: [
        "लक्षणे: कोरडे हिरडे, खोल गेलेले डोळे, जास्त धापा",
        "कुत्र्याचे पंजे, पोट आणि मान ओली करा",
        "बर्फाच्या पाण्याने कधीही भिजवू नका — शॉक होतो",
        "तुमच्या इमारतीबाहेर भटक्या कुत्र्यांसाठी पाणी ठेवा",
      ],
    },
  },
  {
    emoji: "🦠",
    title: {
      en: "Mange — What You Can Do",
      hi: "खुजली (मैंज) — आप क्या कर सकते हैं",
      mr: "खरूज (मेंज) — तुम्ही काय करू शकता",
    },
    summary: {
      en: "Mange is treatable! Contact an NGO for proper treatment. Never apply home remedies like kerosene.",
      hi: "मैंज का इलाज हो सकता है! सही उपचार के लिए किसी NGO से संपर्क करें। केरोसिन जैसे घरेलू उपाय कभी न लगाएं।",
      mr: "खरूज उपचार करता येतो! योग्य उपचारासाठी NGO शी संपर्क साधा. रॉकेल सारखे घरगुती उपाय कधीही लावू नका.",
    },
    tips: {
      en: [
        "Signs: hair loss patches, red skin, excessive scratching",
        "Do NOT use kerosene, engine oil, or turmeric paste",
        "Provide nutritious food to build immunity",
        "Report to WSD or IDA for treatment",
      ],
      hi: [
        "लक्षण: बाल झड़ने के धब्बे, लाल त्वचा, बहुत खुजली",
        "केरोसिन, इंजन ऑइल, या हल्दी का पेस्ट न लगाएं",
        "रोग प्रतिरोधक क्षमता बढ़ाने के लिए पौष्टिक भोजन दें",
        "इलाज के लिए WSD या IDA को सूचित करें",
      ],
      mr: [
        "लक्षणे: केस गळण्याचे ठिपके, लाल त्वचा, खूप खाजवणे",
        "रॉकेल, इंजिन ऑईल, किंवा हळदीचा लेप लावू नका",
        "प्रतिकारशक्ती वाढवण्यासाठी पौष्टिक अन्न द्या",
        "उपचारासाठी WSD किंवा IDA ला कळवा",
      ],
    },
  },
  {
    emoji: "💉",
    title: {
      en: "Rabies Awareness",
      hi: "रेबीज जागरूकता",
      mr: "रेबीज जागरूकता",
    },
    summary: {
      en: "Rabies is 100% fatal but 100% preventable. Wash any bite wound with soap and water for 15 minutes.",
      hi: "रेबीज 100% घातक है लेकिन 100% रोकथाम योग्य। किसी भी काटने पर 15 मिनट साबुन-पानी से धोएं।",
      mr: "रेबीज 100% प्राणघातक पण 100% टाळता येतो. कोणत्याही चाव्याच्या जखमेवर 15 मिनिटे साबण-पाण्याने धुवा.",
    },
    tips: {
      en: [
        "ANY bite or scratch breaking skin needs PEP vaccine",
        "Wash wound with soap + running water for 15 min",
        "Go to hospital immediately for anti-rabies shots",
        "Do NOT apply chilli, turmeric, or folk remedies",
      ],
      hi: [
        "त्वचा तोड़ने वाले किसी भी काटने पर PEP टीका जरूरी",
        "15 मिनट साबुन + बहते पानी से घाव धोएं",
        "एंटी-रेबीज टीके के लिए तुरंत अस्पताल जाएं",
        "मिर्ची, हल्दी या देसी इलाज न लगाएं",
      ],
      mr: [
        "त्वचा फोडणाऱ्या कोणत्याही चाव्याला PEP लस आवश्यक",
        "15 मिनिटे साबण + वाहत्या पाण्याने जखम धुवा",
        "रेबीज विरोधी लसीसाठी ताबडतोब हॉस्पिटलला जा",
        "मिरची, हळद किंवा लोक उपचार लावू नका",
      ],
    },
  },
  {
    emoji: "🐶",
    title: {
      en: "Dog Body Language Guide",
      hi: "कुत्ते की बॉडी लैंग्वेज गाइड",
      mr: "कुत्र्याच्या शारीरिक भाषेचे मार्गदर्शक",
    },
    summary: {
      en: "Understanding body language keeps both you and the dog safe.",
      hi: "बॉडी लैंग्वेज समझना आपको और कुत्ते दोनों को सुरक्षित रखता है।",
      mr: "शारीरिक भाषा समजल्यास तुम्ही आणि कुत्रा दोघेही सुरक्षित राहता.",
    },
    tips: {
      en: [
        "Happy: relaxed body, wide tail wags, open mouth smile",
        "Scared: tucked tail, ears flat, crouching, lip licking",
        "Aggressive: stiff body, raised hackles, showing teeth",
        "In pain: whimpering, limping, licking one area obsessively",
      ],
      hi: [
        "खुश: शिथिल शरीर, चौड़ी पूंछ हिलाना, खुले मुंह की मुस्कान",
        "डरा: दबी पूंछ, चपटे कान, सिकुड़ा हुआ, होंठ चाटना",
        "आक्रामक: तना शरीर, उभे बाल, दात दिखाना",
        "दर्द में: कराहना, लंगड़ाना, एक जगह बार-बार चाटना",
      ],
      mr: [
        "आनंदी: शिथिल शरीर, रुंद शेपटी हलवणे, उघड्या तोंडाचे हसू",
        "घाबरलेला: दाबलेली शेपूट, सपाट कान, वाकलेला, ओठ चाटणे",
        "आक्रमक: ताठ शरीर, उभे केस, दात दाखवणे",
        "दुखापत: ओरडणे, लंगडणे, एकाच जागी सारखे चाटणे",
      ],
    },
  },
  {
    emoji: "🍖",
    title: {
      en: "Feeding Strays Safely",
      hi: "आवारा कुत्तों को सुरक्षित रूप से खिलाना",
      mr: "भटक्या कुत्र्यांना सुरक्षितपणे खाऊ घालणे",
    },
    summary: {
      en: "Feed at the same time and place daily. Avoid chocolate, onions, and cooked bones.",
      hi: "रोज़ एक ही समय और जगह पर खिलाएं। चॉकलेट, प्याज़ और पके हुए हड्डियों से बचें।",
      mr: "रोज एकाच वेळी आणि ठिकाणी खाऊ घाला. चॉकलेट, कांदा आणि शिजवलेली हाडे टाळा.",
    },
    tips: {
      en: [
        "Good: rice + boiled chicken/egg, roti with dal, kibble",
        "Bad: chocolate, onion, garlic, grapes, spicy food",
        "Always provide water alongside food",
        "Clean up leftovers to avoid attracting rats",
      ],
      hi: [
        "अच्छा: चावल + उबला चिकन/अंडा, दाल रोटी, किबल",
        "बुरा: चॉकलेट, प्याज़, लहसुन, अंगूर, मसालेदार खाना",
        "खाने के साथ हमेशा पानी दें",
        "चूहों को आकर्षित करने से बचने के लिए बचा हुआ खाना साफ करें",
      ],
      mr: [
        "चांगले: भात + उकडलेले चिकन/अंडे, डाळ भाकरी, किबल",
        "वाईट: चॉकलेट, कांदा, लसूण, द्राक्षे, तिखट अन्न",
        "अन्नासोबत नेहमी पाणी द्या",
        "उंदरांना आकर्षित होऊ नये म्हणून उरलेले अन्न साफ करा",
      ],
    },
  },
  {
    emoji: "⚖️",
    title: {
      en: "Legal Rights of Stray Dogs in India",
      hi: "भारत में आवारा कुत्तों के कानूनी अधिकार",
      mr: "भारतातील भटक्या कुत्र्यांचे कायदेशीर अधिकार",
    },
    summary: {
      en: "Stray dogs are protected by law. Feeding them is legal. Harming them is a criminal offense.",
      hi: "आवारा कुत्ते कानून द्वारा संरक्षित हैं। उन्हें खिलाना कानूनी है। उन्हें नुकसान पहुंचाना अपराध है।",
      mr: "भटक्या कुत्र्यांना कायद्याने संरक्षण आहे. त्यांना खाऊ घालणे कायदेशीर आहे. त्यांना इजा करणे गुन्हा आहे.",
    },
    tips: {
      en: [
        "PCA Act 1960: illegal to harm, poison, or kill strays",
        "ABC Rules 2023: only sterilize/vaccinate, no relocation",
        "No society can legally ban feeding strays",
        "Report cruelty: AWBI helpline 1962",
      ],
      hi: [
        "PCA अधिनियम 1960: आवारा कुत्तों को नुकसान, ज़हर या मारना गैरकानूनी",
        "ABC नियम 2023: केवल नसबंदी/टीकाकरण, स्थानांतरण नहीं",
        "कोई सोसाइटी कानूनी रूप से कुत्तों को खिलाने पर रोक नहीं लगा सकती",
        "क्रूरता की शिकायत: AWBI हेल्पलाइन 1962",
      ],
      mr: [
        "PCA कायदा 1960: भटक्या कुत्र्यांना दुखापत, विष किंवा मारणे बेकायदेशीर",
        "ABC नियम 2023: फक्त निर्बीजन/लसीकरण, स्थलांतर नाही",
        "कोणतीही सोसायटी कायदेशीररित्या कुत्र्यांना खाऊ घालण्यावर बंदी घालू शकत नाही",
        "क्रूरतेची तक्रार: AWBI हेल्पलाइन 1962",
      ],
    },
  },
  {
    emoji: "🦵",
    title: {
      en: "Dog Limping or Unable to Walk",
      hi: "कुत्ता लंगड़ा रहा है या चल नहीं पा रहा",
      mr: "कुत्रा लंगडत आहे किंवा चालू शकत नाही",
    },
    summary: {
      en: "Check paw pads for glass/thorns. No weight on leg = possible fracture. Don't try to set bones yourself.",
      hi: "पंजों में कांच/कांटे चेक करें। पैर पर वज़न नहीं = संभावित फ्रैक्चर। हड्डी खुद न जोड़ें।",
      mr: "पंजात काच/काटे तपासा. पायावर वजन नाही = संभाव्य फ्रॅक्चर. स्वतः हाडे जोडू नका.",
    },
    tips: {
      en: [
        "Mumbai streets have sharp debris — check paw pads carefully",
        "Suspected fracture: keep the dog still, use a board as stretcher",
        "Swollen paw between toes may be an abscess",
        "Contact a rescue NGO for transport if needed",
      ],
      hi: [
        "मुंबई की सड़कों पर तेज़ कचरा होता है — पंजे ध्यान से जांचें",
        "फ्रैक्चर का शक: कुत्ते को शांत रखें, बोर्ड को स्ट्रेचर की तरह इस्तेमाल करें",
        "उंगलियों के बीच सूजा पंजा फोड़ा हो सकता है",
        "ज़रूरत हो तो परिवहन के लिए बचाव NGO से संपर्क करें",
      ],
      mr: [
        "मुंबईच्या रस्त्यांवर धारदार कचरा असतो — पंजे काळजीपूर्वक तपासा",
        "फ्रॅक्चरचा संशय: कुत्र्याला शांत ठेवा, बोर्ड स्ट्रेचर म्हणून वापरा",
        "बोटांमध्ये सुजलेला पंजा गळू असू शकतो",
        "आवश्यक असल्यास वाहतुकीसाठी बचाव NGO शी संपर्क साधा",
      ],
    },
  },
  {
    emoji: "👁️",
    title: {
      en: "Eye Injuries and Infections",
      hi: "आंख की चोट और संक्रमण",
      mr: "डोळ्यांच्या जखमा आणि संक्रमण",
    },
    summary: {
      en: "Don't touch the eye or remove stuck objects. Clean around the eye gently with warm water.",
      hi: "आंख को न छुएं और फंसी वस्तुएं न निकालें। गुनगुने पानी से आंख के आसपास धीरे साफ करें।",
      mr: "डोळ्याला स्पर्श करू नका आणि अडकलेल्या वस्तू काढू नका. कोमट पाण्याने डोळ्याभोवती हळूवार स्वच्छ करा.",
    },
    tips: {
      en: [
        "Green/yellow discharge = bacterial infection, needs vet",
        "Bulging eye after trauma = emergency, keep moist with saline",
        "Cherry eye (red bulge in corner) is common in puppies",
        "Many one-eyed strays live perfectly normal lives",
      ],
      hi: [
        "हरा/पीला स्राव = बैक्टीरियल संक्रमण, पशु चिकित्सक ज़रूरी",
        "चोट के बाद उभरी आंख = आपातकाल, सेलाइन से नम रखें",
        "चेरी आई (कोने में लाल उभार) पिल्लों में आम है",
        "कई एक-आंख वाले आवारा कुत्ते बिल्कुल सामान्य जीवन जीते हैं",
      ],
      mr: [
        "हिरवा/पिवळा स्राव = बॅक्टेरियल संक्रमण, पशुवैद्य आवश्यक",
        "आघातानंतर फुगलेला डोळा = आणीबाणी, सलाईनने ओला ठेवा",
        "चेरी आय (कोपऱ्यात लाल फुगवटा) पिल्लांमध्ये सामान्य आहे",
        "अनेक एक-डोळ्या भटक्या कुत्र्यांचे आयुष्य अगदी सामान्य असते",
      ],
    },
  },
  {
    emoji: "🪢",
    title: {
      en: "Dog Caught in Wire, Rope, or Manja",
      hi: "तार, रस्सी या मांझा में फंसा कुत्ता",
      mr: "तार, दोरी किंवा मांझा में फंसलेला कुत्रा",
    },
    summary: {
      en: "Don't pull embedded wire out. Cut loose entanglements carefully. Deep wire wounds need a vet.",
      hi: "धंसी तार को बाहर न खींचें। उलझाव को सावधानी से काटें। गहरे तार के घाव के लिए डॉक्टर ज़रूरी।",
      mr: "रुतलेली तार बाहेर ओढू नका. अडकलेले सावधपणे कापा. खोल तारेच्या जखमांसाठी पशुवैद्य आवश्यक.",
    },
    tips: {
      en: [
        "Manja (kite string) cuts are a major problem in Mumbai",
        "Use thick gloves — trapped dogs may bite out of fear",
        "Cover wounds to prevent flies from laying eggs",
        "Rubber bands on muzzle/legs cut off circulation — remove urgently",
      ],
      hi: [
        "मांझा (पतंग की डोर) के कट मुंबई में बड़ी समस्या है",
        "मोटे दस्ताने इस्तेमाल करें — फंसे कुत्ते डर से काट सकते हैं",
        "मक्खियों को अंडे देने से रोकने के लिए घाव ढकें",
        "मुंह/पैरों पर रबर बैंड रक्त प्रवाह रोकते हैं — तुरंत हटाएं",
      ],
      mr: [
        "मांझा (पतंगाची दोरी) चे कट मुंबईत मोठी समस्या आहे",
        "जाड हातमोजे वापरा — अडकलेले कुत्रे भीतीने चावू शकतात",
        "माश्यांना अंडी घालण्यापासून रोखण्यासाठी जखम झाका",
        "तोंड/पायांवरील रबर बॅंड रक्तप्रवाह थांबवतात — ताबडतोब काढा",
      ],
    },
  },
  {
    emoji: "☠️",
    title: {
      en: "Poisoning — What to Do",
      hi: "ज़हर — क्या करें",
      mr: "विषबाधा — काय करावे",
    },
    summary: {
      en: "Time is critical. Don't make the dog vomit. Try to identify what was eaten. Rush to vet.",
      hi: "समय बहुत ज़रूरी है। कुत्ते को उल्टी न कराएं। क्या खाया पहचानने की कोशिश करें। तुरंत डॉक्टर के पास जाएं।",
      mr: "वेळ अत्यंत महत्त्वाचा. कुत्र्याला उलटी करवू नका. काय खाल्ले ते ओळखण्याचा प्रयत्न करा. ताबडतोब पशुवैद्यकाकडे जा.",
    },
    tips: {
      en: [
        "Signs: sudden vomiting, foaming, seizures, blue gums",
        "Rat poison causes delayed symptoms (2-3 days) — internal bleeding",
        "Collect suspicious food/pellets as evidence (wear gloves)",
        "Intentional poisoning is a criminal offense — file an FIR",
      ],
      hi: [
        "लक्षण: अचानक उल्टी, मुंह से झाग, दौरे, नीले मसूड़े",
        "चूहे का ज़हर देर से असर करता है (2-3 दिन) — अंदरूनी रक्तस्राव",
        "संदिग्ध खाना/गोलियां सबूत के रूप में इकट्ठा करें (दस्ताने पहनें)",
        "जानबूझकर ज़हर देना अपराध है — FIR दर्ज करें",
      ],
      mr: [
        "लक्षणे: अचानक उलटी, तोंडातून फेस, झटके, निळे हिरडे",
        "उंदराचे विष उशीरा परिणाम दाखवते (2-3 दिवस) — अंतर्गत रक्तस्राव",
        "संशयास्पद अन्न/गोळ्या पुरावा म्हणून गोळा करा (हातमोजे घाला)",
        "जाणूनबुजून विष देणे गुन्हा आहे — FIR दाखल करा",
      ],
    },
  },
  {
    emoji: "🐛",
    title: {
      en: "Maggot Wounds (Myiasis)",
      hi: "कीड़ों वाले घाव (मैगट)",
      mr: "अळ्यांच्या जखमा (मॅगट)",
    },
    summary: {
      en: "Very common in Mumbai summers. Pour saline water to drive out maggots. Don't use kerosene.",
      hi: "मुंबई की गर्मियों में बहुत आम। कीड़े निकालने के लिए नमक का पानी डालें। केरोसिन का उपयोग न करें।",
      mr: "मुंबईच्या उन्हाळ्यात अत्यंत सामान्य. अळ्या बाहेर काढण्यासाठी मिठाचे पाणी घाला. रॉकेल वापरू नका.",
    },
    tips: {
      en: [
        "Salt water (saline) drives out maggots from wounds",
        "Do NOT use turpentine, kerosene, or chemicals",
        "Cover wound after cleaning to prevent flies",
        "Contact Bombay SPCA or WSD for free treatment",
      ],
      hi: [
        "नमक का पानी (सेलाइन) घाव से कीड़ों को बाहर निकालता है",
        "तारपीन, केरोसिन या रसायन का उपयोग न करें",
        "सफाई के बाद मक्खियों से बचाने के लिए घाव ढकें",
        "मोफत इलाज के लिए Bombay SPCA या WSD से संपर्क करें",
      ],
      mr: [
        "मिठाचे पाणी (सलाईन) जखमेतून अळ्या बाहेर काढते",
        "तारपीन, रॉकेल किंवा रसायने वापरू नका",
        "स्वच्छतेनंतर माश्यांपासून बचावासाठी जखम झाका",
        "मोफत उपचारासाठी Bombay SPCA किंवा WSD शी संपर्क साधा",
      ],
    },
  },
  {
    emoji: "🤰",
    title: {
      en: "Pregnant or Nursing Dogs",
      hi: "गर्भवती या दूध पिलाने वाली कुत्तियां",
      mr: "गर्भवती किंवा स्तनपान करणाऱ्या कुत्र्या",
    },
    summary: {
      en: "Extra nutrition needed. Provide a safe sheltered area. Don't disturb during delivery.",
      hi: "अतिरिक्त पोषण ज़रूरी। सुरक्षित आश्रय वाली जगह दें। प्रसव के दौरान परेशान न करें।",
      mr: "अतिरिक्त पोषण आवश्यक. सुरक्षित आश्रय असलेली जागा द्या. प्रसूतीदरम्यान त्रास देऊ नका.",
    },
    tips: {
      en: [
        "Feed protein-rich food 2-3 times daily (eggs, chicken, paneer)",
        "Provide a quiet corner with cardboard box lined with cloth",
        "Nursing mothers need 2-3x normal food intake",
        "Never separate puppies from mother before 8 weeks",
      ],
      hi: [
        "प्रोटीन-युक्त खाना दिन में 2-3 बार दें (अंडे, चिकन, पनीर)",
        "कपड़े से ढका कार्डबोर्ड बॉक्स एक शांत कोने में रखें",
        "दूध पिलाने वाली मां को सामान्य से 2-3 गुना ज़्यादा खाना चाहिए",
        "8 हफ्ते से पहले कभी पिल्लों को मां से अलग न करें",
      ],
      mr: [
        "प्रथिनेयुक्त अन्न दिवसातून 2-3 वेळा द्या (अंडी, चिकन, पनीर)",
        "कपड्याने आच्छादित कार्डबोर्ड बॉक्स शांत कोपऱ्यात ठेवा",
        "स्तनपान करणाऱ्या मातांना सामान्यच्या 2-3 पट अन्न आवश्यक",
        "8 आठवड्यांपूर्वी कधीही पिल्लांना मातेपासून वेगळे करू नका",
      ],
    },
  },
  {
    emoji: "💩",
    title: {
      en: "Diarrhoea and Stomach Problems",
      hi: "दस्त और पेट की समस्याएं",
      mr: "जुलाब आणि पोटाच्या समस्या",
    },
    summary: {
      en: "Bloody diarrhoea = emergency. Mild cases: bland rice + chicken. Prevent dehydration with ORS.",
      hi: "खूनी दस्त = आपातकाल। हल्के मामले: सादा चावल + चिकन। ORS से निर्जलीकरण रोकें।",
      mr: "रक्तरंजित जुलाब = आणीबाणी. सौम्य: साधा भात + चिकन. ORS ने निर्जलीकरण टाळा.",
    },
    tips: {
      en: [
        "Bloody or black diarrhoea: URGENT — possible parvo or poisoning",
        "Bloated belly + visible ribs usually means heavy worm load",
        "ORS / Electral in water helps prevent dehydration",
        "Do NOT give human anti-diarrhoeal medicines to dogs",
      ],
      hi: [
        "खूनी या काला दस्त: तुरंत — पार्वो या ज़हर हो सकता है",
        "फूला पेट + दिखती पसलियां आमतौर पर भारी कीड़े का मतलब है",
        "ORS / इलेक्ट्रॉल पानी में मिलाकर निर्जलीकरण रोकता है",
        "कुत्तों को इंसानी दस्त-रोधी दवाई न दें",
      ],
      mr: [
        "रक्तरंजित किंवा काळा जुलाब: तातडी — पार्वो किंवा विष असू शकते",
        "फुगलेले पोट + दिसणाऱ्या बरगड्या म्हणजे सामान्यतः भरपूर जंत",
        "ORS / इलेक्ट्रॉल पाण्यात मिसळल्यास निर्जलीकरण टाळता येते",
        "कुत्र्यांना मानवी जुलाब-विरोधी औषधे देऊ नका",
      ],
    },
  },
  {
    emoji: "⚔️",
    title: {
      en: "Dog Fight Wounds",
      hi: "कुत्तों की लड़ाई के घाव",
      mr: "कुत्र्यांच्या भांडणाच्या जखमा",
    },
    summary: {
      en: "Bite puncture wounds look small but go deep. They almost always get infected without treatment.",
      hi: "काटने के पंक्चर घाव छोटे दिखते हैं लेकिन गहरे होते हैं। बिना इलाज लगभग हमेशा संक्रमित होते हैं।",
      mr: "चावल्याच्या पंक्चर जखमा लहान दिसतात पण खोल असतात. उपचाराशिवाय जवळजवळ नेहमीच संक्रमित होतात.",
    },
    tips: {
      en: [
        "Clean with saline (1 tsp salt in 1L boiled cooled water)",
        "Swelling after 2-3 days = abscess forming, needs vet drainage",
        "Neck/chest/abdomen bites can cause internal damage",
        "Never put hands between two fighting dogs — use noise or water",
      ],
      hi: [
        "सेलाइन से साफ करें (1 चम्मच नमक 1 लीटर उबले ठंडे पानी में)",
        "2-3 दिन बाद सूजन = फोड़ा बन रहा है, डॉक्टर से निकासी ज़रूरी",
        "गर्दन/छाती/पेट के काटने से अंदरूनी नुकसान हो सकता है",
        "दो लड़ते कुत्तों के बीच कभी हाथ न डालें — आवाज़ या पानी का उपयोग करें",
      ],
      mr: [
        "सलाईनने स्वच्छ करा (1 चमचा मीठ 1 लीटर उकळलेल्या थंड पाण्यात)",
        "2-3 दिवसांनंतर सूज = गळू तयार होत आहे, पशुवैद्यकाकडून काढणे आवश्यक",
        "मान/छाती/पोटावरील चावे अंतर्गत नुकसान करू शकतात",
        "दोन भांडणाऱ्या कुत्र्यांमध्ये कधीही हात घालू नका — आवाज किंवा पाणी वापरा",
      ],
    },
  },
  {
    emoji: "😤",
    title: {
      en: "Dealing with Aggressive Strays",
      hi: "आक्रामक आवारा कुत्तों से निपटना",
      mr: "आक्रमक भटक्या कुत्र्यांशी सामना",
    },
    summary: {
      en: "Most strays aren't aggressive. Stop, stand still sideways, avoid eye contact. Never run.",
      hi: "ज़्यादातर आवारा कुत्ते आक्रामक नहीं होते। रुकें, बग़ल में खड़े हों, आंख न मिलाएं। कभी न भागें।",
      mr: "बहुतेक भटके कुत्रे आक्रमक नसतात. थांबा, बाजूला उभे राहा, डोळ्यांत पाहू नका. कधीही पळू नका.",
    },
    tips: {
      en: [
        "Running triggers chase instinct — stop and stand your ground",
        "Dogs are more territorial at night — carry a torch",
        "Aggression usually comes from fear or pain, not malice",
        "Report genuinely dangerous dogs to local ABC centre",
      ],
      hi: [
        "भागने से पीछा करने की प्रवृत्ति जागती है — रुकें और डटे रहें",
        "कुत्ते रात में ज़्यादा क्षेत्रीय होते हैं — टॉर्च रखें",
        "आक्रामकता आमतौर पर डर या दर्द से होती है, दुष्टपणामुळे नाही",
        "सच में खतरनाक कुत्तों की सूचना स्थानीय ABC केंद्र को दें",
      ],
      mr: [
        "पळण्याने पाठलाग करण्याची वृत्ती जागते — थांबा आणि ठाम राहा",
        "कुत्रे रात्री जास्त प्रादेशिक असतात — टॉर्च ठेवा",
        "आक्रमकता सामान्यतः भीती किंवा वेदनेमुळे असते, दुष्टपणामुळे नाही",
        "खरोखर धोकादायक कुत्र्यांची माहिती स्थानिक ABC केंद्राला द्या",
      ],
    },
  },
];

const EXTERNAL_LINKS = [
  { url: "https://www.vosd.in/faqs/", label: "VOSD Rescue FAQs" },
  { url: "https://jaagruti.org/first-aid-for-dogs/", label: "Jaagruti: First Aid for Dogs" },
  { url: "https://thebetterindia.com/328239/animal-rescue-and-rehabilitation-centres-in-india/", label: "Animal Rescue & Rehab Centres (Better India)" },
  { url: "https://in.virbac.com/all-diseases", label: "Dog Diseases Guide (Virbac)" },
  { url: "https://cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/listofveDrugs.pdf", label: "List of Veterinary Drugs (CDSCO)" },
  { url: "https://lbb.in/mumbai/animal-shelters-mumbai/", label: "Animal Shelters in Mumbai (LBB)" },
  { url: "https://supertails.com/collections/dog-medicines", label: "Dog Medicines (Supertails)" },
  { url: "https://peepalfarm.org/animal-rescue-training", label: "Animal Rescue Training (Peepal Farm)" },
  { url: "https://www.animalscharities.co.uk/animal-charities-in-india.html", label: "Animal Charities in India" },
  { url: "https://vetstudy.journeywithasr.com/p/veterinary-drug-index-pdf.html", label: "Veterinary Drug Index" },
  { url: "https://helplocal.in/blog/best-foods-for-street-dogs/", label: "Best Foods for Street Dogs" },
  { url: "https://legalbots.in/blog/how-to-report-animal-abuse-in-india", label: "How to Report Animal Abuse" },
  { url: "https://www.caninebible.com/homemade-dog-treat-recipes/", label: "Homemade Dog Treat Recipes" },
  { url: "https://www.woofdoctor.vet/calming-music/", label: "Calming Music for Dogs" }
];

export default function LearnPage() {
  const { language, t } = useLanguage();

  return (
    <main className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-2xl">←</Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-[var(--color-warm-700)]">
            {t("home.learn")}
          </h1>
          <p className="text-sm text-gray-500">{t("learn.subtitle")}</p>
        </div>
        <LanguageSelector compact />
      </div>

      {/* Offline Notice */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-sm text-blue-700 mb-6">
        📱 {t("learn.offline_notice")}
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
                    {guide.title[language] || guide.title.en}
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {guide.summary[language] || guide.summary.en}
                  </p>
                </div>
              </div>
            </summary>
            <div className="px-4 pb-4 border-t border-gray-50 pt-3">
              <ul className="space-y-2">
                {(guide.tips[language] || guide.tips.en).map((tip, j) => (
                  <li key={j} className="flex gap-2 text-sm text-gray-600">
                    <span className="text-[var(--color-warm-400)]">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        ))}
      </div>

      {/* External Resources */}
      <div className="mt-8">
        <h2 className="text-lg font-bold text-[var(--color-warm-700)] mb-3">
          {t("learn.resources_title")}
        </h2>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <ul className="divide-y divide-gray-100">
            {EXTERNAL_LINKS.map((link, i) => (
              <li key={i}>
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 hover:bg-gray-50 transition-colors flex items-center justify-between text-sm text-[var(--color-warm-600)]"
                >
                  <span>{link.label}</span>
                  <span className="text-gray-400">↗</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Emergency Banner */}
      <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-center">
        <div className="font-semibold text-red-700 text-sm mb-1">
          🚨 {t("learn.emergency_title")}
        </div>
        <a
          href="tel:1962"
          className="text-red-600 font-bold text-lg underline"
        >
          {t("learn.emergency_helpline")}: 1962
        </a>
      </div>
    </main>
  );
}
