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
│   └── socratic_tutor.py
├── knowledge_base/              ← 知识库样例
│   ├── math/derivatives.md
│   ├── math/integrals.md
│   └── physics/mechanics.md
├── run_demo.py
└── tests/
```
