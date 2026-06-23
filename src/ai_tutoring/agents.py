"""三个代理的实现：planner / tutor / evaluator。

每个代理是一个薄封装——构造 Anthropic Messages 提示、调用、把响应解析成
shared_memory 里的不可变快照。代理之间零直接引用，全部通过 SharedMemory
通信（第 18 章主题）。

设计取舍：
- 用 anthropic SDK 直接调 Messages API，而非 claude-agent-sdk——后者
  仍在快速迭代，强绑会让本项目随 SDK 版本动荡。anthropic SDK 的
  messages.create 是稳定 API。
- 每个代理接受 inject 的 client，便于测试注入 mock（CLAUDE.md 编码约定）
- 模型名走环境变量，默认 sonnet-4-6 与 version-lock 一致
"""

from __future__ import annotations

import os
from typing import Protocol

from .cost_tracker import CostTracker
from .shared_memory import Evaluation, LearningPlan, Lesson, SharedMemory


class LLMClient(Protocol):
    """anthropic.Anthropic.messages 的最小协议——便于测试注入 mock。"""

    def create(self, *, model: str, max_tokens: int, system: str, messages: list) -> object: ...


def _env_model(var: str, default: str) -> str:
    return os.environ.get(var, default)


# 默认模型与 version-lock 一致
DEFAULT_PLANNER_MODEL = "claude-sonnet-4-6"
DEFAULT_TUTOR_MODEL = "claude-sonnet-4-6"
DEFAULT_EVALUATOR_MODEL = "claude-sonnet-4-6"


def _extract_text(response) -> str:
    """从 Anthropic Messages 响应里抽出文本内容。

    response.content 是 list[ContentBlock]，文本块 type == "text"。
    """
    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )


def _track_usage(agent: str, model: str, response, tracker: CostTracker) -> None:
    """把 response.usage 计入成本追踪器。"""
    usage = response.usage
    tracker.track(
        agent=agent,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )


# ----------------------------------------------------------------------
# planner
# ----------------------------------------------------------------------

def run_planner(memory: SharedMemory, client: LLMClient, tracker: CostTracker) -> LearningPlan:
    """planner：根据用户问题制定学习路径。"""
    model = _env_model("AI_TUTOR_MODEL_PLANNER", DEFAULT_PLANNER_MODEL)

    system = (
        "你是学习规划代理。你的任务是把用户的学习请求拆解成 3-5 个递进的"
        "学习步骤。每个步骤应是一个可独立讲解的概念单元。"
        "输出格式严格为：\n"
        "<rationale>一句话拆分理由</rationale>\n"
        "<step>步骤 1</step>\n"
        "<step>步骤 2</step>\n"
        "..."
    )
    messages = [{"role": "user", "content": f"学习请求：{memory.user_question}"}]

    response = client.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=messages,
    )
    _track_usage("planner", model, response, tracker)

    text = _extract_text(response)
    plan = _parse_plan(text, memory.user_question)
    memory.plan = plan
    return plan


def _parse_plan(text: str, topic: str) -> LearningPlan:
    """从 planner 输出解析 LearningPlan。

    用简单的标签解析而非 JSON——LLM 输出 JSON 容易出格式错误，
    标签解析更鲁棒。第 16 章会专门讲结构化输出的取舍。
    """
    import re

    rationale_match = re.search(r"<rationale>(.*?)</rationale>", text, re.DOTALL)
    rationale = rationale_match.group(1).strip() if rationale_match else "默认拆分"
    steps = tuple(re.findall(r"<step>(.*?)</step>", text, re.DOTALL))
    if not steps:
        # 兜底：按行分割
        steps = tuple(line.strip("- ").strip() for line in text.strip().split("\n") if line.strip())
    return LearningPlan(topic=topic, steps=steps, rationale=rationale)


# ----------------------------------------------------------------------
# tutor
# ----------------------------------------------------------------------

def run_tutor_step(
    step: str,
    memory: SharedMemory,
    client: LLMClient,
    tracker: CostTracker,
) -> Lesson:
    """tutor：讲解学习路径中的某一步。"""
    model = _env_model("AI_TUTOR_MODEL_TUTOR", DEFAULT_TUTOR_MODEL)

    system = (
        "你是学习辅导代理。用清晰、循序渐进的方式讲解给定的学习步骤。"
        "面向高中生/大学生水平。输出格式严格为：\n"
        "<content>讲解正文（markdown，200-400 字）</content>\n"
        "<keypoints>要点 1；要点 2；要点 3</keypoints>"
    )
    messages = [{
        "role": "user",
        "content": (
            f"学习主题：{memory.user_question}\n"
            f"请讲解这一步：{step}\n"
            f"已讲过：{memory.lessons_summary() if memory.lessons else '(本步是第一步)'}"
        ),
    }]

    response = client.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    _track_usage("tutor", model, response, tracker)

    text = _extract_text(response)
    lesson = _parse_lesson(step, text)
    memory.add_lesson(lesson)
    return lesson


def _parse_lesson(step: str, text: str) -> Lesson:
    import re

    content_match = re.search(r"<content>(.*?)</content>", text, re.DOTALL)
    content = content_match.group(1).strip() if content_match else text.strip()
    kp_match = re.search(r"<keypoints>(.*?)</keypoints>", text, re.DOTALL)
    if kp_match:
        key_points = tuple(p.strip() for p in kp_match.group(1).split("；") if p.strip())
    else:
        key_points = ()
    return Lesson(step=step, content=content, key_points=key_points)


# ----------------------------------------------------------------------
# evaluator
# ----------------------------------------------------------------------

def run_evaluator(memory: SharedMemory, client: LLMClient, tracker: CostTracker) -> Evaluation:
    """evaluator：评估本次学习的效果。"""
    model = _env_model("AI_TUTOR_MODEL_EVALUATOR", DEFAULT_EVALUATOR_MODEL)

    system = (
        "你是学习评估代理。根据学习主题与讲解内容，评估学习效果。"
        "输出格式严格为：\n"
        "<score>0-100 的整数</score>\n"
        "<strengths>优点 1；优点 2</strengths>\n"
        "<gaps>不足 1；不足 2</gaps>\n"
        "<recommendation>给 planner 的下一步建议</recommendation>"
    )
    messages = [{
        "role": "user",
        "content": (
            f"学习主题：{memory.user_question}\n"
            f"学习路径：{memory.freeze_plan().format_for_next_agent()}\n"
            f"讲解内容：\n{memory.lessons_summary()}"
        ),
    }]

    response = client.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=messages,
    )
    _track_usage("evaluator", model, response, tracker)

    text = _extract_text(response)
    evaluation = _parse_evaluation(text)
    memory.evaluation = evaluation
    return evaluation


def _parse_evaluation(text: str) -> Evaluation:
    import re

    def grab(tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    score_match = re.search(r"<score>(\d+)</score>", text)
    score = int(score_match.group(1)) if score_match else 0

    def split_semicolon(s: str) -> tuple[str, ...]:
        return tuple(p.strip() for p in s.split("；") if p.strip())

    return Evaluation(
        understanding_score=score,
        strengths=split_semicolon(grab("strengths")),
        gaps=split_semicolon(grab("gaps")),
        recommendation=grab("recommendation") or "继续巩固",
    )
