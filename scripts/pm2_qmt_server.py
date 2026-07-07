#!/usr/bin/env python3
"""PM2 入口：转发至 ``qmt-server``（``cli.main``，自动加载仓库根 ``.env``）。"""

from qmt_bridge.server.cli import main

if __name__ == "__main__":
    main()
