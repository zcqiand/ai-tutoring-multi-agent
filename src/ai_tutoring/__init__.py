"""AI 学习辅导多智能体系统。

《Harness 工程：围绕 Claude Code 构建可靠系统》卷四案例。三代理协作：
    planner（规划学习路径）
      → tutor（按路径分步讲解）
      → evaluator（评估学习效果）

第 17 章「多代理架构」的实物——但这里用的是 Claude Agent SDK 的真实
Messages API 调用，不是模拟 Claude Code 的子代理机制。两者是不同层级：
- Claude Code 子代理（.claude/agents/*.md）：开发者用 Claude Code 时
  的任务委派机制
- 本项目的三代理：终端用户（学生）使用辅导系统时，系统内部的协作

详见 README 与各章「项目对照」小节。
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
