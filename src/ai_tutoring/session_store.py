"""内存会话库（demo 配套仓性质：重启即清，docstring 注明）。

SessionRecord 持有 SharedMemory + CostTracker，API 层据此产出详情/成本事件。
线程安全：FastAPI 同步端点跑在线程池里，用 Lock 护住 dict。
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from .cost_tracker import CostTracker
from .shared_memory import SharedMemory


@dataclass
class SessionRecord:
    id: str
    question: str
    created_at: str
    memory: SharedMemory = field(repr=False)
    tracker: CostTracker = field(repr=False)


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, question: str, budget_usd: float | None) -> SessionRecord:
        record = SessionRecord(
            id=uuid.uuid4().hex[:12],
            question=question,
            created_at=datetime.now().isoformat(timespec="seconds"),
            memory=SharedMemory(user_question=question),
            tracker=CostTracker(budget_usd=budget_usd),
        )
        with self._lock:
            self._sessions[record.id] = record
        return record

    def get(self, sid: str) -> SessionRecord | None:
        with self._lock:
            return self._sessions.get(sid)

    def list_newest_first(self) -> list[SessionRecord]:
        with self._lock:
            records = sorted(
                self._sessions.values(), key=lambda r: r.created_at, reverse=True
            )
        return records
