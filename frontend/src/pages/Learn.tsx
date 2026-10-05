// 学习剧场：提问 → SSE 逐事件驱动三代理线路图点亮 → 讲义/评估/成本台账
import { useRef, useState } from "react";
import { createSession, runSession } from "../api";
import type { Evaluation, Lesson, Plan, SseEvent, UsageRecord } from "../types";
import { AgentTag, CostPanel, EvalCard, LessonCard, PlanCard } from "../pieces";

type Stage = { agent: "planner" | "tutor" | "evaluator"; step?: string } | null;

const NODES = [
  { key: "planner", label: "规划代理", sub: "拆解学习路径" },
  { key: "tutor", label: "辅导代理", sub: "逐步讲解" },
  { key: "evaluator", label: "评估代理", sub: "理解度打分" },
] as const;

export default function Learn() {
  const [question, setQuestion] = useState("");
  const [maxSteps, setMaxSteps] = useState(2);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<Stage>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [usage, setUsage] = useState<UsageRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [budget, setBudget] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  function reset() {
    setStage(null);
    setPlan(null);
    setLessons([]);
    setEvaluation(null);
    setUsage([]);
    setTotal(0);
    setBudget(null);
    setError(null);
  }

  function onEvent(ev: SseEvent) {
    switch (ev.event) {
      case "stage":
        setStage({ agent: ev.agent, step: ev.step });
        break;
      case "plan":
        setPlan(ev.plan);
        setStage(null);
        break;
      case "lesson":
        setLessons((prev) => [...prev, ev.lesson]);
        setStage(null);
        break;
      case "evaluation":
        setEvaluation(ev.evaluation);
        setStage(null);
        break;
      case "usage":
        setUsage((prev) => [...prev, ev.record]);
        setTotal(ev.total_cost_usd);
        setBudget(ev.budget_usd);
        break;
      case "done":
        setStage(null);
        break;
      case "error":
        setError(ev.message);
        setStage(null);
        break;
    }
  }

  async function start() {
    const q = question.trim();
    if (!q || running) return;
    reset();
    setRunning(true);
    try {
      const s = await createSession(q);
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      await runSession(s.id, maxSteps, onEvent, ctrl.signal);
    } catch (e) {
      const aborted = e instanceof DOMException && e.name === "AbortError";
      if (!aborted) setError(e instanceof Error ? e.message : String(e));
    } finally {
      abortRef.current = null;
      setRunning(false);
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  function nodeStatus(key: string): "idle" | "active" | "done" {
    if (key === "planner") {
      if (plan) return "done";
    } else if (key === "tutor") {
      if (lessons.length > 0 && stage?.agent !== "tutor") return "done";
    } else if (evaluation) return "done";
    return stage?.agent === key ? "active" : "idle";
  }

  const started = plan !== null || lessons.length > 0 || error !== null;

  return (
    <div className="page">
      <section className="card ask">
        <div className="ask-row">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !running && start()}
            placeholder="想学什么？例如：请教我导数"
            disabled={running}
            aria-label="学习问题"
          />
          <label className="steps-pick">
            讲解步数
            <select
              value={maxSteps}
              onChange={(e) => setMaxSteps(Number(e.target.value))}
              disabled={running}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          {running ? (
            <button className="btn ghost" onClick={stop}>
              停止
            </button>
          ) : (
            <button className="btn amber" onClick={start} disabled={!question.trim()}>
              开始学习
            </button>
          )}
        </div>
        {stage && (
          <p className="stage-line">
            <AgentTag agent={stage.agent} />
            <span className="mono">
              {stage.step ? `正在讲解：${stage.step}` : "运行中…"}
            </span>
          </p>
        )}
      </section>

      <div className="roadmap" role="img" aria-label="三代理流水线状态">
        {NODES.map((n, i) => {
          const st = nodeStatus(n.key);
          return (
            <div className="road-cell" key={n.key}>
              <div className={`node ${st} node-${n.key}`}>
                <i className="dot" aria-hidden />
                <div>
                  <span className="node-label">{n.label}</span>
                  <span className="node-sub">{n.sub}</span>
                </div>
              </div>
              {i < NODES.length - 1 && <i className="wire" aria-hidden />}
            </div>
          );
        })}
      </div>

      {error && (
        <div className="card errbar" role="alert">
          <strong>中止：</strong>
          {error}
        </div>
      )}

      {!started && (
        <p className="muted empty-hint">
          尚无会话。输入一个问题，三代理将依次完成规划 → 讲解 → 评估，成本实时记账。
        </p>
      )}

      {plan && <PlanCard plan={plan} />}
      {lessons.map((l, i) => (
        <LessonCard key={i} lesson={l} index={i} />
      ))}
      {evaluation && <EvalCard ev={evaluation} />}
      {usage.length > 0 && (
        <CostPanel cost={{ records: usage, total_cost_usd: total, budget_usd: budget }} />
      )}
    </div>
  );
}
