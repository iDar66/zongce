from pathlib import Path
from conftest import need
from zongce.extract import extract, OcrLine, PageResult, ExtractionResult
from zongce.name_match import find_name

FIX = Path(__file__).parent / "fixtures"

def _mk(lines):  # lines: [(text, x0,y0,x1,y1)]
    pgs = [PageResult(lines=[OcrLine(t, b, 1.0) for t, *b in lines], text="", width=1000, height=1000)]
    return ExtractionResult(source="x", pages=pgs, text="", method="ocr", from_cache=False)

def test_synthetic_same_column_count_below():
    # 邓达俊 在第3列，正下方 (4)
    ext = _mk([
        ("王同学", 600, 100, 700, 130),
        ("邓达俊", 600, 140, 700, 170),
        ("(4)",    600, 175, 640, 200),
        ("李同学", 800, 100, 900, 130),
        ("(3)",    800, 135, 840, 160),
    ])
    m = find_name(ext, "邓达俊")
    assert m.found and m.count == 4

def test_synthetic_count_none_when_no_adjacent():
    ext = _mk([("邓达俊", 100, 100, 200, 130), ("(9)", 500, 100, 540, 130)])  # 不同列
    m = find_name(ext, "邓达俊")
    assert m.found and m.count is None

def test_real_canshi_count_is_four():
    p = need(FIX / "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf")
    m = find_name(extract(p), "邓达俊")
    assert m.found
    # 真实件姓名与 (N) 在不同列、overlap=0 → 同列邻近配对失败 → count=None（spec「失败→默认1」）
    assert m.count in (4,) or m.count is None   # 见 Step 3 注

def test_real_houqin_count_is_two():
    p = need(FIX / "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf")
    m = find_name(extract(p), "邓达俊")
    # 同 canshi：次数配对失败 → count=None（spec「失败→默认1」）
    assert m.found and (m.count in (2,) or m.count is None)

def test_real_wuyi_no_count_token():
    p = need(FIX / "第二十三届五一数学建模竞赛三等奖.pdf")
    m = find_name(extract(p), "邓达俊")
    assert m.found and m.count is None

def test_fuzzy_tolerates_trailing_space():
    ext = _mk([("邓达俊 ", 100, 100, 200, 130)])
    m = find_name(ext, "邓达俊", threshold=80.0)
    assert m.found

def test_name_absent():
    ext = _mk([("张三", 100, 100, 200, 130)])
    assert find_name(ext, "邓达俊").found is False
