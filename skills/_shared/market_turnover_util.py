"""近 N 日两市成交额：get_full_tick（当日）+ 本地日缓存（历史）。

官方文档（迅投知识库 · 指数数据）：
- 当日成交额：xtdata.get_full_tick，字段 amount（稳定，不读本地 K 线缓存）
- 历史指数日 K：download_history_data + get_market_data_ex（易触发 BSON，复盘热路径禁用）

复盘/校验默认 **不** 调用任何历史 K 线接口；历史缺口靠每日收盘 tick 写入
``reports/market_turnover_daily.json`` 逐步补齐。可选 ``--try-history`` 单次尝试
子进程 get_market_data（仍可能拖慢或搞坏 QMT 行情服务，仅作手动补救）。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from trading_philosophy import TurnoverDay, classify_volume_zone

SH_INDEX = "000001.SH"
SZ_INDEX = "399106.SZ"
SZ_FALLBACK = "399001.SZ"
DEFAULT_CACHE_PATH = Path("reports/market_turnover_daily.json")


def _normalize_trade_date(raw) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if s.isdigit() and len(s) >= 13:
        try:
            return datetime.fromtimestamp(int(s[:13]) / 1000).strftime("%Y%m%d")
        except (ValueError, OSError):
            return ""
    if s.isdigit() and len(s) >= 8:
        return s[:8]
    if "T" in s:
        return s.split("T", 1)[0].replace("-", "")[:8]
    if "-" in s:
        return s.replace("-", "")[:8]
    return ""


def amount_map_from_records(records: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in records:
        if not isinstance(row, dict):
            continue
        dt = _normalize_trade_date(
            row.get("date") or row.get("time") or row.get("index")
        )
        amt = row.get("amount")
        if not dt or amt is None:
            continue
        try:
            val = float(amt)
        except (TypeError, ValueError):
            continue
        if val > 0:
            out[dt] = val
    return out


def _records_from_market_data_payload(payload, code: str) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    recs = payload.get(code) or payload.get(code.upper())
    if isinstance(recs, list):
        return [x for x in recs if isinstance(x, dict)]
    if len(payload) == 1:
        only = next(iter(payload.values()))
        if isinstance(only, list):
            return [x for x in only if isinstance(x, dict)]
    return []


def get_recent_trading_dates(client, days: int) -> list[str]:
    """近 N 个交易日（YYYYMMDD），来自交易日历 API（不读 K 线）。"""
    if days <= 0:
        return []
    end = date.today().strftime("%Y%m%d")
    start = (date.today() - timedelta(days=max(days * 2 + 14, 21))).strftime("%Y%m%d")
    try:
        raw = client.get_trading_dates("SH", start_time=start, end_time=end)
        normalized = sorted(
            {_normalize_trade_date(d) for d in (raw or []) if _normalize_trade_date(d)}
        )
        return normalized[-days:]
    except Exception:
        return []


def load_index_amount_map_market_data(client, code: str, count: int) -> dict[str, float]:
    """可选补救：子进程 get_market_data 读本地日 K amount（非复盘热路径）。"""
    try:
        payload = client.get_market_data(
            stocks=[code],
            fields="amount",
            period="1d",
            count=max(count, 1),
            dividend_type="none",
            fill_data=True,
        )
        return amount_map_from_records(_records_from_market_data_payload(payload, code))
    except Exception:
        return {}


def persist_amount_maps_to_cache(
    sh_map: dict[str, float],
    sz_map: dict[str, float],
    dates: list[str],
    *,
    source: str = "market_data",
    sz_code: str = SZ_INDEX,
) -> int:
    """将历史成交额写入本地日缓存，返回新写入条数。"""
    saved = 0
    for dt in dates:
        sh = sh_map.get(dt, 0)
        sz = sz_map.get(dt, 0)
        if sh > 0 and sz > 0:
            save_turnover_cache_entry(dt, sh, sz, source=source, sz_code=sz_code)
            saved += 1
    return saved


def try_backfill_history_from_market_data(
    client,
    target_dates: list[str],
) -> tuple[dict[str, float], dict[str, float]]:
    """单次批量尝试从 get_market_data 补齐缺失交易日（可能超时/BSON，慎用）。"""
    if not target_dates:
        return {}, {}
    count = min(len(target_dates) + 2, 10)
    sh_map = load_index_amount_map_market_data(client, SH_INDEX, count)
    sz_primary = load_index_amount_map_market_data(client, SZ_INDEX, count)
    sz_fallback = load_index_amount_map_market_data(client, SZ_FALLBACK, count)
    sz_map = dict(sz_fallback)
    sz_map.update({k: v for k, v in sz_primary.items() if v > 0})
    return sh_map, sz_map


def load_turnover_cache(path: Path | None = None) -> dict[str, dict]:
    path = path or DEFAULT_CACHE_PATH
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = raw.get("entries") if isinstance(raw, dict) else None
    return entries if isinstance(entries, dict) else {}


def save_turnover_cache_entry(
    trade_date: str,
    sh_yuan: float,
    sz_yuan: float,
    *,
    path: Path | None = None,
    source: str = "tick",
    sz_code: str = SZ_INDEX,
) -> None:
    path = path or DEFAULT_CACHE_PATH
    if not trade_date or sh_yuan <= 0 or sz_yuan <= 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = load_turnover_cache(path)
    entries[trade_date] = {
        "sh_yuan": sh_yuan,
        "sz_yuan": sz_yuan,
        "yi": round((sh_yuan + sz_yuan) / 1e8, 2),
        "source": source,
        "sz_code": sz_code,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    keep = sorted(entries)[-120:]
    trimmed = {k: entries[k] for k in keep}
    path.write_text(
        json.dumps({"entries": trimmed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def merge_cache_into_maps(
    sh_map: dict[str, float],
    sz_map: dict[str, float],
    cache: dict[str, dict],
) -> None:
    for dt, row in cache.items():
        if not isinstance(row, dict):
            continue
        try:
            sh = float(row.get("sh_yuan") or 0)
            sz = float(row.get("sz_yuan") or 0)
        except (TypeError, ValueError):
            continue
        if sh > 0 and dt not in sh_map:
            sh_map[dt] = sh
        if sz > 0 and dt not in sz_map:
            sz_map[dt] = sz


def _tick_amount_yuan(tick: dict | None) -> float | None:
    if not isinstance(tick, dict):
        return None
    raw = tick.get("amount")
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _lookup_tick(tick_map: dict, code: str) -> dict | None:
    t = tick_map.get(code) or tick_map.get(code.upper()) or tick_map.get(code.lower())
    return t if isinstance(t, dict) else None


def fetch_today_index_amounts(client) -> tuple[float | None, float | None, str]:
    """当日上证+深市成交额（元）及深市代码，官方推荐 get_full_tick。"""
    for loader in (
        lambda: client.get_market_snapshot([SH_INDEX, SZ_INDEX, SZ_FALLBACK]),
        lambda: (client.get_major_indices() or {}).get("data") or {},
    ):
        try:
            tick_map = loader()
            if not isinstance(tick_map, dict):
                continue
            sh = _tick_amount_yuan(_lookup_tick(tick_map, SH_INDEX))
            sz = _tick_amount_yuan(_lookup_tick(tick_map, SZ_INDEX))
            sz_code = SZ_INDEX
            if sz is None:
                sz = _tick_amount_yuan(_lookup_tick(tick_map, SZ_FALLBACK))
                sz_code = SZ_FALLBACK
            if sh is not None and sz is not None:
                return sh, sz, sz_code
        except Exception:
            continue
    return None, None, SZ_INDEX


def is_history_stale(common_dates: list[str], max_age_days: int = 4) -> bool:
    if not common_dates:
        return True
    latest = common_dates[-1]
    if len(latest) != 8 or not latest.isdigit():
        return True
    try:
        d = datetime.strptime(latest, "%Y%m%d").date()
        return (date.today() - d).days > max_age_days
    except Exception:
        return True


def fetch_turnover_amount_maps(
    client,
    *,
    try_history: bool = False,
) -> tuple[dict[str, float], dict[str, float], str]:
    """构建沪/深成交额映射：缓存 + 当日 tick；默认不拉历史 K 线。"""
    sh_map: dict[str, float] = {}
    sz_map: dict[str, float] = {}
    merge_cache_into_maps(sh_map, sz_map, load_turnover_cache())

    today = date.today().strftime("%Y%m%d")
    sh_today, sz_today, sz_used = fetch_today_index_amounts(client)
    if sh_today and sz_today:
        sh_map[today] = sh_today
        sz_map[today] = sz_today
        save_turnover_cache_entry(
            today, sh_today, sz_today, source="tick", sz_code=sz_used
        )

    if try_history:
        target = get_recent_trading_dates(client, 5)
        missing = [
            d
            for d in target
            if sh_map.get(d, 0) <= 0 or sz_map.get(d, 0) <= 0
        ]
        if missing:
            h_sh, h_sz = try_backfill_history_from_market_data(client, missing)
            for dt, val in h_sh.items():
                if val > 0 and sh_map.get(dt, 0) <= 0:
                    sh_map[dt] = val
            for dt, val in h_sz.items():
                if val > 0 and sz_map.get(dt, 0) <= 0:
                    sz_map[dt] = val
            filled = [
                d for d in missing
                if sh_map.get(d, 0) > 0 and sz_map.get(d, 0) > 0
            ]
            if filled:
                persist_amount_maps_to_cache(
                    sh_map, sz_map, filled, source="market_data", sz_code=sz_used
                )

    return sh_map, sz_map, sz_used


def build_turnover_history(
    sh_map: dict[str, float],
    sz_map: dict[str, float],
    target_dates: list[str],
) -> list[TurnoverDay]:
    if len(target_dates) < 1 or is_history_stale(target_dates):
        return []
    result: list[TurnoverDay] = []
    for dt in target_dates:
        sh = sh_map.get(dt, 0)
        sz = sz_map.get(dt, 0)
        if sh <= 0 or sz <= 0:
            return []
        yi = round((sh + sz) / 1e8, 2)
        zone = classify_volume_zone(yi)
        result.append(
            TurnoverDay(
                trade_date=dt,
                turnover_yi=yi,
                zone_label=zone.label if zone else "—",
            )
        )
    return result


def fetch_turnover_history(client, days: int = 3) -> list[TurnoverDay]:
    target = get_recent_trading_dates(client, days)
    sh_map, sz_map, _ = fetch_turnover_amount_maps(client, try_history=False)
    if not target:
        common = sorted(set(sh_map) & set(sz_map))
        target = common[-days:]
    return build_turnover_history(sh_map, sz_map, target)


def ensure_recent_turnover(
    client, days: int = 3, *, try_history: bool = False
) -> dict:
    """校验近 N 日两市成交额是否齐全（默认仅 tick + 本地缓存）。"""
    target = get_recent_trading_dates(client, days)
    sh_map, sz_map, sz_used = fetch_turnover_amount_maps(
        client, try_history=try_history
    )
    if not target:
        sh_dates = sorted(sh_map)
        target = sh_dates[-days:] if len(sh_dates) >= days else sh_dates
    missing_sh = [d for d in target if sh_map.get(d, 0) <= 0]
    missing_sz = [d for d in target if sz_map.get(d, 0) <= 0]
    ok = bool(target) and not missing_sh and not missing_sz and len(target) >= days
    return {
        "ok": ok,
        "days": days,
        "target_dates": target,
        "sh_code": SH_INDEX,
        "sz_code_used": sz_used,
        "missing_sh_dates": missing_sh,
        "missing_sz_dates": missing_sz,
        "method": "full_tick+cache"
        + ("+optional_market_data" if try_history else ""),
        "cache_path": str(DEFAULT_CACHE_PATH),
    }
