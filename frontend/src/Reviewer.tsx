import { useState } from "react";
import type { Api } from "./api";
import type { Question, Revision } from "./types";
import { useResource } from "./hooks";
import { date } from "./format";
import { ActionForm, Chip, DataState, Empty, Field, Panel } from "./ui";
export default function Reviewer({
  api,
  refresh,
}: {
  api: Api;
  refresh: () => void;
}) {
  const [version, setVersion] = useState(0),
    [selected, setSelected] = useState<number | null>(null),
    [status, setStatus] = useState("pending_review");
  const state = useResource<Question[]>(api, "/questions", version);
  const update = () => {
    setVersion((v) => v + 1);
    refresh();
  };
  return (
    <>
      <div className="tabs" aria-label="Question status">
        {["pending_review", "approved", "rejected", "all"].map((s) => (
          <button
            className={status === s ? "active" : ""}
            key={s}
            onClick={() => {
              setStatus(s);
              setSelected(null);
            }}
          >
            {s.replaceAll("_", " ")}
          </button>
        ))}
      </div>
      <DataState state={state}>
        {(questions) => (
          <div className="review-layout">
            <Panel title="Question queue">
              <div className="queue">
                {questions
                  .filter((q) => status === "all" || q.status === status)
                  .map((q) => (
                    <button
                      className={selected === q.id ? "selected" : ""}
                      key={q.id}
                      onClick={() => setSelected(q.id)}
                    >
                      <span className="eyebrow">
                        Question {q.id} · Level {q.skill_level}
                      </span>
                      <strong>{q.question_text}</strong>
                      <Chip>{q.status}</Chip>
                    </button>
                  ))}
              </div>
              {!questions.some(
                (q) => status === "all" || q.status === status,
              ) && (
                <Empty>
                  No questions in this queue. Generate drafts from the Admin
                  workspace.
                </Empty>
              )}
            </Panel>
            {selected && questions.find((q) => q.id === selected) ? (
              <QuestionWorkspace
                key={`${selected}-${version}`}
                api={api}
                q={questions.find((q) => q.id === selected)!}
                refresh={update}
              />
            ) : (
              <Panel title="Review workspace">
                <Empty>
                  Select a question to inspect its content, source, and revision
                  history.
                </Empty>
              </Panel>
            )}
          </div>
        )}
      </DataState>
    </>
  );
}
function QuestionWorkspace({
  api,
  q,
  refresh,
}: {
  api: Api;
  q: Question;
  refresh: () => void;
}) {
  const history = useResource<Revision[]>(api, `/questions/${q.id}/history`),
    [editing, setEditing] = useState(false);
  return (
    <Panel title={`Question ${q.id}`} action={<Chip>{q.status}</Chip>}>
      <h3>{q.question_text}</h3>
      <div className="answers">
        {Object.entries(q.options).map(([key, value]) => (
          <div
            key={key}
            className={key === q.correct_answer ? "answer correct" : "answer"}
          >
            <b>{key}</b>
            <span>{value}</span>
            {key === q.correct_answer && <Chip>correct</Chip>}
          </div>
        ))}
      </div>
      <div className="inset">
        <strong>Answer rationale</strong>
        <p>{q.explanation}</p>
      </div>
      <div className="source-note">
        <strong>RAG / source provenance</strong>
        <p>{q.rag_source ?? "No source reference available"}</p>
      </div>
      {q.status === "pending_review" && (
        <ActionForm
          label="Record review"
          success={refresh}
          onSubmit={(d) =>
            api(`/questions/${q.id}/review`, "PATCH", {
              status: d.get("decision"),
              review_comment: d.get("comment"),
            })
          }
        >
          <Field label="Review decision">
            <select name="decision">
              <option value="approved">Approve</option>
              <option value="rejected">Reject</option>
            </select>
          </Field>
          <Field label="Review comments">
            <textarea name="comment" required maxLength={500} />
          </Field>
        </ActionForm>
      )}
      <button onClick={() => setEditing(!editing)}>
        {editing ? "Cancel editing" : "Edit a new revision"}
      </button>
      <DataState state={history}>
        {(rows) => (
          <>
            {editing && (
              <ActionForm
                label="Save revision for reapproval"
                success={refresh}
                onSubmit={(d) =>
                  api(`/questions/${q.id}`, "PATCH", {
                    question_text: d.get("text"),
                    options: Object.fromEntries(
                      "ABCD".split("").map((k) => [k, d.get(k)]),
                    ),
                    correct_answer: d.get("answer"),
                    explanation: d.get("explanation"),
                    comment: d.get("comment"),
                    expected_revision: rows.at(-1)?.revision,
                    is_critical: rows.at(-1)?.snapshot.is_critical ?? false,
                  })
                }
              >
                <Field label="Question text">
                  <textarea
                    name="text"
                    required
                    defaultValue={q.question_text}
                  />
                </Field>
                {"ABCD".split("").map((k) => (
                  <Field key={k} label={`Option ${k}`}>
                    <input name={k} required defaultValue={q.options[k]} />
                  </Field>
                ))}
                <Field label="Correct answer">
                  <select name="answer" defaultValue={q.correct_answer}>
                    {"ABCD".split("").map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Explanation">
                  <textarea
                    name="explanation"
                    required
                    defaultValue={q.explanation}
                  />
                </Field>
                <Field label="Reason for revision">
                  <textarea required name="comment" maxLength={1000} />
                </Field>
              </ActionForm>
            )}
            <h3>Revision history</h3>
            <ol className="timeline">
              {rows.map((r) => (
                <li key={r.id}>
                  <strong>
                    Revision {r.revision} · {r.action}
                  </strong>
                  <small>
                    {date(r.created_at)} · Actor {r.actor_id}
                  </small>
                  <details>
                    <summary>View frozen content</summary>
                    <p>{r.snapshot.question_text}</p>
                    {Object.entries(r.snapshot.options).map(([k, v]) => (
                      <p key={k}>
                        {k}: {v}
                      </p>
                    ))}
                    <p>
                      Correct: {r.snapshot.correct_answer} ·{" "}
                      {r.snapshot.explanation}
                    </p>
                  </details>
                </li>
              ))}
            </ol>
          </>
        )}
      </DataState>
    </Panel>
  );
}
