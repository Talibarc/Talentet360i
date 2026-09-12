import { useState } from "react";
import type { Api } from "./api";
import type { Audit, Notice } from "./types";
import { useResource } from "./hooks";
import { date } from "./format";
import { ActionForm, Chip, DataState, Empty, Field, Panel } from "./ui";
export function Notifications({
  api,
  refresh,
}: {
  api: Api;
  refresh: () => void;
}) {
  const [version, setVersion] = useState(0),
    [unread, setUnread] = useState(false),
    state = useResource<Notice[]>(
      api,
      `/notifications?unread_only=${unread}`,
      version,
    );
  return (
    <Panel
      title="Notifications"
      action={
        <label className="check">
          <input
            type="checkbox"
            checked={unread}
            onChange={(e) => setUnread(e.target.checked)}
          />
          Unread only
        </label>
      }
    >
      <DataState state={state}>
        {(rows) =>
          rows.length ? (
            rows.map((n) => (
              <article
                className={`record ${!n.read_at ? "unread" : ""}`}
                key={n.id}
              >
                <div className="row">
                  <h3>{n.title}</h3>
                  <Chip>{n.read_at ? "read" : "unread"}</Chip>
                </div>
                <p>{n.message}</p>
                <small>{date(n.created_at)}</small>
                {!n.read_at && (
                  <ActionForm
                    label="Mark as read"
                    onSubmit={() => api(`/notifications/${n.id}/read`, "PATCH")}
                    success={() => {
                      setVersion((v) => v + 1);
                      refresh();
                    }}
                  >
                    <span />
                  </ActionForm>
                )}
              </article>
            ))
          ) : (
            <Empty>
              You’re all caught up. Workflow updates will appear here.
            </Empty>
          )
        }
      </DataState>
    </Panel>
  );
}
export default function Governance({ api }: { api: Api }) {
  const [action, setAction] = useState(""),
    [query, setQuery] = useState(""),
    [after, setAfter] = useState(0),
    state = useResource<Audit[]>(
      api,
      `/audit-events?limit=100&after_id=${after}&action=${encodeURIComponent(query)}`,
    );
  return (
    <>
      <div className="warning">
        <strong>Data-source limitations</strong>
        <p>
          13 Finance skill references remain unresolved. Approved SOP documents
          are absent. Mock exercises are synthetic; company scoring policies and
          workbook confidentiality still need validation. Missing learning
          mappings produce no course recommendations.
        </p>
      </div>
      <Panel title="Audit history">
        <form
          className="actions"
          onSubmit={(e) => {
            e.preventDefault();
            setAfter(0);
            setQuery(action);
          }}
        >
          <Field label="Exact event action">
            <input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g. assessment.submitted"
            />
          </Field>
          <button className="primary">Filter events</button>
          <button
            type="button"
            onClick={() => {
              setAction("");
              setQuery("");
              setAfter(0);
            }}
          >
            Reset
          </button>
        </form>
        <p className="muted">
          Append-only history within your role’s scope. Showing up to 100 events
          per page.
        </p>
        <DataState state={state}>
          {(rows) => (
            <>
              {rows.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Event</th>
                        <th>Record</th>
                        <th>Actor</th>
                        <th>Time</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((a) => (
                        <tr key={a.id}>
                          <td>
                            <Chip>{a.action}</Chip>
                          </td>
                          <td>
                            {a.entity_type} {a.entity_id}
                          </td>
                          <td>{a.actor_id ?? "System"}</td>
                          <td>{date(a.created_at)}</td>
                          <td>
                            <details>
                              <summary>Inspect</summary>
                              <pre>{JSON.stringify(a.details, null, 2)}</pre>
                            </details>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty>No audit events match this filter.</Empty>
              )}
              <div className="actions">
                <button disabled={after === 0} onClick={() => setAfter(0)}>
                  First page
                </button>
                <button
                  disabled={rows.length < 100}
                  onClick={() => setAfter(rows.at(-1)!.id)}
                >
                  Next page
                </button>
              </div>
            </>
          )}
        </DataState>
      </Panel>
    </>
  );
}
