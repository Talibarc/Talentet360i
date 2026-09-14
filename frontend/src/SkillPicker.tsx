import { useState } from "react";
import { Chip, Field } from "./ui";
export type SkillOption = { skill_id: string; skill_name: string };
export default function SkillPicker({
  skills,
  selected,
  change,
  label,
}: {
  skills: SkillOption[];
  selected: string[];
  change: (ids: string[]) => void;
  label: string;
}) {
  const [search, setSearch] = useState("");
  return (
    <fieldset className="skill-picker" aria-label={label}>
      <legend>{label}</legend>
      <Field label="Search skills">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Skill ID or name"
        />
      </Field>
      <div className="selected-skills" aria-live="polite">
        {selected.map((id) => (
          <Chip key={id}>
            {id} —{" "}
            {skills.find((s) => s.skill_id === id)?.skill_name ?? "Unavailable"}
          </Chip>
        ))}
      </div>
      <div className="skill-options">
        {skills
          .filter((s) =>
            `${s.skill_id} ${s.skill_name}`
              .toLowerCase()
              .includes(search.toLowerCase()),
          )
          .map((s) => (
            <label className="skill-option" key={s.skill_id}>
              <input
                type="checkbox"
                checked={selected.includes(s.skill_id)}
                onChange={(e) =>
                  change(
                    e.target.checked
                      ? [...selected, s.skill_id]
                      : selected.filter((id) => id !== s.skill_id),
                  )
                }
              />
              <span>
                <strong>{s.skill_id}</strong> — {s.skill_name}
              </span>
            </label>
          ))}
      </div>
    </fieldset>
  );
}
