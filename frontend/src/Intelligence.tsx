import { useState } from "react";
import type { Api } from "./api";
import { useResource } from "./hooks";
import { Chip, DataState, Empty, Field, Panel, Stat } from "./ui";
type Provenance = {
  workbook: string;
  sheet: string;
  row: number;
  source_id: string;
};
type RecordRow = {
  employee_id: number;
  employee_name: string;
  role_id: string;
  role_name: string;
  skill_id: string | null;
  skill_name: string;
  current_level: number | null;
  provisional_level: number | null;
  target_level: number;
  gap: number | null;
  gap_severity: string;
  readiness: string;
  assessment_status: string;
  policy_status: string;
  mapping_status: string;
  recommendation_status: string;
  recommendations: {
    course_id: string;
    title: string;
    reason: string;
    provenance: Provenance[];
  }[];
  provenance: Provenance[];
  history: { date: string; level: number }[];
  movement: number | null;
};
type Group = {
  function: string;
  role_id: string;
  team: string;
  hub: string;
  skill_id: string;
  skill_name: string;
  current_level: number | null;
  readiness: string;
  count: number;
  gap_count: number;
  movement_records: number;
  movement_total: number;
};
type IntelligenceData = {
  basis: string;
  records: RecordRow[];
  groups: Group[];
  readiness: Record<string, number>;
  coverage: Record<string, number>;
  limitations: string[];
};
export default function Intelligence({
  api,
  role,
  view,
}: {
  api: Api;
  role: string;
  view: string;
}) {
  const state = useResource<IntelligenceData>(api, "/skill-intelligence");
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState<Record<string, string>>({});
  return (
    <DataState state={state}>
      {(data) => (
        <>
          <div className="stats">
            <Stat
              label="Expected skills"
              value={data.coverage.expected_records}
              note="Within your authorized scope"
            />
            <Stat
              label="Validated mappings"
              value={data.coverage.validated_mappings}
              note="Exact workbook identities"
            />
            <Stat
              label="Validated training"
              value={data.coverage.validated_recommendations}
              note="Approved TNI and course joins"
            />
          </div>
          <Panel
            title={
              view.includes("training")
                ? "Validated training plan"
                : view.includes("movement")
                  ? "Skill movement"
                  : "Skill intelligence"
            }
          >
            <Field label="Search employee, role or skill">
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={
                  role === "leader"
                    ? "Search role or skill"
                    : "Search employee, role or skill"
                }
              />
            </Field>
            {role === "leader" ? (
              <>
                <div className="form-grid">
                  {[
                    "function",
                    "role_id",
                    "team",
                    "hub",
                    "skill_id",
                    "readiness",
                  ].map((key) => (
                    <Field key={key} label={key.replaceAll("_", " ")}>
                      <select
                        value={filter[key] ?? ""}
                        onChange={(e) =>
                          setFilter({ ...filter, [key]: e.target.value })
                        }
                      >
                        <option value="">All</option>
                        {[
                          ...new Set(
                            data.groups.map((g) =>
                              String(g[key as keyof Group] ?? ""),
                            ),
                          ),
                        ]
                          .filter(Boolean)
                          .map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                      </select>
                    </Field>
                  ))}
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Skill / role</th>
                        <th>Confirmed level</th>
                        <th>Readiness</th>
                        <th>Records / gaps</th>
                        <th>Movement</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.groups
                        .filter(
                          (g) =>
                            `${g.skill_id} ${g.skill_name} ${g.role_id}`
                              .toLowerCase()
                              .includes(search.toLowerCase()) &&
                            Object.entries(filter).every(
                              ([k, v]) =>
                                !v || String(g[k as keyof Group]) === v,
                            ),
                        )
                        .map((g, i) => (
                          <tr key={i}>
                            <td>
                              {g.skill_id} — {g.skill_name}
                              <small>
                                {g.role_id} · {g.function} · {g.team} · {g.hub}
                              </small>
                            </td>
                            <td>{g.current_level ?? "Not confirmed"}</td>
                            <td>
                              <Chip>{g.readiness}</Chip>
                            </td>
                            <td>
                              {g.count} / {g.gap_count}
                            </td>
                            <td>
                              {g.movement_records
                                ? `${g.movement_total} levels across ${g.movement_records} records`
                                : "History unavailable"}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="intelligence-grid">
                {data.records
                  .filter((r) =>
                    `${r.employee_name} ${r.role_name} ${r.skill_id} ${r.skill_name}`
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  )
                  .map((r) => (
                    <article
                      className="skill-card"
                      key={`${r.employee_id}-${r.skill_id ?? r.skill_name}`}
                    >
                      <div className="row">
                        <h3>
                          {r.skill_id ? `${r.skill_id} — ` : ""}
                          {r.skill_name}
                        </h3>
                        <Chip>{r.readiness}</Chip>
                      </div>
                      {role !== "employee" && (
                        <p>
                          {r.employee_name} · {r.role_name}
                        </p>
                      )}
                      <div className="level-comparison">
                        <div>
                          <small>Official current</small>
                          <strong>{r.current_level ?? "Not confirmed"}</strong>
                        </div>
                        <div>
                          <small>Target</small>
                          <strong>{r.target_level}</strong>
                        </div>
                        <div>
                          <small>Gap</small>
                          <strong>{r.gap ?? "Pending"}</strong>
                        </div>
                      </div>
                      <p>
                        Provisional:{" "}
                        {r.provisional_level ?? "Pending policy validation."} ·
                        Assessment: {r.assessment_status.replaceAll("_", " ")}
                      </p>
                      <p>Severity: {r.gap_severity}</p>
                      {r.recommendations.length ? (
                        r.recommendations.map((c) => (
                          <div className="inset" key={c.course_id}>
                            <strong>
                              {c.course_id} — {c.title}
                            </strong>
                            <p>{c.reason}</p>
                            {c.provenance.map((p) => (
                              <small key={`${p.sheet}-${p.row}`}>
                                {p.workbook} · {p.sheet} · Row {p.row}
                              </small>
                            ))}
                          </div>
                        ))
                      ) : (
                        <p className="source-note">
                          No validated course recommendation available.
                        </p>
                      )}
                      <details>
                        <summary>Progress and mapping provenance</summary>
                        <p>{r.mapping_status}</p>
                        {r.provenance.map((p) => (
                          <p key={p.source_id}>
                            {p.source_id} · {p.workbook} / {p.sheet} / row{" "}
                            {p.row}
                          </p>
                        ))}
                        {r.history.length ? (
                          <ol className="timeline">
                            {r.history.map((h, i) => (
                              <li key={i}>
                                {new Date(h.date).toLocaleDateString()} ·
                                Confirmed level {h.level}
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p>No confirmed history available.</p>
                        )}
                      </details>
                    </article>
                  ))}
              </div>
            )}
            {!data.records.length && !data.groups.length && (
              <Empty>
                No expected skills in your scope. L&D can import validated role
                mappings and assign a job role.
              </Empty>
            )}
          </Panel>
          <details className="card">
            <summary>Policy and data limitations</summary>
            {data.limitations.map((l) => (
              <p key={l}>{l}</p>
            ))}
            {data.coverage.missing_role_assignments > 0 && (
              <p>
                {data.coverage.missing_role_assignments} employees need a role
                assignment.
              </p>
            )}
          </details>
        </>
      )}
    </DataState>
  );
}

export function MappingCoverage({ api }: { api: Api }) {
  const state = useResource<{
    mappings: {
      role_id: string;
      skill_id: string;
      skill_name: string;
      target: string;
      mapping_status: string;
      learning_status: string;
      provenance: Provenance;
      resources: {
        resource_id: string;
        title: string;
        provenance: Provenance;
      }[];
    }[];
  }>(api, "/skill-intelligence/mappings");
  const [search, setSearch] = useState("");
  return (
    <Panel title="Training mappings and source coverage">
      <Field label="Search official mappings">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </Field>
      <DataState state={state}>
        {(data) =>
          data.mappings.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Role / skill</th>
                    <th>Target</th>
                    <th>Validation</th>
                    <th>Learning references</th>
                    <th>Provenance</th>
                  </tr>
                </thead>
                <tbody>
                  {data.mappings
                    .filter((r) =>
                      `${r.role_id} ${r.skill_id} ${r.skill_name}`
                        .toLowerCase()
                        .includes(search.toLowerCase()),
                    )
                    .map((r, i) => (
                      <tr key={i}>
                        <td>
                          {r.role_id}
                          <small>
                            {r.skill_id} — {r.skill_name}
                          </small>
                        </td>
                        <td>{r.target}</td>
                        <td>{r.mapping_status}</td>
                        <td>
                          {r.learning_status}
                          {r.resources.map((c) => (
                            <details key={c.resource_id}>
                              <summary>
                                {c.resource_id} — {c.title}
                              </summary>
                              {c.provenance.workbook} / {c.provenance.sheet} /
                              row {c.provenance.row}
                            </details>
                          ))}
                        </td>
                        <td>
                          {r.provenance.workbook}
                          <small>
                            {r.provenance.sheet} / row {r.provenance.row}
                          </small>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty>
              Import workbook mappings from L&D Overview to review coverage.
            </Empty>
          )
        }
      </DataState>
    </Panel>
  );
}
