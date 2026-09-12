import { it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Leader from "./Leader";
import Employee from "./Employee";
import type { Api } from "./api";
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: () => <div>Distribution chart</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));
it("leader uses confirmed aggregate endpoint and sends all six filters without personal ranking", async () => {
  const api = vi
    .fn()
    .mockResolvedValue({
      basis: "manager_confirmed_only",
      total_confirmed_records: 1,
      groups: [
        {
          skill: "Synthetic skill",
          level: 0,
          count: 1,
          gap_count: 1,
          total_gap: 2,
        },
      ],
    }) as unknown as Api;
  render(
    <Leader
      api={api}
      catalog={{
        users: [],
        mappings: [],
        roles: [
          { id: 88, role_name: "Synthetic role", business_function: "Finance" },
        ],
        skills: [{ id: 99, name: "Synthetic skill" }],
      }}
    />,
  );
  await screen.findByText("Distribution chart");
  await userEvent.selectOptions(screen.getByLabelText("Function"), "Finance");
  await userEvent.selectOptions(screen.getByLabelText("Role"), "88");
  await userEvent.type(screen.getByLabelText("Team"), "Synthetic team");
  await userEvent.type(screen.getByLabelText("Hub"), "Synthetic hub");
  await userEvent.selectOptions(screen.getByLabelText("Skill"), "99");
  await userEvent.selectOptions(screen.getByLabelText("Level"), "0");
  await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/leader/aggregates?group_by=skill,level&function=Finance&role_id=88&team=Synthetic+team&hub=Synthetic+hub&skill_id=99&level=0",
      "GET",
      undefined,
      expect.any(AbortSignal),
    ),
  );
  expect(screen.queryByText(/leaderboard/i)).not.toBeInTheDocument();
});
it("completed quest claims the returned quest ID and keeps proficiency separate", async () => {
  const api = vi.fn(async (path: string) =>
    path === "/quests"
      ? [
          {
            quest: {
              id: 888,
              title: "Synthetic quest",
              description: "Synthetic activity",
              required_count: 1,
              xp_reward: 20,
            },
            progress: 1,
            completed: true,
            claimed: false,
          },
        ]
      : path === "/xp"
        ? { xp_points: 10, affects_proficiency: false, awards: [] }
        : [],
  ) as unknown as Api;
  render(
    <Employee
      api={api}
      user={{
        id: 999,
        role: "employee",
        full_name: "Synthetic",
        business_function: "Finance",
        job_role_id: null,
        team: null,
        hub: null,
        xp_points: 10,
      }}
      catalog={{ users: [], roles: [], skills: [], mappings: [] }}
      page="quests"
      refresh={vi.fn()}
    />,
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Claim reward" }),
  );
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith("/quests/888/claim", "POST"),
  );
  expect(
    screen.getByText("XP never changes official proficiency"),
  ).toBeInTheDocument();
});
