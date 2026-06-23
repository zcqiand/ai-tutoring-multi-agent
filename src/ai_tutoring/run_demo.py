"""run_demo：一条命令跑完三代理协作。

用法：
    python -m ai_tutoring.run_demo "请教我导数"
    # 或安装后：
    ai-tutor-demo "请教我导数"

需要 ANTHROPIC_API_KEY 环境变量。没有 key 会立刻报错退出。
"""

from __future__ import annotations

import os
import sys

from .cost_tracker import BudgetExceededError, CostTracker
from .orchestrator import make_client, run_full_session


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print('用法：ai-tutor-demo "请教你导数"')
        print("需要环境变量 ANTHROPIC_API_KEY。")
        return 1

    question = argv[0]
    budget_str = os.environ.get("AI_TUTOR_BUDGET_USD", "0.50")
    budget = float(budget_str)

    try:
        client = make_client()
    except RuntimeError as exc:
        print(f"启动失败：{exc}")
        return 2

    tracker = CostTracker(budget_usd=budget)

    print(f"学习请求：{question}")
    print(f"预算上限：${budget:.4f}")
    print("=" * 50)

    try:
        memory = run_full_session(question, client, tracker)
    except BudgetExceededError as exc:
        print(f"\n⚠ 预算超限，流程中止：{exc}")
        print(tracker.format_summary())
        return 3

    # 打印三代理产出
    plan = memory.freeze_plan()
    print(f"\n【planner】学习路径（{len(plan.steps)} 步）")
    for i, step in enumerate(plan.steps, 1):
        print(f"  {i}. {step}")
    print(f"  拆分理由：{plan.rationale}")

    print(f"\n【tutor】讲解了 {len(memory.lessons)} 步")
    for lesson in memory.lessons:
        print(f"\n  ── {lesson.step} ──")
        print(f"  {lesson.content[:200]}{'...' if len(lesson.content) > 200 else ''}")
        if lesson.key_points:
            print(f"  关键要点：{'；'.join(lesson.key_points)}")

    if memory.evaluation:
        ev = memory.evaluation
        print(f"\n【evaluator】学习效果评估")
        print(f"  理解度：{ev.understanding_score}/100")
        if ev.strengths:
            print(f"  优点：{'；'.join(ev.strengths)}")
        if ev.gaps:
            print(f"  不足：{'；'.join(ev.gaps)}")
        print(f"  建议：{ev.recommendation}")

    print()
    print(tracker.format_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
