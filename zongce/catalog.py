# -*- coding: utf-8 -*-
"""解析学科竞赛分类表，提供白名单查询与描述性匹配关键词。"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


class Level(enum.Enum):
    """综测竞赛定级序列（专项奖学金只覆盖前六级，校 C 不覆盖）。"""
    WORLD = "世界级"
    NATIONAL_A = "国A"
    NATIONAL_B = "国B"
    PROVINCIAL_A = "省A"
    PROVINCIAL_B = "省B"
    MUNICIPAL = "市级"
    SCHOOL_C = "校C"


# 级别分段标题 → Level 映射（分类表里只有这两段是白名单；其余段为描述性）
_SECTION_LEVEL = {"国家级A类": Level.NATIONAL_A, "省级A类": Level.PROVINCIAL_A}

# 描述性匹配关键词：从分类表各段文字描述提炼，供 level.py 按主办方性质判级
DESCRIPTION_KEYWORDS: dict[Level, tuple[str, ...]] = {
    Level.NATIONAL_B: ("教育部", "教指委", "国家一级学会", "中国科协", "全国学会", "中国文联", "全国文艺家协会"),
    Level.PROVINCIAL_B: ("省级", "省一级学会", "省级教指委", "省级政府部门"),
    Level.SCHOOL_C: ("教务处", "学生处", "团委", "校级", "选拔赛"),
}


@dataclass(frozen=True)
class LevelHit:
    level: Level | None
    matched_by: str  # "白名单" / "未匹配"


@dataclass(frozen=True)
class Catalog:
    whitelist: dict[str, tuple[Level, str]]  # 竞赛名 → (级别, 主办方)

    def lookup(self, competition: str, host: str) -> LevelHit:
        if competition in self.whitelist:
            return LevelHit(self.whitelist[competition][0], "白名单")
        return LevelHit(None, "未匹配")


def load_catalog(path: str | Path) -> Catalog:
    """读分类表，抽取国家级A类/省级A类白名单。其余段为描述性，由 DESCRIPTION_KEYWORDS 覆盖。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"分类表不存在：{path}")
    frame = pd.read_excel(path, header=None)
    whitelist: dict[str, tuple[Level, str]] = {}
    current: Level | None = None
    for _, row in frame.iterrows():
        first = "" if pd.isna(row[0]) else str(row[0]).strip()
        name = "" if pd.isna(row[1]) else str(row[1]).strip()
        # 分段行：首列含「类」、且竞赛名列为空
        if name == "" and "类" in first:
            current = _SECTION_LEVEL.get(first)
            continue
        if current is None or name == "":
            continue
        host = "" if pd.isna(row[3]) else str(row[3]).strip()
        whitelist[name] = (current, host)
    return Catalog(whitelist=whitelist)
