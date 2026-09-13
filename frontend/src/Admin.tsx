import { mappingName } from "./catalog";
import { useState } from "react";
import type { Api } from "./api";
import type { Mapping, Role, Skill, User } from "./types";
import { useResource } from "./hooks";
import { ActionForm, Chip, DataState, Empty, Field, Panel, Stat } from "./ui";
export interface Catalog {
  roles: Role[];
  skills: Skill[];
  mappings: Mapping[];
  users: User[];
}
export function MappingSelect({
  catalog,
  name = "mapping",
  employee,
  id,
}: {
  catalog: Catalog;
  name?: string;
  employee?: number;
  id?: string;
}) {
  return (
    <select id={id} name={name} required defaultValue="">
      <option value="" disabled>
        Select a mapped skill
      </option>
      {catalog.mappings
        .filter(
          (m) =>
            m.is_expected &&
            m.target_level !== null &&
            (!employee ||
              m.role_id ===
                catalog.users.find((u) => u.id === employee)?.job_role_id),
        )
        .map((m) => (
          <option value={m.id} key={m.id}>
            {mappingName(catalog, m.id)} · {m.target_label ?? `Level ${m.target_level}`}
          </option>
        ))}
    </select>
  );
}
export function Assignment({
  api,
  catalog,
  refresh,
}: {
  api: Api;
  catalog: Catalog;
  refresh: () => void;
}) {
  const [employee, setEmployee] = useState(0);
  return (
    <Panel title="Assign an assessment">
      <p className="muted">
        Only approved questions for the employee’s role and target level are
        eligible.
      </p>
      <ActionForm
        label="Assign assessment"
        success={refresh}
        onSubmit={(d) =>
          api("/assessments", "POST", {
            employee_id: Number(d.get("employee")),
            role_skill_map_id: Number(d.get("mapping")),
            question_count: Number(d.get("count")),
          })
        }
      >
        <div className="form-grid">
          <Field label="Employee">
            <select
              required
              name="employee"
              value={employee || ""}
              onChange={(e) => setEmployee(Number(e.target.value))}
            >
              <option value="" disabled>
                Select employee
              </option>
              {catalog.users
                .filter((u) => u.role === "employee")
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Mapped skill">
            <MappingSelect
              key={employee}
              catalog={catalog}
              employee={employee}
            />
          </Field>
          <Field label="Question count">
            <input
              name="count"
              type="number"
              min="1"
              max="20"
              defaultValue="20"
              required
            />
          </Field>
        </div>
      </ActionForm>
    </Panel>
  );
}
export default function Admin({
  api,
  catalog,
  refresh,
}: {
  api: Api;
  catalog: Catalog;
  refresh: () => void;
}) {
  const source = useResource<{
    status: string;
    missing_finance_skill_references?: number;
    reason: string;
    approved_sop_available: boolean;
  }>(api, "/sources/status");
  const [validation, setValidation] = useState<unknown>(),
    [context, setContext] = useState<unknown>(),
    [filter, setFilter] = useState("");
  return (
    <>
      <div className="stats">
        <Stat
          label="Business functions"
          value={new Set(catalog.roles.map((r) => r.business_function)).size}
          note="Finance and DataOps in one workspace"
        />
        <Stat
          label="Role mappings"
          value={catalog.mappings.length}
          note="Existing database mappings"
        />
        <Stat
          label="Generation provider"
          value="Mock"
          note="Deterministic synthetic exercises"
        />
      </div>
      <DataState state={source}>
        {(s) => (
          <div className="warning">
            <strong>Source acceptance requires review</strong>
            <p>{s.reason}</p>
            <p>
              Missing Finance references:{" "}
              {s.missing_finance_skill_references ?? "Unavailable"} · Approved
              SOP documents:{" "}
              {s.approved_sop_available ? "Available" : "Not available"}
            </p>
          </div>
        )}
      </DataState>
      <div className="two-col">
        <Panel title="Workbook source integration">
          <p>Original Finance and RD workbooks supply mappings and eligible questions. Unsupported records remain pending source validation.</p>
          <ActionForm label="Validate source inventory" onSubmit={async () => setValidation(await api("/data/inventory"))} success={() => {}}><span /></ActionForm>
          <ActionForm label="Import workbook mappings" onSubmit={async () => setValidation(await api("/data/import", "POST"))} success={refresh}><span /></ActionForm>
        </Panel>
        <Panel title="Generate question drafts">
          <p className="muted">
            Drafts require SME approval before assignment. Mock content does not
            claim company SOP provenance.
          </p>
          <ActionForm
            label="Generate drafts"
            success={refresh}
            onSubmit={(d) =>
              api("/questions/generate", "POST", {
                role_skill_map_id: Number(d.get("mapping")),
                question_count: Number(d.get("count")),
                require_approved_sop: d.get("sop") === "on",
              })
            }
          >
            <Field label="Role and skill">
              <MappingSelect catalog={catalog} />
            </Field>
            <Field label="Questions">
              <input
                required
                name="count"
                type="number"
                min="1"
                max="5"
                defaultValue="3"
              />
            </Field>
            <label className="check">
              <input type="checkbox" name="sop" />
              Require approved SOP (currently unavailable)
            </label>
          </ActionForm>
        </Panel>
        <Panel title="Source validation">
          <p>
            Validate workbook structure and unresolved references without
            changing supplied data.
          </p>
          <ActionForm
            label="Run validation"
            onSubmit={async () => setValidation(await api("/data/validate"))}
          >
            <span />
          </ActionForm>
          {validation !== undefined && (
            <pre className="source-output">
              {JSON.stringify(validation, null, 2)}
            </pre>
          )}
        </Panel>
      </div>
      <Panel
        title="Mapping overview"
        action={
          <select
            aria-label="Filter mappings by function"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">All functions</option>
            {[...new Set(catalog.roles.map((r) => r.business_function))].map(
              (f) => (
                <option key={f}>{f}</option>
              ),
            )}
          </select>
        }
      >
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Skill</th>
                <th>Role</th>
                <th>Function</th>
                <th>Target</th>
                <th>Expected</th>
              </tr>
            </thead>
            <tbody>
              {catalog.mappings
                .filter(
                  (m) =>
                    !filter ||
                    catalog.roles.find((r) => r.id === m.role_id)
                      ?.business_function === filter,
                )
                .map((m) => {
                  const r = catalog.roles.find((r) => r.id === m.role_id);
                  return (
                    <tr key={m.id}>
                      <td>
                        {catalog.skills.find((s) => s.id === m.skill_id)?.name}
                        <small>{catalog.skills.find((s) => s.id === m.skill_id)?.category}</small>
                      </td>
                      <td>{r?.role_name}</td>
                      <td>{r?.business_function}</td>
                      <td>
                        {m.target_level === null
                          ? "Not Expected"
                          : m.target_label ?? `Level ${m.target_level}`}
                      </td>
                      <td>
                        <Chip>
                          {m.is_expected ? "expected" : "not_expected"}
                        </Chip>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
        {!catalog.mappings.length && (
          <Empty>
            No mappings are configured. No workbook references are inferred.
          </Empty>
        )}
      </Panel>
      <Assignment api={api} catalog={catalog} refresh={refresh} />
      <div className="two-col">
        <Panel title="Inspect Finance source context">
          <p className="muted">
            Exact supplied names are required. DataOps production retrieval and
            approved document RAG remain unavailable.
          </p>
          <ActionForm
            label="Retrieve context"
            onSubmit={async (d) =>
              setContext(
                await api(
                  `/rag/context?${new URLSearchParams({ role_name: String(d.get("role")), skill_name: String(d.get("skill")) })}`,
                ),
              )
            }
          >
            <Field label="Exact Finance role name">
              <input required name="role" />
            </Field>
            <Field label="Exact Finance skill name">
              <input required name="skill" />
            </Field>
          </ActionForm>
          {context !== undefined && (
            <pre className="source-output">
              {JSON.stringify(context, null, 2)}
            </pre>
          )}
        </Panel>
        <Panel title="Publish SkillQuest">
          <p className="muted">
            Engagement rewards count future activity. XP never changes
            proficiency.
          </p>
          <ActionForm
            label="Publish quest"
            success={refresh}
            onSubmit={(d) =>
              api("/quests", "POST", {
                title: d.get("title"),
                description: d.get("description"),
                event_type: d.get("event"),
                required_count: Number(d.get("count")),
                xp_reward: Number(d.get("xp")),
                business_function: d.get("function") || null,
              })
            }
          >
            <Field label="Quest title">
              <input name="title" required maxLength={200} />
            </Field>
            <Field label="Description">
              <textarea name="description" required maxLength={2000} />
            </Field>
            <div className="form-grid">
              <Field label="Qualifying activity">
                <select name="event">
                  <option value="assessment.submitted">
                    Submit assessments
                  </option>
                  <option value="evidence.submitted">Submit evidence</option>
                </select>
              </Field>
              <Field label="Required activities">
                <input
                  required
                  name="count"
                  type="number"
                  min="1"
                  max="100"
                  defaultValue="1"
                />
              </Field>
              <Field label="Engagement XP reward">
                <input
                  required
                  name="xp"
                  type="number"
                  min="0"
                  max="1000"
                  defaultValue="0"
                />
              </Field>
              <Field label="Function">
                <select name="function">
                  <option value="">All functions</option>
                  {[
                    ...new Set(catalog.roles.map((r) => r.business_function)),
                  ].map((f) => (
                    <option key={f}>{f}</option>
                  ))}
                </select>
              </Field>
            </div>
          </ActionForm>
        </Panel>
      </div>
    </>
  );
}
