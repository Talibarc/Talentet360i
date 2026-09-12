import { lazy, Suspense, useMemo, useState } from "react";

import {
  Bell,
  BookOpen,
  CheckSquare,
  ClipboardList,
  Database,
  FileCheck,
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

import Admin from "./Admin";

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
  employee: "Employee",
  manager: "Manager",
  leader: "Leader",
};

const items = [
  {
    id: "admin",
    label: "Sources & generation",
    icon: Database,
    roles: ["admin", "ld"],
  },

  {
    id: "review",
    label: "Question review",
    icon: CheckSquare,
    roles: ["admin", "ld", "reviewer"],
  },

  {
    id: "home",
    label: "My development",
    icon: LayoutDashboard,
    roles: ["employee"],
  },

  {
    id: "learning",
    label: "Skills & learning",
    icon: BookOpen,
    roles: ["employee"],
  },

  {
    id: "evidence",
    label: "My evidence",
    icon: FileCheck,
    roles: ["employee"],
  },

  { id: "quests", label: "SkillQuest & XP", icon: Target, roles: ["employee"] },

  { id: "manager", label: "Team reviews", icon: Users, roles: ["manager"] },

  {
    id: "leader",
    label: "Skill intelligence",
    icon: LayoutDashboard,
    roles: ["leader", "admin", "ld"],
  },

  {
    id: "notifications",
    label: "Notifications",
    icon: Bell,
    roles: Object.keys(labels),
  },

  {
    id: "audit",
    label: "Governance & audit",
    icon: ShieldCheck,
    roles: Object.keys(labels),
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
                  {data.identities.map((i) => (
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
                  No synthetic identities found. Run backend/seed_demo.py with
                  LLM_PROVIDER=mock, then reload.
                </Empty>
              )}
              <div className="source-note">
                Mock mode · Synthetic exercises · No Luna connection
              </div>
            </Panel>
          </main>
        ) : (
          <Workspace
            key={id}
            id={id}
            identities={data.identities}
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
  switchIdentity,
}: {
  id: number;
  identities: Identity[];
  switchIdentity: (id: number | null) => void;
}) {
  const api = useMemo(() => createApi(id), [id]),
    [version, setVersion] = useState(0),
    [page, setPage] = useState(""),
    [mobile, setMobile] = useState(false);

  const me = useResource<User>(api, "/me"),
    count = useResource<{ unread_count: number }>(
      api,
      "/notifications/unread-count",
      version,
    );

  const roles = useResource<Role[]>(api, "/roles"),
    skills = useResource<Skill[]>(api, "/skills"),
    mappings = useResource<Mapping[]>(api, "/role-skill-maps"),
    users = useResource<User[]>(api, "/users");

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
        const nav = items.filter((i) => i.roles.includes(user.role)),
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
                <span>LOCAL SYNTHETIC DEMO</span>
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
                    {active.id === "admin" ? (
                      <Admin api={api} catalog={catalog} refresh={refresh} />
                    ) : active.id === "review" ? (
                      <Reviewer api={api} refresh={refresh} />
                    ) : ["home", "learning", "evidence", "quests"].includes(
                        active.id,
                      ) ? (
                      <Employee
                        api={api}
                        user={user}
                        catalog={catalog}
                        page={active.id}
                        refresh={refresh}
                      />
                    ) : active.id === "manager" ? (
                      <Manager api={api} catalog={catalog} refresh={refresh} />
                    ) : active.id === "leader" ? (
                      <Suspense
                        fallback={
                          <p role="status">Loading skill intelligence…</p>
                        }
                      >
                        <Leader api={api} catalog={catalog} />
                      </Suspense>
                    ) : active.id === "notifications" ? (
                      <Notifications api={api} refresh={refresh} />
                    ) : (
                      <Governance api={api} />
                    )}
                  </div>
                )}
                <footer>
                  Talent360i · Mock exercises are synthetic. Official levels
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
