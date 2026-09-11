# AI 学习辅导多智能体系统 — 仓库工作约定（供 Claude Code）

本仓为可运行配套工程，是书稿代码块的 **source of truth**。

## 项目定位

三代理（planner / tutor / evaluator）协作的 AI 学习辅导系统，演示多代理架构、代理间通信、团队知识管理、Token 经济学与成本控制。

## 铁律

- **TDD**：每个模块先写失败测试 → 跑确认失败 → 实现 → 跑确认绿 → commit。
- **版本钉死**：依赖与 `version-lock.json` 的 `version_lock` 一致；不引入 lock 外的库。
- **只增不改**：扩充时不动现有模块签名/行为；新模块独立测试，CI 双跑。
- **mock-friendly**：`pip install -e . && pytest -q` 必须在无 Key、无 Docker、无网下全绿。

## 技术栈与版本（钉死于 version-lock.json）

- Python 3.10+
- Claude Agent SDK（最新稳定版）
- pytest 8.x

## 验收

```bash
pip install -e .       # 离线可用（首次需联网，之后 node_modules 已就绪）
pytest -q              # 必须全绿，无需 Key/Docker/网络
```

## 目录结构

```
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

## 编码约定

- **代理职责单一**：planner 不讲课，tutor 不评估，evaluator 不规划。
- **上下文显式传递**：代理间通过 `shared_memory.SharedMemory` 实例传递，禁止用全局变量。
- **API 调用必须经 cost_tracker**：禁止裸调用 `client.messages.create()`，必须经过包装。
- **模型选型**：复杂规划与评估用 sonnet-4-6，简单讲解可降级到 haiku-4-5。

## Tag 规约

| 字段 | 值 |
|---|---|
| 格式 | `v<MAJOR>.<MINOR>.<PATCH>-<YYYYMMDD>` |
| 用途 | 公开里程碑（sprint 收尾 / 部署上线 / 版本基线） |
| 能否删 / 覆盖 | **禁止** |

样例：

- `v0.7.0-20260821` —— saas-nextjs backend 塌缩后的 0.7.0 release
- `v0.1.2-20260821` —— suite 根仓的 release（这次 form A → B + tag / submodule 规约更新）

> `<YYYYMMDD>` 是 tag 创建日（commit author date 也可，但要同一仓一致）。
> 不放 commit 数 —— `git describe` 会自动加 `-<N>-g<sha>` 后缀。
>
> **历史遗留**：tag（legacy，已按 Release 格式重命名）——
>
> - `v1.0-003` → `v0.0.1-20260627`（`12af366`）
> - `v1.0-Harness-工程：围绕-Claude-Code-构建可靠系统` → `v0.0.2-20260629`（`12af366`）
>
> 旧名已删，仅 Release 格式名生效；**新 tag 一律用 Release 格式**。

```bash
# 正确
git push origin v0.7.0-20260821

# 错误：可能误推未准备好的 tag
git push --tags
```

`--tags` 把本地**全部** tag 推上去。Release tag 应该显式 `push origin <tag>`，让
reviewer 在推送前显式选择。
