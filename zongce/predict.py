# -*- coding: utf-8 -*-
"""组装单文件加分预测。"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .extract import ExtractionResult
from .name_match import find_name
from .classify import classify_mode, classify_panel, Mode
from . import rules

@dataclass
class Prediction:
    file: str            # 完整源路径：export 取 stem 展示、organize 取 name 复制
    panel: str
    mode: Mode | None
    points: float | None
    count: int | None
    basis: str
    status: str
    note: str

_SENT_END = "。\n；;"
_KW_FOR_DEFAULT = [("参赛", "参赛"), ("裁判", "裁判"), ("后勤", "后勤"), ("工作人员", "工作人员")]

def _kw_default(panel: str, text: str) -> float | None:
    for kw, key in _KW_FOR_DEFAULT:
        if kw in text:
            return rules.PER_TIME_DEFAULT.get((panel, key))
    return None

def _basis(text: str, stmt_match) -> str:
    if stmt_match:
        i = stmt_match.start()
        # brief 原写 _SENT_SPLIT.split(seg)[0] 取首段，但 match 前若有分隔符，
        # [0] 会取到陈述"前"一句（如"…根据综测细则"），而非含陈述的句。
        # 修正：定位含 match 的句子——往前找最近分隔符、往后找首个分隔符。
        lo = max(text.rfind(c, 0, i) + 1 for c in _SENT_END)
        hi = i
        while hi < len(text) and text[hi] not in _SENT_END:
            hi += 1
        return text[lo:hi][:60].replace("\n", " ").strip()
    return text[:60].replace("\n", " ")

def predict(extraction: ExtractionResult, name: str) -> Prediction:
    src = extraction.source
    text = extraction.text
    nm = find_name(extraction, name)
    if not nm.found and name not in text:
        # 守卫：find_name 未命中且姓名不是全文子串 → 确实不在该件。
        # find_name 命中失败但 name in text（如新年音乐会名单 WRatio≈60）时
        # 不伪造 NameMatch——保留 find_name 的真实结果（count=None）继续走分类，
        # 后续 count=None → 按"次数配对失败默认1次"处理。
        return Prediction(src, "待确认", None, None, None, text[:40], "待确认", "未找到姓名")
    mode = classify_mode(text)
    stmt = rules.STMT_RE.search(text)
    # 裁决 1：brief 原写 fname（未定义）；改用 Path(src).name 取文件名喂给 classify_panel
    # final review N1：STMT 命中但 group(2)=None（裸"加2分"无数值后板块词）时，
    # normalize_panel(None)=None 会丢板块→即使抽到值也不加分。改成 group(2) 在才走它，
    # 否则 classify_panel 关键词兜底（如"篮球比赛加2分"→文体）。
    panel = rules.normalize_panel(stmt.group(2)) if (stmt and stmt.group(2)) else classify_panel(text, Path(src).name)

    points = None; count = nm.count; status = "待确认"; note = ""
    if mode == Mode.COUNT:
        per = float(stmt.group(1)) if stmt else _kw_default(panel or "", text)
        count = nm.count if nm.count is not None else 1
        if nm.count is None:
            note = "次数配对失败，默认1次"
        if per is not None and panel:
            points = round(per * count, 2); status = "自动"
        else:
            note = (note + "；" if note else "") + "单次值/板块缺失"
    elif mode == Mode.FIXED:
        if stmt and panel:
            points = float(stmt.group(1)); status = "自动"
    elif mode == Mode.GRADE:
        note = "级别待按《学科竞赛分类表》认定"
    else:  # RULE_REF
        note = "无数值/名次，按细则参照待人工确认"
    return Prediction(src, panel or "待确认", mode, points, count,
                      _basis(text, stmt), status, note)
