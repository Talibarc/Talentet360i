import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import Employee, { TniView } from "./Employee";
import Reviewer from "./Reviewer";
import Manager from "./Manager";
import Governance, { Notifications } from "./Governance";
import Admin from "./Admin";
import { ActionForm, Modal } from "./ui";
import type { Api } from "./api";
import type { Catalog } from "./Admin";
const user = {
  id: 701,
  full_name: "Synthetic Person",
  role: "employee",
  business_function: "Finance",
  job_role_id: 801,
  team: "Demo team",
  hub: "Demo hub",
  xp_points: 0,
};
const catalog: Catalog = {
  users: [user],
  roles: [
    { id: 801, role_name: "Synthetic Analyst", business_function: "Finance" },
  ],
  skills: [{ id: 901, name: "Synthetic Practice" }],
  mappings: [
    {
      id: 601,
      role_id: 801,
      skill_id: 901,
      target_level: 0,
      is_expected: true,
      target_label: null,
    },
  ],
};
function mockApi(routes: Record<string, unknown>) {
  return vi.fn(async (path: string) => {
    if (!(path in routes)) throw Error(`Unexpected request ${path}`);
    return routes[path];
  }) as unknown as Api;
}
const assessment = {
  id: 501,
  employee_id: 701,
  role_skill_map_id: 601,
  status: "assigned",
  total_questions: 1,
  correct_answers: 0,
  score_percentage: null,
  achieved_level: null,
  xp_awarded: 0,
};
describe("role workflows", () => {
  it("allows local demo selection while Luna remains the configured provider", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      provider: "luna",
      identities: [{ id: 701, role: "employee", label: "Synthetic", business_function: "Finance" }],
    })));
    render(<App />);
    expect(await screen.findByRole("button", { name: "Employee Finance" })).toBeInTheDocument();
    expect(screen.getByText(/Generation provider: luna/)).toBeInTheDocument();
    expect(screen.getByText(/Generation provider: luna/)).toBeInTheDocument();
  });
  it("discovers identities dynamically and hides admin navigation for employees", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      const data: Record<string, unknown> = {
        "/api/demo/identities": {
          provider: "mock",
          identities: [
            {
              id: 701,
              role: "employee",
              label: "Synthetic",
              business_function: "Finance",
            },
          ],
        },
        "/api/me": user,
        "/api/roles": catalog.roles,
        "/api/skills": catalog.skills,
        "/api/role-skill-maps": catalog.mappings,
        "/api/users": [user],
        "/api/notifications/unread-count": { unread_count: 0 },
        "/api/assessments": [],
        "/api/evidence": [],
      };
      return new Response(JSON.stringify(data[path]));
    });
    render(<App />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Employee Finance" }),
    );
    expect(
      await screen.findByRole("heading", { name: "My development" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Sources & generation" }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText(/No assessment assigned yet/),
    ).toBeInTheDocument();
  });
  it("submits only employee-selected answers, never renders answer keys", async () => {
    const api = mockApi({
      "/assessments": [assessment],
      "/evidence": [],
      "/assessments/501": {
        assessment,
        questions: [
          {
            question_id: 301,
            question_text: "Choose a synthetic action",
            options: { A: "Observe", B: "Review", C: "Escalate", D: "Wait" },
            correct_answer: "B",
            explanation: "Hidden answer rationale",
          },
        ],
        review_status: "not_submitted",
      },
      "/assessments/501/submit": { status: "submitted" },
      "/assessments/501/start": { status: "in_progress" },
    });
    const refresh = vi.fn();
    render(
      <Employee
        api={api}
        user={user}
        catalog={catalog}
        page="home"
        refresh={refresh}
      />,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Start Assessment" }),
    );
    await screen.findByText("Choose a synthetic action");
    expect(api).toHaveBeenCalledWith("/assessments/501/start", "POST");
    expect(
      screen.queryByText("Hidden answer rationale"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit assessment" }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "A Observe" }));
    await userEvent.click(
      screen.getByRole("button", { name: "Submit assessment" }),
    );
    await waitFor(() =>
      expect(api).toHaveBeenCalledWith("/assessments/501/submit", "POST", {
        answers: [{ question_id: 301, selected_answer: "A" }],
      }),
    );
    expect(refresh).toHaveBeenCalled();
  });
  it("keeps zero levels and missing courses explicit in TNI", async () => {
    const api = mockApi({
      "/users/701/tni": {
        skills_assessed: 1,
        target_met: 1,
        development_needed: 0,
        unassessed_skills: [],
        skill_gaps: [
          {
            assessment_id: 501,
            skill_name: "Synthetic Practice",
            current_level: 0,
            target_level: 0,
            official_confirmed_level: null,
            review_status: "pending_review",
            learning_status: "unavailable",
            learning_resources: [],
            detail: {
              summary: "Synthetic summary",
              development_focus: "Review work",
              next_steps: ["Discuss with manager"],
              limitations: ["Synthetic only"],
            },
          },
        ],
      },
    });
    render(<TniView api={api} userId={701} />);
    expect(await screen.findByText("Not confirmed")).toBeInTheDocument();
    expect(screen.getAllByText("Level 0")).toHaveLength(2);
    expect(
      screen.getByText(/No course recommendations have been invented/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("reviewer approves a pending question with comments and can inspect history", async () => {
    const q = {
      id: 301,
      skill_id: 901,
      skill_level: 0,
      question_text: "Synthetic question",
      options: { A: "One", B: "Two", C: "Three", D: "Four" },
      correct_answer: "A",
      explanation: "Synthetic rationale",
      rag_source: "Synthetic mock",
      status: "pending_review",
    };
    const api = mockApi({
      "/questions": [q],
      "/questions/301/history": [
        {
          id: 201,
          revision: 4,
          action: "generated",
          created_at: "2026-09-12T00:00:00",
          actor_id: 99,
          snapshot: q,
        },
      ],
      "/questions/301/review": q,
    });
    render(<Reviewer api={api} refresh={vi.fn()} />);
    await userEvent.click(
      await screen.findByRole("button", { name: /Question 301/ }),
    );
    await screen.findByText("Synthetic rationale");
    await userEvent.type(
      screen.getByLabelText("Review comments"),
      "Approved synthetic draft",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record review" }),
    );
    await waitFor(() =>
      expect(api).toHaveBeenCalledWith("/questions/301/review", "PATCH", {
        status: "approved",
        review_comment: "Approved synthetic draft",
      }),
    );
    expect(await screen.findByText(/Revision 4/)).toBeInTheDocument();
  });
  it("evidence submission uses selected mappings and never invents IDs", async () => {
    const api = mockApi({ "/assessments": [], "/evidence": [] });
    render(
      <Employee
        api={api}
        user={user}
        catalog={catalog}
        page="evidence"
        refresh={vi.fn()}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Skill"), "601");
    await userEvent.type(
      screen.getByLabelText("Evidence title"),
      "Synthetic evidence",
    );
    await userEvent.type(
      screen.getByLabelText("Work performed and what it demonstrates"),
      "Synthetic work description",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Submit evidence" }),
    );
    await waitFor(() =>
      expect(api).toHaveBeenCalledWith("/evidence", "POST", {
        role_skill_map_id: 601,
        assessment_id: null,
        title: "Synthetic evidence",
        description: "Synthetic work description",
        url: null,
      }),
    );
  });
  it("manager send-back includes current revision and mandatory comments", async () => {
    const api = mockApi({
      "/manager/reviews": {
        results: [
          {
            assessment: {
              ...assessment,
              status: "submitted",
              achieved_level: 0,
              score_percentage: 100,
            },
            review: { revision: 7 },
          },
        ],
        evidence: [],
      },
      "/assessments": [],
      "/users/701/tni": {
        skills_assessed: 0,
        target_met: 0,
        development_needed: 0,
        skill_gaps: [],
        unassessed_skills: [],
      },
      "/assessments/501/history": { decisions: [] },
      "/evidence?employee_id=701": [],
      "/assessments/501/decision": {},
    });
    render(<Manager api={api} catalog={catalog} refresh={vi.fn()} />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Review result" }),
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Decision"),
      "send_back",
    );
    await userEvent.type(
      screen.getByLabelText("Manager comments"),
      "Please clarify the synthetic evidence",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record manager decision" }),
    );
    await waitFor(() =>
      expect(api).toHaveBeenCalledWith("/assessments/501/decision", "POST", {
        decision: "send_back",
        comment: "Please clarify the synthetic evidence",
        expected_revision: 7,
      }),
    );
  });
  it("notification marks only the displayed notice as read", async () => {
    const api = mockApi({
      "/notifications?unread_only=false": [
        {
          id: 411,
          title: "Review update",
          message: "Synthetic notice",
          created_at: "2026-09-12T00:00:00",
          read_at: null,
        },
      ],
      "/notifications/411/read": {},
    });
    render(<Notifications api={api} refresh={vi.fn()} />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Mark as read" }),
    );
    expect(api).toHaveBeenCalledWith("/notifications/411/read", "PATCH");
  });
  it("audit filters exact action and exposes source limitations", async () => {
    const api = mockApi({
      "/audit-events?limit=100&after_id=0&action=": [],
      "/audit-events?limit=100&after_id=0&action=evidence.submitted": [],
    });
    render(<Governance api={api} />);
    expect(screen.getByText(/13 Finance skill references/)).toBeInTheDocument();
    await userEvent.type(
      screen.getByLabelText("Exact event action"),
      "evidence.submitted",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Filter events" }),
    );
    await waitFor(() =>
      expect(api).toHaveBeenCalledWith(
        "/audit-events?limit=100&after_id=0&action=evidence.submitted",
        "GET",
        undefined,
        expect.any(AbortSignal),
      ),
    );
  });
  it("admin generation preserves numeric zero target and mock source warning", async () => {
    const api = mockApi({
      "/sources/status": {
        status: "needs_review",
        missing_finance_skill_references: 13,
        approved_sop_available: false,
        reason: "Synthetic mock",
      },
      "/questions/generate": [],
    });
    render(<Admin api={api} catalog={catalog} refresh={vi.fn()} />);
    await userEvent.selectOptions(
      screen.getByLabelText("Role and skill"),
      "601",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Generate drafts" }),
    );
    await waitFor(() =>
      expect(api).toHaveBeenCalledWith("/questions/generate", "POST", {
        role_skill_map_id: 601,
        question_count: 3,
        require_approved_sop: false,
      }),
    );
    expect(screen.getByText("Level 0")).toBeInTheDocument();
  });
  it("action errors remain visible and allow retry", async () => {
    const save = vi
      .fn()
      .mockRejectedValueOnce(Error("Record changed; refresh"))
      .mockResolvedValueOnce({});
    render(
      <ActionForm onSubmit={save}>
        <input aria-label="Required" required defaultValue="ready" />
      </ActionForm>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Record changed",
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Completed: Save.",
    );
  });
  it("modal has a named accessible close action", async () => {
    const close = vi.fn();
    render(
      <Modal title="History" close={close}>
        <p>Synthetic history</p>
      </Modal>,
    );
    await userEvent.click(
      within(screen.getByRole("dialog", { name: "History" })).getByRole(
        "button",
        { name: "Close dialog" },
      ),
    );
    expect(close).toHaveBeenCalled();
  });
});
