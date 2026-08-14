#!/usr/bin/env python3
"""批量调用 QMT 公式/指标（只读）。

用法:
    python skills/qmt-bridge-technical-signal/scripts/formula_check.py \\
        --formula MA --codes 000001.SZ,600519.SH --param N=20
    python skills/qmt-bridge-technical-signal/scripts/formula_check.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, load_env_files, make_client, unwrap_data  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def _parse_params(items: list[str]) -> dict:
    params: dict = {}
    for item in items:
        if "=" not in item:
            continue
        k, _, v = item.partition("=")
        k, v = k.strip(), v.strip()
        try:
            params[k] = int(v)
        except ValueError:
            try:
                params[k] = float(v)
            except ValueError:
                params[k] = v
    return params


def _last_scalar(result: dict) -> str:
    """从公式返回中提取最后一个可展示标量。"""
    if not isinstance(result, dict):
        return str(result)[:120]
    for key in ("value", "result", "data", "close"):
        if key in result:
            return str(result[key])[-120:]
    if "series" in result and isinstance(result["series"], list) and result["series"]:
        return str(result["series"][-1])[:120]
    text = json.dumps(result, ensure_ascii=False, default=str)
    return text[:200] + ("..." if len(text) > 200 else "")


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT 公式批量检查（只读）")
    add_client_args(parser)
    parser.add_argument("--list", action="store_true", help="列出可用公式")
    parser.add_argument("--formula", default="", help="公式名称，如 MA、MACD")
    parser.add_argument("--codes", default="", help="股票代码，逗号分隔")
    parser.add_argument("--period", default="1d", help="K 线周期")
    parser.add_argument("--count", type=int, default=5, help="返回条数（默认 5）")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="公式参数，如 --param N=20",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)

    if args.list:
        import urllib.error

        try:
            formulas = unwrap_data(
                call_api(client.get_formulas, raise_on_error=False)
            )
        except urllib.error.HTTPError as exc:
            print(
                f"公式列表不可用 (HTTP {exc.code})。"
                "请确认 QMT 公式引擎已就绪，或直接 --formula 指定名称。",
                file=sys.stderr,
            )
            return 1
        print("=== 可用公式 ===")
        if isinstance(formulas, list):
            for f in formulas[:50]:
                print(f"  {f}")
            if len(formulas) > 50:
                print(f"  ... 共 {len(formulas)} 个")
        else:
            print(json.dumps(formulas, ensure_ascii=False, indent=2, default=str))
        return 0

    if not args.formula or not args.codes:
        print("错误: 须指定 --formula 与 --codes，或使用 --list", file=sys.stderr)
        return 2

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    params = _parse_params(args.param)
    name_map = fetch_stock_names(client, codes)

    import urllib.error

    try:
        raw = call_api(
            client.call_formula_batch,
            formula_name=args.formula,
            stock_codes=codes,
            period=args.period,
            count=args.count,
            raise_on_error=False,
            **params,
        )
    except urllib.error.HTTPError as exc:
        print(
            f"公式计算失败 (HTTP {exc.code})。"
            "请确认 QMT 已登录、公式引擎可用，或稍后重试。",
            file=sys.stderr,
        )
        return 1
    data = unwrap_data(raw) if isinstance(raw, dict) else raw
    if not isinstance(data, dict):
        data = {codes[0]: data} if codes else {}

    rows = []
    for code in codes:
        res = data.get(code) or data.get(code.upper()) or {}
        rows.append({"code": code, "summary": _last_scalar(res), "raw": res})

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, default=str))
        return 0

    print(f"=== 公式 {args.formula} ({args.period}) ===")
    for r in rows:
        sym = label_stock(r["code"], name_map)
        print(f"  {sym}  {r['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
