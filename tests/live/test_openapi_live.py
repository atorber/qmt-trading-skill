"""对真实 Bridge 做 OpenAPI 全量/只读联调扫端。"""

from __future__ import annotations

import os

import pytest

from tests.openapi_harness import (
    ApiOperation,
    collect_operations,
    invoke_operation_http,
    run_all_operations_http,
)
from tests.openapi_samples import TRADING_PREFIXES

pytestmark = pytest.mark.live

_READONLY_PREFIXES = (
    "/api/meta/",
    "/api/sector/",
    "/api/calendar/",
    "/api/market/full_tick",
    "/api/market/indices",
    "/api/market/market_data_ex",
    "/api/etf/",
    "/api/meta/",
)


def _is_readonly(op: ApiOperation) -> bool:
    if op.requires_auth:
        return False
    return any(
        op.path.startswith(p) or op.path == p.rstrip("/")
        for p in _READONLY_PREFIXES
    )


def _format_failures(
    failures: list[tuple[ApiOperation, int, str]],
    limit: int = 25,
) -> str:
    lines = [
        f"  {op.method.upper()} {op.path} -> {status}: {detail[:100]}"
        for op, status, detail in failures[:limit]
    ]
    extra = len(failures) - limit
    if extra > 0:
        lines.append(f"  ... 另有 {extra} 个失败")
    return "\n".join(lines)


def test_live_openapi_readonly(
    live_client,
    live_openapi_spec,
    live_auth_headers,
) -> None:
    """只读类端点应全部 2xx（不触发 POST 下载/交易）。"""
    ops = [op for op in collect_operations(live_openapi_spec) if _is_readonly(op)]
    assert len(ops) >= 10

    failures = []
    for op in ops:
        resp = invoke_operation_http(
            live_client,
            live_openapi_spec,
            op,
            headers=live_auth_headers if op.requires_auth else {},
        )
        if resp.status_code not in {200, 201, 204}:
            failures.append((op, resp.status_code, resp.text[:300]))

    assert not failures, f"只读联调失败 {len(failures)} 个:\n{_format_failures(failures)}"


def test_live_openapi_full_sweep(
    live_client,
    live_openapi_spec,
    live_auth_headers,
    live_trading_enabled: bool,
) -> None:
    """全量 OpenAPI 扫端（可选；交易未启用时跳过 trading 路径）。"""
    if os.environ.get("QMT_BRIDGE_LIVE_FULL", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("全量扫端未启用：设置 QMT_BRIDGE_LIVE_FULL=1")

    failures = run_all_operations_http(
        live_client,
        live_openapi_spec,
        auth_headers=live_auth_headers,
    )

    if not live_trading_enabled:
        failures = [
            f
            for f in failures
            if not any(f[0].path.startswith(p) for p in TRADING_PREFIXES)
        ]

    max_fail = int(os.environ.get("QMT_BRIDGE_LIVE_MAX_FAILURES", "0"))
    if len(failures) <= max_fail:
        return

    pytest.fail(
        f"全量联调失败 {len(failures)} 个（允许 {max_fail}）:\n"
        f"{_format_failures(failures)}"
    )
