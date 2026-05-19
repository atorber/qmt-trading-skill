#!/usr/bin/env python3
"""WebSocket 实时行情订阅示例：运行 N 秒后输出收到条数摘要。

用法:
    python skills/qmt-bridge-realtime-monitor/scripts/ws_subscribe.py \\
        --codes 000001.SZ,600519.SH --seconds 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, load_env_files, resolve_connection  # noqa: E402


async def _run(host: str, port: int, codes: list[str], seconds: int, period: str) -> int:
    try:
        import websockets
    except ImportError:
        print("错误: 需要 pip install websockets", file=sys.stderr)
        return 2

    url = f"ws://{host}:{port}/ws/realtime"
    count = 0
    last_sample: dict = {}

    async def _collect():
        nonlocal count, last_sample
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"stocks": codes, "period": period}))
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    count += 1
                    data = json.loads(msg)
                    if isinstance(data, dict) and count <= 3:
                        last_sample = data
                except asyncio.TimeoutError:
                    continue

    try:
        await asyncio.wait_for(_collect(), timeout=seconds)
    except asyncio.TimeoutError:
        pass

    print(f"=== WebSocket 订阅摘要 ({seconds}s) ===")
    print(f"  地址: {url}")
    print(f"  代码: {','.join(codes)}")
    print(f"  收到消息: {count} 条")
    if last_sample:
        text = json.dumps(last_sample, ensure_ascii=False, default=str)
        print(f"  样本: {text[:300]}{'...' if len(text) > 300 else ''}")
    return 0


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="WebSocket 行情订阅示例")
    add_client_args(parser)
    parser.add_argument("--codes", required=True, help="股票代码，逗号分隔")
    parser.add_argument(
        "--seconds",
        "--duration",
        type=int,
        default=10,
        help="运行秒数（默认 10；演示脚本，非生产监控）",
    )
    parser.add_argument("--period", default="tick", help="tick 或 1m 等")
    args = parser.parse_args()

    host, port, _, _ = resolve_connection(args)
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    return asyncio.run(_run(host, port, codes, args.seconds, args.period))


if __name__ == "__main__":
    sys.exit(main())
