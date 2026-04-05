"""时间工具。"""

import time


def now_ts() -> int:
    """返回当前 Unix 秒级时间戳。"""
    return int(time.time())
