"""Token 经济学与成本追踪。

第 20 章「生产级配置：成本控制」的实物。多代理系统最大的运营风险是
成本失控——三个代理每次调用都消耗 token，没有显式追踪就会在 demo 里
不知不觉烧掉几美元。

设计原则：
- 每次代理调用必须经过 track() 记录，禁止裸调 client.messages.create
- 错误立即抛 BudgetExceededError，不让代理继续烧钱
- pricing 表与 version-lock 模型对齐，可单点更新

定价来源：Anthropic 官方定价页面，以调用时官方页面为准（version-lock
chapter_version_dependencies 已声明"模型定价随版本变化"）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceededError(RuntimeError):
    """超出预算上限——orchestrator 必须捕获并中止整个 demo。"""


# 每百万 token 定价（美元）。input 是输入 token，output 是输出 token。
# 这些数字会随 Anthropic 调价变化——更新时同步改 version-lock 注释。
PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    # (input_per_mtollk, output_per_mtok)
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-opus-4-7": (15.00, 75.00),
}


@dataclass
class CallRecord:
    """单次代理调用的成本记录。"""

    agent: str               # planner / tutor / evaluator
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def cost_usd(self) -> float:
        in_price, out_price = PRICING_USD_PER_MTOK.get(self.model, (0.0, 0.0))
        return (self.input_tokens * in_price + self.output_tokens * out_price) / 1_000_000


@dataclass
class CostTracker:
    """累计成本追踪器。

    budget_usd 为 None 表示不限预算（仅统计，不中止）。
    """

    budget_usd: float | None = None
    records: list[CallRecord] = field(default_factory=list)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    def track(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CallRecord:
        """记录一次代理调用，并检查预算。

        Raises:
            BudgetExceededError: 累计成本超过 budget_usd。
        """
        record = CallRecord(
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.records.append(record)

        if self.budget_usd is not None and self.total_cost_usd > self.budget_usd:
            raise BudgetExceededError(
                f"累计成本 ${self.total_cost_usd:.4f} 超出预算 ${self.budget_usd:.4f}；"
                f"最近一次调用：{agent}/{model}"
            )
        return record

    def format_summary(self) -> str:
        """渲染成本汇总——run_demo 结束时打印。"""
        if not self.records:
            return "(无调用记录)"

        lines = ["─" * 50, "Token 消耗汇总", "─" * 50]
        for r in self.records:
            lines.append(
                f"  {r.agent:<10} {r.model:<20} "
                f"{r.input_tokens:>6} in / {r.output_tokens:>5} out  "
                f"(${r.cost_usd:.4f})"
            )
        lines.append("─" * 50)
        lines.append(
            f"  TOTAL      {self.total_input_tokens:>6} in / "
            f"{self.total_output_tokens:>5} out  (${self.total_cost_usd:.4f})"
        )
        if self.budget_usd is not None:
            remaining = max(0.0, self.budget_usd - self.total_cost_usd)
            lines.append(f"  预算 ${self.budget_usd:.4f}，剩余 ${remaining:.4f}")
        return "\n".join(lines)
