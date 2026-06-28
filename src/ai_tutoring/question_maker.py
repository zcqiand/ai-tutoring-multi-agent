"""出题代理：根据知识点 ID 和难度生成选择题。

设计原则：
- 只生成题目文本，不评判答案（评判由 grader 负责）
- 难度 1-3：1 基础，2 中等，3 进阶
- 通过 LLM 生成结构化题目输出
"""

from __future__ import annotations

import os
import re
from typing import Protocol

from .cost_tracker import CostTracker


class LLMClient(Protocol):
    """anthropic.Anthropic.messages 的最小协议。"""

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


def make_question(kp_id: str, difficulty: int, client: LLMClient) -> dict:
    """根据知识点 ID 和难度生成一道选择题。

    返回格式：
    {
        "question": str,        # 题目正文
        "options": list[str],    # 选项列表，通常 4 个
        "answer": str,          # 正确答案（与某个 option 相同）
        "explanation": str      # 解析
    }
    """
    model = _env_model("AI_TUTOR_MODEL_QUESTION_MAKER", DEFAULT_MODEL)
    tracker = CostTracker()  # 调用方若无 tracker 可传 None，但函数内总创建以满足签名

    difficulty_labels = {1: "基础", 2: "中等", 3: "进阶"}
    diff_label = difficulty_labels.get(difficulty, "中等")

    system = (
        "你是出题代理。根据给定的知识点和难度，生成一道高中数学选择题。\n"
        "输出格式严格为：\n"
        "<question>题目正文</question>\n"
        "<optionA>A. 选项内容</optionA>\n"
        "<optionB>B. 选项内容</optionB>\n"
        "<optionC>C. 选项内容</optionC>\n"
        "<optionD>D. 选项内容</optionD>\n"
        "<answer>A</answer>\n"
        "<explanation>解析内容</explanation>\n"
        "选项应为 4 个，答案只能是 A/B/C/D 之一。"
    )
    messages = [{
        "role": "user",
        "content": f"知识点 ID：{kp_id}\n难度：{diff_label}（1=基础，2=中等，3=进阶）",
    }]

    response = client.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    _track_usage("question_maker", model, response, tracker)

    text = _extract_text(response)
    return _parse_question(text)


def _parse_question(text: str) -> dict:
    """从 LLM 输出解析题目结构。"""
    def grab(tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    question = grab("question")
    answer_raw = grab("answer").upper()
    # 规范化答案为 A/B/C/D
    if answer_raw not in ("A", "B", "C", "D"):
        answer_raw = "A"

    options = []
    for tag in ("optionA", "optionB", "optionC", "optionD"):
        content = grab(tag)
        if content:
            # 去掉标签前缀如 "A. "，保留选项文本
            options.append(content)

    explanation = grab("explanation")

    return {
        "question": question or text[:200],
        "options": options if options else ["A. 对", "B. 错", "C. 不确定", "D. 以上都不对"],
        "answer": answer_raw,
        "explanation": explanation,
    }
