# 目录结构与模块职责

> 从 CLAUDE.md 移出（L0 60 行门）。树是文件系统的复写，以仓库实际为准；
> 模块职责注解在此维护。

```text
ai-tutoring-multi-agent/
├── pyproject.toml
├── .env.example
├── CLAUDE.md
├── .claude/
│   ├── settings.json
│   └── agents/                  ← 三代理定义
│       ├── planner.md
│       ├── tutor.md
│       └── evaluator.md
├── src/ai_tutoring/
│   ├── __init__.py
│   ├── orchestrator.py          ← 主调度
│   ├── planner_agent.py
│   ├── tutor_agent.py
│   ├── evaluator_agent.py
│   ├── shared_memory.py         ← 代理间上下文共享
│   ├── cost_tracker.py          ← Token 经济学
│   ├── question_maker.py
│   ├── grader.py
│   ├── student_tracker.py
│   ├── recommend_kp.py
│   ├── socratic_tutor.py
│   ├── config.py                ← Web 层：Settings 装配（LLM_MODE 必填，fail-fast）
│   ├── mock_llm.py              ← Web 层：MockLLM 兼测试件兼离线演示（满足三 parser 格式）
│   ├── session_store.py         ← Web 层：内存会话库（demo 性质，重启即清）
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            ← Web 层：/api/sessions CRUD + run SSE 直通
│   ├── main.py                  ← Web 层：create_app 工厂（settings/llm 注入）
│   └── __main__.py              ← python -m ai_tutoring = uvicorn 起服务
├── frontend/                    ← Web 前端（React 18 + Vite + TS，同源相对 /api）
│   ├── package.json
│   ├── vite.config.ts           ← 5804；dev/preview 均代理 /api → 127.0.0.1:8804
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              ← 壳：导航 + health 模式徽标
│       ├── types.ts             ← API 形状镜像
│       ├── api.ts               ← getJSON/postJSON + SSE reader（\n\n 分帧）
│       ├── pieces.tsx           ← 共享展示件（Plan/Lesson/Eval/Cost 卡）
│       ├── styles.css           ← 工程蓝图风 token 系统
│       └── pages/
│           ├── Learn.tsx        ← 三代理剧场（SSE 事件驱动）
│           └── Board.tsx        ← 学情看板（列表 + 只读详情）
├── knowledge_base/              ← 知识库样例
│   ├── math/derivatives.md
│   ├── math/integrals.md
│   └── physics/mechanics.md
├── run_demo.py
└── tests/                       ← 含 test_api.py（TestClient 全链路离线 e2e）
```
