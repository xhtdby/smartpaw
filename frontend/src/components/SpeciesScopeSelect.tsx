"use client";

import type { SpeciesFilter } from "@/lib/species";

type SpeciesOption = {
  value: SpeciesFilter;
  label: string;
};

export function SpeciesScopeSelect({
  value,
  onChange,
  options,
  label = "Animal",
}: {
  value: SpeciesFilter;
  onChange: (value: SpeciesFilter) => void;
  options: SpeciesOption[];
  label?: string;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-semibold text-gray-500 mb-1">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as SpeciesFilter)}
        className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm font-medium text-gray-700 focus:border-[var(--color-warm-400)] focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
