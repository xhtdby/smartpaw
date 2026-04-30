export type SupportedSpecies = "dog" | "cat" | "cow" | "other";
export type SpeciesFilter = SupportedSpecies | "all";

export const SPECIES_OPTIONS: Array<{ value: SupportedSpecies; label: string; pluralLabel: string }> = [
  { value: "dog", label: "Dog", pluralLabel: "Dogs" },
  { value: "cat", label: "Cat", pluralLabel: "Cats" },
  { value: "cow", label: "Cow", pluralLabel: "Cows" },
  { value: "other", label: "Other animal", pluralLabel: "Other animals" },
];

export const SPECIES_FILTER_OPTIONS: Array<{ value: SpeciesFilter; label: string }> = [
  { value: "all", label: "All animals" },
  ...SPECIES_OPTIONS.map((option) => ({ value: option.value, label: option.pluralLabel })),
];

const KNOWN_SPECIES = new Set<SupportedSpecies>(["dog", "cat", "cow", "other"]);

export function normalizeSpecies(value?: string | null): SupportedSpecies {
  if (!value) return "other";
  const lower = value.toLowerCase();
  return KNOWN_SPECIES.has(lower as SupportedSpecies) ? (lower as SupportedSpecies) : "other";
}

export function normalizeSpeciesFilter(value?: string | null): SpeciesFilter {
  if (!value || value === "all") return "all";
  return normalizeSpecies(value);
}

export function getSpeciesLabel(value?: string | null): string {
  const species = normalizeSpecies(value);
  return SPECIES_OPTIONS.find((option) => option.value === species)?.label ?? "Animal";
}

export function getSpeciesPluralLabel(value?: string | null): string {
  const species = normalizeSpecies(value);
  return SPECIES_OPTIONS.find((option) => option.value === species)?.pluralLabel ?? "Animals";
}

export function getSpeciesScopeLabel(value: SpeciesFilter): string {
  if (value === "all") return "All animals";
  return getSpeciesPluralLabel(value);
}

export function isDogSpecies(value?: string | null): boolean {
  return normalizeSpecies(value) === "dog";
}

export function getNearbyHref(value?: string | null): string {
  if (!value || value === "all") return "/nearby";
  return `/nearby?species=${normalizeSpecies(value)}`;
}

export function getLearnHref(value?: string | null): string {
  if (!value || value === "all") return "/learn";
  return `/learn?species=${normalizeSpecies(value)}`;
}

export function getFirstAidHref(value?: string | null): string {
  if (!value || value === "all") return "/first-aid-kit";
  return `/first-aid-kit?species=${normalizeSpecies(value)}`;
}

export function getSpeciesFromContext(context?: unknown): SupportedSpecies | undefined {
  if (!context || typeof context !== "object") return undefined;
  const candidate = (context as { species?: unknown }).species;
  return typeof candidate === "string" ? normalizeSpecies(candidate) : undefined;
}

export function getSpeciesFromTriage(triage?: unknown): SupportedSpecies | undefined {
  if (!triage || typeof triage !== "object") return undefined;
  const candidate = (triage as { species?: unknown }).species;
  return typeof candidate === "string" ? normalizeSpecies(candidate) : undefined;
}

export function getSpeciesSearchQuery(value?: string | null): string {
  const species = normalizeSpecies(value);
  if (species === "cow") return "livestock veterinary hospital near me";
  if (species === "cat") return "24 hour cat veterinary hospital near me";
  if (species === "dog") return "24 hour veterinary hospital near me";
  return "animal rescue near me";
}

export function getPhotoThreadLabel(value?: string | null): string {
  return `${getSpeciesLabel(value)} photo`;
}
