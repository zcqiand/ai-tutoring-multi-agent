"""评判代理：对学生答案进行打分和反馈。

与 evaluator 不同，grader 专注单题打分和反馈，不做整体学习评估。
设计原则：
- 判断对错，给出分数（0-100）
- 提供分步分析和个性化反馈
- 不输出下一步学习建议（那是 recommend_kp 的职责）
"""

from __future__ import annotations

import os
import re
from typing import Protocol

from .cost_tracker import CostTracker


class LLMClient(Protocol):
    def create(self, *, model: str, max_tokens: int, system: str, messages: list) -> object: ...


DEFAULT_MODEL = "claude-sonnet-4-6"


def _env_model(var: str, default: str) -> str:
    return os.environ.get(var, default)


def _extract_text(response) -> str:
    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )


def _track_usage(agent: str, model: str, response, tracker: CostTracker) -> None:
    usage = response.usage
    tracker.track(
        agent=agent,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )


def grade_answer(question: dict, student_answer: str, client: LLMClient) -> dict:
    """评判学生的答案。

    参数：
        question: make_question 产出的题目 dict，含 question/options/answer/explanation
        student_answer: 学生提交的答案（应为 "A"/"B"/"C"/D 之一）
        client: LLM client

    返回格式：
    {
        "correct": bool,
        "score": int,              # 0-100
        "feedback": str,           # 个性化反馈
        "step_analysis": str      # 分步解题分析
    }
    """
    model = _env_model("AI_TUTOR_MODEL_GRADER", DEFAULT_MODEL)
    tracker = CostTracker()

    system = (
        "你是评判代理。给定一道选择题的原题、正确答案，以及学生的作答，"
        "判断对错并给出分数和反馈。\n"
        "输出格式严格为：\n"
        "<correct>true 或 false</correct>\n"
        "<score>0-100 的整数</score>\n"
        "<feedback>针对学生的个性化反馈（20-50 字）</feedback>\n"
        "<step_analysis>分步解题分析</step_analysis>"
    )
    messages = [{
        "role": "user",
        "content": (
            f"题目：{question.get('question', '')}\n"
            f"选项：\n" + "\n".join(f"  {opt}" for opt in question.get("options", [])) + "\n"
            f"正确答案：{question.get('answer', '')}\n"
            f"学生答案：{student_answer}"
        ),
    }]

    response = client.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=messages,
    )
    _track_usage("grader", model, response, tracker)

    text = _extract_text(response)
    return _parse_grade(text)


def _parse_grade(text: str) -> dict:
    """从 LLM 输出解析评判结果。"""
    def grab(tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    correct_raw = grab("correct").lower()
    correct = correct_raw == "true"

    score_match = re.search(r"<score>(\d+)</score>", text)
    score = int(score_match.group(1)) if score_match else (100 if correct else 0)

    feedback = grab("feedback")
    step_analysis = grab("step_analysis")

    return {
        "correct": correct,
        "score": max(0, min(100, score)),
        "feedback": feedback or ("回答正确！" if correct else "答案有误，请查看解析。"),
        "step_analysis": step_analysis or "",
    }
