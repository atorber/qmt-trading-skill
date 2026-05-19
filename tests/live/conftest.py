"""联调测试 fixtures：连接真实 Bridge HTTP 服务。"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.live


def live_enabled() -> bool:
    return os.environ.get("QMT_BRIDGE_LIVE", "").lower() in ("1", "true", "yes")


def _live_base_url() -> str:
    explicit = os.environ.get("QMT_BRIDGE_LIVE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    host = os.environ.get("QMT_BRIDGE_HOST", "127.0.0.1")
    port = os.environ.get("QMT_BRIDGE_PORT", "8080")
    return f"http://{host}:{port}"


@pytest.fixture(scope="session")
def live_base_url() -> str:
    if not live_enabled():
        pytest.skip("未启用联调：请设置环境变量 QMT_BRIDGE_LIVE=1")
    return _live_base_url()


@pytest.fixture(scope="session")
def live_timeout() -> float:
    return float(os.environ.get("QMT_BRIDGE_LIVE_TIMEOUT", "30"))


@pytest.fixture(scope="session")
def live_client(live_base_url: str, live_timeout: float):
    """httpx 客户端；不可达时跳过整套联调用例。"""
    with httpx.Client(
        base_url=live_base_url,
        timeout=live_timeout,
    ) as client:
        try:
            resp = client.get("/api/meta/health")
        except httpx.RequestError as exc:
            pytest.skip(f"无法连接 Bridge ({live_base_url}): {exc}")
        if resp.status_code != 200:
            pytest.skip(
                f"Bridge 健康检查失败 ({live_base_url}): "
                f"HTTP {resp.status_code}"
            )
        yield client


@pytest.fixture(scope="session")
def live_api_key() -> str:
    return os.environ.get("QMT_BRIDGE_API_KEY", "")


@pytest.fixture(scope="session")
def live_auth_headers(live_api_key: str) -> dict[str, str]:
    if not live_api_key:
        return {}
    return {"X-API-Key": live_api_key}


@pytest.fixture(scope="session")
def live_openapi_spec(live_client: httpx.Client) -> dict:
    resp = live_client.get("/openapi.json")
    assert resp.status_code == 200, resp.text[:200]
    return resp.json()


@pytest.fixture(scope="session")
def live_trading_enabled(
    live_client: httpx.Client,
    live_auth_headers: dict[str, str],
) -> bool:
    """探测 /api/trading/* 是否已挂载。"""
    if not live_auth_headers:
        return False
    resp = live_client.get(
        "/api/trading/positions",
        headers=live_auth_headers,
    )
    if resp.status_code == 404:
        return False
    return resp.status_code == 200
