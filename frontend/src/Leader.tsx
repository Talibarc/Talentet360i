import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { Api } from "./api";
import type { Aggregate } from "./types";
import type { Catalog } from "./Admin";
import { useResource } from "./hooks";
import { DataState, Empty, Field, Panel, Stat } from "./ui";
export default function Leader({
  api,
  catalog,
}: {
  api: Api;
  catalog: Catalog;
}) {
  const [filters, setFilters] = useState<Record<string, string>>({}),
    [query, setQuery] = useState("");
  const state = useResource<Aggregate>(
    api,
    `/leader/aggregates?group_by=skill,level${query}`,
  );
  return (
    <>
      <div className="source-note">
        <strong>Manager-confirmed proficiency only</strong>
        <p>
          Reporting is restricted to your authorized scope. Counts represent
          employee–skill records. Provisional results and XP are excluded.
        </p>
      </div>
      <Panel title="Reporting filters">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(
              "&" +
                new URLSearchParams(
                  Object.fromEntries(
                    Object.entries(filters).filter(([, v]) => v !== ""),
                  ),
                ),
            );
          }}
        >
          <div className="filter-grid">
            {["function", "role_id", "team", "hub", "skill_id", "level"].map(
              (key) => (
                <Field
                  key={key}
                  label={
                    {
                      role_id: "Role",
                      skill_id: "Skill",
                      function: "Function",
                      team: "Team",
                      hub: "Hub",
                      level: "Level",
                    }[key]!
                  }
                >
                  {key === "team" || key === "hub" ? (
                    <input
                      value={filters[key] ?? ""}
                      placeholder={`All ${key}s in scope`}
                      onChange={(e) =>
                        setFilters({ ...filters, [key]: e.target.value })
                      }
                    />
                  ) : (
                    <select
                      value={filters[key] ?? ""}
                      onChange={(e) =>
                        setFilters({ ...filters, [key]: e.target.value })
                      }
                    >
                      <option value="">All in scope</option>
                      {key === "role_id"
                        ? catalog.roles.map((r) => (
                            <option key={r.id} value={r.id}>
                              {r.role_name}
                            </option>
                          ))
                        : key === "skill_id"
                          ? catalog.skills.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.name}
                              </option>
                            ))
                          : key === "function"
                            ? [
                                ...new Set(
                                  catalog.roles.map((r) => r.business_function),
                                ),
                              ].map((f) => <option key={f}>{f}</option>)
                            : [0, 1, 2, 3, 4, 5].map((l) => (
                                <option key={l} value={l}>
                                  Level {l}
                                </option>
                              ))}
                    </select>
                  )}
                </Field>
              ),
            )}
          </div>
          <div className="actions">
            <button className="primary">Apply filters</button>
            <button
              type="button"
              onClick={() => {
                setFilters({});
                setQuery("");
              }}
            >
              Reset
            </button>
          </div>
        </form>
      </Panel>
      <DataState state={state}>
        {(a) => {
          const gaps = a.groups.reduce((sum, g) => sum + g.gap_count, 0),
            totalGap = a.groups.reduce((sum, g) => sum + g.total_gap, 0);
          const levels = [0, 1, 2, 3, 4, 5].map((level) => ({
            name: `L${level}`,
            records: a.groups
              .filter((g) => g.level === level)
              .reduce((sum, g) => sum + g.count, 0),
          }));
          return (
            <>
              <div className="stats">
                <Stat
                  label="Confirmed skill records"
                  value={a.total_confirmed_records}
                  note="Official manager-confirmed results"
                />
                <Stat
                  label="Records below target"
                  value={gaps}
                  note="Confirmed skill gaps"
                />
                <Stat
                  label="Total level gap"
                  value={totalGap}
                  note="Sum of gaps against mapped targets"
                />
              </div>
              <div className="two-col">
                <Panel title="Confirmed skill distribution">
                  {a.total_confirmed_records ? (
                    <div
                      className="chart"
                      role="img"
                      aria-label={levels
                        .map((l) => `${l.name}: ${l.records} records`)
                        .join(", ")}
                    >
                      <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={levels}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />
                          <XAxis dataKey="name" />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Bar
                            dataKey="records"
                            fill="#4f46c8"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <Empty>
                      No confirmed results match these filters. Manager
                      confirmation populates this view.
                    </Empty>
                  )}
                </Panel>
                <Panel title="Skill gap heatmap">
                  <p className="muted">
                    Cells show records below target / confirmed records at each
                    level.
                  </p>
                  {a.groups.length ? (
                    <div className="table-scroll">
                      <table className="heatmap">
                        <thead>
                          <tr>
                            <th>Skill</th>
                            {levels.map((l) => (
                              <th key={l.name}>{l.name}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {[...new Set(a.groups.map((g) => g.skill))].map(
                            (skill) => (
                              <tr key={skill}>
                                <th>{skill}</th>
                                {levels.map((l, index) => {
                                  const g = a.groups.find(
                                    (g) =>
                                      g.skill === skill && g.level === index,
                                  );
                                  return (
                                    <td
                                      key={l.name}
                                      className={
                                        g?.gap_count
                                          ? "has-gap"
                                          : g
                                            ? "met"
                                            : ""
                                      }
                                    >
                                      {g ? `${g.gap_count} / ${g.count}` : "—"}
                                    </td>
                                  );
                                })}
                              </tr>
                            ),
                          )}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <Empty>No confirmed skill records to display.</Empty>
                  )}
                </Panel>
              </div>
              <Panel title="Distribution details">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Skill</th>
                        <th>Confirmed level</th>
                        <th>Records</th>
                        <th>Below target</th>
                        <th>Total gap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {a.groups.map((g) => (
                        <tr key={`${g.skill}-${g.level}`}>
                          <td>{g.skill}</td>
                          <td>{g.level}</td>
                          <td>{g.count}</td>
                          <td>{g.gap_count}</td>
                          <td>{g.total_gap}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </>
          );
        }}
      </DataState>
    </>
  );
}
