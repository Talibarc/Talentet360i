import { mappingName } from "./catalog";
import { useRef, useState } from "react";
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
type RagSource = { source_id: string; source_title: string | null; source_type: string | null; source_owner: string | null; mapped_skill_ids: string[]; availability_status: string };
type BatchRow = { id: string; file: File; sourceId: string; skillIds: string[]; confirmed: boolean; status: string; message?: string };

export function RagBatchUpload({ api }: { api: Api }) {
  const registry = useResource<{ sources: RagSource[]; skill_ids: string[]; skills: { skill_id: string; skill_name: string }[]; limits: { maximum_files: number; maximum_file_bytes: number; maximum_batch_bytes: number } }>(api, "/rag/source-registry");
  const [rows, setRows] = useState<BatchRow[]>([]), [summary, setSummary] = useState<{ selected_count:number; successfully_ingested:number; duplicates_skipped:number; pending_validation:number; failed:number } | null>(null), [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const addFiles = (files: FileList | File[]) => {
    const additions = Array.from(files).map((file, index) => ({ id: `${Date.now()}-${index}-${file.name}`, file, sourceId: "", skillIds: [], confirmed: false, status: "Mapping required" }));
    setRows((current) => [...current, ...additions]); setSummary(null); setError("");
  };
  const update = (id: string, values: Partial<BatchRow>) => setRows((current) => current.map((row) => row.id === id ? { ...row, ...values } : row));
  const payload = (row: BatchRow) => ({ client_id: row.id, original_filename: row.file.name, source_id: row.sourceId || null, skill_ids: row.skillIds, approved_source_confirmed: row.confirmed, file_size: row.file.size });
  const validate = async () => {
    try {
      const result = await api<{ files: { client_id: string; validation_status: string; message?: string }[] }>("/rag/batch/validate", "POST", { files: rows.map(payload) });
      setRows((current) => current.map((row) => { const found=result.files.find((item) => item.client_id===row.id); return found ? { ...row, status: found.validation_status, message: found.message } : row; })); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Batch validation failed"); }
  };
  const ingest = async () => {
    try {
      setRows((current) => current.map((row) => ({ ...row, status: row.status === "Ready" ? "Uploading" : row.status })));
      await new Promise((resolve) => setTimeout(resolve, 0));
      setRows((current) => current.map((row) => ({ ...row, status: row.status === "Uploading" ? "Ingesting" : row.status })));
      const form = new FormData(); rows.forEach((row) => form.append("files", row.file));
      form.append("metadata", JSON.stringify(rows.map(({ id, file, sourceId, skillIds, confirmed }) => ({ client_id:id, original_filename:file.name, source_id:sourceId || null, skill_ids:skillIds, approved_source_confirmed:confirmed }))));
      const result = await api<{ selected_count:number; successfully_ingested:number; duplicates_skipped:number; pending_validation:number; failed:number; files:{client_id:string;validation_status:string;message?:string}[] }>("/rag/batch/upload", "POST", form);
      setRows((current) => current.map((row) => { const found=result.files.find((item) => item.client_id===row.id); return found ? { ...row, status:found.validation_status, message:found.message } : row; }));
      setSummary(result); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Batch upload failed"); }
  };
  return <Panel title="Bulk document ingestion">
    <p className="muted">Select or drop PDF, DOCX, PPTX and TXT files. Review every source and skill mapping before ingestion.</p>
    <div className="source-note" role="button" tabIndex={0} onClick={() => input.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); addFiles(event.dataTransfer.files); }}>
      Drop documents here or select files
      <input ref={input} aria-label="Select source documents" hidden multiple type="file" accept=".pdf,.docx,.pptx,.txt" onChange={(event) => event.target.files && addFiles(event.target.files)} />
    </div>
    <DataState state={registry}>{(data) => <>
      {rows.length ? <div className="table-scroll"><table><thead><tr><th>File</th><th>Source</th><th>Source details</th><th>Skills</th><th>Approved source</th><th>Size</th><th>Status</th><th /></tr></thead><tbody>
        {rows.map((row) => { const source=data.sources.find((item) => item.source_id===row.sourceId); return <tr key={row.id}><td>{row.file.name}</td><td><select aria-label={`Source for ${row.file.name}`} value={row.sourceId} onChange={(event) => { const selected=data.sources.find((item)=>item.source_id===event.target.value); update(row.id,{sourceId:event.target.value,skillIds:selected?.mapped_skill_ids.length===1 ? selected.mapped_skill_ids : [],confirmed:false,status:selected?.mapped_skill_ids.length===1 ? "Pending source validation" : "Mapping required"}); }}><option value="">Select Source_ID</option>{data.sources.map((item)=><option key={item.source_id} value={item.source_id}>{item.source_id}</option>)}</select></td>
          <td>{source ? <>{source.source_title}<small>{source.source_type} · {source.source_owner}</small></> : "Mapping required"}</td>
          <td><fieldset className="skill-picker" aria-label={`Skills for ${row.file.name}`}><legend>Select mapped skills</legend>{data.skills.map((skill)=><label className="skill-option" key={skill.skill_id}><input type="checkbox" checked={row.skillIds.includes(skill.skill_id)} onChange={(event)=>update(row.id,{skillIds:event.target.checked ? [...row.skillIds,skill.skill_id] : row.skillIds.filter((id)=>id!==skill.skill_id),status:"Pending source validation"})}/><span><strong>{skill.skill_id}</strong> — {skill.skill_name}</span></label>)}</fieldset></td>
          <td><input aria-label={`Approve ${row.file.name}`} type="checkbox" checked={row.confirmed} onChange={(event)=>update(row.id,{confirmed:event.target.checked,status:event.target.checked && row.sourceId && row.skillIds.length ? "Ready" : "Pending source validation"})} /></td>
          <td>{(row.file.size/1024).toFixed(1)} KB</td><td><Chip>{row.status}</Chip>{row.message && <small>{row.message}</small>}</td><td><button type="button" className="secondary" onClick={()=>setRows((current)=>current.filter((item)=>item.id!==row.id))}>Remove</button></td></tr>; })}
      </tbody></table></div> : <Empty>No documents selected.</Empty>}
      <div className="actions"><button type="button" className="secondary" disabled={!rows.length} onClick={validate}>Validate All</button><button type="button" disabled={!rows.length} onClick={ingest}>Upload &amp; Ingest All</button></div>
      <p className="muted">Limits: {data.limits.maximum_files} files · {(data.limits.maximum_file_bytes/1048576).toFixed(0)} MB/file · {(data.limits.maximum_batch_bytes/1048576).toFixed(0)} MB/batch</p>
    </>}</DataState>
    {summary && <div className="success">Selected {summary.selected_count} · Ingested {summary.successfully_ingested} · Duplicates {summary.duplicates_skipped} · Pending {summary.pending_validation} · Failed {summary.failed}</div>}
    {error && <div className="error">{error}</div>}
  </Panel>;
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
    ingested_source_count?: number;
    local_rag_sources?: {
      source_id: string;
      title: string | null;
      skill_ids: string[];
      source_type: string;
      availability_status: string;
      ingestion_status: string;
      chunk_count: number;
      content_hash: string | null;
      limitation: string | null;
    }[];
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
            <p>Locally ingested approved sources: {s.ingested_source_count ?? 0}</p>
          </div>
        )}
      </DataState>
      <RagBatchUpload api={api} />
      <DataState state={source}>
        {(s) => (
          <Panel title="Offline RAG source status">
            <p className="muted">Metadata and version indicators only. Extracted document content is not displayed here.</p>
            {s.local_rag_sources?.length ? (
              <div className="table-scroll"><table><thead><tr><th>Source</th><th>Mapped skill</th><th>Type</th><th>Availability</th><th>Ingestion</th><th>Chunks</th><th>Version</th><th>Limitation</th></tr></thead><tbody>
                {s.local_rag_sources.map((item) => <tr key={item.source_id}><td>{item.title ?? item.source_id}<small>{item.source_id}</small></td><td>{item.skill_ids.join(", ")}</td><td>{item.source_type}</td><td><Chip>{item.availability_status}</Chip></td><td>{item.ingestion_status}</td><td>{item.chunk_count}</td><td>{item.content_hash?.slice(0, 12) ?? "Not indexed"}</td><td>{item.limitation ?? "—"}</td></tr>)}
              </tbody></table></div>
            ) : <Empty>No local documents have been ingested. Workbook URLs remain metadata only.</Empty>}
          </Panel>
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
