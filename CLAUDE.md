# ai-tutoring-multi-agent — Claude Code 项目级上下文

> 本文件是《Harness 工程》第 17 章「多代理架构」配套项目的项目级上下文。

## 项目定位

AI 学习辅导系统，演示 Claude Agent SDK 下三代理协作模式：

- **planner**：根据用户问题制定学习路径
- **tutor**：按路径分步讲解
- **evaluator**：评估学习效果并给出改进建议

用于讲解多代理架构、代理间通信、团队知识管理、Token 经济学与成本控制。

## 技术栈

| 类别 | 选型 | 版本 |
|------|------|------|
| 语言 | Python | 3.10+ |
| AI SDK | Claude Agent SDK | 最新稳定版 |
| 模型 | claude-sonnet-4-6 / claude-haiku-4-5 | 与书籍 version-lock 一致 |
| 测试 | pytest | 8.x |

## 目录结构

```
ai-tutoring-multi-agent/
├── pyproject.toml
├── .env.example                    ← ANTHROPIC_API_KEY 模板
├── CLAUDE.md                        ← 本文件
├── .claude/
│   ├── settings.json
│   └── agents/                      ← 三代理定义（第 17 章实物）
│       ├── planner.md
│       ├── tutor.md
│       └── evaluator.md
├── src/ai_tutoring/
│   ├── __init__.py
│   ├── orchestrator.py              ← 主调度（第 18 章）
│   ├── planner_agent.py
│   ├── tutor_agent.py
│   ├── evaluator_agent.py
│   ├── shared_memory.py             ← 代理间上下文共享（第 18 章）
│   └── cost_tracker.py              ← Token 经济学（第 20 章）
├── knowledge_base/                  ← 知识库样例（第 19 章）
│   ├── math/derivatives.md
│   ├── math/integrals.md
│   └── physics/mechanics.md
├── run_demo.py                      ← 一条命令跑完三代理协作
└── tests/
```

## 编码约定

- **代理职责单一**：planner 不讲课，tutor 不评估，evaluator 不规划。违反者重构。
- **上下文显式传递**：代理间通过 `shared_memory.SharedMemory` 实例传递，禁止用全局变量。
- **每次 API 调用必须计入 cost_tracker**：禁止裸调用 `client.messages.create()`，必须经过包装。
- **模型选型**：复杂规划与评估用 sonnet-4-6，简单讲解可降级到 haiku-4-5（写入 cost_tracker 备注）。
- **零伪代码**：禁止 `pass` 占位、`TODO`、`...`。

## 危险操作

- 修改 `.env`（涉及 API Key）
- 删除 `knowledge_base/` 下任何文件
- 在 `cost_tracker.py` 内绕过预算检查

## 预算控制

- 单次 demo 默认硬上限：$0.50
- 超出时 orchestrator 必须中止并报告
- 实现见 `src/ai_tutoring/cost_tracker.py`

## 与本书的关系

| 章节 | 本仓库对应 |
|------|----------|
| 第 17 章 多代理架构 | `.claude/agents/{planner,tutor,evaluator}.md` |
| 第 18 章 代理间通信 | `orchestrator.py` + `shared_memory.py` |
| 第 19 章 团队知识管理 | `knowledge_base/` |
| 第 20 章 生产级配置 | `cost_tracker.py` + `.claude/settings.json` |
