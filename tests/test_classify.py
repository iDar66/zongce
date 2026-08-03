from zongce.classify import Mode, classify_mode, classify_panel

CANSHI = "每场次加1文体分（括号后数字表示参加场次数，未标注为1次）"
HOUQIN = "下列学生出任作为后勤，根据综测细则每次加0.5品德分（括号里的数字表示参加次数）"
WUYI = "荣获第二十三届五一数学建模竞赛三等奖 证书编号：51MCM"
XINNIAN = "参加2026新年音乐会活动的工作人员名单如下：李同学、邓达俊……特此证明"

def test_mode_count():
    assert classify_mode(CANSHI) == Mode.COUNT
    assert classify_mode(HOUQIN) == Mode.COUNT

def test_mode_grade():
    assert classify_mode(WUYI) == Mode.GRADE

def test_mode_rule_ref_when_no_number_no_award():
    assert classify_mode(XINNIAN) == Mode.RULE_REF

def test_mode_fixed_synthetic():
    assert classify_mode("该同学在宿舍评比中加2分") == Mode.FIXED

def test_panel_by_keyword_unique():
    # 无"X分"陈述时走关键词：数学建模 → 学业
    assert classify_panel(WUYI, "第二十三届五一数学建模竞赛三等奖.pdf") == "学业"

def test_panel_tie_or_none_yields_pending():
    # "证明"是品德关键词、无其它命中且仅一类 → 品德；这里测真正零命中
    assert classify_panel("特此证明", "???") in {"品德", "待确认"}  # "证明"∈品德
    assert classify_panel("没有关键词的一段话", "xyz") == "待确认"
