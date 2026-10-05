// 学情看板：会话列表 → 选中载入详情只读回看（复用剧场展示件）
import { useCallback, useEffect, useState } from "react";
import { getSession, listSessions } from "../api";
import type { SessionDetail, SessionSummary } from "../types";
import { CostPanel, EvalCard, LessonCard, PlanCard } from "../pieces";

export default function Board() {
  const [items, setItems] = useState<SessionSummary[] | null>(null);
  const [selected, setSelected] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    listSessions()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(refresh, [refresh]);

  function open(sid: string) {
    setSelected(null);
    setError(null);
    getSession(sid)
      .then(setSelected)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }

  return (
    <div className="page">
      <div className="board-head">
        <h2>学情看板</h2>
        <button className="btn ghost" onClick={refresh} disabled={loading}>
          {loading ? "刷新中…" : "刷新"}
        </button>
      </div>
      {error && (
        <div className="card errbar" role="alert">
          <strong>加载失败：</strong>
          {error}
        </div>
      )}
      {items !== null && items.length === 0 && (
        <p className="muted empty-hint">
          还没有会话记录。回「学习剧场」完成一次学习，这里就会出现学情档案。
        </p>
      )}
      {items !== null && items.length > 0 && (
        <table className="board-table card">
          <thead>
            <tr>
              <th>问题</th>
              <th className="num">讲义</th>
              <th className="num">理解分</th>
              <th className="num">成本 USD</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr
                key={r.id}
                onClick={() => open(r.id)}
                className={selected?.id === r.id ? "sel" : undefined}
              >
                <td>{r.question}</td>
                <td className="num mono">{r.lessons}</td>
                <td className="num mono">{r.score ?? "—"}</td>
                <td className="num mono">{r.total_cost_usd.toFixed(4)}</td>
                <td className="mono">{r.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted table-hint">点击行查看完整学情档案（内存会话库，重启后即清空）。</p>

      {selected && (
        <div className="detail">
          <div className="detail-meta card">
            <span className="mono">#{selected.id}</span>
            <span>{selected.question}</span>
            <span className="mono">{selected.created_at}</span>
          </div>
          {selected.plan && <PlanCard plan={selected.plan} />}
          {selected.lessons.map((l, i) => (
            <LessonCard key={i} lesson={l} index={i} />
          ))}
          {selected.evaluation && <EvalCard ev={selected.evaluation} />}
          <CostPanel cost={selected.cost} />
        </div>
      )}
    </div>
  );
}
