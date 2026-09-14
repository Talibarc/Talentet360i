import { useState } from "react";
import type { Api } from "./api";
import { safeUrl } from "./api";
import type { Assessment, Evidence } from "./types";
import type { Catalog } from "./Admin";
import { mappingName } from "./catalog";
import { Assignment } from "./Admin";
import { HistoryView, TniView } from "./Employee";
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
export default function Manager({
  api,
  catalog,
  refresh,
  page = "manager",
}: {
  api: Api;
  catalog: Catalog;
  refresh: () => void;
  page?: string;
}) {
  const [employeeId, setEmployeeId] = useState(0);
  const [version, setVersion] = useState(0),
    [selected, setSelected] = useState<{
      type: "evidence" | "assessments";
      id: number;
      employee: number;
      revision: number;
      level?: number | null;
      score?: number | null;
    } | null>(null);
  const inbox = useResource<{
    results: { assessment: Assessment; review: { revision: number } }[];
    evidence: Evidence[];
  }>(api, "/manager/reviews", version);
  const all = useResource<Assessment[]>(api, "/assessments", version);
  const update = () => {
    setSelected(null);
    setVersion((v) => v + 1);
    refresh();
  };
  const name = (id: number) =>
    catalog.users.find((u) => u.id === id)?.full_name ?? "Employee unavailable";
  return (
    <>
      {page === "team-employee" && (
        <Panel title="Employee development">
          <Field label="Select employee">
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(Number(e.target.value))}
            >
              <option value={0}>Choose a direct report</option>
              {catalog.users
                .filter((u) => u.role === "employee")
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
            </select>
          </Field>
          {employeeId > 0 && <TniView api={api} userId={employeeId} />}
        </Panel>
      )}
      {page === "manager" && (
        <DataState state={inbox}>
          {(data) => (
            <>
              <div className="stats">
                <Stat
                  label="Results to review"
                  value={data.results.length}
                  note="Provisional levels awaiting a decision"
                />
                <Stat
                  label="Evidence to review"
                  value={data.evidence.length}
                  note="Confirm linked evidence before results"
                />
                <Stat
                  label="Direct reports"
                  value={
                    catalog.users.filter((u) => u.role === "employee").length
                  }
                  note="Restricted to your reporting scope"
                />
              </div>
              <div className="two-col">
                <Panel title="Result review inbox">
                  {data.results.length ? (
                    data.results.map(({ assessment: a, review: r }) => (
                      <div className="record" key={a.id}>
                        <Chip>pending_review</Chip>
                        <h3>{name(a.employee_id)}</h3>
                        <p>{mappingName(catalog, a.role_skill_map_id)}</p>
                        <div className="row">
                          <span>
                            Score {a.score_percentage}% · Provisional level{" "}
                            {a.achieved_level ?? "Pending policy validation"}
                          </span>
                          <button
                            className="primary"
                            onClick={() =>
                              setSelected({
                                type: "assessments",
                                id: a.id,
                                employee: a.employee_id,
                                revision: r.revision,
                                level: a.achieved_level,
                                score: a.score_percentage,
                              })
                            }
                          >
                            Review result
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <Empty>
                      No pending results. Submitted assessments will appear
                      here.
                    </Empty>
                  )}
                </Panel>
                <Panel title="Evidence review inbox">
                  {data.evidence.length ? (
                    data.evidence.map((e) => (
                      <div className="record" key={e.id}>
                        <h3>{e.title}</h3>
                        <small>
                          {name(e.employee_id)} · Revision {e.revision}
                        </small>
                        <p>{e.description}</p>
                        {safeUrl(e.url) && (
                          <a
                            href={safeUrl(e.url)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Supporting evidence
                          </a>
                        )}
                        <button
                          onClick={() =>
                            setSelected({
                              type: "evidence",
                              id: e.id,
                              employee: e.employee_id,
                              revision: e.revision,
                            })
                          }
                        >
                          Review evidence
                        </button>
                      </div>
                    ))
                  ) : (
                    <Empty>No evidence awaiting review.</Empty>
                  )}
                </Panel>
              </div>
            </>
          )}
        </DataState>
      )}
      {page !== "manager" && (
        <Panel title="Assessment and decision history">
          <DataState state={all}>
            {(rows) =>
              rows.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Employee</th>
                        <th>Assessment</th>
                        <th>Status</th>
                        <th>Calculated level</th>
                        <th>History</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((a) => (
                        <tr key={a.id}>
                          <td>{name(a.employee_id)}</td>
                          <td>{mappingName(catalog, a.role_skill_map_id)}</td>
                          <td>
                            <Chip>{a.status}</Chip>
                          </td>
                          <td>{a.achieved_level ?? "Not assessed"}</td>
                          <td>
                            <button
                              onClick={() =>
                                setSelected({
                                  type: "assessments",
                                  id: a.id,
                                  employee: a.employee_id,
                                  revision: 0,
                                  level: a.achieved_level,
                                  score: a.score_percentage,
                                })
                              }
                            >
                              View history
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty>No assessments in your scope.</Empty>
              )
            }
          </DataState>
        </Panel>
      )}
      {page === "team-progress" && (
        <Assignment api={api} catalog={catalog} refresh={update} />
      )}
      {selected && (
        <Modal
          title={`${selected.type === "evidence" ? "Evidence" : "Result"} review · ${name(selected.employee)}`}
          close={() => setSelected(null)}
        >
          {selected.type === "assessments" && (
            <div className="inset">
              <strong>Selected assessment {selected.id}</strong>
              <p>
                Score: {selected.score ?? "Not assessed"}% · Calculated level:{" "}
                {selected.level ?? "Pending policy validation"}
              </p>
            </div>
          )}
          <h3>Latest employee development context</h3>
          <TniView api={api} userId={selected.employee} />
          <HistoryView
            api={api}
            path={`/${selected.type}/${selected.id}/history`}
          />
          {selected.revision > 0 && (
            <ActionForm
              label="Record manager decision"
              success={update}
              onSubmit={(d) =>
                api(`/${selected.type}/${selected.id}/decision`, "POST", {
                  decision: d.get("decision"),
                  comment: d.get("comment"),
                  expected_revision: selected.revision,
                })
              }
            >
              <p className="source-note">
                Confirmation uses the calculated result. XP cannot change the
                confirmed level. All linked evidence must be confirmed first.
              </p>
              <Field label="Decision">
                <select
                  name="decision"
                  defaultValue={
                    selected.type === "assessments" && selected.level === null
                      ? "send_back"
                      : "confirm"
                  }
                >
                  <option
                    value="confirm"
                    disabled={
                      selected.type === "assessments" && selected.level === null
                    }
                  >
                    Confirm
                  </option>
                  <option value="send_back">Send back</option>
                </select>
              </Field>
              <Field label="Manager comments">
                <textarea name="comment" required maxLength={2000} />
              </Field>
            </ActionForm>
          )}
          <EvidenceHistoryList api={api} employee={selected.employee} />
        </Modal>
      )}
    </>
  );
}
function EvidenceHistoryList({
  api,
  employee,
}: {
  api: Api;
  employee: number;
}) {
  const state = useResource<Evidence[]>(
    api,
    `/evidence?employee_id=${employee}`,
  );
  return (
    <DataState state={state}>
      {(rows) => (
        <>
          {rows.map((e) => (
            <details key={e.id}>
              <summary>
                {e.title} · {e.status.replaceAll("_", " ")}
              </summary>
              <HistoryView api={api} path={`/evidence/${e.id}/history`} />
            </details>
          ))}
        </>
      )}
    </DataState>
  );
}
