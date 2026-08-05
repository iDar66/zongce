# -*- coding: utf-8 -*-
"""获奖比例（≤50% 生死线）获取：已知库 → 联网 → 用户填 → 待确认。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .level import KNOWN_COMPETITIONS


CAP = 0.5  # 获奖比例生死线（含 50%，不含优秀奖）


@dataclass(frozen=True)
class RatioResult:
    ratio: float | None          # None 表示未取到
    source: str                  # "已知库" / "联网" / "用户填" / "待确认"
    passes_cap: bool             # ratio is not None and ratio <= CAP
    note: str


def _fetch_ratio_from_url(url: str, timeout: int = 10) -> float | None:
    """fetch 公开赛事官网公示页并启发式解析获奖比例。

    【隐私不变量】本函数是 ratio.py 联网出口，受以下硬约束（违反即为护栏破口）：
    - **只读公开页面**：URL 由调用方传入，必须指向公开的赛事成绩/获奖公示页，
      不得是任何需要登录/鉴权的内部系统、教务后台或学生档案接口。
    - **GET-only**：仅用 `urllib.request.urlopen` 发起一次 GET；**绝不** POST、
      **绝不**提交任何表单/参数（不写、不改远端状态）。
    - **禁传 PII**：本函数把 `url` 原样发出去，不附加任何学生 PII（姓名/学号/
      成绩/证明内容）——URL 只是公开赛事公示页本身，与具体学生无关。
    - **失败返回 None 不崩**：任何网络/解析异常一律吞掉返回 None，由上层
      `award_ratio` 标为「待确认」；绝不抛异常打断流水线，也不缓存错误结果。
    """
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    # 启发式：找形如「2205/5307」或「41.5%」的片段；不可靠则返回 None
    pct = re.search(r"(\d+(?:\.\d+)?)\s*%", html)
    if pct:
        return float(pct.group(1)) / 100
    frac = re.search(r"(\d+)\s*/\s*(\d+)", html)
    if frac:
        return int(frac.group(1)) / int(frac.group(2))
    return None


def award_ratio(
    competition: str,
    online: bool = False,
    url: str | None = None,
    user_ratio: float | None = None,
) -> RatioResult:
    # 1) 用户手填优先（认定文件覆盖）
    if user_ratio is not None:
        return RatioResult(user_ratio, "用户填", user_ratio <= CAP, "")
    # 2) 已知库（五一数模天然过 45% 上限）
    if competition in KNOWN_COMPETITIONS or any(
        competition in k or any(a in competition for a in v["aliases"])
        for k, v in KNOWN_COMPETITIONS.items()
    ):
        return RatioResult(0.45, "已知库", True, "章程规定一/二/三等≤5%/15%/25%，合计≤45%<50%")
    # 3) 联网
    if online and url:
        ratio = _fetch_ratio_from_url(url)
        if ratio is not None:
            return RatioResult(ratio, "联网", ratio <= CAP, "")
        return RatioResult(None, "待确认", False, "联网解析失败，请手填或核对公式")
    # 4) 兜底
    return RatioResult(None, "待确认", False, "未知竞赛，需联网（--allow-online + URL）或手填比例")
