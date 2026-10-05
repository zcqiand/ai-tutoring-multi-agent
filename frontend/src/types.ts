// API 形状镜像（与 src/ai_tutoring/api/routes.py 序列化输出一一对应）

export interface Plan {
  topic: string;
  rationale: string;
  steps: string[];
}

export interface Lesson {
  step: string;
  content: string;
  key_points: string[];
}

export interface Evaluation {
  understanding_score: number;
  strengths: string[];
  gaps: string[];
  recommendation: string;
}

export interface UsageRecord {
  agent: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface CostInfo {
  records: UsageRecord[];
  total_cost_usd: number;
  budget_usd: number | null;
}

export interface SessionDetail {
  id: string;
  question: string;
  created_at: string;
  plan: Plan | null;
  lessons: Lesson[];
  evaluation: Evaluation | null;
  cost: CostInfo;
}

export interface SessionSummary {
  id: string;
  question: string;
  created_at: string;
  lessons: number;
  score: number | null;
  total_cost_usd: number;
}

// SSE 事件（data 行内 JSON，event 判别字段）
export type SseEvent =
  | { event: "stage"; agent: "planner" | "tutor" | "evaluator"; step?: string }
  | { event: "plan"; plan: Plan }
  | { event: "lesson"; lesson: Lesson }
  | { event: "evaluation"; evaluation: Evaluation }
  | {
      event: "usage";
      record: UsageRecord;
      total_cost_usd: number;
      budget_usd: number | null;
    }
  | { event: "done"; detail: SessionDetail }
  | { event: "error"; message: string };

export interface Health {
  ok: boolean;
  mode: string;
}
