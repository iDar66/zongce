# -*- coding: utf-8 -*-
"""姓名模糊匹配 + 同列邻近 (N) 还原次数。"""
from __future__ import annotations
from dataclasses import dataclass
from rapidfuzz import fuzz
from .extract import ExtractionResult, OcrLine
from . import rules

@dataclass
class NameMatch:
    found: bool
    count: int | None
    confidence: float
    context: str
    best_token: str
    best_score: float

def _overlap_ratio(a: tuple, b: tuple) -> float:
    lo = max(a[0], b[0]); hi = min(a[2], b[2])
    if hi <= lo:
        return 0.0
    inter = hi - lo
    w = min(a[2] - a[0], b[2] - b[0]) or 1.0
    return inter / w

def _find_name_line(lines: list[OcrLine], name: str, threshold: float):
    best = None
    for ln in lines:
        t = ln.text.strip()
        if not t:
            continue
        score = fuzz.WRatio(name, t)
        if score >= threshold and (best is None or score > best[1]):
            best = (ln, score)
    return best  # (OcrLine, score) | None

def _count_below_in_column(lines: list[OcrLine], name_line: OcrLine) -> int | None:
    nh = name_line.h or 20
    candidates = []
    for ln in lines:
        m = rules.COUNT_TOKEN_RE.match(ln.text.strip())
        if not m:
            continue
        n = int(m.group(1) or m.group(2))
        if _overlap_ratio(name_line.bbox, ln.bbox) < 0.5:   # 同列
            continue
        dy = ln.cy - name_line.cy
        if -nh <= dy <= 2 * nh:                             # 上方1行 或 下方2行内
            candidates.append((abs(dy), n))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]

def _context(text: str, name: str) -> str:
    i = text.find(name)
    if i < 0:
        return ""
    return text[max(0, i - 30): i + len(name) + 30].replace("\n", " ")

def find_name(extraction: ExtractionResult, name: str, threshold: float = 80.0) -> NameMatch:
    best_overall = None
    chosen_page_lines = None
    for pg in extraction.pages:
        hit = _find_name_line(pg.lines, name, threshold)
        if hit and (best_overall is None or hit[1] > best_overall[1]):
            best_overall = hit
            chosen_page_lines = pg.lines
    if best_overall is None:
        return NameMatch(False, None, 0.0, "", "", 0.0)
    name_line, score = best_overall
    count = _count_below_in_column(chosen_page_lines, name_line)
    return NameMatch(True, count, score / 100.0,
                     _context(extraction.text, name_line.text.strip()),
                     name_line.text.strip(), score)
