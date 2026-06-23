"""三代理 + orchestrator 测试。

用 fake LLM client 注入——不依赖真实 API key 也能跑完整流程。
这是 CLAUDE.md「测试隔离」原则的实践。
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_tutoring.agents import run_evaluator, run_planner, run_tutor_step
from ai_tutoring.cost_tracker import BudgetExceededError, CostTracker
from ai_tutoring.orchestrator import run_full_session
from ai_tutoring.shared_memory import SharedMemory


@dataclass
class FakeBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list
    usage: "FakeUsage"


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


class FakeClient:
    """按预设脚本返回响应的 fake client。

    responses 是 list[str]，按调用顺序依次返回。让测试能精确控制
    planner/tutor/evaluator 各看到什么输入。
    """

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, *, model, max_tokens, system, messages):
        self.calls.append({"model": model, "system": system, "messages": messages})
        text = self.responses.pop(0)
        return FakeResponse(
            content=[FakeBlock(text=text)],
            usage=FakeUsage(input_tokens=100, output_tokens=len(text) // 4),
        )


# ============= planner =============

def test_planner_parses_steps_and_rationale():
    memory = SharedMemory(user_question="请教我导数")
    client = FakeClient([
        "<rationale>从定义到应用递进</rationale>"
        "<step>导数定义</step>"
        "<step>几何意义</step>"
        "<step>求导法则</step>"
    ])
    tracker = CostTracker()

    plan = run_planner(memory, client, tracker)

    assert plan.topic == "请教我导数"
    assert plan.rationale == "从定义到应用递进"
    assert plan.steps == ("导数定义", "几何意义", "求导法则")
    assert memory.plan is plan
    assert len(tracker.records) == 1
    assert tracker.records[0].agent == "planner"


def test_planner_fallback_when_no_tags():
    """planner 输出没有标签时走兜底按行分割。"""
    memory = SharedMemory(user_question="积分")
    client = FakeClient(["步骤一\n步骤二\n步骤三"])
    tracker = CostTracker()

    plan = run_planner(memory, client, tracker)

    assert len(plan.steps) >= 1


# ============= tutor =============

def test_tutor_parses_lesson_content_and_keypoints():
    memory = SharedMemory(user_question="导数")
    client = FakeClient([
        "<rationale>r</rationale><step>定义</step>",  # planner（如果先跑）
    ])
    # 直接测 tutor：跳过 planner
    memory = SharedMemory(user_question="导数")
    tracker = CostTracker()
    client = FakeClient([
        "<content>导数描述瞬时变化率。</content>"
        "<keypoints>瞬时变化率；切线斜率；极限定义</keypoints>"
    ])

    lesson = run_tutor_step("导数定义", memory, client, tracker)

    assert lesson.step == "导数定义"
    assert "瞬时变化率" in lesson.content
    assert lesson.key_points == ("瞬时变化率", "切线斜率", "极限定义")
    assert lesson in memory.lessons


# ============= evaluator =============

def test_evaluator_parses_score_and_recommendation():
    memory = SharedMemory(user_question="导数")
    memory.plan = type(memory).plan.__class__.__mro__  # 占位，真正赋值在下方
    # 用真正的 LearningPlan
    from ai_tutoring.shared_memory import LearningPlan
    memory.plan = LearningPlan(topic="导数", steps=("定义",), rationale="r")
    memory.add_lesson = memory.add_lesson  # 保持原方法
    from ai_tutoring.shared_memory import Lesson
    memory.lessons.append(Lesson(step="定义", content="讲解", key_points=("a",)))

    client = FakeClient([
        "<score>85</score>"
        "<strengths>讲解清晰；例子贴切</strengths>"
        "<gaps>缺少练习题</gaps>"
        "<recommendation>下次加练习</recommendation>"
    ])
    tracker = CostTracker()

    ev = run_evaluator(memory, client, tracker)

    assert ev.understanding_score == 85
    assert ev.strengths == ("讲解清晰", "例子贴切")
    assert ev.gaps == ("缺少练习题",)
    assert ev.recommendation == "下次加练习"


# ============= orchestrator 端到端（fake client） =============

def test_run_full_session_with_fake_client():
    """用 fake client 跑完整三代理流程，验证编排顺序与成本累计。"""
    # planner(1) + tutor(2 步) + evaluator(1) = 4 次调用
    client = FakeClient([
        # planner
        "<rationale>递进</rationale><step>定义</step><step>法则</step>",
        # tutor step 1
        "<content>定义讲解</content><keypoints>要点 A；要点 B</keypoints>",
        # tutor step 2
        "<content>法则讲解</content><keypoints>要点 C；要点 D</keypoints>",
        # evaluator
        "<score>90</score><strengths>清晰</strengths><gaps>缺练习</gaps>"
        "<recommendation>加练习</recommendation>",
    ])
    tracker = CostTracker(budget_usd=1.0)

    memory = run_full_session("导数", client, tracker, max_steps=2)

    assert memory.plan is not None
    assert len(memory.lessons) == 2
    assert memory.evaluation is not None
    assert memory.evaluation.understanding_score == 90
    # 4 次调用：planner + 2 tutor + evaluator
    assert len(tracker.records) == 4
    agents_called = [r.agent for r in tracker.records]
    assert agents_called == ["planner", "tutor", "tutor", "evaluator"]


def test_budget_exceeded_aborts_session():
    """预算超限时 orchestrator 抛 BudgetExceededError。"""
    client = FakeClient([
        "<rationale>r</rationale><step>s1</step><step>s2</step>",
        "<content>c1</content><keypoints>k</keypoints>",
    ])
    # 极低预算，第二次调用后必然超限
    tracker = CostTracker(budget_usd=0.0001)

    import pytest
    with pytest.raises(BudgetExceededError):
        run_full_session("topic", client, tracker, max_steps=2)


def test_cost_tracker_format_summary():
    tracker = CostTracker(budget_usd=0.50)
    tracker.track("planner", "claude-sonnet-4-6", 1000, 500)
    tracker.track("tutor", "claude-sonnet-4-6", 2000, 1000)

    summary = tracker.format_summary()

    assert "planner" in summary
    assert "tutor" in summary
    assert "TOTAL" in summary
    assert "预算" in summary
