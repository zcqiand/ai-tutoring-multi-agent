"""配置装配：fail-fast，无默认兜底。

LLM_MODE 必填（mock|live）；live 模式下 ANTHROPIC_API_KEY 缺失即拒绝启动。
优先级：真实环境变量 > .env 文件。密钥只放 .env，不入库。
形态逐行对齐 cs-support-agent/config.py（家族范式）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    llm_mode: str
    api_key: str
    budget_usd: float | None
    app_port: int
    llm_base_url: str = ""  # 可选；空 = Anthropic 官方，家族 prod 指向 MiniMax 兼容端点


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_settings(
    environ: Mapping[str, str] | None = None,
    env_file: str | Path | None = None,
) -> Settings:
    env = dict(os.environ if environ is None else environ)
    if env_file is None:
        env_file = Path.cwd() / ".env"
    merged = {**_parse_env_file(Path(env_file)), **{k: v for k, v in env.items() if v != ""}}

    mode = merged.get("LLM_MODE", "")
    if not mode:
        raise ValueError(
            "缺少 LLM_MODE（必填：mock | live）。"
            "请复制 .env.example 为 .env 并填写。本项目禁止 env 默认值兜底。"
        )
    if mode not in ("mock", "live"):
        raise ValueError(f"LLM_MODE 必须是 mock 或 live，当前为: {mode}")

    api_key = merged.get("ANTHROPIC_API_KEY", "")
    if mode == "live" and not api_key:
        raise ValueError(
            "LLM_MODE=live 需要 ANTHROPIC_API_KEY。"
            "请复制 .env.example 为 .env 并填入 API key。"
        )

    budget_raw = merged.get("AI_TUTOR_BUDGET_USD", "")
    budget = float(budget_raw) if budget_raw else None

    return Settings(
        llm_mode=mode,
        api_key=api_key,
        budget_usd=budget,
        app_port=int(merged.get("APP_PORT", "8804")),
        llm_base_url=merged.get("LLM_BASE_URL", ""),
    )
