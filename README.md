# ai-tutoring-multi-agent

《Harness 工程：围绕 Claude Code 构建可靠系统》一书**卷四**的可部署案例项目——AI 学习辅导多智能体系统。

本仓库是书中讲解多代理架构、代理间通信、团队知识管理、生产级配置等概念的实物载体。

## 章节映射

| 章节 | 对应代码 |
|------|---------|
| 第 17 章 多代理架构 | `.claude/agents/{planner,tutor,evaluator}.md` |
| 第 18 章 代理间通信 | `src/ai_tutoring/orchestrator.py` + `shared_memory.py` |
| 第 19 章 团队知识管理 | `knowledge_base/` |
| 第 20 章 生产级配置 | `src/ai_tutoring/cost_tracker.py` + `.claude/settings.json` |

## 技术栈

- Python 3.10+
- Claude Agent SDK（Python 版）
- 三代理协作：planner（规划）→ tutor（辅导）→ evaluator（评估）

## 快速开始

```bash
# 1. 安装
pip install -e .

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 3. 运行 demo
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
   ┌──────┼──────┬─────────┐
   ▼      ▼      ▼         ▼
┌────────┐┌────────┐┌────────────┐
│planner ││ tutor  ││ evaluator  │
└────┬───┘└───┬────┘└─────┬──────┘
     │       │           │
     └───────┼───────────┘
             ▼
      ┌──────────────┐
      │ shared_memory │
      └──────┬────────┘
             ▼
      ┌──────────────┐
      │knowledge_base │  ← 数学、物理样例
      └──────────────┘
```

## 配套书籍

- **书名**：Harness 工程：围绕 Claude Code 构建可靠系统
- **作者**：南荣相如
- **代码片段索引**：[claudecode-harness-book](https://github.com/zcqiand/claudecode-harness-book)
- **Issues**：https://github.com/zcqiand/ai-tutoring-multi-agent/issues
