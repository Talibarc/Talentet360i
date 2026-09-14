import type { Catalog } from "./Admin";
export function mappingName(c: Catalog, id: number) {
  const m = c.mappings.find((m) => m.id === id);
  return m
    ? `${c.skills.find((s) => s.id === m.skill_id)?.source_key ? c.skills.find((s) => s.id === m.skill_id)?.source_key + " — " : ""}${c.skills.find((s) => s.id === m.skill_id)?.name ?? "Unknown skill"} · ${c.roles.find((r) => r.id === m.role_id)?.role_name ?? "Unknown role"}`
    : "Mapping unavailable — pending source validation.";
}
