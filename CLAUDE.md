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

Web 层验收（同样离线）：

```bash
LLM_MODE=mock python -m ai_tutoring   # 后端起 8804，GET /api/health 应得 {"ok":true,"mode":"mock"}
cd frontend && npm run build          # tsc strict + vite，必须过
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

## 正式区 / 临时区（2026-10-24 人定，全产品线通用）

- 过程件不与正式件混放：任务卡/批次卡、片段（frags-*）、批次文件、合并/对账/自检脚本、门控回执（receipts-*）、调试日志、QC 抽帧——项目级进 `_work/`，章级/集级进所属正式目录下 `_work/` 子目录
- 正式区同名正式件有且仅有一个（不堆 v2/final 副本）
- 章节正文、章级门控记录（chapter-NNN.*）、各类台账 json 是正式件，不进 `_work`
- `_work/` 整目录 .gitignore，过程件可追溯由本地盘承担；`scratch/` 已废弃并入 `_work/`，临时区只认 `_work/` 一个入口（2026-10-27 人裁，同 xr-code-suite）
- 可再生件不入库（见 .gitignore）：node_modules、build、out、bin/obj、`**/_work/render`、hook 审计日志
