# AI 学习辅导多智能体系统

三代理协作（planner / tutor / evaluator）的命令行学习辅导系统，配套《Codex 从入门到项目实践》卷五。

## 快速开始

```bash
pip install -e .          # 安装依赖（Python 3.10+）
cp .env.example .env      # 填入 ANTHROPIC_API_KEY
python run_demo.py "请教我导数"
pytest -q                 # 全量测试（FakeLLM，无需 API Key）
```

## 功能特性

- **三代理协作**：planner 制定路径、tutor 分步讲解、evaluator 评估效果
- **知识库**：数学/物理学科建模，支持扩展
- **出题与批改**：question_maker 生成选择题，grader 评分并反馈
- **自适应学习**：student_tracker 追踪掌握度，recommend_kp 推荐下一知识点
- **苏格拉底式辅导**：socratic_tutor 以提问引导思考
- **Token 经济学**：cost_tracker 实时追踪消耗，支持预算硬上限

## 技术栈

| 技术 | 版本 |
| :--- | :--- |
| Python | 3.10+ |
| Claude Agent SDK | 最新稳定版 |
| 测试框架 | pytest 8.x |

## 配套书籍及章节映射

| 章 | 主题 | 对应源文件 |
| :--- | :--- | :--- |
| 35 | 多智能体架构设计 | `.claude/agents/{planner,tutor,evaluator}.md` + `orchestrator.py` |
| 36 | 知识库与学科建模 | `knowledge_base/` |
| 37 | 出题智能体与批改智能体 | `src/ai_tutoring/{question_maker,grader}.py` |
| 38 | 学习路径规划与自适应引擎 | `src/ai_tutoring/{student_tracker,recommend_kp}.py` |
| 39 | 辅导对话智能体 | `src/ai_tutoring/socratic_tutor.py` |
| 40 | 家长看板与学情报告 | `src/ai_tutoring/shared_memory.py` |
| 41 | 集成测试、部署与项目回顾 | 全项目集成 + `tests/` |

## 快速链接

- [功能规格文档.md](功能规格文档.md) — 功能名称、描述与验收标准
- [CLAUDE.md](CLAUDE.md) — 开发约定与编码规范
