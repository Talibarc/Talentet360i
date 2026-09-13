export interface Identity {
  id: number;
  role: string;
  label: string;
  business_function: string | null;
}
export interface User {
  id: number;
  full_name: string;
  role: string;
  business_function: string | null;
  job_role_id: number | null;
  team: string | null;
  hub: string | null;
  xp_points: number;
}
export interface Role {
  id: number;
  role_name: string;
  business_function: string;
}
export interface Skill {
  id: number;
  name: string;
  category?: string | null;
}
export interface Mapping {
  id: number;
  role_id: number;
  skill_id: number;
  target_level: number | null;
  is_expected: boolean;
  target_label: string | null;
}
export interface Question {
  id: number;
  skill_id: number;
  skill_level: number;
  question_text: string;
  options: Record<string, string>;
  correct_answer: string;
  explanation: string;
  rag_source: string | null;
  status: string;
}
export interface Revision {
  id: number;
  revision: number;
  action: string;
  created_at: string;
  actor_id: number;
  snapshot: Question & { is_critical: boolean };
}
export interface Assessment {
  id: number;
  employee_id: number;
  role_skill_map_id: number;
  status: string;
  total_questions: number;
  correct_answers: number;
  score_percentage: number | null;
  achieved_level: number | null;
  xp_awarded: number;
}
export interface AssessmentDetail {
  assessment: Assessment;
  questions: {
    question_id: number;
    question_text: string;
    options: Record<string, string>;
  }[];
  review_status: string;
  review_revision: number;
  critical_failed: boolean;
}
export interface Evidence {
  id: number;
  employee_id: number;
  role_skill_map_id: number;
  assessment_id: number | null;
  status: string;
  revision: number;
  title: string;
  description: string;
  url: string | null;
  created_at: string;
}
export interface Decision {
  id: number;
  decision: string;
  comment: string;
  created_at: string;
  manager_id: number;
  confirmed_level: number | null;
}
export interface History {
  decisions: Decision[];
  revisions?: {
    id: number;
    revision: number;
    title: string;
    description: string;
    created_at: string;
  }[];
  review?: { status: string; revision: number };
}
export interface Resource {
  resource_id: string;
  title: string;
  url: string | null;
  source_file: string;
  source_sheet: string;
  source_row: number;
  level_scope: string | null;
  review_status: string | null;
  availability_status?: string | null;
}
export interface Gap {
  assessment_id: number;
  skill_name: string;
  current_level: number | null;
  target_level: number;
  skill_gap: number | null;
  official_confirmed_level: number | null;
  review_status: string;
  learning_status: string;
  learning_resources: Resource[];
  detail: {
    summary: string;
    development_focus: string;
    next_steps: string[];
    limitations: string[];
  };
}
export interface Tni {
  skills_assessed: number;
  target_met: number;
  development_needed: number;
  skill_gaps: Gap[];
  unassessed_skills: { skill_name: string; target_level: number; target_label?: string; learning_resources?: Resource[]; learning_status?: string }[];
}
export interface Notice {
  id: number;
  title: string;
  message: string;
  created_at: string;
  read_at: string | null;
}
export interface Quest {
  id: number;
  title: string;
  description: string;
  event_type: string;
  required_count: number;
  xp_reward: number;
  business_function: string | null;
}
export interface QuestProgress {
  quest: Quest;
  progress: number;
  completed: boolean;
  claimed: boolean;
}
export interface Audit {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  actor_id: number | null;
  created_at: string;
  details: Record<string, unknown>;
}
export interface Aggregate {
  basis: string;
  total_confirmed_records: number;
  groups: {
    skill: string;
    level: number;
    count: number;
    gap_count: number;
    total_gap: number;
  }[];
}
