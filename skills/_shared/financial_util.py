"""财报下载与查询辅助（供 financial-download / fundamental-screen 共用）。"""

from __future__ import annotations

from typing import Any

from common import call_api

# 常用财务表（与 xtquant 一致）
KNOWN_TABLES = (
    "Pershareindex",
    "Income",
    "Balance",
    "CashFlow",
    "Capital",
    "Holdernum",
)


def fetch_financial(client, codes: list[str], table: str) -> dict:
    data = call_api(
        client.get_financial_data,
        stocks=codes,
        tables=[table],
    )
    return data if isinstance(data, dict) else {}


def codes_without_table(data: dict, codes: list[str], table: str) -> list[str]:
    missing: list[str] = []
    for code in codes:
        stock_tables = data.get(code) or data.get(code.upper()) or {}
        recs = stock_tables.get(table) if isinstance(stock_tables, dict) else []
        if not recs:
            missing.append(code)
    return missing


def download_financial(
    client,
    codes: list[str],
    table: str,
    *,
    start_time: str = "",
    end_time: str = "",
    all_tables: bool = False,
) -> dict:
    tables = [] if all_tables else [table]
    return call_api(
        client.download_financial,
        codes,
        tables=tables,
        start_time=start_time,
        end_time=end_time,
    )


def latest_record(records: list[dict]) -> dict | None:
    if not records:
        return None
    return max(records, key=lambda r: str(r.get("m_timetag") or r.get("report_date") or ""))


def verify_cache(
    client,
    codes: list[str],
    table: str,
) -> list[dict[str, Any]]:
    """查询缓存并返回每只标的的验证结果。"""
    data = fetch_financial(client, codes, table)
    rows: list[dict[str, Any]] = []
    for code in codes:
        stock_tables = data.get(code) or data.get(code.upper()) or {}
        recs = stock_tables.get(table) if isinstance(stock_tables, dict) else []
        latest = latest_record(recs if isinstance(recs, list) else [])
        if latest:
            tag = latest.get("m_timetag") or latest.get("report_date", "")
            rows.append({"code": code, "status": "ok", "report_period": tag, "record": latest})
        else:
            rows.append({"code": code, "status": "no_data"})
    return rows
