import { useState } from "react";
import type { Assessment } from "./types";
import type { Api } from "./api";
import { Assignment, MappingSelect, RagBatchUpload } from "./Admin";
import type { Catalog } from "./Admin";
import { useResource } from "./hooks";
import {
  ActionForm,
  Chip,
  DataState,
  Empty,
  Field,
  Modal,
  Panel,
  Stat,
} from "./ui";
import SkillPicker from "./SkillPicker";
import type { SkillOption } from "./SkillPicker";
type Source = {
  source_id: string;
  title: string;
  skill_ids: string[];
  chunk_count: number;
  version: string;
  ingestion_status: string;
  synthetic_only: boolean;
};
type Inventory = {
  issues?: { workbook: string; sheet: string; reason: string; key?: string }[];
  limitations?: string[];
  counts?: Record<string, Record<string, number>>;
  changed?: number;
};
export default function SourcePages({
  api,
  catalog,
  refresh,
  page = "overview",
  provider = "mock",
}: {
  api: Api;
  catalog: Catalog;
  refresh: () => void;
  page?: string;
  provider?: string;
}) {
  const source = useResource<{
    local_rag_sources?: Source[];
    reason: string;
    missing_finance_skill_references?: number;
  }>(api, "/sources/status");
  const [report, setReport] = useState<Inventory | null>(null);
  const businessFunction = page === "finance" ? "Finance" : "DataOps";
  const filtered = {
    ...catalog,
    roles: catalog.roles.filter(
      (r) => r.business_function === businessFunction,
    ),
    mappings: catalog.mappings.filter((m) =>
      catalog.roles.some(
        (r) => r.id === m.role_id && r.business_function === businessFunction,
      ),
    ),
  };
  if (page === "administration")
    return (
      <AssessmentAdministration api={api} catalog={catalog} refresh={refresh} />
    );
  return (
    <>
      <div className="stats">
        <Stat
          label="Generation provider"
          value={provider}
          note="Questions always require SME review"
        />
        <Stat
          label="Role mappings"
          value={
            page === "finance" || page === "dataops"
              ? filtered.mappings.length
              : catalog.mappings.length
          }
          note="Source-linked role expectations"
        />
      </div>
      {(page === "overview" || page === "sources" || page === "finance") && (
        <Panel title="Workbook source integration">
          <p>
            Validate official mappings and question-bank eligibility.
            Unsupported records remain pending.
          </p>
          <div className="actions">
            <ActionForm
              label="Validate source inventory"
              onSubmit={async () =>
                setReport(await api<Inventory>("/data/inventory"))
              }
            >
              <span />
            </ActionForm>
            <ActionForm
              label="Import workbook mappings"
              onSubmit={async () => {
                setReport(await api<Inventory>("/data/import", "POST"));
              }}
            >
              <span />
            </ActionForm>
          </div>
          {report && (
            <>
              <p role="status">
                {report.changed === undefined
                  ? "Validation complete"
                  : `Import complete: ${report.changed} records updated. Refresh to load mappings.`}
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Workbook</th>
                      <th>Sheet</th>
                      <th>Reference</th>
                      <th>Action required</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.issues
                      ?.filter(
                        (i) =>
                          page !== "finance" || i.workbook.includes("finance"),
                      )
                      .map((i, n) => (
                        <tr key={n}>
                          <td>{i.workbook}</td>
                          <td>{i.sheet}</td>
                          <td>{i.key ?? "—"}</td>
                          <td>{i.reason}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              <details>
                <summary>Policy and source limitations</summary>
                {report.limitations?.map((l) => (
                  <p key={l}>{l}</p>
                ))}
              </details>
            </>
          )}
        </Panel>
      )}
      {page === "overview" && <EngagementAdmin api={api} />}
      {page === "overview" && (
        <Panel title="Your L&D workspace">
          <p>
            Use Finance or DataOps/RD to prepare question drafts. Review the
            question bank before assigning assessments. Training Mappings shows
            validated recommendations and missing policy.
          </p>
          <DataState state={source}>
            {(s) => <p className="source-note">{s.reason}</p>}
          </DataState>
        </Panel>
      )}
      {page === "dataops" && (
        <>
          <RagBatchUpload api={api} />
          <SourceMappings api={api} />
        </>
      )}
      {(page === "finance" || page === "dataops") && (
        <Panel title="Generate question drafts">
          <p>
            {page === "finance"
              ? "Uses validated Finance role/skill mappings and approved question-bank context."
              : "Uses retrieved chunks from approved local SOP documents."}{" "}
            Drafts require SME approval.
          </p>
          {provider === "mock" && (
            <p className="source-note">
              Mock exercises are synthetic and do not establish company
              provenance.
            </p>
          )}
          <ActionForm
            label="Generate drafts"
            onSubmit={(d) =>
              api("/questions/generate", "POST", {
                role_skill_map_id: Number(d.get("mapping")),
                question_count: Number(d.get("count")),
                difficulty: d.get("difficulty"),
                require_approved_sop: page === "dataops",
              })
            }
          >
            <Field label="Role and skill">
              <MappingSelect catalog={filtered} />
            </Field>
            <div className="form-grid">
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
              <Field label="Difficulty">
                <select name="difficulty">
                  <option>Easy</option>
                  <option>Moderate</option>
                  <option>Difficult</option>
                </select>
              </Field>
            </div>
            {page === "dataops" && (
              <label className="check">
                <input type="checkbox" checked disabled readOnly />
                Require approved SOP
              </label>
            )}
          </ActionForm>
          <Panel title={`${businessFunction} mapping overview`}>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Role</th>
                    <th>Skill</th>
                    <th>Target</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.mappings.map((m) => (
                    <tr key={m.id}>
                      <td>
                        {
                          catalog.roles.find((r) => r.id === m.role_id)
                            ?.role_name
                        }
                      </td>
                      <td>
                        {
                          catalog.skills.find((s) => s.id === m.skill_id)
                            ?.source_key
                        }{" "}
                        —{" "}
                        {catalog.skills.find((s) => s.id === m.skill_id)?.name}
                      </td>
                      <td>
                        {m.target_label ?? m.target_level ?? "Not expected"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </Panel>
      )}
      {page === "sources" && <SourceMappings api={api} />}
    </>
  );
}
export function SourceMappings({ api }: { api: Api }) {
  const [version, setVersion] = useState(0),
    [selected, setSelected] = useState<Source | null>(null),
    [ids, setIds] = useState<string[]>([]),
    [confirm, setConfirm] = useState(false);
  const sources = useResource<{ local_rag_sources?: Source[] }>(
    api,
    "/sources/status",
    version,
  );
  const registry = useResource<{ skills: SkillOption[] }>(
    api,
    "/rag/source-registry",
    version,
  );
  return (
    <Panel title="Source governance">
      <DataState state={sources}>
        {(data) => {
          const grouped = [
            ...new Set(data.local_rag_sources?.map((s) => s.source_id)),
          ].map((id) => {
            const rows = data.local_rag_sources!.filter(
              (s) => s.source_id === id,
            );
            return {
              ...rows[0],
              skill_ids: [...new Set(rows.flatMap((s) => s.skill_ids))],
              chunk_count: rows.reduce((n, s) => n + s.chunk_count, 0),
              version: rows.map((s) => s.version).join(", "),
            };
          });
          return grouped.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Skills</th>
                    <th>Chunks / versions</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {grouped.map((s) => (
                    <tr key={s.source_id}>
                      <td>
                        {s.source_id} — {s.title}
                      </td>
                      <td>
                        {s.skill_ids.map((id) => (
                          <div key={id}>
                            {id} —{" "}
                            {registry.data?.skills.find(
                              (k) => k.skill_id === id,
                            )?.skill_name ?? "Name unavailable"}
                          </div>
                        ))}
                      </td>
                      <td>
                        {s.chunk_count}
                        <small>{s.version}</small>
                      </td>
                      <td>
                        <Chip>{s.ingestion_status}</Chip>
                      </td>
                      <td>
                        <button
                          disabled={
                            s.ingestion_status !== "Ingested" ||
                            s.synthetic_only
                          }
                          onClick={() => {
                            setSelected(s);
                            setIds(s.skill_ids);
                            setConfirm(false);
                          }}
                        >
                          Edit skill mapping
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty>
              No local documents ingested. Upload approved documents from
              DataOps/RD.
            </Empty>
          );
        }}
      </DataState>
      {selected && (
        <Modal
          title={`Edit skill mapping · ${selected.source_id}`}
          close={() => setSelected(null)}
        >
          <DataState state={registry}>
            {(data) => (
              <SkillPicker
                skills={data.skills}
                selected={ids}
                change={(value) => {
                  setIds(value);
                  setConfirm(false);
                }}
                label="Mapped skills"
              />
            )}
          </DataState>
          <p>Current: {selected.skill_ids.join(", ")}</p>
          <p>Proposed: {ids.join(", ") || "Select at least one skill"}</p>
          <p>Content, chunk IDs and document versions will be preserved.</p>
          <ActionForm
            label="Confirm mapping change"
            onSubmit={(d) => {
              if (!confirm || !ids.length)
                return Promise.reject(
                  Error("Review and confirm the proposed mapping first."),
                );
              return api(
                `/rag/sources/${encodeURIComponent(selected.source_id)}/skills`,
                "PATCH",
                {
                  skill_ids: ids,
                  expected_skill_ids: selected.skill_ids,
                  comment: d.get("comment"),
                  confirmed: true,
                },
              );
            }}
            success={() => {
              setSelected(null);
              setVersion((v) => v + 1);
            }}
          >
            <Field label="Reason for change">
              <textarea
                name="comment"
                required
                minLength={3}
                maxLength={1000}
              />
            </Field>
            <label className="check">
              <input
                type="checkbox"
                checked={confirm}
                onChange={(e) => setConfirm(e.target.checked)}
              />
              I confirm the old and new mapping above.
            </label>
          </ActionForm>
        </Modal>
      )}
    </Panel>
  );
}

function AssessmentAdministration({
  api,
  catalog,
  refresh,
}: {
  api: Api;
  catalog: Catalog;
  refresh: () => void;
}) {
  const state = useResource<Assessment[]>(api, "/assessments");
  return (
    <>
      <Assignment api={api} catalog={catalog} refresh={refresh} />
      <Panel title="Assessment progress">
        <DataState state={state}>
          {(rows) =>
            rows.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Associate</th>
                      <th>Status</th>
                      <th>Questions</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id}>
                        <td>
                          {catalog.users.find((u) => u.id === r.employee_id)
                            ?.full_name ?? "Unavailable"}
                        </td>
                        <td>
                          <Chip>{r.status}</Chip>
                        </td>
                        <td>{r.total_questions}</td>
                        <td>
                          {r.score_percentage === null
                            ? "Not submitted"
                            : `${r.score_percentage}%`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty>
                No assessments assigned. Select an associate and an approved
                question pool above.
              </Empty>
            )
          }
        </DataState>
      </Panel>
    </>
  );
}

function EngagementAdmin({ api }: { api: Api }) {
  return (
    <details className="card">
      <summary>Progress and achievements administration</summary>
      <ActionForm
        label="Publish quest"
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
        <p>
          Rewards measure engagement only and cannot change official
          proficiency.
        </p>
        <Field label="Quest title">
          <input name="title" required maxLength={200} />
        </Field>
        <Field label="Description">
          <textarea name="description" required maxLength={2000} />
        </Field>
        <div className="form-grid">
          <Field label="Activity">
            <select name="event">
              <option value="assessment.submitted">Submit assessments</option>
              <option value="evidence.submitted">Submit evidence</option>
            </select>
          </Field>
          <Field label="Required activities">
            <input
              name="count"
              type="number"
              required
              min="1"
              max="100"
              defaultValue="1"
            />
          </Field>
          <Field label="XP reward">
            <input
              name="xp"
              type="number"
              required
              min="0"
              max="1000"
              defaultValue="0"
            />
          </Field>
          <Field label="Function">
            <select name="function">
              <option value="">All functions</option>
              <option>Finance</option>
              <option>DataOps</option>
            </select>
          </Field>
        </div>
      </ActionForm>
    </details>
  );
}
