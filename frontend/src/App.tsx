// 壳：顶部导航（剧场 / 看板）+ 模式徽标（health 探测）
import { useEffect, useState } from "react";
import { getHealth } from "./api";
import Board from "./pages/Board";
import Learn from "./pages/Learn";

export default function App() {
  const [page, setPage] = useState<"learn" | "board">("learn");
  const [mode, setMode] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((h) => setMode(h.mode))
      .catch(() => setMode(null));
  }, []);

  return (
    <>
      <header className="topbar">
        <span className="brand">
          三代理学习剧场
          <span className="brand-sub">ai-tutoring-multi-agent</span>
        </span>
        <nav aria-label="页面导航">
          <button
            className={page === "learn" ? "nav on" : "nav"}
            onClick={() => setPage("learn")}
          >
            学习剧场
          </button>
          <button
            className={page === "board" ? "nav on" : "nav"}
            onClick={() => setPage("board")}
          >
            学情看板
          </button>
        </nav>
        {mode && <span className={`mode-pill mode-${mode}`}>{mode}</span>}
      </header>
      <main>{page === "learn" ? <Learn /> : <Board />}</main>
      <footer className="foot mono">
        planner → tutor → evaluator · 成本经 cost_tracker 记账 · API 见 /docs
      </footer>
    </>
  );
}
