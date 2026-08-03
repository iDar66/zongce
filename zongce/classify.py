# -*- coding: utf-8 -*-
"""加分模式识别 + 板块关键词分类（兜底）。"""
from __future__ import annotations
from enum import Enum
from . import rules

class Mode(str, Enum):
    COUNT = "次数型"
    FIXED = "固定值型"
    GRADE = "获奖分级型"
    RULE_REF = "细则参照型"

def classify_mode(text: str) -> Mode:
    """优先级：次数型 > 获奖分级型 > 固定值型 > 细则参照型。"""
    if rules.COUNT_RE.search(text) and rules.COUNT_HINT_RE.search(text):
        return Mode.COUNT
    if any(k in text for k in rules.GRADE_KEYWORDS):
        return Mode.GRADE
    if rules.FIXED_RE.search(text):
        return Mode.FIXED
    return Mode.RULE_REF

def classify_panel(text: str, filename: str) -> str:
    """关键词投票；唯一命中→该板块，零命中或并列→待确认。"""
    hay = f"{filename} {text}"
    scores = {p: sum(1 for kw in kws if kw in hay) for p, kws in rules.PANEL_KEYWORDS.items()}
    hits = {p: s for p, s in scores.items() if s > 0}
    if not hits:
        return "待确认"
    if len(hits) == 1:
        return next(iter(hits))
    mx = max(hits.values())
    winners = [p for p, s in hits.items() if s == mx]
    return winners[0] if len(winners) == 1 else "待确认"
