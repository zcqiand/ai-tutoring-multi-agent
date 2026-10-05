# AI 学习辅导多智能体系统

三代理协作（planner / tutor / evaluator）的命令行学习辅导系统，配套《Harness 工程：围绕 Claude Code 构建可靠系统》。

## 快速开始

```bash
pip install -e .          # 安装依赖（Python 3.10+）
cp .env.example .env      # 填入 ANTHROPIC_API_KEY
ai-tutor-demo "请教我导数"
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

### 书一《Harness 工程：围绕 Claude Code 构建可靠系统》

配套版本：`v0.1.1-20260909`（本书全部引用源文件以此 tag 为准；其后提交仅为文档修订，代码未变）

案例以「案例对照」小节嵌入第 17—20 章机制讲解，对应源文件如下（均在配套 tag 下真实存在）：

| 章 | 主题 | 对应源文件 |
| :--- | :--- | :--- |
| 17 多代理（§17.5.1 案例对照） | 运行时三代理与 Claude Code 子代理的两层区分 | `src/ai_tutoring/agents.py` |
| 18 代理协作（§18.6.1 案例对照） | 星型总线：orchestrator 中心化数据流 | `src/ai_tutoring/orchestrator.py` |
| 19 团队知识库（§19.10.1 案例对照） | 团队开发知识 vs 项目运行时学科知识 | `knowledge_base/math/*.md` |
| 20 生产级部署（§20.10.1 案例对照） | 开发成本控制 vs 运行时成本控制 | `src/ai_tutoring/cost_tracker.py` |

> 其余模块（question_maker / grader / student_tracker / recommend_kp / socratic_tutor / shared_memory）为项目完整功能的一部分，见 [功能规格.md](docs/功能规格.md)。

## 快速链接

- [CLAUDE.md](CLAUDE.md) — 开发约定与编码规范
- [功能规格.md](docs/功能规格.md) — 功能名称、描述与验收标准
