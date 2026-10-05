"""python -m ai_tutoring：以 LLM_MODE 指定的模式起 HTTP 服务（默认 8804）。"""

from __future__ import annotations

import uvicorn

from .config import load_settings
from .main import create_app


def main() -> None:
    settings = load_settings()
    app = create_app(settings)
    uvicorn.run(app, host="127.0.0.1", port=settings.app_port, log_level="info")


if __name__ == "__main__":
    main()
