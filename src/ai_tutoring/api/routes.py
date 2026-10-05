"""REST + SSE 路由（前端唯一消费面）。

流式编排：SSE 生成器直接组合 agents.py 的三个公开函数（run_planner /
run_tutor_step / run_evaluator）——不改 orchestrator.py，逐事件产出三代理协作过程。
事件为 data 行内 JSON，带 event 判别字段（cs 家族同款）。
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents import run_evaluator, run_planner, run_tutor_step
from ..cost_tracker import BudgetExceededError
from ..session_store import SessionRecord, SessionStore

router = APIRouter(prefix="/api")


class SessionIn(BaseModel):
    question: str


class RunIn(BaseModel):
    max_steps: int = 3


def _plan_dict(plan) -> dict:
    return {"topic": plan.topic, "steps": list(plan.steps), "rationale": plan.rationale}


def _lesson_dict(lesson) -> dict:
    return {
        "step": lesson.step,
        "content": lesson.content,
        "key_points": list(lesson.key_points),
    }


def _eval_dict(ev) -> dict:
    return {
        "understanding_score": ev.understanding_score,
        "strengths": list(ev.strengths),
        "gaps": list(ev.gaps),
        "recommendation": ev.recommendation,
    }


def _usage_event(record: SessionRecord) -> dict:
    r = record.tracker.records[-1]
    return {
        "event": "usage",
        "record": {
            "agent": r.agent,
            "model": r.model,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cost_usd": r.cost_usd,
        },
        "total_cost_usd": record.tracker.total_cost_usd,
        "budget_usd": record.tracker.budget_usd,
    }


def _detail(record: SessionRecord) -> dict:
    m = record.memory
    return {
        "id": record.id,
        "question": record.question,
        "created_at": record.created_at,
        "plan": _plan_dict(m.plan) if m.plan else None,
        "lessons": [_lesson_dict(l) for l in m.lessons],
        "evaluation": _eval_dict(m.evaluation) if m.evaluation else None,
        "cost": {
            # 显式序列化：cost_usd 是 CallRecord 的 property，asdict 会静默丢键
            "records": [
                {
                    "agent": r.agent,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": r.cost_usd,
                }
                for r in record.tracker.records
            ],
            "total_cost_usd": record.tracker.total_cost_usd,
            "budget_usd": record.tracker.budget_usd,
        },
    }


def _summary(record: SessionRecord) -> dict:
    return {
        "id": record.id,
        "question": record.question,
        "created_at": record.created_at,
        "lessons": len(record.memory.lessons),
        "score": record.memory.evaluation.understanding_score if record.memory.evaluation else None,
        "total_cost_usd": record.tracker.total_cost_usd,
    }


def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


@router.post("/sessions", status_code=201)
def create_session(body: SessionIn, request: Request):
    settings = request.app.state.settings
    record = request.app.state.store.create(body.question, settings.budget_usd)
    return _summary(record)


@router.get("/sessions")
def list_sessions(request: Request):
    store: SessionStore = request.app.state.store
    return [_summary(r) for r in store.list_newest_first()]


@router.get("/sessions/{sid}")
def get_session_detail(sid: str, request: Request):
    record = request.app.state.store.get(sid)
    if record is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _detail(record)


@router.post("/sessions/{sid}/run")
def run_session(sid: str, body: RunIn, request: Request):
    store: SessionStore = request.app.state.store
    record = store.get(sid)
    if record is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    llm = request.app.state.llm

    def gen():
        try:
            yield _sse({"event": "stage", "agent": "planner"})
            plan = run_planner(record.memory, llm, record.tracker)
            yield _sse({"event": "plan", "plan": _plan_dict(plan)})
            yield _sse(_usage_event(record))
            for step in plan.steps[: body.max_steps]:
                yield _sse({"event": "stage", "agent": "tutor", "step": step})
                lesson = run_tutor_step(step, record.memory, llm, record.tracker)
                yield _sse({"event": "lesson", "lesson": _lesson_dict(lesson)})
                yield _sse(_usage_event(record))
            yield _sse({"event": "stage", "agent": "evaluator"})
            evaluation = run_evaluator(record.memory, llm, record.tracker)
            yield _sse({"event": "evaluation", "evaluation": _eval_dict(evaluation)})
            yield _sse(_usage_event(record))
            yield _sse({"event": "done", "detail": _detail(record)})
        except BudgetExceededError as exc:
            yield _sse({"event": "error", "message": str(exc)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
