from __future__ import annotations

from typing import Any


def options_risk_plan(
    *,
    premium_per_share: float,
    contracts: int = 1,
    multiplier: float = 100.0,
    take_profit_pct: float = 0.2,
    stop_loss_pct: float = 0.07,
) -> dict[str, Any]:
    """Cash-risked plan for long options. Does not invent prices beyond inputs."""
    if contracts != 1:
        raise ValueError("Phase rules require max 1 contract")
    cash = premium_per_share * multiplier * contracts
    return {
        "asset_class": "option",
        "contracts": contracts,
        "premium_per_share": premium_per_share,
        "multiplier": multiplier,
        "cash_risked": cash,
        "take_profit_pct": take_profit_pct,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_value": cash * (1.0 + take_profit_pct),
        "stop_loss_value": cash * (1.0 - stop_loss_pct),
        "take_profit_premium": premium_per_share * (1.0 + take_profit_pct),
        "stop_loss_premium": premium_per_share * (1.0 - stop_loss_pct),
        "broker_exit": "stop_first_until_oco",
        "monitor_take_profit_in_loop": True,
    }


def equity_risk_plan(
    *,
    cost_basis: float,
    take_profit_pct: float = 0.25,
    stop_loss_pct: float = 0.2,
) -> dict[str, Any]:
    return {
        "asset_class": "equity",
        "cost_basis": cost_basis,
        "take_profit_pct": take_profit_pct,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_value": cost_basis * (1.0 + take_profit_pct),
        "stop_loss_value": cost_basis * (1.0 - stop_loss_pct),
        "broker_exit": "stop_first_until_oco",
        "monitor_take_profit_in_loop": True,
    }
