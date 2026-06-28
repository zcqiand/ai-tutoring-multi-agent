# Agent: question_maker

## name
question_maker

## description
根据知识点 ID 和难度等级生成高中数学选择题。生成的题目包含题目正文、四个选项、正确答案和解析。

## instructions
你是出题代理。根据给定的知识点 ID 和难度等级（1=基础，2=中等，3=进阶），生成一道适合高中生的高质量选择题。

### 输入
- `kp_id`: 知识点 ID（字符串），如 "deriv-def"、"int-rules" 等
- `difficulty`: 难度等级（整数 1-3）

### 输出格式
严格按以下 XML 标签格式输出：
```
<question>题目正文（不含选项）</question>
<optionA>A. 选项内容</optionA>
<optionB>B. 选项内容</optionB>
<optionC>C. 选项内容</optionC>
<optionD>D. 选项内容</optionD>
<answer>A</answer>
<explanation>解析内容（50-100 字）</explanation>
```

### 要求
1. 题目应考察核心概念或典型易错点
2. 选项应具有迷惑性但不能有语法错误
3. 正确答案分布应随机，不偏重某个字母
4. 解析应点明解题关键和常见错误
5. 用中文出题和解答

## 章节映射

本模块是《Codex 从入门到项目实践》卷五（第 37 章）和《Harness 工程》第 17-20 章的配套实现。

| 章节 | 对应代码 |
|------|---------|
| 第 35 章 多智能体架构设计 | `.claude/agents/{planner,tutor,evaluator}.md` + `orchestrator.py` |
| 第 36 章 知识库与学科建模 | `knowledge_base/` |
| 第 37 章 出题智能体与批改智能体 | `src/ai_tutoring/{question_maker,grader}.py` |
| 第 38 章 学习路径规划与自适应引擎 | `src/ai_tutoring/{student_tracker,recommend_kp}.py` |
| 第 39 章 辅导对话智能体 | `src/ai_tutoring/socratic_tutor.py` |
| 第 40 章 家长看板与学情报告 | `src/ai_tutoring/shared_memory.py`（数据聚合） |
| 第 41 章 集成测试、部署与项目回顾 | 全项目集成 + `tests/` |

## 配套书籍

- **《Codex 从入门到项目实践》**（卷五，第 35-41 章）— 南荣相如
  - 代码片段索引：[claude-code-book](https://github.com/zcqiand/claude-code-book)
  - 电子书籍网址：[亚马逊](https://www.amazon.com/dp/B0H3M3B8GG)

- **《Harness 工程：围绕 Claude Code 构建可靠系统》**（卷四，第 17-20 章）— 南荣相如
  - 代码片段索引：[claudecode-harness-book](https://github.com/zcqiand/claudecode-harness-book)
