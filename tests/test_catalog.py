# -*- coding: utf-8 -*-
"""学科竞赛分类表解析测试。"""
from __future__ import annotations

from pathlib import Path
from openpyxl import Workbook
from zongce.catalog import DESCRIPTION_KEYWORDS, Level, load_catalog


def _write_catalog(path: Path, rows: list) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(["序号", "竞赛名称", "网址", "主办单位"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_load_catalog_parses_whitelist_and_matches(tmp_path):
    p = _write_catalog(tmp_path / "catalog.xlsx", [
        ["国家级A类", None, None, None],                                   # 分段行
        ["1", "全国大学生数学建模竞赛", "http://x", "中国工业与应用数学学会"],
        ["省级A类", None, None, None],
        ["1", "广东省大学生数学建模竞赛", "http://y", "中山大学"],
        ["省级B类", None, None, None],
        [None, None, None, "省级B类竞赛：省一级学会组织的全省性竞赛。"],       # 描述行（跳过）
    ])
    cat = load_catalog(p)

    hit = cat.lookup("全国大学生数学建模竞赛", "中国工业与应用数学学会")
    assert hit.level == Level.NATIONAL_A
    assert hit.matched_by == "白名单"

    lower = cat.lookup("广东省大学生数学建模竞赛", "中山大学")
    assert lower.level == Level.PROVINCIAL_A

    miss = cat.lookup("五一数学建模竞赛", "江苏省工业与应用数学学会")
    assert miss.level is None
    assert miss.matched_by == "未匹配"


def test_description_keywords_covers_provincial_b():
    # 描述性匹配的关键词预定义（描述行文字不可靠，不从其动态解析）
    assert "省一级学会" in DESCRIPTION_KEYWORDS[Level.PROVINCIAL_B]
    assert "国家一级学会" in DESCRIPTION_KEYWORDS[Level.NATIONAL_B]
    assert Level.SCHOOL_C in DESCRIPTION_KEYWORDS
