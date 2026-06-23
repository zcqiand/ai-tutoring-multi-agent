"""主调度器：把 planner → tutor → evaluator 串成完整流程。

第 18 章「代理间通信」的核心实物。orchestrator 不持有任何业务逻辑——
它只决定"先调谁、后调谁、中间怎么传上下文"。所有业务在 agents.py 里。

设计原则：
- 顺序编排（planner → tutor × N → evaluator），不并行——三代理有数据依赖
- 失败立即中止，不让后续代理基于错误状态继续烧 token
- 预算超限抛 BudgetExceededError，由调用层（run_demo）决定如何收尾
"""

from __future__ import annotations

import os

from .agents import LLMClient, run_evaluator, run_planner, run_tutor_step
from .cost_tracker import CostTracker
from .shared_memory import SharedMemory


def make_client() -> LLMClient:
    """构造真实的 Anthropic 客户端。

    独立成函数便于测试 mock——测试里不调这个，直接注入 fake client。
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未设置 ANTHROPIC_API_KEY 环境变量。"
            "请拷贝 .env.example 为 .env 并填入 API key。"
        )
    # anthropic.Anthropic 的 .messages 属性满足 LLMClient 协议
    return anthropic.Anthropic(api_key=api_key).messages  # type: ignore[return-value]


def run_full_session(
    user_question: str,
    client: LLMClient,
    tracker: CostTracker,
    max_steps: int = 3,
) -> SharedMemory:
    """跑完整三代理流程：plan → tutor × min(steps, max_steps) → evaluate。

    max_steps 限制 tutor 最多讲几步——避免长学习路径在 demo 里烧太多 token。
    生产环境可去掉这个限制。

    返回填满产出的 SharedMemory。
    """
    memory = SharedMemory(user_question=user_question)

    # 1. planner
    run_planner(memory, client, tracker)

    # 2. tutor 按路径逐步讲解
    steps_to_teach = memory.freeze_plan().steps[:max_steps]
    for step in steps_to_teach:
        run_tutor_step(step, memory, client, tracker)

    # 3. evaluator
    run_evaluator(memory, client, tracker)

    return memory
