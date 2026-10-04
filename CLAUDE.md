# AI 学习辅导多智能体系统 — 仓库工作约定（供 Claude Code）

本仓为可运行配套工程，是书稿代码块的 **source of truth**。

## 项目定位

三代理（planner / tutor / evaluator）协作的 AI 学习辅导系统，演示多代理架构、代理间通信、团队知识管理、Token 经济学与成本控制。

## 铁律

- **TDD**：每个模块先写失败测试 → 跑确认失败 → 实现 → 跑确认绿 → commit。
- **版本钉死**：依赖与 `version-lock.json` 的 `version_lock` 一致；不引入 lock 外的库。
- **只增不改**：扩充时不动现有模块签名/行为；新模块独立测试，CI 双跑。
- **mock-friendly**：`pip install -e . && pytest -q` 必须在无 Key、无 Docker、无网下全绿。

## 技术栈（版本钉死于 `version-lock.json`）

Python 3.10+ / Claude Agent SDK（最新稳定版）/ pytest 8

## 验收

```bash
pip install -e .       # 离线可用
pytest -q              # 必须全绿，无需 Key/Docker/网络
```

## 编码约定

- **代理职责单一**：planner 不讲课，tutor 不评估，evaluator 不规划。
- **上下文显式传递**：代理间通过 `shared_memory.SharedMemory` 实例传递，禁止用全局变量。
- **API 调用必须经 cost_tracker**：禁止裸调用 `client.messages.create()`，必须经过包装。
- **模型选型**：复杂规划与评估用 sonnet-4-6，简单讲解可降级到 haiku-4-5。

## 细则（docs/conventions/，按需引用）

- 目录结构与模块职责 → `docs/conventions/structure.md`
- Tag 规约：Release 格式 `v<MAJOR>.<MINOR>.<PATCH>-<YYYYMMDD>`，禁止删/覆盖，
  禁止 `git push --tags`（显式 `push origin <tag>`）→ `docs/conventions/tagging.md`
