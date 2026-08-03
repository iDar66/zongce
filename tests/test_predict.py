from pathlib import Path
from conftest import need
from zongce.extract import extract, OcrLine, PageResult, ExtractionResult
from zongce.predict import predict, Mode

FIX = Path(__file__).parent / "fixtures"

def test_canshi_predicts_wenti_count_4():
    p = need(FIX / "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf")
    pr = predict(extract(p), "邓达俊")
    assert pr.panel == "文体"
    assert pr.mode == Mode.COUNT
    # 裁决 2：真实件次数配对结构性失效（count=None→默认1），per=1.0 → points=1.0
    assert pr.points == 1.0
    assert pr.status == "自动"
    assert "次数配对失败" in pr.note
    assert "每场次" in pr.basis or "文体分" in pr.basis

def test_houqin_predicts_pinde_count_2():
    p = need(FIX / "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf")
    pr = predict(extract(p), "邓达俊")
    assert pr.panel == "品德"          # 由"加0.5品德分"决定，非文件名
    assert pr.mode == Mode.COUNT
    # 裁决 2：真实件次数配对失效（count=None→默认1），per=0.5 → points=0.5
    assert pr.points == 0.5
    assert pr.status == "自动"
    assert "次数配对失败" in pr.note

def test_wuyi_pending_grade():
    p = need(FIX / "第二十三届五一数学建模竞赛三等奖.pdf")
    pr = predict(extract(p), "邓达俊")
    assert pr.panel == "学业"
    assert pr.mode == Mode.GRADE
    assert pr.points is None and pr.status == "待确认"

def test_xinnian_pending_rule_ref():
    p = need(FIX / "2026新年音乐会志愿服务活动工作人员证明.pdf")
    pr = predict(extract(p), "邓达俊")
    assert pr.panel == "品德"
    assert pr.mode == Mode.RULE_REF
    assert pr.points is None and pr.status == "待确认"

def test_name_absent_pending():
    p = need(FIX / "第二十三届五一数学建模竞赛三等奖.pdf")
    pr = predict(extract(p), "不存在的姓名")
    assert pr.panel == "待确认" and pr.status == "待确认"

def test_count_multiply_when_count_available():
    """裁决 3：合成测试——次数可用时 per × count 乘法正确（弥补真实件次数失效的覆盖损失）。
    参照 test_name_match.py 的 _mk 构造法：text 含陈述触发 STMT_RE + COUNT 模式；
    邓达俊 + 同列正下方 (4) token 让 find_name 拿到 count=4。"""
    text = "每场次加1文体分"
    pgs = [PageResult(lines=[
        OcrLine("邓达俊", (600, 140, 700, 170), 1.0),
        OcrLine("(4)",    (600, 175, 640, 200), 1.0),
    ], text=text, width=1000, height=1000)]
    ext = ExtractionResult(source="x.pdf", pages=pgs, text=text, method="ocr", from_cache=False)
    pr = predict(ext, "邓达俊")
    assert pr.mode == Mode.COUNT
    assert pr.points == 4.0   # per=1 × count=4
    assert pr.status == "自动"
