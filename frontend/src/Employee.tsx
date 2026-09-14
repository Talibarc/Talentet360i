import { useState } from "react";
import type { Api } from "./api";
import { safeUrl } from "./api";
import type {
  Assessment,
  AssessmentDetail,
  Evidence,
  History,
  QuestProgress,
  Tni,
  User,
} from "./types";
import type { Catalog } from "./Admin";
import { mappingName } from "./catalog";
import { MappingSelect } from "./Admin";
import { useResource } from "./hooks";
import { date } from "./format";
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
export function HistoryView({ api, path }: { api: Api; path: string }) {
  const state = useResource<History>(api, path);
  return (
    <DataState state={state}>
      {(h) => (
        <>
          {h.revisions?.map((r) => (
            <div className="inset" key={r.id}>
              <strong>
                Evidence revision {r.revision}: {r.title}
              </strong>
              <p>{r.description}</p>
            </div>
          ))}
          {!h.decisions.length ? (
            <Empty>No manager decisions recorded yet.</Empty>
          ) : (
            <ol className="timeline">
              {h.decisions.map((d) => (
                <li key={d.id}>
                  <Chip>{d.decision}</Chip>
                  <p>{d.comment}</p>
                  <small>
                    {date(d.created_at)} · Manager {d.manager_id}
                    {d.confirmed_level !== null
                      ? ` · Confirmed level ${d.confirmed_level}`
                      : ""}
                  </small>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </DataState>
  );
}
export function TniView({ api, userId }: { api: Api; userId: number }) {
  const state = useResource<Tni>(api, `/users/${userId}/tni`);
  return (
    <DataState state={state}>
      {(t) => (
        <>
          <div className="stats">
            <Stat
              label="Skills assessed"
              value={t.skills_assessed}
              note="Calculated assessment results"
            />
            <Stat
              label="Calculated target met"
              value={t.target_met}
              note="Manager confirmation remains separate"
            />
            <Stat
              label="Development areas"
              value={t.development_needed}
              note="Compared with role targets"
            />
          </div>
          <div className="two-col">
            {t.skill_gaps.map((g) => (
              <Panel
                key={g.assessment_id}
                title={g.skill_name}
                action={<Chip>{g.review_status}</Chip>}
              >
                <div className="level-comparison">
                  <div>
                    <small>Calculated / provisional</small>
                    <strong>
                      {g.current_level === null
                        ? "Pending policy validation"
                        : `Level ${g.current_level}`}
                    </strong>
                  </div>
                  <div>
                    <small>Official confirmed</small>
                    <strong>
                      {g.official_confirmed_level === null
                        ? "Not confirmed"
                        : `Level ${g.official_confirmed_level}`}
                    </strong>
                  </div>
                  <div>
                    <small>Role target</small>
                    <strong>Level {g.target_level}</strong>
                  </div>
                </div>
                <p>{g.detail.summary}</p>
                <h3>Learning journey</h3>
                <p>{g.detail.development_focus}</p>
                <ol>
                  {g.detail.next_steps.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ol>
                <h3>Mapped learning resources</h3>
                {g.learning_resources.length ? (
                  g.learning_resources.map((r) => (
                    <div className="inset" key={r.resource_id}>
                      {safeUrl(r.url) ? (
                        <a
                          href={safeUrl(r.url)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {r.title}
                        </a>
                      ) : (
                        <strong>{r.title}</strong>
                      )}
                      <small>
                        {r.source_file} · {r.source_sheet}, row {r.source_row}
                      </small>
                      <p>
                        Scope: {r.level_scope ?? "Not supplied"} · Approval:{" "}
                        {r.review_status ?? "Not supplied"}
                        {r.availability_status
                          ? ` · Availability: ${r.availability_status.replaceAll("_", " ")}`
                          : ""}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="source-note">
                    No supported learning mapping is available. No course
                    recommendations have been invented. Status:{" "}
                    {g.learning_status.replaceAll("_", " ")}
                  </p>
                )}
                <details>
                  <summary>Result limitations</summary>
                  {g.detail.limitations.map((l) => (
                    <p key={l}>{l}</p>
                  ))}
                </details>
              </Panel>
            ))}
          </div>
          {t.unassessed_skills.map((s) => (
            <div className="card row" key={s.skill_name}>
              <div>
                <strong>{s.skill_name}</strong>
                <p>
                  Target {s.target_label ?? `level ${s.target_level}`} · Current
                  level has not been calculated.
                </p>
                {s.learning_resources?.map((r) => (
                  <p key={r.resource_id}>
                    {safeUrl(r.url) ? (
                      <a href={safeUrl(r.url)} target="_blank" rel="noreferrer">
                        {r.title}
                      </a>
                    ) : (
                      r.title
                    )}{" "}
                    <small>
                      {r.source_file}, row {r.source_row}
                    </small>
                  </p>
                ))}
                {s.learning_resources?.length === 0 && (
                  <p>Mapping unavailable — pending source validation.</p>
                )}
              </div>
              <Chip>not_assessed</Chip>
            </div>
          ))}
          {!t.skill_gaps.length && !t.unassessed_skills.length && (
            <Empty>
              No expected skills or submitted assessments are available.
            </Empty>
          )}
        </>
      )}
    </DataState>
  );
}
export default function Employee({
  api,
  user,
  catalog,
  page,
  refresh,
}: {
  api: Api;
  user: User;
  catalog: Catalog;
  page: string;
  refresh: () => void;
}) {
  const [version, setVersion] = useState(0),
    [assessment, setAssessment] = useState<number | null>(null),
    [history, setHistory] = useState<string | null>(null),
    [edit, setEdit] = useState<Evidence | null>(null),
    [startError, setStartError] = useState("");
  const assessments = useResource<Assessment[]>(api, "/assessments", version),
    evidence = useResource<Evidence[]>(api, "/evidence", version);
  const update = () => {
    setVersion((v) => v + 1);
    refresh();
  };
  return (
    <>
      {page === "learning" ? (
        <TniView key={version} api={api} userId={user.id} />
      ) : page === "quests" ? (
        <QuestView api={api} refresh={update} />
      ) : page === "evidence" ? (
        <>
          <Panel title="Submit skill evidence">
            <p className="muted">
              Describe your work and optionally link supporting material. Use
              synthetic examples in this local demo. File uploads are not
              supported.
            </p>
            <ActionForm
              label="Submit evidence"
              success={update}
              onSubmit={(d) =>
                api("/evidence", "POST", {
                  role_skill_map_id: Number(d.get("mapping")),
                  assessment_id: d.get("assessment")
                    ? Number(d.get("assessment"))
                    : null,
                  title: d.get("title"),
                  description: d.get("description"),
                  url: d.get("url") || null,
                })
              }
            >
              <Field label="Skill">
                <MappingSelect catalog={catalog} />
              </Field>
              <Field label="Link a submitted assessment (optional)">
                <select name="assessment">
                  <option value="">Standalone evidence</option>
                  {assessments.data
                    ?.filter((a) => a.status === "submitted")
                    .map((a) => (
                      <option value={a.id} key={a.id}>
                        Assessment {a.id} ·{" "}
                        {mappingName(catalog, a.role_skill_map_id)}
                      </option>
                    ))}
                </select>
              </Field>
              <EvidenceFields />
            </ActionForm>
          </Panel>
          <Panel title="Evidence history">
            <DataState state={evidence}>
              {(rows) =>
                rows.length ? (
                  rows.map((e) => (
                    <div className="record" key={e.id}>
                      <div className="row">
                        <h3>{e.title}</h3>
                        <Chip>{e.status}</Chip>
                      </div>
                      <p>{e.description}</p>
                      {safeUrl(e.url) && (
                        <a
                          href={safeUrl(e.url)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open supporting link
                        </a>
                      )}
                      <small>
                        {mappingName(catalog, e.role_skill_map_id)} · Revision{" "}
                        {e.revision}
                      </small>
                      <div className="actions">
                        <button
                          onClick={() =>
                            setHistory(`/evidence/${e.id}/history`)
                          }
                        >
                          View history
                        </button>
                        {e.status === "sent_back" && (
                          <button onClick={() => setEdit(e)}>
                            Revise and resubmit
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <Empty>
                    No evidence yet. Submit work against an expected skill to
                    begin.
                  </Empty>
                )
              }
            </DataState>
          </Panel>
        </>
      ) : (
        <>
          <div className="welcome">
            <span className="eyebrow">Your development workspace</span>
            <h2>Build skills. Demonstrate progress.</h2>
            <p>
              Complete your assessments, reflect on your skill gaps, and share
              evidence with your manager.
            </p>
            <div className="journey">
              <span>01 Assess</span>
              <span>02 Develop</span>
              <span>03 Share evidence</span>
              <span>04 Manager confirms</span>
            </div>
          </div>
          <Panel title="Your assessments">
            {startError && <p role="alert">{startError}</p>}
            <DataState state={assessments}>
              {(rows) =>
                rows.some((a) =>
                  page === "results"
                    ? a.status === "submitted"
                    : a.status !== "submitted",
                ) ? (
                  rows
                    .filter((a) =>
                      page === "results"
                        ? a.status === "submitted"
                        : a.status !== "submitted",
                    )
                    .map((a) => (
                      <div className="record" key={a.id}>
                        <div className="row">
                          <div>
                            <h3>{mappingName(catalog, a.role_skill_map_id)}</h3>
                            <small>
                              Assessment {a.id} · {a.total_questions} questions
                            </small>
                          </div>
                          <Chip>{a.status}</Chip>
                        </div>
                        {a.status === "submitted" ? (
                          <>
                            <div className="level-comparison">
                              <div>
                                <small>Score</small>
                                <strong>{a.score_percentage}%</strong>
                              </div>
                              <div>
                                <small>Calculated / provisional</small>
                                <strong>
                                  {a.achieved_level === null
                                    ? "Pending policy validation"
                                    : `Level ${a.achieved_level}`}
                                </strong>
                              </div>
                              <div>
                                <small>Engagement</small>
                                <strong>+{a.xp_awarded} XP</strong>
                              </div>
                            </div>
                            <button onClick={() => setAssessment(a.id)}>
                              Result and review status
                            </button>
                          </>
                        ) : (
                          <button
                            className="primary"
                            onClick={async () => {
                              setStartError("");
                              try {
                                await api(`/assessments/${a.id}/start`, "POST");
                                setAssessment(a.id);
                                setVersion((v) => v + 1);
                              } catch (error) {
                                setStartError(
                                  error instanceof Error
                                    ? error.message
                                    : "Could not start assessment. Please retry.",
                                );
                              }
                            }}
                          >
                            {a.status === "in_progress"
                              ? "Resume assessment"
                              : "Start Assessment"}
                          </button>
                        )}
                      </div>
                    ))
                ) : (
                  <Empty>
                    No assessment assigned yet. Your manager or L&D can assign
                    approved questions.{" "}
                    {user.business_function === "DataOps" &&
                      "The Faiza question source is Unavailable — excluded from MVP. Imported records: 0."}
                  </Empty>
                )
              }
            </DataState>
          </Panel>
        </>
      )}
      {assessment !== null && (
        <Modal
          title={`Assessment ${assessment}`}
          close={() => setAssessment(null)}
        >
          <AssessmentScreen
            key={`${assessment}-${version}`}
            api={api}
            id={assessment}
            refresh={update}
          />
        </Modal>
      )}
      {history && (
        <Modal title="Evidence history" close={() => setHistory(null)}>
          <HistoryView api={api} path={history} />
        </Modal>
      )}
      {edit && (
        <Modal title="Revise sent-back evidence" close={() => setEdit(null)}>
          <HistoryView api={api} path={`/evidence/${edit.id}/history`} />
          <ActionForm
            label="Resubmit evidence"
            success={() => {
              setEdit(null);
              update();
            }}
            onSubmit={(d) =>
              api(`/evidence/${edit.id}/resubmit`, "POST", {
                title: d.get("title"),
                description: d.get("description"),
                url: d.get("url") || null,
                expected_revision: edit.revision,
              })
            }
          >
            <EvidenceFields evidence={edit} />
          </ActionForm>
        </Modal>
      )}
    </>
  );
}
function EvidenceFields({ evidence }: { evidence?: Evidence }) {
  return (
    <>
      <Field label="Evidence title">
        <input
          name="title"
          required
          maxLength={200}
          defaultValue={evidence?.title}
        />
      </Field>
      <Field label="Work performed and what it demonstrates">
        <textarea
          name="description"
          required
          maxLength={10000}
          defaultValue={evidence?.description}
        />
      </Field>
      <Field label="Supporting URL (optional)">
        <input
          name="url"
          type="url"
          pattern="https?://.*"
          defaultValue={evidence?.url ?? ""}
        />
      </Field>
    </>
  );
}
function AssessmentScreen({
  api,
  id,
  refresh,
}: {
  api: Api;
  id: number;
  refresh: () => void;
}) {
  const state = useResource<AssessmentDetail>(api, `/assessments/${id}`),
    [answers, setAnswers] = useState<Record<number, string>>({}),
    [index, setIndex] = useState(0);
  return (
    <DataState state={state}>
      {(d) =>
        d.assessment.status === "submitted" ? (
          <>
            <div className="stats">
              <Stat
                label="Score"
                value={`${d.assessment.score_percentage}%`}
                note="Deterministically calculated"
              />
              <Stat
                label="Provisional level"
                value={
                  d.assessment.achieved_level ?? "Pending policy validation"
                }
                note="Official level requires manager confirmation"
              />
            </div>
            {d.skill_results?.length ? (
              <Panel title="Assessed skills">
                {d.skill_results.map((r) => (
                  <p key={r.role_skill_map_id}>
                    {r.source_skill_id ? `${r.source_skill_id} — ` : ""}{r.skill_name}: {r.score_percentage}% ·{" "}
                    {r.total_questions} questions ·{" "}
                    {r.achieved_level ?? "Pending policy validation."}
                  </p>
                ))}
              </Panel>
            ) : null}
            <Chip>{d.review_status}</Chip>
            <HistoryView api={api} path={`/assessments/${id}/history`} />
            {d.review_status === "sent_back" && (
              <ActionForm
                label="Request another review"
                success={refresh}
                onSubmit={(f) =>
                  api(`/assessments/${id}/resubmit-review`, "POST", {
                    expected_revision: d.review_revision,
                    comment: f.get("comment"),
                  })
                }
              >
                <Field label="Response to manager">
                  <textarea name="comment" required maxLength={2000} />
                </Field>
              </ActionForm>
            )}
          </>
        ) : (
          <>
            <div className="row">
              <strong>
                Question {index + 1} of {d.questions.length}
              </strong>
              <span>{Object.keys(answers).length} answered</span>
            </div>
            <progress
              aria-label="Assessment completion"
              value={Object.keys(answers).length}
              max={d.questions.length}
            />
            <h3>{d.questions[index]?.question_text}</h3>
            <div className="answers">
              {Object.entries(d.questions[index]?.options ?? {}).map(
                ([k, v]) => (
                  <label
                    className={`answer ${answers[d.questions[index].question_id] === k ? "chosen" : ""}`}
                    key={k}
                  >
                    <input
                      aria-label={`${k} ${v}`}
                      type="radio"
                      name={`question-${d.questions[index].question_id}`}
                      checked={answers[d.questions[index].question_id] === k}
                      onChange={() =>
                        setAnswers({
                          ...answers,
                          [d.questions[index].question_id]: k,
                        })
                      }
                    />
                    <b>{k}</b>
                    <span>{v}</span>
                  </label>
                ),
              )}
            </div>
            <div className="row">
              <button
                disabled={index === 0}
                onClick={() => setIndex((i) => i - 1)}
              >
                Previous
              </button>
              <button
                disabled={index === d.questions.length - 1}
                onClick={() => setIndex((i) => i + 1)}
              >
                Next question
              </button>
            </div>
            <p className="muted">
              Answers are final after submission. Progress is kept while this
              assessment stays open.
            </p>
            {Object.keys(answers).length === d.questions.length ? (
              <ActionForm
                label="Submit assessment"
                success={refresh}
                onSubmit={() =>
                  api(`/assessments/${id}/submit`, "POST", {
                    answers: d.questions.map((q) => ({
                      question_id: q.question_id,
                      selected_answer: answers[q.question_id],
                    })),
                  })
                }
              >
                <span />
              </ActionForm>
            ) : (
              <p>Answer every question to submit.</p>
            )}
          </>
        )
      }
    </DataState>
  );
}
function QuestView({ api, refresh }: { api: Api; refresh: () => void }) {
  const [version, setVersion] = useState(0),
    quests = useResource<QuestProgress[]>(api, "/quests", version),
    xp = useResource<{
      xp_points: number;
      affects_proficiency: boolean;
      awards: {
        id: number;
        points: number;
        source_key: string;
        created_at: string;
      }[];
    }>(api, "/xp", version);
  return (
    <>
      <DataState state={xp}>
        {(x) => (
          <>
            <div className="stats">
              <Stat
                label="Your engagement XP"
                value={x.xp_points}
                note="XP never changes official proficiency"
              />
            </div>
            <Panel title="XP activity">
              {x.awards.length ? (
                x.awards.map((a) => (
                  <div className="row record" key={a.id}>
                    <span>
                      {a.source_key} <small>{date(a.created_at)}</small>
                    </span>
                    <strong>+{a.points} XP</strong>
                  </div>
                ))
              ) : (
                <Empty>No XP awarded yet.</Empty>
              )}
            </Panel>
          </>
        )}
      </DataState>
      <Panel title="SkillQuest">
        <p className="muted">
          Progress counts qualifying activity after each quest was published.
        </p>
        <DataState state={quests}>
          {(rows) =>
            rows.length ? (
              rows.map((p) => (
                <div className="record" key={p.quest.id}>
                  <div className="row">
                    <h3>{p.quest.title}</h3>
                    <Chip>
                      {p.claimed
                        ? "claimed"
                        : p.completed
                          ? "completed"
                          : "in_progress"}
                    </Chip>
                  </div>
                  <p>{p.quest.description}</p>
                  <progress
                    aria-label={`${p.quest.title} progress`}
                    value={p.progress}
                    max={p.quest.required_count}
                  />
                  <p>
                    {p.progress} / {p.quest.required_count} ·{" "}
                    {p.quest.xp_reward} engagement XP
                  </p>
                  {p.completed && !p.claimed && (
                    <ActionForm
                      label="Claim reward"
                      onSubmit={() =>
                        api(`/quests/${p.quest.id}/claim`, "POST")
                      }
                      success={() => {
                        setVersion((v) => v + 1);
                        refresh();
                      }}
                    >
                      <span />
                    </ActionForm>
                  )}
                </div>
              ))
            ) : (
              <Empty>
                No quests published for your function. L&D can publish a new
                engagement quest.
              </Empty>
            )
          }
        </DataState>
      </Panel>
    </>
  );
}
