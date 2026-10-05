"""API e2e（TestClient，LLM_MODE=mock 全链路离线）。

流程：health → 建会话 → run SSE（stage/plan/lesson/usage/evaluation/done 全序列）
→ 详情 → 列表 → 404 → 超预算 error 事件。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from ai_tutoring.config import load_settings
from ai_tutoring.main import create_app
from ai_tutoring.mock_llm import MockLLM


@pytest.fixture()
def client(tmp_path):
    settings = load_settings(environ={"LLM_MODE": "mock"}, env_file=tmp_path / "no.env")
    app = create_app(settings, llm=MockLLM())
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def budget_client(tmp_path):
    settings = load_settings(
        environ={"LLM_MODE": "mock", "AI_TUTOR_BUDGET_USD": "0.0001"},
        env_file=tmp_path / "no.env",
    )
    app = create_app(settings, llm=MockLLM())
    with TestClient(app) as c:
        yield c


def _events(text: str) -> list[dict]:
    return [
        json.loads(line[len("data: "):])
        for line in text.splitlines()
        if line.startswith("data: ")
    ]


def _new_session(client) -> str:
    r = client.post("/api/sessions", json={"question": "请教我导数"})
    assert r.status_code == 201
    return r.json()["id"]


# ---- 基础 ----


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["mode"] == "mock"


def test_create_session(client):
    r = client.post("/api/sessions", json={"question": "请教我导数"})
    assert r.status_code == 201
    body = r.json()
    assert body["question"] == "请教我导数"
    assert body["id"]
    assert body["created_at"]


def test_unknown_session_404(client):
    assert client.get("/api/sessions/nope").status_code == 404
    r = client.post("/api/sessions/nope/run", json={"max_steps": 2})
    assert r.status_code == 404


# ---- run SSE 主链路 ----


def test_run_sse_full_sequence(client):
    sid = _new_session(client)
    r = client.post(f"/api/sessions/{sid}/run", json={"max_steps": 2})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    evs = _events(r.text)
    kinds = [e["event"] for e in evs]

    # stage(plan) → plan → usage → (stage(tutor) → lesson → usage)×2 → stage(evaluator) → evaluation → usage → done
    assert kinds == [
        "stage", "plan", "usage",
        "stage", "lesson", "usage",
        "stage", "lesson", "usage",
        "stage", "evaluation", "usage",
        "done",
    ]
    plan_ev = evs[1]["plan"]
    assert plan_ev["topic"] == "请教我导数"
    assert len(plan_ev["steps"]) >= 3
    assert plan_ev["rationale"]

    lessons = [e["lesson"] for e in evs if e["event"] == "lesson"]
    assert len(lessons) == 2
    for l in lessons:
        assert l["content"]
        assert l["key_points"]

    ev = next(e["evaluation"] for e in evs if e["event"] == "evaluation")
    assert isinstance(ev["understanding_score"], int)
    assert 0 <= ev["understanding_score"] <= 100
    assert ev["recommendation"]

    # usage 事件累计：末条 total_cost_usd 等于全部 cost_usd 之和
    usages = [e for e in evs if e["event"] == "usage"]
    assert len(usages) == 4  # planner 1 + tutor 2 + evaluator 1
    total = sum(u["record"]["cost_usd"] for u in usages)
    assert abs(usages[-1]["total_cost_usd"] - total) < 1e-9

    # done 事件的详情与会话详情端点一致
    detail = evs[-1]["detail"]
    assert detail["id"] == sid
    assert len(detail["lessons"]) == 2
    assert detail["evaluation"]["understanding_score"] == ev["understanding_score"]

    # run 之后 GET 详情应含同样内容
    r = client.get(f"/api/sessions/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["lessons"]) == 2
    assert body["evaluation"]["understanding_score"] == ev["understanding_score"]
    assert body["cost"]["total_cost_usd"] > 0


def test_session_list_shows_progress(client):
    sid = _new_session(client)
    client.post(f"/api/sessions/{sid}/run", json={"max_steps": 1})
    r = client.get("/api/sessions")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    row = items[0]
    for key in ("id", "question", "created_at", "lessons", "score", "total_cost_usd"):
        assert key in row
    assert row["lessons"] == 1
    assert row["score"] is not None


# ---- 预算中止 ----


def test_budget_exceeded_yields_error_event(budget_client):
    sid = _new_session(budget_client)
    r = budget_client.post(f"/api/sessions/{sid}/run", json={"max_steps": 2})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    evs = _events(r.text)
    assert [e["event"] for e in evs] == ["stage", "error"]
    assert "预算" in evs[1]["message"]
    # 会话详情仍可取（阶段产物保留到中止点为止）
    r = budget_client.get(f"/api/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["plan"] is None
