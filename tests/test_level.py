# tests/test_level.py
from zongce.catalog import Catalog, DESCRIPTION_KEYWORDS, Level
from zongce.level import KNOWN_COMPETITIONS, LevelDecision, decide_level, drop_one_level


def _empty_catalog() -> Catalog:
    return Catalog(whitelist={})


def test_whitelist_match_returns_national_a():
    cat = Catalog(whitelist={"全国大学生数学建模竞赛": (Level.NATIONAL_A, "中国工业与应用数学学会")})
    d = decide_level("全国大学生数学建模竞赛", "中国工业与应用数学学会", cat)
    assert d.level == Level.NATIONAL_A
    assert d.basis == "白名单"
    assert d.confidence == "高"


def test_descriptive_drops_provincial_society_to_school_c():
    # 非 known 库竞赛、主办方=省一级学会 → 描述性兜底命中省B → 行业协(学)会主办降一级 → 校C
    d = decide_level("某省级数学建模竞赛", "江苏省工业与应用数学学会", _empty_catalog())
    assert d.level == Level.SCHOOL_C
    assert d.basis == "描述性"
    assert d.confidence == "中"
    assert "降一级" in d.note


def test_known_competition_wuyi_drops_to_school_c():
    # 已知库直接给完整路径：五一数模 → 省B → 行业协会主办降一级 → 校C
    d = decide_level("五一数学建模竞赛", "江苏省工业与应用数学学会", _empty_catalog(), known=KNOWN_COMPETITIONS)
    assert d.level == Level.SCHOOL_C
    assert d.confidence == "高"


def test_drop_one_level_sequence():
    assert drop_one_level(Level.NATIONAL_A) == Level.NATIONAL_B
    assert drop_one_level(Level.PROVINCIAL_B) == Level.SCHOOL_C


def test_ambiguous_host_marks_pending():
    d = decide_level("某神秘比赛", "某公司", _empty_catalog())
    assert d.level is None
    assert d.confidence == "低"
    assert "待" in d.note
