"""加载复盘 thresholds.yaml（无 PyYAML 依赖的简易 KEY: VALUE 解析）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_THRESHOLDS_PATH = (
    Path(__file__).resolve().parents[1]
    / "qmt-bridge-execution-review"
    / "references"
    / "thresholds.yaml"
)

_DEFAULTS: dict[str, float] = {
    "turnover_cautious_max_yi": 10_000.0,
    "turnover_moderate_max_yi": 28_500.0,
    "take_profit_1d_pct": 5.0,
    "take_profit_3d_pct": 8.0,
    "chase_range_position": 0.65,
    "dip_range_position": 0.40,
    "dip_uplift_from_buy_pct": 2.0,
    "chase_near_close_ratio": 0.995,
    "dip_buy_pct": -2.0,
    "strong_rise_hold_pct": 3.0,
    "success_dip_close_pct": 5.0,
    "max_holdings_focus": 6,
    "max_active_traded_today": 4,
    "min_cash_pct_cautious": 15.0,
    "min_cash_pct_moderate": 10.0,
    "slippage_warn_bp": 30.0,
    "slippage_severe_bp": 100.0,
    "order_count_busy": 10,
    "cancel_count_busy": 3,
    "heat_trend_up_pct": 5.0,
    "heat_trend_down_pct": -8.0,
    "heat_spike_pullback_pct": -10.0,
    "op_alpha_positive_hint": 2000.0,
    "op_alpha_improve_hint": -2000.0,
    "pnl_positive_large": 5000.0,
    "pnl_positive_mid": 3000.0,
    "score_alpha_large": 5000.0,
    "score_alpha_large_bonus": 1.2,
    "score_alpha_pos_bonus": 0.8,
    "score_alpha_large_penalty": -1.6,
    "score_alpha_neg_penalty": -1.1,
}

_cache: dict[str, float] | None = None


def _parse_simple_yaml(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        val = rest.split("#", 1)[0].strip()
        if not key or not val:
            continue
        try:
            out[key] = float(val)
        except ValueError:
            continue
    return out


def load_thresholds(path: Path | None = None, *, reload: bool = False) -> dict[str, float]:
    """返回阈值字典；文件缺失或损坏时用内置默认。"""
    global _cache
    if _cache is not None and not reload and path is None:
        return _cache
    merged = dict(_DEFAULTS)
    p = path or _THRESHOLDS_PATH
    if p.is_file():
        try:
            merged.update(_parse_simple_yaml(p.read_text(encoding="utf-8")))
        except OSError:
            pass
    if path is None:
        _cache = merged
    return merged


def thr(key: str, default: float | None = None) -> float:
    vals = load_thresholds()
    if key in vals:
        return vals[key]
    if default is not None:
        return default
    return float(_DEFAULTS.get(key, 0.0))


def thresholds_snapshot() -> dict[str, Any]:
    return dict(load_thresholds())
