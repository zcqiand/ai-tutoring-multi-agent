# AI 学习辅导多智能体系统

> 三代理协作的命令行学习辅导系统——**《Codex 从入门到项目实践》卷五·AI 学习辅导多智能体系统**的可部署配套案例。

一款基于 Claude Agent SDK 的 AI 学习辅导多智能体系统：planner 制定学习路径、tutor 分步讲解、evaluator 评估效果。书中讲的每一个核心概念（多代理架构、代理间通信、团队知识管理、Token 经济学、成本控制……），在本仓库里都有对应的、可运行的最小实现，而不是停在截图或伪代码。

## 项目背景

为什么用「AI 学习辅导」来配书？多代理系统的复杂度刚好够用：

- **小而可跑**：零部署依赖，`pip install -e .` 后填入 API Key 即可跑，读者一次能读完整个仓库；
- **要素齐全**：多代理协作（planner / tutor / evaluator）、代理间通信（shared_memory）、知识管理（knowledge_base）、Token 经济学（cost_tracker）、预算控制一应俱全；
- **贴近实战**：每个人都能想象一个「AI 家教」的需求，业务逻辑简单，读者可以专注工程实现。

## 功能特性

### 业务功能

- planner 根据用户问题制定学习路径（分步大纲）
- tutor 按路径分步讲解，支持多轮追问
- evaluator 评估学习效果，给出改进建议
- question_maker 根据知识点和难度生成选择题
- grader 对学生答案进行打分和个性化反馈
- socratic_tutor 以苏格拉底式提问引导思考
- student_tracker 追踪学生掌握度和错题本（JSON 持久化）
- recommend_kp 基于自适应路径推荐下一个知识点
- shared_memory 在三代理间传递上下文，追踪完整学习轨迹
- cost_tracker 实时追踪 Token 消耗，支持预算硬上限

### 工程特性（教学要点）

- 三代理职责单一：planner 不讲课，tutor 不评估，evaluator 不规划
- 上下文显式传递：代理间通过 `SharedMemory` 实例传递，禁止全局变量
- 每次 API 调用必须过 cost_tracker，禁止裸调用
- 模型降级：复杂规划用 sonnet-4-6，简单讲解可降级到 haiku-4-5
- 零伪代码：禁止 `pass` / `TODO` / `...` 占位

## 章节映射

### 书一《Codex 从入门到项目实践》卷五·AI 学习辅导多智能体系统（第 35-41 章）

| 章节 | 对应代码 |
|------|---------|
| 第 35 章 多智能体架构设计 | `.claude/agents/{planner,tutor,evaluator}.md` + `orchestrator.py` |
| 第 36 章 知识库与学科建模 | `knowledge_base/` |
| 第 37 章 出题智能体与批改智能体 | `src/ai_tutoring/{question_maker,grader}.py` |
| 第 38 章 学习路径规划与自适应引擎 | `src/ai_tutoring/{student_tracker,recommend_kp}.py` |
| 第 39 章 辅导对话智能体 | `src/ai_tutoring/socratic_tutor.py` |
| 第 40 章 家长看板与学情报告 | `src/ai_tutoring/shared_memory.py`（数据聚合） |
| 第 41 章 集成测试、部署与项目回顾 | 全项目集成 + `tests/` |

### 书二《Harness 工程：围绕 Claude Code 构建可靠系统》多代理架构部分

| 章节 | 对应代码 |
|------|---------|
| 第 17 章 多代理架构 | `.claude/agents/{planner,tutor,evaluator}.md` |
| 第 18 章 代理间通信 | `orchestrator.py` + `shared_memory.py` |
| 第 19 章 团队知识管理 | `knowledge_base/` |
| 第 20 章 生产级配置 | `cost_tracker.py` + `.claude/settings.json` |

## 快速开始

```bash
# 安装（需要 Python 3.10+）
pip install -e .

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 运行
python run_demo.py "请教我导数"
```

预期输出：

```
[planner]   制定学习路径：导数定义 → 几何意义 → 求导法则 → 应用
[tutor]     讲解导数定义...
[tutor]     讲解几何意义...
[evaluator] 学习效果评估：理解度 85/100
─────────────────────────
Token 消耗：
  planner:   1,234 input / 567 output  ($0.0123)
  tutor:     5,678 input / 2,345 output ($0.0567)
  evaluator: 890 input / 234 output    ($0.0089)
  TOTAL:     7,802 input / 3,146 output ($0.0779)
```

## 部署架构

```
   用户问题
      │
      ▼
┌──────────────────┐
│  orchestrator    │  调度主循环（第 18 章）
└─────────┬────────┘
          │
   ┌──────┼──────┐─────────┐
   ▼      ▼      ▼         ▼
┌────────┐┌────────┐┌────────────┐
│planner ││ tutor  ││ evaluator  │
└────┬───┘└───┬────┘└─────┬──────┘
     │       │           │
     └───────┼───────────┘
             ▼
      ┌──────────────┐
      │shared_memory │  ← 代理间上下文共享
      └──────┬────────┘
             ▼
      ┌──────────────┐
      │knowledge_base │  ← 数学、物理样例
      └──────────────┘

  自适应学习扩展模块（独立调度）
  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐
  │ question_maker  │  │     grader     │  │ socratic_tutor   │
  │  出题 agent     │  │  评判 agent    │  │ 苏格拉底式辅导   │
  └────────┬────────┘  └────────┬───────┘  └──────────────────┘
           │                    │
           ▼                    ▼
  ┌─────────────────┐  ┌────────────────┐
  │ student_tracker │  │  recommend_kp  │
  │  学生追踪/持久化 │  │  自适应路径推荐 │
  └─────────────────┘  └────────────────┘
```

## 配套书籍

本仓库是以下书籍的可部署配套案例：

- **《Codex 从入门到项目实践》**（卷五·AI 学习辅导多智能体系统，第 35-41 章）— 南荣相如

  - 多代理架构设计 / 知识库与学科建模 / 出题与批改智能体 / 自适应学习引擎 / 苏格拉底式辅导 / 学情报告
  - 代码片段索引：[claude-code-book](https://github.com/zcqiand/claude-code-book)
  - 电子书籍网址：[亚马逊](https://www.amazon.com/dp/B0H3M3B8GG)

- **《Harness 工程：围绕 Claude Code 构建可靠系统》**（卷四·多代理架构，第 17-20 章）— 南荣相如

  - 多代理架构 / 代理间通信 / 团队知识管理 / Token 经济学与成本控制
  - 代码片段索引：[claudecode-harness-book](https://github.com/zcqiand/claudecode-harness-book)

**Issues**：[https://github.com/zcqiand/ai-tutoring-multi-agent/issues](https://github.com/zcqiand/ai-tutoring-multi-agent/issues)
