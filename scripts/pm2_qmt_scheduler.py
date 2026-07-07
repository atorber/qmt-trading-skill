#!/usr/bin/env python3
"""PM2 入口：转发至 ``qmt-scheduler``（``cli.scheduler_main``）。"""

from qmt_bridge.server.cli import scheduler_main

if __name__ == "__main__":
    scheduler_main()
