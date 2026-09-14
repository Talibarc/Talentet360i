import { it, expect, vi } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Intelligence from "./Intelligence";
import SourcePages, { SourceMappings } from "./SourcePages";
import SkillPicker from "./SkillPicker";
import type { Api } from "./api";
const empty = { roles: [], skills: [], users: [], mappings: [] };
it.each(["finance", "dataops"])("separates %s controls", async (page) => {
  const api = vi.fn(async (path: string) =>
    path === "/rag/source-registry"
      ? {
          sources: [],
          skills: [],
          limits: {
            maximum_files: 20,
            maximum_file_bytes: 1000,
            maximum_batch_bytes: 2000,
          },
        }
      : { local_rag_sources: [] },
  ) as unknown as Api;
  render(
    <SourcePages
      api={api}
      catalog={empty}
      refresh={vi.fn()}
      page={page}
      provider="luna"
    />,
  );
  expect(screen.queryByText(/luna/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Mock exercises/)).not.toBeInTheDocument();
  if (page === "finance") {
    expect(
      screen.queryByText("Use approved source documents only"),
    ).not.toBeInTheDocument();
  } else {
    expect(screen.getByText("Use approved source documents only")).toBeInTheDocument();
    expect(screen.queryByText("Add approved documents")).not.toBeInTheDocument();
  }
});
it("searches full skill labels and preserves explicit selections", async () => {
  const change = vi.fn();
  render(
    <SkillPicker
      skills={[
        { skill_id: "RD_PRO_01", skill_name: "Item Coding" },
        { skill_id: "RD_PRO_06", skill_name: "Char Population" },
      ]}
      selected={["RD_PRO_01"]}
      change={change}
      label="Skills"
    />,
  );
  await userEvent.type(screen.getByLabelText("Search skills"), "Char");
  await userEvent.click(screen.getByLabelText("RD_PRO_06 — Char Population"));
  expect(change).toHaveBeenCalledWith(["RD_PRO_01", "RD_PRO_06"]);
});
it("remapping requires explicit old/new confirmation and sends stable IDs", async () => {
  const api = vi.fn(async (path: string) =>
    path === "/rag/source-registry"
      ? {
          skills: [
            { skill_id: "A", skill_name: "Original" },
            { skill_id: "B", skill_name: "Replacement" },
          ],
        }
      : {
          local_rag_sources: [
            {
              source_id: "SOURCE",
              title: "Fixture",
              skill_ids: ["A"],
              chunk_count: 2,
              version: "same",
              ingestion_status: "Ingested",
            },
          ],
        },
  ) as unknown as Api;
  render(<SourceMappings api={api} />);
  await userEvent.click(await screen.findByText("Edit skill mapping"));
  const modal = within(screen.getByRole("dialog"));
  await userEvent.click(modal.getByLabelText("A — Original"));
  await userEvent.click(modal.getByLabelText("B — Replacement"));
  expect(modal.getByText("Current: Original")).toBeInTheDocument();
  expect(modal.getByText("Proposed: Replacement")).toBeInTheDocument();
  await userEvent.type(
    modal.getByLabelText("Reason for change"),
    "Correct mapping",
  );
  await userEvent.click(
    modal.getByText("I confirm the old and new mapping above."),
  );
  await userEvent.click(modal.getByText("Confirm mapping change"));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith("/rag/sources/SOURCE/skills", "PATCH", {
      skill_ids: ["B"],
      expected_skill_ids: ["A"],
      comment: "Correct mapping",
      confirmed: true,
    }),
  );
});
it.each(["employee", "manager", "ld", "leader"])(
  "renders %s intelligence with explicit pending states",
  async (role) => {
    const api = vi
      .fn()
      .mockResolvedValue({
        basis: "confirmed",
        records: [],
        groups: [],
        readiness: {},
        coverage: {
          expected_records: 0,
          validated_mappings: 0,
          validated_recommendations: 0,
        },
        limitations: ["Pending policy validation."],
      }) as unknown as Api;
    render(<Intelligence api={api} role={role} view="training" />);
    expect(
      await screen.findByText("Pending policy validation."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No expected skills in your scope/),
    ).toBeInTheDocument();
  },
);
