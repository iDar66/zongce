# -*- coding: utf-8 -*-
"""专项奖学金（竞赛类）4 门槛判定与奖金计算。

门槛（管理办法第13条）：主办方资质 / 获奖比例≤50% / 学校组织备案 / 申报时间。
奖金公式：总额 = 国家级基准(元/人) × 级别折算 × 组队系数；校C 不覆盖。
详见 docs/综测领域规则.md §3。
"""
from __future__ import annotations

import enum
from dataclasses import dataclass

from .catalog import Level
from .level import LevelDecision
from .ratio import RatioResult


class Award(enum.Enum):
    SPECIAL = "特等"
    FIRST = "一等"
    SECOND = "二等"
    THIRD = "三等"


# 管理办法第13条第2款：国家级基准（元/人）
PRIZE_TABLE: dict[Award, float] = {
    Award.SPECIAL: 3000, Award.FIRST: 2000, Award.SECOND: 1500, Award.THIRD: 800,
}

# 级别折算：世界×3、国×1、省×0.5、市×0.25；校C 不覆盖
LEVEL_SCALE: dict[Level, float] = {
    Level.WORLD: 3.0, Level.NATIONAL_A: 1.0, Level.NATIONAL_B: 1.0,
    Level.PROVINCIAL_A: 0.5, Level.PROVINCIAL_B: 0.5, Level.MUNICIPAL: 0.25,
}

# 门槛常量
GATE_HOST = "主办方资质"
GATE_RATIO = "获奖比例"
GATE_ORGANIZED = "学校组织备案"
GATE_TIME = "申报时间"


def team_factor(team_size: int) -> float:
    """组队系数：2-4 人 (n+1)/2；5 人及以上 ×3；个人 1。"""
    if team_size <= 1:
        return 1.0
    if team_size <= 4:
        return (team_size + 1) / 2
    return 3.0


def prize_for(level: Level, award: Award, team_size: int) -> tuple[float, float]:
    """返回 (总额, 人均)。校C/未知奖项 → (0, 0)。"""
    if level == Level.SCHOOL_C or award is None:
        return 0.0, 0.0
    base = PRIZE_TABLE.get(award, 0.0)
    scale = LEVEL_SCALE.get(level, 0.0)
    total = base * scale * team_factor(team_size)
    return total, (total / team_size if team_size > 0 else total)


_AWARD_KEYWORDS = (
    (Award.SPECIAL, ("特等",)),
    (Award.FIRST, ("一等", "冠军", "第一名", "金奖")),
    (Award.SECOND, ("二等", "亚军", "第二名", "银奖")),
    (Award.THIRD, ("三等", "季军", "第三名", "铜奖")),
)


def map_award(text: str) -> Award | None:
    for award, kws in _AWARD_KEYWORDS:
        if any(kw in text for kw in kws):
            return award
    return None


@dataclass(frozen=True)
class CompetitionCandidate:
    competition: str
    host: str
    award_text: str
    team_size: int
    source: str


@dataclass(frozen=True)
class ScholarshipItem:
    competition: str
    award: Award | None
    level: Level | None
    gates: dict[str, str]            # 门槛名 → "通过"/"不通过"/"待确认"
    prize_total: float
    prize_per_capita: float
    confidence: str                  # "高"/"中"/"低"
    pending_notes: list[str]
    source: str


def _gate(value, ok_flag=True) -> str:
    if value is None:
        return "待确认"
    return "通过" if (value if ok_flag else True) else "不通过"


def evaluate_competition(
    candidate: CompetitionCandidate,
    level_decision: LevelDecision,
    ratio_result: RatioResult,
    organized_by_school: bool | None,
    in_time_window: bool | None,
) -> ScholarshipItem:
    award = map_award(candidate.award_text)
    total, per = prize_for(level_decision.level, award, candidate.team_size) if award else (0.0, 0.0)

    # 主办方资质：公司/企业主办不通过；学会/协会/政府/教指委/部门 通过；不明 待确认
    host = candidate.host
    if any(kw in host for kw in ("公司", "企业")):
        host_gate = "不通过"
    elif any(kw in host for kw in ("学会", "协会", "政府", "部", "委员会", "教指委", "大学", "学院")):
        host_gate = "通过"
    else:
        host_gate = "待确认"

    ratio_gate = "通过" if ratio_result.passes_cap else ("不通过" if ratio_result.ratio is not None else "待确认")

    gates = {
        GATE_HOST: host_gate,
        GATE_RATIO: ratio_gate,
        GATE_ORGANIZED: _gate(organized_by_school),
        GATE_TIME: _gate(in_time_window),
    }

    pending = []
    if level_decision.level is None:
        pending.append("级别待辅导员认定")
    if ratio_result.ratio is None:
        pending.append("获奖比例待确认（--allow-online + URL 或手填）")
    # 联网比例来自启发式正则解析（命中公示页任意百分比、无语义裁决），
    # 而「获奖比例≤50%」是生死线门槛——盲信有误判风险，提示人工核对。
    if ratio_result.source == "联网":
        pending.append("获奖比例来自联网公示启发式解析，请人工核对官网公示与公式")
    if host_gate == "待确认":
        pending.append("主办方资质待确认，请提供主办方性质说明（如学会/协会/政府部门）")
    if organized_by_school is None:
        pending.append("学校组织备案待确认")
    if in_time_window is None:
        pending.append("申报时间范围待确认")
    if level_decision.level == Level.SCHOOL_C:
        pending.append("校C：专项奖金不覆盖，综测加分不受影响")
    if award is None:
        pending.append(f"奖项未识别：{candidate.award_text}")

    all_decided = all(g != "待确认" for g in gates.values())
    confidence = "高" if (all_decided and level_decision.confidence == "高") else ("中" if all_decided else "低")

    return ScholarshipItem(
        competition=candidate.competition, award=award, level=level_decision.level,
        gates=gates, prize_total=total, prize_per_capita=per,
        confidence=confidence, pending_notes=pending, source=candidate.source,
    )
