#!/usr/bin/env python3
"""检查 QMT Bridge 是否可达（只读，无需 API Key）。

用法:
    python skills/qmt-bridge-setup/scripts/bridge_health.py
    python skills/qmt-bridge-setup/scripts/bridge_health.py --host 127.0.0.1 --port 8080
    python skills/qmt-bridge-setup/scripts/bridge_health.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import (  # noqa: E402
    add_client_args,
    call_api,
    load_env_files,
    make_client,
    resolve_connection,
)


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 健康检查（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    host, port, _, _, _ = resolve_connection(args)
    client, _ = make_client(args, require_api_key=False)
    result = call_api(client.health_check)

    payload = {
        "ok": True,
        "host": host,
        "port": port,
        "health": result,
        "docs": f"http://{host}:{port}/docs",
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0

    print("=== QMT Bridge 健康检查 ===")
    print(f"目标: http://{host}:{port}")
    print(f"状态: 可达")
    if isinstance(result, dict):
        for k, v in result.items():
            print(f"  {k}: {v}")
    else:
        print(f"  响应: {result}")
    print(f"Swagger: {payload['docs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
