# -*- coding: utf-8 -*-
"""scholarship.py 测试：奖金公式 / 校C无奖金 / 4门槛 / 奖项映射 / 联网比例人工核对。"""
from __future__ import annotations

import pytest

from zongce.catalog import Level
from zongce.level import LevelDecision
from zongce.ratio import RatioResult
from zongce.scholarship import (
    Award,
    CompetitionCandidate,
    LEVEL_SCALE,
    PRIZE_TABLE,
    evaluate_competition,
    map_award,
    prize_for,
    team_factor,
)


def test_prize_provincial_b_third_3person_team_800_total():
    # 省B 三等 3 人队 = 800(国三等基准) × 0.5(省) × (3+1)/2 = 800 总额
    total, per = prize_for(Level.PROVINCIAL_B, Award.THIRD, team_size=3)
    assert total == pytest.approx(800.0)
    assert per == pytest.approx(800.0 / 3)


def test_prize_school_c_not_covered():
    total, per = prize_for(Level.SCHOOL_C, Award.THIRD, team_size=3)
    assert total == 0
    assert per == 0


def test_team_factor_boundaries():
    assert team_factor(1) == 1.0
    assert team_factor(2) == pytest.approx(1.5)   # (2+1)/2
    assert team_factor(4) == pytest.approx(2.5)   # (4+1)/2
    assert team_factor(5) == pytest.approx(3.0)   # 5 人及以上 ×3


def test_map_award_keywords():
    assert map_award("荣获一等奖") == Award.FIRST
    assert map_award("冠军") == Award.FIRST
    assert map_award("三等奖") == Award.THIRD
    assert map_award("优秀奖") is None


def test_evaluate_competition_records_gates_and_pending():
    cand = CompetitionCandidate(competition="五一数学建模竞赛", host="江苏省工业与应用数学学会",
                                award_text="三等奖", team_size=3, source="五一.pdf")
    level_d = LevelDecision(level=Level.SCHOOL_C, basis="已知库", confidence="高", note="x")
    ratio_r = RatioResult(ratio=0.45, source="已知库", passes_cap=True, note="")
    item = evaluate_competition(cand, level_d, ratio_r,
                                organized_by_school=True, in_time_window=True)
    assert item.level == Level.SCHOOL_C
    assert item.gates["主办方资质"] == "通过"
    assert item.gates["获奖比例"] == "通过"
    assert item.gates["学校组织备案"] == "通过"
    assert item.gates["申报时间"] == "通过"
    assert item.prize_total == 0  # 校C 不覆盖
    assert item.confidence == "高"


def test_evaluate_flags_online_ratio_for_human_review():
    """联网比例来自启发式正则解析，需提示人工核对官网公示与公式。"""
    cand = CompetitionCandidate(competition="某赛", host="某学会", award_text="一等奖",
                                team_size=1, source="x.pdf")
    level_d = LevelDecision(level=Level.PROVINCIAL_B, basis="描述性", confidence="中", note="")
    ratio_r = RatioResult(ratio=0.3, source="联网", passes_cap=True, note="")
    item = evaluate_competition(cand, level_d, ratio_r,
                                organized_by_school=True, in_time_window=True)
    assert any("人工核对" in n for n in item.pending_notes)
