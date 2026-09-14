import { lazy, Suspense, useMemo, useState } from "react";

import {
  Bell,
  BookOpen,
  CheckSquare,
  ClipboardList,
  Database,
  GraduationCap,
  LayoutDashboard,
  Menu,
  ShieldCheck,
  Target,
  Users,
  X,
} from "lucide-react";

import { createApi } from "./api";

import type { Identity, User, Role, Skill, Mapping } from "./types";

import type { Catalog } from "./Admin";

import Admin from "./SourcePages";
import Intelligence, { MappingCoverage } from "./Intelligence";

import Reviewer from "./Reviewer";

import Employee from "./Employee";

import Manager from "./Manager";

const Leader = lazy(() => import("./Leader"));

import Governance, { Notifications } from "./Governance";

import { useResource } from "./hooks";

import { Chip, DataState, Empty, Field, Panel } from "./ui";

import "./App.css";

const labels: Record<string, string> = {
  admin: "Admin",
  ld: "L&D",
  reviewer: "SME / Reviewer",
  employee: "Associate",
  manager: "Manager",
  leader: "Leader",
};

const ldItems: {id: string; label: string; icon: typeof Database; roles: string[]; functions?: string[]}[] = [
  ...[["finance", "Create Questions"]].map(([id, label]) => ({
    id, label, icon: Database, roles: ["ld"], functions: ["Finance"],
  })),
  // DataOps starts with its document workflow, followed by question creation.
  ...[["sources", "Sources"], ["dataops", "Create Questions"]].map(([id, label]) => ({
    id, label, icon: Database, roles: ["ld"], functions: ["DataOps"],
  })),
  ...[["bank", "Question Bank"], ["administration", "Assessments"], ["training-admin", "Training Mappings"]].map(([id, label]) => ({
    id, label, icon: Database, roles: ["ld"],
  })),
];

const items: {id: string; label: string; icon: typeof Database; roles: string[]; functions?: string[]}[] = [
  ...ldItems,
  ...[
    ["home", "My Assessments"],
    ["results", "My Results"],
    ["skills", "My Skills"],
    ["training", "My Training Plan"],
    ["quests", "Progress and achievements"],
    ["evidence", "My evidence"],
  ].map(([id, label]) => ({ id, label, icon: BookOpen, roles: ["employee"] })),
  ...[
    ["review", "Review Queue"],
    ["question-review", "Question Review"],
    ["review-history", "Approved/Rejected History"],
  ].map(([id, label]) => ({
    id,
    label,
    icon: CheckSquare,
    roles: ["reviewer"],
  })),
  ...[
    ["manager", "Team Overview"],
    ["team-gaps", "Team Skill Gaps"],
    ["team-progress", "Assessment Progress"],
    ["team-training", "TNI and Course Recommendations"],
    ["team-employee", "Employee drill-down"],
  ].map(([id, label]) => ({ id, label, icon: Users, roles: ["manager"] })),
  ...[
    ["leader", "Skill Distribution"],
    ["org-gaps", "Organizational Gaps"],
    ["readiness", "Readiness"],
    ["movement", "Skill movement/trends"],
    ["indicators", "Decision indicators"],
  ].map(([id, label]) => ({
    id,
    label,
    icon: LayoutDashboard,
    roles: ["leader"],
  })),
  {
    id: "notifications",
    label: "Notifications",
    icon: Bell,
    roles: Object.keys(labels),
  },
  {
    id: "audit",
    label: "Audit History",
    icon: ShieldCheck,
    roles: Object.keys(labels).filter(r=>r!=="employee"),
  },
];

export default function App() {
  const anonymous = useMemo(() => createApi(null), []),
    identities = useResource<{ provider: string; identities: Identity[] }>(
      anonymous,
      "/demo/identities",
    );

  const [id, setId] = useState<number | null>(null);

  return (
    <DataState state={identities}>
      {(data) =>
        id === null ? (
          <main className="login">
            <div className="brand">
              <GraduationCap />
              <strong>
                Talent360<span>i</span>
              </strong>
            </div>
            <div className="login-intro">
              <span className="eyebrow">Capability. Confidence. Growth.</span>
              <h1>
                Your people’s potential,
                <br />
                made visible.
              </h1>
              <p>
                One development workspace for Finance and DataOps. Assess
                skills, guide learning, and recognize confirmed progress.
              </p>
              <div className="journey">
                <span>
                  <ClipboardList /> Assess
                </span>
                <span>
                  <Users /> Confirm
                </span>
                <span>
                  <Target /> Develop
                </span>
              </div>
            </div>
            <Panel title="Enter the demo workspace">
              <p className="muted">
                Select a seeded synthetic identity. Local demo selection is not
                production authentication.
              </p>
              {data.identities.length ? (
                <div className="identity-grid">
                  {data.identities.filter(i=>i.role!=="admin" && !!i.business_function).map((i) => (
                    <button
                      key={i.id}
                      aria-label={`${labels[i.role] ?? i.role} ${i.business_function ?? "All functions"}`}
                      onClick={() => setId(i.id)}
                    >
                      <strong>{labels[i.role] ?? i.role}</strong>
                      <small>{i.business_function ?? "All functions"}</small>
                    </button>
                  ))}
                </div>
              ) : (
                <Empty>
                  No seeded demo identities found. Seed them in mock mode, then
                  enable demo identities for this local environment.
                </Empty>
              )}
              <div className="source-note">Local demo workspace              </div>
            </Panel>
          </main>
        ) : (
          <Workspace
            key={id}
            id={id}
            provider={data.provider}
            identities={data.identities.filter(i=>i.role!=="admin" && !!i.business_function)}
            switchIdentity={setId}
          />
        )
      }
    </DataState>
  );
}

function Workspace({
  id,
  identities,
  provider,
  switchIdentity,
}: {
  id: number;
  identities: Identity[];
  provider: string;
  switchIdentity: (id: number | null) => void;
}) {
  const api = useMemo(() => createApi(id), [id]),
    [version, setVersion] = useState(0),
    [page, setPage] = useState(() => window.location.hash.slice(1)),
    [mobile, setMobile] = useState(false);

  const me = useResource<User>(api, "/me", version),
    count = useResource<{ unread_count: number }>(
      api,
      "/notifications/unread-count",
      version,
    );

  const roles = useResource<Role[]>(api, "/roles", version),
    skills = useResource<Skill[]>(api, "/skills", version),
    mappings = useResource<Mapping[]>(api, "/role-skill-maps", version),
    users = useResource<User[]>(api, "/users", version);

  const refresh = () => {
    setVersion((v) => v + 1);
  };

  const catalog: Catalog = {
    roles: roles.data ?? [],
    skills: skills.data ?? [],
    mappings: mappings.data ?? [],
    users: users.data ?? [],
  };

  return (
    <DataState state={me}>
      {(user) => {
        const nav = items.filter((i) => i.roles.includes(user.role) && (!i.functions || i.functions.includes(user.business_function ?? ""))),
          active = nav.find((i) => i.id === page) ?? nav[0];
        return (
          <div className="app-shell">
            <a href="#main" className="skip-link">
              Skip to content
            </a>
            <aside className={mobile ? "sidebar open" : "sidebar"}>
              <div className="brand">
                <GraduationCap />
                <strong>
                  Talent360<span>i</span>
                </strong>
                <button
                  className="mobile-only"
                  aria-label="Close navigation"
                  onClick={() => setMobile(false)}
                >
                  <X size={18} />
                </button>
              </div>
              <p className="nav-caption">DEVELOPMENT WORKSPACE</p>
              <nav aria-label="Main navigation">
                {nav.map((i) => (
                  <button
                    key={i.id}
                    className={active.id === i.id ? "active" : ""}
                    aria-current={active.id === i.id ? "page" : undefined}
                    onClick={() => {
                      setPage(i.id);
                      window.history.replaceState(null, "", `#${i.id}`);
                      setMobile(false);
                    }}
                  >
                    <i.icon size={19} />
                    {i.label}
                  </button>
                ))}
              </nav>
              <div className="sidebar-footer">
                <ShieldCheck size={20} />
                <strong>Built on trusted progress</strong>
                <p>
                  Human-reviewed content.
                  <br />
                  Manager-confirmed proficiency.
                </p>
                <span>LOCAL DEMO</span>
              </div>
            </aside>
            {mobile && (
              <button
                className="nav-backdrop"
                aria-label="Dismiss navigation"
                onClick={() => setMobile(false)}
              />
            )}
            <div className="main-shell">
              <header className="topbar">
                <button
                  className="mobile-only"
                  aria-label="Open navigation"
                  onClick={() => setMobile(true)}
                >
                  <Menu />
                </button>
                <span className="breadcrumb">
                  Workspace <span>/</span> {active.label}
                </span>
                <div className="header-actions">
                  <Chip>{user.business_function ?? "All functions"}</Chip>
                  <button
                    aria-label={`Notifications: ${count.data?.unread_count ?? 0} unread`}
                    onClick={() => setPage("notifications")}
                  >
                    <Bell size={19} />
                    <span className="count">
                      {count.data?.unread_count ?? 0}
                    </span>
                  </button>
                  <Field label="Demo identity">
                    <select
                      aria-label="Demo identity"
                      value={id}
                      onChange={(e) => switchIdentity(Number(e.target.value))}
                    >
                      {identities.map((i) => (
                        <option value={i.id} key={i.id}>
                          {labels[i.role]} ·{" "}
                          {i.business_function ?? "All functions"}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
              </header>
              <main id="main" tabIndex={-1}>
                <div className="page-heading">
                  <div>
                    <span className="eyebrow">
                      {labels[user.role]} ·{" "}
                      {user.business_function ?? "Finance & DataOps"}
                    </span>
                    <h1>{active.label}</h1>
                    <p>
                      Trusted skills. Meaningful development. Human oversight.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setVersion((v) => v + 1);
                    }}
                  >
                    Refresh
                  </button>
                </div>
                {[roles, skills, mappings, users].some((s) => s.error) ? (
                  <Panel title="Workspace data unavailable">
                    <p role="alert">
                      {
                        [roles, skills, mappings, users].find((s) => s.error)
                          ?.error
                      }
                    </p>
                    <button onClick={() => window.location.reload()}>
                      Retry connection
                    </button>
                  </Panel>
                ) : [roles, skills, mappings, users].some((s) => s.loading) ? (
                  <p role="status">Loading workspace…</p>
                ) : (
                  <div key={`${active.id}-${version}`} className="page-content">
                    {[
                      "overview",
                      "finance",
                      "dataops",
                      "sources",
                      "administration",
                    ].includes(active.id) ? (
                      <Admin
                        api={api}
                        catalog={catalog}
                        refresh={refresh}
                        page={active.id}
                        provider={provider}
                      />
                    ) : [
                        "review",
                        "question-review",
                        "review-history",
                        "bank",
                      ].includes(active.id) ? (
                      <Reviewer
                        api={api}
                        refresh={refresh}
                        initialStatus={
                          active.id === "review-history"
                            ? "approved"
                            : "pending_review"
                        }
                        businessFunction={user.business_function}
                        catalog={catalog}
                        canManage={user.role === "ld"}
                      />
                    ) : ["home", "results", "evidence", "quests"].includes(
                        active.id,
                      ) ? (
                      <Employee
                        api={api}
                        user={user}
                        catalog={catalog}
                        page={active.id}
                        refresh={refresh}
                      />
                    ) : ["manager", "team-progress", "team-employee"].includes(
                        active.id,
                      ) ? (
                      <Manager
                        api={api}
                        catalog={catalog}
                        refresh={refresh}
                        page={active.id}
                      />
                    ) : active.id === "leader" ? (
                      <Suspense
                        fallback={
                          <p role="status">Loading skill intelligence…</p>
                        }
                      >
                        <Leader api={api} catalog={catalog} />
                      </Suspense>
                    ) : active.id === "training-admin" ? (
                      <MappingCoverage api={api} />
                    ) : [
                        "skills",
                        "training",
                        "team-gaps",
                        "team-training",
                        "org-gaps",
                        "readiness",
                        "movement",
                        "indicators",
                      ].includes(active.id) ? (
                      <Intelligence
                        api={api}
                        role={user.role}
                        view={active.id}
                      />
                    ) : active.id === "notifications" ? (
                      <Notifications api={api} refresh={refresh} />
                    ) : (
                      <Governance api={api} businessFunction={user.business_function} />
                    )}
                  </div>
                )}
                <footer>
                  Talent360i · Question provenance is retained. Official levels
                  require manager confirmation. XP is engagement-only.
                </footer>
              </main>
            </div>
          </div>
        );
      }}
    </DataState>
  );
}
