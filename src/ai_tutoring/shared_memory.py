"""代理间共享上下文。

第 18 章「代理间通信」的实物。三个代理（planner/tutor/evaluator）之间
不靠全局变量传消息，而是通过 SharedMemory 显式传递——这让数据流可观察、
可测试、可序列化。

设计原则：
- 显式传递，不用全局变量（CLAUDE.md 编码约定）
- 不可变快照：每个阶段的产出 freeze 后供下一阶段只读
- 可序列化为 dict：便于日志、调试、回放
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LearningPlan:
    """planner 的产出——学习路径。"""

    topic: str                       # 用户原始问题，如"请教我导数"
    steps: tuple[str, ...]           # 学习步骤，如("导数定义", "几何意义", "求导法则")
    rationale: str                   # 为什么这样拆分

    def format_for_next_agent(self) -> str:
        """渲染成给 tutor 的提示文本。"""
        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.steps))
        return (
            f"学习主题：{self.topic}\n"
            f"学习路径：\n{steps_text}\n"
            f"拆分理由：{self.rationale}"
        )


@dataclass(frozen=True)
class Lesson:
    """tutor 的产出——一节课的讲解。"""

    step: str                        # 对应 LearningPlan.steps 中的某一步
    content: str                     # 讲解正文（markdown）
    key_points: tuple[str, ...]      # 关键要点，给 evaluator 做评估锚点


@dataclass(frozen=True)
class Evaluation:
    """evaluator 的产出——学习效果评估。"""

    understanding_score: int         # 0-100
    strengths: tuple[str, ...]
    gaps: tuple[str, ...]
    recommendation: str              # 给 planner 的下一轮建议


@dataclass
class SharedMemory:
    """三代理共享的会话状态。

    每个 freeze_xxx 方法返回不可变快照，确保下游代理不会回写上游产出。
    """

    user_question: str
    plan: LearningPlan | None = None
    lessons: list[Lesson] = field(default_factory=list)
    evaluation: Evaluation | None = None

    def freeze_plan(self) -> LearningPlan:
        if self.plan is None:
            raise ValueError("plan 尚未生成")
        return self.plan

    def add_lesson(self, lesson: Lesson) -> None:
        self.lessons.append(lesson)

    def lessons_summary(self) -> str:
        """给 evaluator 看的已讲解内容摘要。"""
        if not self.lessons:
            return "(尚未讲解)"
        return "\n\n".join(
            f"【{l.step}】\n{l.content}\n关键要点：{', '.join(l.key_points)}"
            for l in self.lessons
        )
