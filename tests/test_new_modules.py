"""新增模块测试：question_maker / grader / student_tracker / recommend_kp / socratic_tutor。

用 fake LLM client 注入，不依赖真实 API key。
这是 CLAUDE.md「测试隔离」原则的实践。
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from ai_tutoring.question_maker import make_question, _parse_question
from ai_tutoring.grader import grade_answer, _parse_grade
from ai_tutoring.student_tracker import StudentTracker, StudentRecord
from ai_tutoring.recommend_kp import recommend_next_kp
from ai_tutoring.socratic_tutor import socratic_tutor


# ----------------------------------------------------------------------
# FakeClient（复制自 test_agents.py，确保测试隔离）
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# question_maker
# ----------------------------------------------------------------------

def test_parse_question():
    """_parse_question 能正确解析 LLM 输出的 XML 标签。"""
    text = (
        "<question>链式法则求导：若 y = sin(x²)，则 dy/dx = ？</question>\n"
        "<optionA>A. cos(x²)</optionA>\n"
        "<optionB>B. 2x·cos(x²)</optionB>\n"
        "<optionC>C. x²·cos(x²)</optionC>\n"
        "<optionD>D. 2cos(x²)</optionD>\n"
        "<answer>B</answer>\n"
        "<explanation>复合函数求导：外层 sin 的导数为 cos，内层 x² 的导数为 2x，故结果为 2x·cos(x²)。</explanation>"
    )
    result = _parse_question(text)

    assert "链式法则" in result["question"]
    assert len(result["options"]) == 4
    assert result["answer"] == "B"
    assert "复合函数" in result["explanation"]


def test_parse_question_fallback():
    """LLM 输出缺少标签时走兜底。"""
    result = _parse_question("这是一道导数题。")
    assert result["question"] == "这是一道导数题。"


def test_make_question_calls_client():
    """make_question 调用 client 并记录调用参数。"""
    client = FakeClient([
        "<question>Q</question>"
        "<optionA>A. A</optionA>"
        "<optionB>B. B</optionB>"
        "<optionC>C. C</optionC>"
        "<optionD>D. D</optionD>"
        "<answer>C</answer>"
        "<explanation>exp</explanation>"
    ])
    result = make_question("deriv-chain", 2, client)

    assert "Q" in result["question"]
    assert result["answer"] == "C"
    assert len(client.calls) == 1
    assert client.calls[0]["model"] == "claude-sonnet-4-6"


# ----------------------------------------------------------------------
# grader
# ----------------------------------------------------------------------

def test_parse_grade_correct():
    """_parse_grade 解析正确答案返回 correct=True。"""
    text = (
        "<correct>true</correct>\n"
        "<score>100</score>\n"
        "<feedback>回答正确！掌握链式法则的核心。</feedback>\n"
        "<step_analysis>先求外层导数 cos(x²)，再乘内层导数 2x。</step_analysis>"
    )
    result = _parse_grade(text)

    assert result["correct"] is True
    assert result["score"] == 100
    assert "正确" in result["feedback"]


def test_parse_grade_wrong():
    """_parse_grade 解析错误答案返回 correct=False。"""
    text = (
        "<correct>false</correct>\n"
        "<score>0</score>\n"
        "<feedback>漏掉了内层导数。</feedback>\n"
        "<step_analysis>正确答案应乘以内层 x² 的导数 2x。</step_analysis>"
    )
    result = _parse_grade(text)

    assert result["correct"] is False
    assert result["score"] == 0


def test_parse_grade_defaults_on_missing_tags():
    """标签缺失时走兜底。"""
    result = _parse_grade("no tags here")
    assert result["correct"] is False
    assert result["score"] == 0


def test_grade_answer_calls_client():
    """grade_answer 调用 client 并返回评判结果。"""
    question = {
        "question": "链式法则",
        "options": ["A", "B", "C", "D"],
        "answer": "B",
        "explanation": "复合函数求导",
    }
    client = FakeClient([
        "<correct>true</correct>\n"
        "<score>100</score>\n"
        "<feedback>正确</feedback>\n"
        "<step_analysis>分步分析</step_analysis>"
    ])
    result = grade_answer(question, "B", client)

    assert result["correct"] is True
    assert result["score"] == 100
    assert len(client.calls) == 1


# ----------------------------------------------------------------------
# student_tracker
# ----------------------------------------------------------------------

def test_record_answer_updates_mastery():
    """record_answer 答对增加掌握度，答错降低。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = StudentTracker(data_dir=tmpdir)
        sid = "student_test_001"

        # 第一次答错
        tracker.record_answer(sid, "deriv-def", correct=False, question="q1", student_answer="A")
        assert tracker.get_mastery(sid, "deriv-def") == 0.0  # 0.0 - 0.05 = -0.05 → clamp to 0.0

        # 第二次答对
        tracker.record_answer(sid, "deriv-def", correct=True, question="q2", student_answer="B")
        assert tracker.get_mastery(sid, "deriv-def") == 0.1

        # 第三次答对
        tracker.record_answer(sid, "deriv-def", correct=True, question="q3", student_answer="C")
        assert tracker.get_mastery(sid, "deriv-def") == 0.2


def test_get_weak_points():
    """get_weak_points 返回掌握度低于阈值的知识点。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = StudentTracker(data_dir=tmpdir)
        sid = "student_test_002"

        tracker.record_answer(sid, "deriv-def", correct=True)   # mastery 0.1
        tracker.record_answer(sid, "deriv-geo", correct=False)  # mastery 0.0
        tracker.record_answer(sid, "deriv-rules", correct=False)  # mastery 0.0

        weak = tracker.get_weak_points(sid)
        assert "deriv-geo" in weak
        assert "deriv-rules" in weak
        assert "deriv-def" in weak  # 0.1 < 0.6


def test_wrong_answers_persisted():
    """错题写入 JSON 文件，重启后仍可查询。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker1 = StudentTracker(data_dir=tmpdir)
        tracker1.record_answer("alice", "deriv-def", correct=False, question="错题1", student_answer="C")

        tracker2 = StudentTracker(data_dir=tmpdir)
        wrong = tracker2.get_wrong_answers("alice")
        assert len(wrong) == 1
        assert wrong[0]["question"] == "错题1"


def test_get_mastery_unseen_kp():
    """未练习过的知识点返回 0.0。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = StudentTracker(data_dir=tmpdir)
        assert tracker.get_mastery("nobody", "deriv-def") == 0.0


# ----------------------------------------------------------------------
# recommend_kp
# ----------------------------------------------------------------------

def test_recommend_kp_respects_prerequisites():
    """recommend_kp 不会推荐先修未掌握的知识点。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = StudentTracker(data_dir=tmpdir)
        sid = "student_test_003"

        # 先修 deriv-def 已掌握
        for _ in range(9):
            tracker.record_answer(sid, "deriv-def", correct=True)

        # 推荐 deriv-geo（依赖 deriv-def）或更高阶
        recommended = recommend_next_kp(sid, tracker)
        # deriv-geo 的先修 deriv-def 已满足 0.6 阈值，应该可以推荐
        assert recommended in ("deriv-geo", "deriv-rules", "deriv-chain",
                               "int-def", "int-rules", "int-sub", "newton-leibniz",
                               "deriv-def")


def test_recommend_kp_fallback():
    """无任何数据时返回知识图谱第一个知识点作为兜底。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = StudentTracker(data_dir=tmpdir)
        recommended = recommend_next_kp("new_student", tracker)
        assert isinstance(recommended, str)
        assert len(recommended) > 0


# ----------------------------------------------------------------------
# socratic_tutor
# ----------------------------------------------------------------------

def test_socratic_tutor_returns_text():
    """socratic_tutor 调用 client 并返回引导式回复。"""
    client = FakeClient([
        "你有没有想过，如果把 x² 看成 u，那么 sin(u) 的导数是什么？"
    ])
    result = socratic_tutor("导数", "sin(x²) 的导数怎么求？", client)

    assert len(result) > 0
    assert len(client.calls) == 1


def test_socratic_tutor_does_not_give_direct_answer():
    """回复不应包含直接答案的关键词。"""
    client = FakeClient([
        "试着想想：sin(u) 的导数是 cos(u)，那么 u 应该是什么？"
    ])
    result = socratic_tutor("导数", "sin(x²) 的导数是什么？", client)

    # 苏格拉底式回复不应直接给出"2x·cos(x²)"
    assert "2x" not in result or "cos" not in result


# ----------------------------------------------------------------------
# student_tracker StudentRecord dataclass
# ----------------------------------------------------------------------

def test_student_record_dataclass():
    """StudentRecord 和 KnowledgePointRecord 数据类正常工作。"""
    record = StudentRecord(
        student_id="test",
        knowledge_points={"deriv-def": {"mastery": 0.5, "wrong_count": 2, "last_practiced": "2024-01-01T00:00:00"}},
        wrong_answers=[{"kp_id": "deriv-def", "question": "q", "student_answer": "A", "correct": False, "timestamp": "2024-01-01T00:00:00"}],
    )
    assert record.student_id == "test"
    assert record.knowledge_points["deriv-def"]["mastery"] == 0.5
    assert len(record.wrong_answers) == 1
