// 共享展示件：Learn（实时流）与 Board（只读回看）两页复用的纯组件
import type { CostInfo, Evaluation, Lesson, Plan, UsageRecord } from "./types";

const AGENT_LABEL: Record<string, string> = {
  planner: "规划代理",
  tutor: "辅导代理",
  evaluator: "评估代理",
};

export function AgentTag({ agent }: { agent: string }) {
  return (
    <span className={`agent-tag agent-${agent}`}>
      <i className="dot" aria-hidden />
      {AGENT_LABEL[agent] ?? agent}
    </span>
  );
}

export function PlanCard({ plan }: { plan: Plan }) {
  return (
    <section className="card">
      <div className="card-head">
        <AgentTag agent="planner" />
        <h3>学习路径 · {plan.topic}</h3>
      </div>
      {plan.rationale && <p className="muted">{plan.rationale}</p>}
      <ol className="steps">
        {plan.steps.map((s, i) => (
          <li key={i} className="step-chip">
            <span className="step-no">{String(i + 1).padStart(2, "0")}</span>
            {s}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function LessonCard({ lesson, index }: { lesson: Lesson; index: number }) {
  return (
    <section className="card lesson">
      <div className="card-head">
        <AgentTag agent="tutor" />
        <h3>
          第 {index + 1} 步 · {lesson.step}
        </h3>
      </div>
      {lesson.content.split(/\n+/).map((p, i) => (
        <p key={i}>{p}</p>
      ))}
      {lesson.key_points.length > 0 && (
        <ul className="chips">
          {lesson.key_points.map((k, i) => (
            <li key={i}>{k}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function EvalCard({ ev }: { ev: Evaluation }) {
  return (
    <section className="card eval">
      <div className="card-head">
        <AgentTag agent="evaluator" />
        <h3>理解度评估</h3>
      </div>
      <div className="eval-grid">
        <div className="score">
          <span className="score-num">{ev.understanding_score}</span>
          <span className="score-sub">/ 100</span>
        </div>
        <div className="two-col">
          <div>
            <h4>已掌握</h4>
            <ul className="list ok">
              {ev.strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4>待补强</h4>
            <ul className="list gap">
              {ev.gaps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <p className="verdict">{ev.recommendation}</p>
    </section>
  );
}

export function CostPanel({ cost }: { cost: CostInfo }) {
  const pct =
    cost.budget_usd && cost.budget_usd > 0
      ? Math.min(100, (cost.total_cost_usd / cost.budget_usd) * 100)
      : null;
  return (
    <section className="card cost">
      <div className="card-head">
        <h3>成本台账</h3>
      </div>
      <table className="cost-table">
        <thead>
          <tr>
            <th>代理</th>
            <th>模型</th>
            <th className="num">输入 tok</th>
            <th className="num">输出 tok</th>
            <th className="num">费用 USD</th>
          </tr>
        </thead>
        <tbody>
          {cost.records.map((r: UsageRecord, i) => (
            <tr key={i}>
              <td>
                <AgentTag agent={r.agent} />
              </td>
              <td className="mono">{r.model}</td>
              <td className="num mono">{r.input_tokens}</td>
              <td className="num mono">{r.output_tokens}</td>
              <td className="num mono">{r.cost_usd.toFixed(6)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="cost-foot">
        <span className="mono">
          合计 ${cost.total_cost_usd.toFixed(6)}
          {cost.budget_usd != null && (
            <> / 预算 ${cost.budget_usd.toFixed(2)}</>
          )}
        </span>
        {pct != null && (
          <span className="bar" role="img" aria-label={`预算用量 ${Math.round(pct)}%`}>
            <i style={{ width: `${pct}%` }} />
          </span>
        )}
      </div>
    </section>
  );
}
