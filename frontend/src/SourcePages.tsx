import { useState } from "react";
import type { Assessment } from "./types";
import type { Api } from "./api";
import { Assignment, RoleSkillFields, RagBatchUpload } from "./Admin";
import type { Catalog } from "./Admin";
import { useResource } from "./hooks";
import { ActionForm, Chip, DataState, Empty, Field, Modal, Panel } from "./ui";
import SkillPicker from "./SkillPicker";
import type { SkillOption } from "./SkillPicker";
type Source = { source_id: string; title: string; skill_ids: string[]; chunk_count: number; version: string; ingestion_status: string; synthetic_only: boolean; };
type Inventory = { issues?: { reason: string }[]; changed?: number; };
export default function SourcePages({api, catalog, refresh, page = "finance", provider = "mock"}: {
  api: Api; catalog: Catalog; refresh: () => void; page?: string; provider?: string;
}) {
  const [report, setReport] = useState<Inventory | null>(null);
  const businessFunction = page === "finance" ? "Finance" : "DataOps";
  const filtered = {...catalog, roles: catalog.roles.filter(r=>r.business_function===businessFunction),
    mappings: catalog.mappings.filter(m=>catalog.roles.some(r=>r.id===m.role_id&&r.business_function===businessFunction))};
  if(page === "administration") return <AssessmentAdministration api={api} catalog={catalog} refresh={refresh} />;
  return <>
    {page === "sources" ? <><Panel title="Add approved documents"><p>Upload documents and confirm the skills they support.</p><RagBatchUpload api={api}/></Panel><SourceMappings api={api}/></> :
    <Panel title="Create Questions">
      <p>Generated questions will be sent for SME review.</p>
      {provider === "mock" && <p className="source-note">Demo only: practice questions are not company guidance.</p>}
      <ActionForm label="Generate Questions" onSubmit={d=>api("/questions/generate","POST",{
        role_skill_map_id:Number(d.get("mapping")),question_count:Number(d.get("count")),difficulty:d.get("difficulty"),require_approved_sop:page==="dataops"
      })}>
        <RoleSkillFields catalog={filtered}/>
        <div className="form-grid"><Field label="Number of questions"><input required name="count" type="number" min="1" max="5" defaultValue="3"/></Field>
        <Field label="Difficulty"><select name="difficulty" defaultValue="Moderate"><option>Easy</option><option>Moderate</option><option>Difficult</option></select></Field></div>
        {page === "dataops" && <label className="check"><input type="checkbox" checked disabled readOnly/>Use approved source documents only</label>}
      </ActionForm>
    </Panel>}
    <details className="setup-area"><summary>Setup and settings</summary>
      <Panel title="Workbook setup"><p>Check or update the approved mappings for your function.</p>
        <div className="actions"><ActionForm label="Check mappings" onSubmit={async()=>setReport(await api<Inventory>("/data/inventory"))}><span/></ActionForm>
        <ActionForm label="Update mappings" onSubmit={async()=>setReport(await api<Inventory>("/data/import","POST"))} success={refresh}><span/></ActionForm></div>
        {report && <div role="status"><p>{report.issues?.length ?? 0} items need review.</p>{report.issues?.map((r,i)=><p key={i}>{r.reason}</p>)}</div>}
      </Panel>
    </details>
  </>;
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
    <Panel title="Sources">
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
                    <th>Version</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {grouped.map((s) => (
                    <tr key={s.source_id}>
                      <td>
                        {s.title}
                        <details><summary>Source details</summary>Reference: {s.source_id}</details>
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
                        {s.version}<details><summary>Document details</summary>{s.chunk_count} indexed text sections</details>
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
              No approved documents added yet. Upload documents above to get started.
            </Empty>
          );
        }}
      </DataState>
      {selected && (
        <Modal
          title={`Edit skill mapping · ${selected.title}`}
          close={() => setSelected(null)}
        >
          <DataState state={registry}>
            {(data) => {
              const skillLabel = (id: string) => data.skills.find((skill) => skill.skill_id === id)?.skill_name ?? "Unavailable skill";
              return <>
                <SkillPicker
                  skills={data.skills}
                  selected={ids}
                  change={(value) => {
                    setIds(value);
                    setConfirm(false);
                  }}
                  label="Mapped skills"
                />
                <p>Current: {selected.skill_ids.map(skillLabel).join(", ")}</p>
                <p>Proposed: {ids.length ? ids.map(skillLabel).join(", ") : "Select at least one skill"}</p>
              </>;
            }}
          </DataState>
          <p>The document and its version will be preserved.</p>
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
