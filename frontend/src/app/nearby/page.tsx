"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchNearby, type ShelterVet } from "@/lib/api";
import { LanguageSelector, useLanguage } from "@/lib/language";

type PageLanguage = "en" | "hi" | "mr";
type ResourceType = "all" | "rescue" | "official" | "advice";
type SpeciesFilter = "all" | "dog" | "cat" | "cow" | "other";

const COPY: Record<
  PageLanguage,
  {
    title: string;
    subtitle: string;
    safetyTitle: string;
    safetyBody: string;
    aiTitle: string;
    aiBody: string;
    quickLinks: Array<{ label: string; href: string }>;
    filters: Record<ResourceType, string>;
    speciesFilters: Record<SpeciesFilter, string>;
    sections: Record<Exclude<ResourceType, "all">, string>;
    typeLabels: Record<Exclude<ResourceType, "all">, string>;
    scopeLabels: Record<string, string>;
    hoursLabel: string;
    areaLabel: string;
    notesLabel: string;
    actions: {
      call: string;
      website: string;
      map: string;
      email: string;
    };
    emergency24: string;
    loading: string;
    empty: string;
    error: string;
  }
> = {
  en: {
    title: "Find Help",
    subtitle: "Verified rescue, official, and emergency-support resources",
    safetyTitle: "Human safety first",
    safetyBody: "If a person is in danger, bitten, trapped in traffic, or the rescue scene is unsafe, call 112 first.",
    aiTitle: "How to use this page",
    aiBody: "IndieAid is AI guidance. These contacts are the hands-on next step when an animal needs transport, treatment, reporting, or poison support.",
    quickLinks: [
      {
        label: "Emergency Vet Near Me",
        href: "https://www.google.com/maps/search/?api=1&query=24+hour+veterinary+hospital+near+me",
      },
      {
        label: "AWBI Directory",
        href: "https://awbi.gov.in/view/index/list-of-awo",
      },
      {
        label: "WHO Rabies Guidance",
        href: "https://www.who.int/news-room/fact-sheets/detail/rabies%EF%BB%BF",
      },
    ],
    filters: {
      all: "All",
      rescue: "Hands-on Rescue",
      official: "Official",
      advice: "Advice / Poison",
    },
    speciesFilters: {
      all: "All animals",
      dog: "Dogs",
      cat: "Cats",
      cow: "Cows",
      other: "Other",
    },
    sections: {
      rescue: "Hands-on Rescue",
      official: "Official Reporting and Directories",
      advice: "Advice and Poison Support",
    },
    typeLabels: {
      rescue: "RESCUE",
      official: "OFFICIAL",
      advice: "ADVICE",
    },
    scopeLabels: {
      regional: "Regional",
      national: "India-wide",
      global: "Global",
    },
    hoursLabel: "Availability",
    areaLabel: "Coverage",
    notesLabel: "Limits",
    actions: {
      call: "Call",
      website: "Open Site",
      map: "Map",
      email: "Email",
    },
    emergency24: "24x7",
    loading: "Loading verified resources...",
    empty: "No resources matched this filter.",
    error: "Could not load help resources. Please try again.",
  },
  hi: {
    title: "मदद खोजें",
    subtitle: "सत्यापित रेस्क्यू, आधिकारिक और आपातकालीन सहायता संसाधन",
    safetyTitle: "पहले मानव सुरक्षा",
    safetyBody: "अगर कोई व्यक्ति खतरे में है, काट लिया गया है, ट्रैफिक में फंसा है, या रेस्क्यू स्थल असुरक्षित है, तो पहले 112 पर कॉल करें।",
    aiTitle: "इस पेज का उपयोग कैसे करें",
    aiBody: "IndieAid AI-आधारित मार्गदर्शन देता है। जब किसी जानवर को ले जाने, इलाज, शिकायत या ज़हर संबंधी मदद की ज़रूरत हो, तो यह पेज अगला व्यावहारिक कदम देता है।",
    quickLinks: [
      {
        label: "पास का इमरजेंसी वेट",
        href: "https://www.google.com/maps/search/?api=1&query=24+hour+veterinary+hospital+near+me",
      },
      {
        label: "AWBI निर्देशिका",
        href: "https://awbi.gov.in/view/index/list-of-awo",
      },
      {
        label: "WHO रेबीज़ मार्गदर्शन",
        href: "https://www.who.int/news-room/fact-sheets/detail/rabies%EF%BB%BF",
      },
    ],
    filters: {
      all: "सभी",
      rescue: "रेस्क्यू",
      official: "आधिकारिक",
      advice: "सलाह / ज़हर",
    },
    speciesFilters: {
      all: "सभी जानवर",
      dog: "कुत्ते",
      cat: "बिल्लियां",
      cow: "गाय/मवेशी",
      other: "अन्य",
    },
    sections: {
      rescue: "मैदानी रेस्क्यू सहायता",
      official: "आधिकारिक शिकायत और निर्देशिकाएँ",
      advice: "सलाह और ज़हर सहायता",
    },
    typeLabels: {
      rescue: "रेस्क्यू",
      official: "आधिकारिक",
      advice: "सलाह",
    },
    scopeLabels: {
      regional: "क्षेत्रीय",
      national: "पूरे भारत में",
      global: "वैश्विक",
    },
    hoursLabel: "उपलब्धता",
    areaLabel: "सेवा क्षेत्र",
    notesLabel: "सीमाएँ",
    actions: {
      call: "कॉल",
      website: "वेबसाइट",
      map: "मैप",
      email: "ईमेल",
    },
    emergency24: "24x7",
    loading: "सत्यापित संसाधन लोड हो रहे हैं...",
    empty: "इस फ़िल्टर में कोई संसाधन नहीं मिला।",
    error: "मदद संसाधन लोड नहीं हो सके। कृपया फिर से कोशिश करें।",
  },
  mr: {
    title: "मदत शोधा",
    subtitle: "सत्यापित रेस्क्यू, अधिकृत आणि आपत्कालीन सहाय्य संसाधने",
    safetyTitle: "सर्वप्रथम मानवी सुरक्षितता",
    safetyBody: "जर एखादी व्यक्ती धोक्यात असेल, चावा लागला असेल, वाहतुकीत अडकली असेल, किंवा रेस्क्यूची जागा असुरक्षित असेल, तर आधी 112 वर कॉल करा.",
    aiTitle: "हे पान कसे वापरावे",
    aiBody: "IndieAid हे AI-आधारित मार्गदर्शन आहे. प्राण्याला वाहतूक, उपचार, तक्रार नोंदवणे किंवा विषबाधा मदत हवी असल्यास हे पान पुढची प्रत्यक्ष पायरी दाखवते.",
    quickLinks: [
      {
        label: "जवळचा इमरजेंसी वेट",
        href: "https://www.google.com/maps/search/?api=1&query=24+hour+veterinary+hospital+near+me",
      },
      {
        label: "AWBI निर्देशिका",
        href: "https://awbi.gov.in/view/index/list-of-awo",
      },
      {
        label: "WHO रेबीज मार्गदर्शन",
        href: "https://www.who.int/news-room/fact-sheets/detail/rabies%EF%BB%BF",
      },
    ],
    filters: {
      all: "सर्व",
      rescue: "रेस्क्यू",
      official: "अधिकृत",
      advice: "सल्ला / विष",
    },
    speciesFilters: {
      all: "सर्व प्राणी",
      dog: "कुत्रे",
      cat: "मांजरी",
      cow: "गाय/जनावरे",
      other: "इतर",
    },
    sections: {
      rescue: "प्रत्यक्ष रेस्क्यू मदत",
      official: "अधिकृत तक्रार आणि निर्देशिका",
      advice: "सल्ला आणि विष सहाय्य",
    },
    typeLabels: {
      rescue: "रेस्क्यू",
      official: "अधिकृत",
      advice: "सल्ला",
    },
    scopeLabels: {
      regional: "प्रादेशिक",
      national: "भारतभर",
      global: "जागतिक",
    },
    hoursLabel: "उपलब्धता",
    areaLabel: "सेवा क्षेत्र",
    notesLabel: "मर्यादा",
    actions: {
      call: "कॉल",
      website: "वेबसाइट",
      map: "नकाशा",
      email: "ईमेल",
    },
    emergency24: "24x7",
    loading: "सत्यापित संसाधने लोड होत आहेत...",
    empty: "या फिल्टरमध्ये कोणतेही संसाधन सापडले नाही.",
    error: "मदत संसाधने लोड होऊ शकली नाहीत. कृपया पुन्हा प्रयत्न करा.",
  },
};

const TYPE_STYLES: Record<Exclude<ResourceType, "all">, string> = {
  rescue: "bg-emerald-50 text-emerald-700 border-emerald-200",
  official: "bg-blue-50 text-blue-700 border-blue-200",
  advice: "bg-amber-50 text-amber-700 border-amber-200",
};

function buildMapLink(resource: ShelterVet): string | null {
  if (!resource.address) return null;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(resource.address)}`;
}

export default function NearbyPage() {
  const { language } = useLanguage();
  const copy = COPY[(language as PageLanguage) || "en"];
  const [resources, setResources] = useState<ShelterVet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterType, setFilterType] = useState<ResourceType>("all");
  const [filterSpecies, setFilterSpecies] = useState<SpeciesFilter>("all");

  useEffect(() => {
    const species = new URLSearchParams(window.location.search).get("species");
    if (species === "dog" || species === "cat" || species === "cow" || species === "other") {
      setFilterSpecies(species);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchNearby(
          filterType === "all" ? undefined : filterType,
          filterSpecies === "all" ? undefined : filterSpecies
        );
        setResources(data);
      } catch {
        setError(copy.error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filterType, filterSpecies, copy.error]);

  const groupedResources = useMemo(() => {
    const order: Array<Exclude<ResourceType, "all">> = ["rescue", "official", "advice"];
    return order
      .map((type) => ({
        type,
        title: copy.sections[type],
        items: resources.filter((item) => item.type === type),
      }))
      .filter((group) => group.items.length > 0);
  }, [copy.sections, resources]);

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

      <div className="space-y-3 mb-5">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="font-semibold text-red-700 text-sm mb-1">{copy.safetyTitle}</div>
          <p className="text-sm text-red-700">{copy.safetyBody}</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="font-semibold text-amber-800 text-sm mb-1">{copy.aiTitle}</div>
          <p className="text-sm text-amber-800">{copy.aiBody}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-5">
        {copy.quickLinks.map((link) => (
          <a
            key={link.label}
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm font-medium text-gray-700 hover:border-[var(--color-warm-400)] hover:text-[var(--color-warm-700)] transition-colors"
          >
            {link.label}
          </a>
        ))}
      </div>

      <div className="flex gap-2 mb-5 overflow-x-auto">
        {(Object.keys(copy.filters) as ResourceType[]).map((type) => (
          <button
            key={type}
            onClick={() => setFilterType(type)}
            className={`px-4 py-2 rounded-full text-sm whitespace-nowrap transition-colors ${
              filterType === type
                ? "bg-[var(--color-warm-500)] text-white"
                : "bg-white border border-gray-200 text-gray-600"
            }`}
          >
            {copy.filters[type]}
          </button>
        ))}
      </div>

      <div className="flex gap-2 mb-5 overflow-x-auto">
        {(Object.keys(copy.speciesFilters) as SpeciesFilter[]).map((species) => (
          <button
            key={species}
            onClick={() => setFilterSpecies(species)}
            className={`px-4 py-2 rounded-full text-sm whitespace-nowrap transition-colors ${
              filterSpecies === species
                ? "bg-[var(--color-sage-500)] text-white"
                : "bg-white border border-gray-200 text-gray-600"
            }`}
          >
            {copy.speciesFilters[species]}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-gray-500 py-8">{copy.loading}</p>}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      {!loading && !error && groupedResources.length === 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-sm text-gray-600">
          {copy.empty}
        </div>
      )}

      <div className="space-y-6">
        {groupedResources.map((group) => (
          <section key={group.type} className="space-y-3">
            <h2 className="text-lg font-semibold text-[var(--color-warm-700)]">{group.title}</h2>
            <div className="space-y-3">
              {group.items.map((resource) => {
                const mapLink = buildMapLink(resource);
                return (
                  <article
                    key={resource.id}
                    className="bg-white rounded-xl p-4 shadow-sm border border-gray-100"
                  >
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span
                        className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                          TYPE_STYLES[resource.type as Exclude<ResourceType, "all">]
                        }`}
                      >
                        {copy.typeLabels[resource.type as Exclude<ResourceType, "all">]}
                      </span>
                      <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
                        {copy.scopeLabels[resource.scope] || resource.scope}
                      </span>
                      {resource.emergency_24hr && (
                        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-red-100 text-red-700">
                          {copy.emergency24}
                        </span>
                      )}
                      {resource.species?.map((species) => (
                        <span
                          key={species}
                          className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700"
                        >
                          {copy.speciesFilters[species as SpeciesFilter] || species}
                        </span>
                      ))}
                    </div>

                    <h3 className="font-semibold text-gray-900">{resource.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {copy.areaLabel}: {resource.service_area}
                    </p>
                    <p className="text-sm text-gray-700 mt-3">{resource.summary}</p>

                    {resource.address && (
                      <p className="text-xs text-gray-500 mt-3">{resource.address}</p>
                    )}

                    {resource.hours && (
                      <p className="text-xs text-gray-500 mt-1">
                        {copy.hoursLabel}: {resource.hours}
                      </p>
                    )}

                    {resource.notes && (
                      <p className="text-xs text-gray-500 mt-2">
                        {copy.notesLabel}: {resource.notes}
                      </p>
                    )}

                    <div className="flex flex-wrap gap-2 mt-4">
                      {resource.phone && (
                        <a
                          href={`tel:${resource.phone}`}
                          className="bg-[var(--color-sage-500)] text-white rounded-lg px-3 py-2 text-sm font-medium"
                        >
                          {copy.actions.call}
                        </a>
                      )}
                      {resource.website && (
                        <a
                          href={resource.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-[var(--color-warm-500)] text-white rounded-lg px-3 py-2 text-sm font-medium"
                        >
                          {copy.actions.website}
                        </a>
                      )}
                      {mapLink && (
                        <a
                          href={mapLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-blue-500 text-white rounded-lg px-3 py-2 text-sm font-medium"
                        >
                          {copy.actions.map}
                        </a>
                      )}
                      {resource.email && (
                        <a
                          href={`mailto:${resource.email}`}
                          className="bg-gray-100 text-gray-700 rounded-lg px-3 py-2 text-sm font-medium"
                        >
                          {copy.actions.email}
                        </a>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
