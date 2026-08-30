from __future__ import annotations

from typing import Any

OPTIONS_SL_PCT_MIN = 0.20
OPTIONS_SL_PCT_MAX = 0.50
OPTIONS_TP_PCT_MIN = 0.30
OPTIONS_TARGET_REWARD_TO_RISK = 2.0
OPTIONS_DEFAULT_SL_PCT = 0.25
OPTIONS_DEFAULT_TP_PCT = 0.50


def options_risk_plan(
    *,
    premium_per_share: float,
    contracts: int = 1,
    multiplier: float = 100.0,
    take_profit_pct: float = OPTIONS_DEFAULT_TP_PCT,
    stop_loss_pct: float = OPTIONS_DEFAULT_SL_PCT,
) -> dict[str, Any]:
    """Cash-risked plan for long options. Does not invent prices beyond inputs.

    Locked bands: SL 20–50% of premium; TP 30–100%+ of premium; aim 1:2 R:R.
    Default working pair is −25% / +50% (1:2, inside the bands).
    """
    if contracts != 1:
        raise ValueError("Phase rules require max 1 contract")
    if stop_loss_pct < OPTIONS_SL_PCT_MIN or stop_loss_pct > OPTIONS_SL_PCT_MAX:
        raise ValueError(
            f"options stop_loss_pct must be in [{OPTIONS_SL_PCT_MIN}, {OPTIONS_SL_PCT_MAX}], got {stop_loss_pct}"
        )
    if take_profit_pct < OPTIONS_TP_PCT_MIN:
        raise ValueError(
            f"options take_profit_pct must be >= {OPTIONS_TP_PCT_MIN}, got {take_profit_pct}"
        )
    cash = premium_per_share * multiplier * contracts
    reward_to_risk = take_profit_pct / stop_loss_pct if stop_loss_pct else None
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
        "stop_loss_pct_band": {"min": OPTIONS_SL_PCT_MIN, "max": OPTIONS_SL_PCT_MAX},
        "take_profit_pct_band": {"min": OPTIONS_TP_PCT_MIN, "uncapped": True},
        "target_reward_to_risk": OPTIONS_TARGET_REWARD_TO_RISK,
        "reward_to_risk": reward_to_risk,
        "meets_target_rr": reward_to_risk is not None
        and reward_to_risk + 1e-12 >= OPTIONS_TARGET_REWARD_TO_RISK,
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
