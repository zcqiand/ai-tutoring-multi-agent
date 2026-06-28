"""自适应学习路径推荐：根据学生薄弱点推荐下一个知识点。

设计原则：
- 推荐考虑前置知识依赖（不能跳过未掌握的先修知识点）
- 优先推荐：薄弱点 > 未掌握先修 > 已掌握进阶
- 纯函数，无状态，通过 tracker 查询学生数据
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from .student_tracker import StudentTracker


class LLMClient(Protocol):
    def create(self, *, model: str, max_tokens: int, system: str, messages: list) -> object: ...


DEFAULT_MODEL = "claude-sonnet-4-6"

_KG_CACHE: dict | None = None


def _load_knowledge_graph() -> dict:
    """加载知识图谱，缓存于模块级。"""
    global _KG_CACHE
    if _KG_CACHE is not None:
        return _KG_CACHE

    # 支持环境变量指定路径
    kg_path = os.environ.get(
        "KNOWLEDGE_GRAPH_PATH",
        str(Path(__file__).parent.parent.parent / "knowledge_base" / "math" / "knowledge_graph.json"),
    )
    with open(kg_path, "r", encoding="utf-8") as f:
        _KG_CACHE = json.load(f)
    return _KG_CACHE


def _get_prerequisites(kp_id: str) -> list[str]:
    """获取某知识点的先修列表。"""
    kg = _load_knowledge_graph()
    for kp in kg.get("knowledge_points", []):
        if kp["id"] == kp_id:
            return list(kp.get("prerequisites", []))
    return []


def _all_kp_ids() -> list[str]:
    """返回所有知识点 ID。"""
    kg = _load_knowledge_graph()
    return [kp["id"] for kp in kg.get("knowledge_points", [])]


def _can_study(kp_id: str, tracker: StudentTracker, student_id: str) -> bool:
    """判断学生是否可以学习该知识点（所有先修都已掌握 >= 0.6）。"""
    for prereq in _get_prerequisites(kp_id):
        if tracker.get_mastery(student_id, prereq) < 0.6:
            return False
    return True


def recommend_next_kp(student_id: str, tracker: StudentTracker) -> str:
    """自适应推荐下一个最合适的知识点 ID。

    优先级：
    1. 弱项中可学的（薄弱且前置已满足）
    2. 未学过的先修知识点（前置已满足但未练习）
    3. 已掌握知识点的进阶（前置已满足）
    """
    weak = tracker.get_weak_points(student_id)
    studied = set(tracker.all_kp_ids(student_id))
    all_ids = _all_kp_ids()

    # 优先从弱项中选择可学的
    for kp_id in weak:
        if kp_id in studied and _can_study(kp_id, tracker, student_id):
            return kp_id

    # 寻找未学过的知识点（前置已满足）
    for kp_id in all_ids:
        if kp_id not in studied and _can_study(kp_id, tracker, student_id):
            return kp_id

    # 从弱项中放宽条件（前置不满足也推荐，但提示前置未掌握）
    if weak:
        return weak[0]

    # 全都掌握或无数据，返回第一个知识点作为兜底
    return all_ids[0] if all_ids else "deriv-def"
