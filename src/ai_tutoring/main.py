"""应用装配：create_app 工厂——LLM/Store 注入点。

settings 缺省走 load_settings()（fail-fast，LLM_MODE 缺失直接拒绝启动）；
测试与离线演示用参数注入 MockLLM，不读 env。
"""

from __future__ import annotations

from fastapi import FastAPI

from .api.routes import router
from .config import Settings, load_settings
from .mock_llm import MockLLM
from .session_store import SessionStore



def build_llm(settings: Settings):
    if settings.llm_mode == "live":
        import anthropic

        return anthropic.Anthropic(api_key=settings.api_key).messages
    return MockLLM()


def create_app(settings: Settings | None = None, llm=None) -> FastAPI:
    settings = settings if settings is not None else load_settings()
    app = FastAPI(title="AI 学习辅导多智能体系统", version="0.2.0")
    app.state.settings = settings
    app.state.llm = llm if llm is not None else build_llm(settings)
    app.state.store = SessionStore()
    app.include_router(router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "mode": settings.llm_mode}

    return app
