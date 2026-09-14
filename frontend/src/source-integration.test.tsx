import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TniView } from "./Employee";
import Reviewer from "./Reviewer";
import { mappingName } from "./catalog";
import type { Api } from "./api";

it("keeps a workbook result without policy pending and withholds a recommendation", async () => {
  const api = vi.fn().mockResolvedValue({
    skills_assessed: 1, target_met: 0, development_needed: 0,
    skill_gaps: [{assessment_id: 99, skill_name: "Workbook skill", current_level: null,
      target_level: 3, skill_gap: null, official_confirmed_level: null,
      review_status: "pending_review", learning_status: "Workbook-mapped resources",
      learning_resources: [],
      detail: {summary: "Result pending policy validation.", development_focus: "Validate policy.",
        next_steps: ["Contact L&D."], limitations: ["No inferred level."]}}],
    unassessed_skills: [{skill_name: "RD skill", target_level: 2, target_label: "Moderate",
      learning_resources: []}],
  }) as unknown as Api;
  render(<TniView api={api} userId={37} />);
  expect(await screen.findByText("Pending policy validation")).toBeInTheDocument();
  expect(screen.getByText("Not confirmed")).toBeInTheDocument();
  expect(screen.queryByText("Level 0")).not.toBeInTheDocument();
  expect(screen.queryByText("Supplied resource")).not.toBeInTheDocument();
  expect(screen.getByText(/Target Moderate/)).toBeInTheDocument();
  expect(screen.getByText("Mapping unavailable — pending source validation.")).toBeInTheDocument();
});

it("does not invent a missing catalog mapping", () => {
  expect(mappingName({roles: [], skills: [], mappings: [], users: []}, 123))
    .toBe("Mapping unavailable — pending source validation.");
});

it("keeps an empty DataOps review queue focused on the reviewer workflow", async () => {
  const api = vi.fn().mockResolvedValue([]) as unknown as Api;
  render(<Reviewer api={api} refresh={vi.fn()} businessFunction="DataOps" />);
  expect(await screen.findByText(/No DataOps questions in this queue/)).toBeInTheDocument();
  expect(screen.queryByText(/Luna|RAG/i)).not.toBeInTheDocument();
});
