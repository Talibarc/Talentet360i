import SkillPicker from "./SkillPicker";
import { mappingName } from "./catalog";
import { useRef, useState } from "react";
import type { Api } from "./api";
import type { Mapping, Role, Skill, User } from "./types";
import { useResource } from "./hooks";
import { ActionForm, Chip, DataState, Empty, Field, Panel } from "./ui";
export interface Catalog {
  roles: Role[];
  skills: Skill[];
  mappings: Mapping[];
  users: User[];
}
type RagSource = {
  source_id: string;
  source_title: string | null;
  source_type: string | null;
  source_owner: string | null;
  mapped_skill_ids: string[];
  availability_status: string;
};
type BatchRow = {
  id: string;
  file: File;
  sourceId: string;
  skillIds: string[];
  confirmed: boolean;
  status: string;
  message?: string;
};

export function RagBatchUpload({ api }: { api: Api }) {
  const registry = useResource<{
    sources: RagSource[];
    skill_ids: string[];
    skills: { skill_id: string; skill_name: string }[];
    limits: {
      maximum_files: number;
      maximum_file_bytes: number;
      maximum_batch_bytes: number;
    };
  }>(api, "/rag/source-registry");
  const [rows, setRows] = useState<BatchRow[]>([]),
    [summary, setSummary] = useState<{
      selected_count: number;
      successfully_ingested: number;
      duplicates_skipped: number;
      pending_validation: number;
      failed: number;
    } | null>(null),
    [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const addFiles = (files: FileList | File[]) => {
    const additions = Array.from(files).map((file, index) => ({
      id: `${Date.now()}-${index}-${file.name}`,
      file,
      sourceId: "",
      skillIds: [],
      confirmed: false,
      status: "Mapping required",
    }));
    setRows((current) => [...current, ...additions]);
    setSummary(null);
    setError("");
  };
  const update = (id: string, values: Partial<BatchRow>) =>
    setRows((current) =>
      current.map((row) => (row.id === id ? { ...row, ...values } : row)),
    );
  const payload = (row: BatchRow) => ({
    client_id: row.id,
    original_filename: row.file.name,
    source_id: row.sourceId || null,
    skill_ids: row.skillIds,
    approved_source_confirmed: row.confirmed,
    file_size: row.file.size,
  });
  const validate = async () => {
    setBusy(true);
    try {
      const result = await api<{
        files: {
          client_id: string;
          validation_status: string;
          message?: string;
        }[];
      }>("/rag/batch/validate", "POST", { files: rows.map(payload) });
      setRows((current) =>
        current.map((row) => {
          const found = result.files.find((item) => item.client_id === row.id);
          return found
            ? {
                ...row,
                status: found.validation_status,
                message: found.message,
              }
            : row;
        }),
      );
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Batch validation failed",
      );
    } finally {
      setBusy(false);
    }
  };
  const ingest = async () => {
    setBusy(true);
    try {
      setRows((current) =>
        current.map((row) => ({
          ...row,
          status: row.status === "Ready" ? "Uploading" : row.status,
        })),
      );
      await new Promise((resolve) => setTimeout(resolve, 0));
      setRows((current) =>
        current.map((row) => ({
          ...row,
          status: row.status === "Uploading" ? "Ingesting" : row.status,
        })),
      );
      const form = new FormData();
      rows.forEach((row) => form.append("files", row.file));
      form.append(
        "metadata",
        JSON.stringify(
          rows.map(({ id, file, sourceId, skillIds, confirmed }) => ({
            client_id: id,
            original_filename: file.name,
            source_id: sourceId || null,
            skill_ids: skillIds,
            approved_source_confirmed: confirmed,
          })),
        ),
      );
      const result = await api<{
        selected_count: number;
        successfully_ingested: number;
        duplicates_skipped: number;
        pending_validation: number;
        failed: number;
        files: {
          client_id: string;
          validation_status: string;
          message?: string;
        }[];
      }>("/rag/batch/upload", "POST", form);
      setRows((current) =>
        current.map((row) => {
          const found = result.files.find((item) => item.client_id === row.id);
          return found
            ? {
                ...row,
                status: found.validation_status,
                message: found.message,
              }
            : row;
        }),
      );
      setSummary(result);
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Batch upload failed",
      );
      setRows((current) =>
        current.map((row) =>
          row.status === "Ingesting"
            ? {
                ...row,
                status: "Failed",
                message: "Retry upload; successful duplicates will be skipped.",
              }
            : row,
        ),
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel title="Bulk document ingestion">
      <p className="muted">
        Select or drop PDF, DOCX, PPTX and TXT files. Review every source and
        skill mapping before ingestion.
      </p>
      <fieldset disabled={busy}>
        <div
          className="source-note"
          role="button"
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              input.current?.click();
            }
          }}
          tabIndex={0}
          onClick={() => input.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            addFiles(event.dataTransfer.files);
          }}
        >
          Drop documents here or select files
          <input
            ref={input}
            aria-label="Select source documents"
            hidden
            multiple
            type="file"
            accept=".pdf,.docx,.pptx,.txt"
            onChange={(event) =>
              event.target.files && addFiles(event.target.files)
            }
          />
        </div>
        <DataState state={registry}>
          {(data) => (
            <>
              {rows.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>File</th>
                        <th>Source</th>
                        <th>Source details</th>
                        <th>Skills</th>
                        <th>Approved source</th>
                        <th>Size</th>
                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => {
                        const source = data.sources.find(
                          (item) => item.source_id === row.sourceId,
                        );
                        return (
                          <tr key={row.id}>
                            <td>{row.file.name}</td>
                            <td>
                              <select
                                aria-label={`Source for ${row.file.name}`}
                                value={row.sourceId}
                                onChange={(event) => {
                                  const selected = data.sources.find(
                                    (item) =>
                                      item.source_id === event.target.value,
                                  );
                                  update(row.id, {
                                    sourceId: event.target.value,
                                    skillIds:
                                      selected?.mapped_skill_ids.length === 1
                                        ? selected.mapped_skill_ids
                                        : [],
                                    confirmed: false,
                                    status:
                                      selected?.mapped_skill_ids.length === 1
                                        ? "Pending source validation"
                                        : "Mapping required",
                                  });
                                }}
                              >
                                <option value="">Select Source_ID</option>
                                {data.sources.map((item) => (
                                  <option
                                    key={item.source_id}
                                    value={item.source_id}
                                  >
                                    {item.source_id}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td>
                              {source ? (
                                <>
                                  {source.source_title}
                                  <small>
                                    {source.source_type} · {source.source_owner}
                                  </small>
                                </>
                              ) : (
                                "Mapping required"
                              )}
                            </td>
                            <td>
                              <SkillPicker
                                skills={data.skills}
                                selected={row.skillIds}
                                label={`Skills for ${row.file.name}`}
                                change={(skillIds) =>
                                  update(row.id, {
                                    skillIds,
                                    status: "Pending source validation",
                                  })
                                }
                              />
                            </td>
                            <td>
                              <input
                                aria-label={`Approve ${row.file.name}`}
                                type="checkbox"
                                checked={row.confirmed}
                                onChange={(event) =>
                                  update(row.id, {
                                    confirmed: event.target.checked,
                                    status:
                                      event.target.checked &&
                                      row.sourceId &&
                                      row.skillIds.length
                                        ? "Ready"
                                        : "Pending source validation",
                                  })
                                }
                              />
                            </td>
                            <td>{(row.file.size / 1024).toFixed(1)} KB</td>
                            <td>
                              <Chip>{row.status}</Chip>
                              {row.message && <small>{row.message}</small>}
                            </td>
                            <td>
                              <button
                                type="button"
                                className="secondary"
                                onClick={() =>
                                  setRows((current) =>
                                    current.filter(
                                      (item) => item.id !== row.id,
                                    ),
                                  )
                                }
                              >
                                Remove
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty>No documents selected.</Empty>
              )}
              <div className="actions">
                <button
                  type="button"
                  className="secondary"
                  disabled={!rows.length}
                  onClick={validate}
                >
                  Validate All
                </button>
                <button type="button" disabled={!rows.length} onClick={ingest}>
                  Upload &amp; Ingest All
                </button>
              </div>
              <p className="muted">
                Limits: {data.limits.maximum_files} files ·{" "}
                {(data.limits.maximum_file_bytes / 1048576).toFixed(0)} MB/file
                · {(data.limits.maximum_batch_bytes / 1048576).toFixed(0)}{" "}
                MB/batch
              </p>
            </>
          )}
        </DataState>
      </fieldset>
      {summary && (
        <div className="success">
          Selected {summary.selected_count} · Ingested{" "}
          {summary.successfully_ingested} · Duplicates{" "}
          {summary.duplicates_skipped} · Pending {summary.pending_validation} ·
          Failed {summary.failed}
        </div>
      )}
      {error && <div className="error">{error}</div>}
    </Panel>
  );
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
  const [search, setSearch] = useState("");
  return (
    <div>
      <input
        type="search"
        aria-label="Search role and skill"
        placeholder="Search role or skill"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <select id={id} name={name} required defaultValue="">
        <option value="" disabled>
          Select a mapped skill
        </option>
        {catalog.mappings
          .filter(
            (m) =>
              mappingName(catalog, m.id)
                .toLowerCase()
                .includes(search.toLowerCase()) &&
              m.is_expected &&
              m.target_level !== null &&
              (!employee ||
                m.role_id ===
                  catalog.users.find((u) => u.id === employee)?.job_role_id),
          )
          .map((m) => (
            <option value={m.id} key={m.id}>
              {mappingName(catalog, m.id)} ·{" "}
              {m.target_label ?? `Level ${m.target_level}`}
            </option>
          ))}
      </select>
    </div>
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
