# -*- coding: utf-8 -*-
"""竞赛定级：已知库 → 白名单 → 主办方性质描述性匹配 → 行业协(学)会主办降一级。

定级规则见综测领域规则.md §3「定级流程」：先按分类表定级，再对行业协(学)会主办降一级
（序列 国A>国B>省A>省B>校C）。文中「最终能否拿钱取决于学校认定」指降级后奖金能否发放
（下游 scholarship 步骤处理），不影响此处的级别判定本身。
"""
from __future__ import annotations

from dataclasses import dataclass

from .catalog import DESCRIPTION_KEYWORDS, Catalog, Level


# 降级序列（高 → 低）：分类表 5 级（国A>国B>省A>省B>校C）。
# 世界级/市级是「奖金折算档」，不来自分类表定级、不参与「降一级」。
_DROP_ORDER: tuple[Level, ...] = (
    Level.NATIONAL_A, Level.NATIONAL_B,
    Level.PROVINCIAL_A, Level.PROVINCIAL_B, Level.SCHOOL_C,
)


def drop_one_level(level: Level) -> Level:
    """分类表定级序列中退一格；已是最低、或不在此序列（世界/市级）则原样返回。"""
    if level not in _DROP_ORDER:
        return level
    idx = _DROP_ORDER.index(level)
    return _DROP_ORDER[min(idx + 1, len(_DROP_ORDER) - 1)]


# 已知竞赛库：竞赛名 → (主办方关键词, 描述性命中级别, 是否行业协会主办降一级, 最终级别, 说明)
# 首条：五一数模——省一级学会→省B→点名降一级→校C（见综测领域规则.md §3）
KNOWN_COMPETITIONS: dict[str, dict] = {
    "五一数学建模竞赛": {
        "aliases": ("五一数模", "五一数学建模", "五一"),
        "host_keyword": "工业与应用数学学会",
        "base_level": Level.PROVINCIAL_B,
        "drop_one": True,
        "final_level": Level.SCHOOL_C,
        "note": "省一级学会→省B→行业协(学)会主办降一级→校C；综测加分不受影响，专项奖金不覆盖",
    },
}


@dataclass(frozen=True)
class LevelDecision:
    level: Level | None
    basis: str          # "已知库" / "白名单" / "描述性" / "未匹配"
    confidence: str     # "高" / "中" / "低"
    note: str


def _match_known(competition: str, host: str, known) -> dict | None:
    if not known:
        return None
    for key, info in known.items():
        if key in competition or any(a in competition for a in info["aliases"]):
            return info
    return None


def _descriptive_level(host: str) -> Level | None:
    # 按级别从高到低匹配主办方性质关键词；国A/省A 需走白名单，这里只判国B/省B/校C
    for level in (Level.NATIONAL_B, Level.PROVINCIAL_B, Level.SCHOOL_C):
        if any(kw in host for kw in DESCRIPTION_KEYWORDS[level]):
            return level
    # 兜底：主办方名含「省」+「学会/协会」但未命中显式关键词
    # （如「江苏省工业与应用数学学会」是省一级学会，但不含字面子串「省一级学会」）
    # → 视为省一级学会/省级协会 → 省B
    if "省" in host and ("学会" in host or "协会" in host):
        return Level.PROVINCIAL_B
    return None


def decide_level(competition: str, host: str, catalog: Catalog, known=None) -> LevelDecision:
    """按 已知库 → 白名单 → 描述性 → 行业协(学)会主办降一级 的顺序定级。"""
    known_hit = _match_known(competition, host, known)
    if known_hit:
        return LevelDecision(
            level=known_hit["final_level"], basis="已知库",
            confidence="高", note=known_hit["note"],
        )

    white = catalog.lookup(competition, host)
    if white.level is not None:
        return LevelDecision(level=white.level, basis="白名单", confidence="高", note="")

    desc = _descriptive_level(host)
    if desc is None:
        return LevelDecision(level=None, basis="未匹配", confidence="低",
                             note="主办方性质不明，待辅导员认定级别")
    # 行业协(学)会主办 → 降一级（综测领域规则.md §3 定级流程第4步；序列 国A>国B>省A>省B>校C）
    if "学会" in host or "协会" in host:
        dropped = drop_one_level(desc)
        return LevelDecision(
            level=dropped, basis="描述性", confidence="中",
            note=f"{desc.value}→行业协(学)会主办降一级→{dropped.value}；能否拿专项奖金取决于学校认定，申报前问辅导员",
        )
    return LevelDecision(level=desc, basis="描述性", confidence="中", note="")
