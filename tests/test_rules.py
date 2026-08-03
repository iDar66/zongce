import re
from zongce import rules

def test_panel_keywords_have_three_panels():
    assert set(rules.PANELS) == {"品德", "学业", "文体"}

def test_count_regex_matches_proof_statement():
    assert rules.COUNT_RE.search("每场次加1文体分")
    assert rules.COUNT_RE.search("每次加0.5品德分")
    assert not rules.COUNT_RE.search("荣获三等奖")

def test_count_hint_matches_count_marker():
    assert rules.COUNT_HINT_RE.search("（括号后数字表示参加场次数）")
    assert rules.COUNT_HINT_RE.search("(4)")
    assert not rules.COUNT_HINT_RE.search("特此证明")

def test_grade_keywords_include_common_awards():
    assert "三等奖" in rules.GRADE_KEYWORDS
    assert "获奖" in rules.GRADE_KEYWORDS

def test_fixed_re_matches_standalone_points():
    assert rules.FIXED_RE.search("加2分")
    assert rules.FIXED_RE.search("+1.5分")
    # 带板块词的陈述（"加0.5品德分"）不应被 FIXED_RE 当作独立数值误匹配
    assert not rules.FIXED_RE.search("加0.5品德分")

def test_stmt_re_captures_value_and_panel():
    m = rules.STMT_RE.search("每场次加1文体分")
    assert m and m.group(1) == "1" and m.group(2) == "文体"
    m = rules.STMT_RE.search("每次加0.5品德分")
    assert m and m.group(1) == "0.5" and m.group(2) == "品德"

def test_normalize_panel():
    assert rules.normalize_panel("文体") == "文体"
    assert rules.normalize_panel("体") == "文体"
    assert rules.normalize_panel("德") == "品德"
    assert rules.normalize_panel("智") == "学业"
    assert rules.normalize_panel(None) is None
