"""学生追踪数据类与持久化。

功能：
- 记录学生在每个知识点的掌握度、错题数、上次练习时间
- 错题本持久化到 JSON 文件
- 提供弱项查询和掌握度查询

设计原则：
- 显式传递 student_id，不使用全局状态
- JSON 文件与实例方法解耦
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class KnowledgePointRecord:
    """单个知识点的学习记录。"""
    mastery: float          # 掌握度 0.0-1.0
    wrong_count: int         # 错题次数
    last_practiced: str     # ISO 格式时间戳


@dataclass
class StudentRecord:
    """单个学生的完整学习档案。"""
    student_id: str
    knowledge_points: dict[str, dict]  # kp_id -> {mastery, wrong_count, last_practiced}
    wrong_answers: list[dict]          # [{kp_id, question, student_answer, correct, timestamp}]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat()


class StudentTracker:
    """学生追踪器，支持内存操作和 JSON 持久化。"""

    DEFAULT_DIR = "data/student_tracker"

    def __init__(self, data_dir: str | None = None):
        self._data_dir = data_dir or self.DEFAULT_DIR
        self._cache: dict[str, StudentRecord] = {}
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        Path(self._data_dir).mkdir(parents=True, exist_ok=True)

    def _file_path(self, student_id: str) -> Path:
        return Path(self._data_dir) / f"{student_id}.json"

    def _load(self, student_id: str) -> StudentRecord:
        """从磁盘加载或创建空白记录。"""
        if student_id in self._cache:
            return self._cache[student_id]

        path = self._file_path(student_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            record = StudentRecord(
                student_id=data["student_id"],
                knowledge_points=data.get("knowledge_points", {}),
                wrong_answers=data.get("wrong_answers", []),
            )
        else:
            record = StudentRecord(
                student_id=student_id,
                knowledge_points={},
                wrong_answers=[],
            )
        self._cache[student_id] = record
        return record

    def _save(self, record: StudentRecord) -> None:
        """持久化到磁盘。"""
        self._cache[record.student_id] = record
        path = self._file_path(record.student_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(record), f, ensure_ascii=False, indent=2)

    def record_answer(
        self,
        student_id: str,
        kp_id: str,
        correct: bool,
        *,
        question: str = "",
        student_answer: str = "",
    ) -> None:
        """记录一次作答，更新掌握度和错题本。"""
        record = self._load(student_id)

        now = StudentRecord._now_iso()
        kp_data = record.knowledge_points.get(kp_id, {
            "mastery": 0.0,
            "wrong_count": 0,
            "last_practiced": now,
        })

        # 掌握度更新：答对 +0.1（上限 1.0），答错 -0.05（下限 0.0）
        delta = 0.1 if correct else -0.05
        new_mastery = max(0.0, min(1.0, kp_data.get("mastery", 0.0) + delta))

        record.knowledge_points[kp_id] = {
            "mastery": new_mastery,
            "wrong_count": kp_data.get("wrong_count", 0) + (0 if correct else 1),
            "last_practiced": now,
        }

        if not correct and question:
            record.wrong_answers.append({
                "kp_id": kp_id,
                "question": question,
                "student_answer": student_answer,
                "correct": False,
                "timestamp": now,
            })

        self._save(record)

    def get_weak_points(self, student_id: str) -> list[str]:
        """返回掌握度低于 0.6 的知识点 ID 列表，按掌握度升序。"""
        record = self._load(student_id)
        weak = [
            (kp_id, data.get("mastery", 0.0))
            for kp_id, data in record.knowledge_points.items()
            if data.get("mastery", 1.0) < 0.6
        ]
        weak.sort(key=lambda x: x[1])
        return [kp_id for kp_id, _ in weak]

    def get_mastery(self, student_id: str, kp_id: str) -> float:
        """查询指定知识点的掌握度，未练习过返回 0.0。"""
        record = self._load(student_id)
        return record.knowledge_points.get(kp_id, {}).get("mastery", 0.0)

    def get_wrong_answers(self, student_id: str, kp_id: str | None = None) -> list[dict]:
        """获取错题本，可按 kp_id 过滤。"""
        record = self._load(student_id)
        if kp_id is None:
            return list(record.wrong_answers)
        return [w for w in record.wrong_answers if w.get("kp_id") == kp_id]

    def all_kp_ids(self, student_id: str) -> list[str]:
        """返回该学生已练习过的所有知识点 ID。"""
        record = self._load(student_id)
        return list(record.knowledge_points.keys())
