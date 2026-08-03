from pathlib import Path
import fitz
from conftest import need
from zongce.extract import extract, ExtractionResult

FIX = Path(__file__).parent / "fixtures"

def _make_text_pdf(path: Path, text: str):
    doc = fitz.open()
    pg = doc.new_page()
    # china-s = MuPDF 内置简体中文 CID 字体；默认 Helvetica 无法渲染 CJK，
    # 否则 fitz 抽出来全是占位符 "·"，无法测试文字层路径。
    pg.insert_text((72, 72), text, fontsize=12, fontname="china-s")
    doc.save(str(path)); doc.close()

def test_text_layer_pdf_uses_text_method(tmp_path):
    p = tmp_path / "t.pdf"
    # 文本需 ≥ MIN_TEXT_CHARS(10) 字，否则被当作扫描件走 OCR。
    _make_text_pdf(p, "张三同学 加2分 品德证明")
    r = extract(p)
    assert r.method == "text_layer"
    assert "张三" in r.text
    assert len(r.pages) == 1 and r.pages[0].lines  # 文字层也产出 lines+bbox

def test_scanned_pdf_uses_ocr_and_finds_name():
    p = need(FIX / "第二十三届五一数学建模竞赛三等奖.pdf")
    r = extract(p)
    assert r.method == "ocr"
    assert "邓达俊" in r.text
    assert any(ln.conf >= 0 for pg in r.pages for ln in pg.lines)

def test_ocr_keeps_bbox_coordinates():
    p = need(FIX / "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf")
    r = extract(p)
    line = r.pages[0].lines[0]
    assert len(line.bbox) == 4
    assert all(isinstance(v, (int, float)) for v in line.bbox)

def test_cache_second_call_hits_cache(tmp_path):
    p = need(FIX / "第二十三届五一数学建模竞赛三等奖.pdf")
    cache = tmp_path / ".cache"
    r1 = extract(p, cache_dir=cache)
    r2 = extract(p, cache_dir=cache)
    assert r1.from_cache is False and r2.from_cache is True
    assert r1.text == r2.text

def test_image_file_is_ocr():
    p = need(FIX / "校第一届班BA篮球联赛甲组第三名(校级）.jpg")
    r = extract(p)
    assert r.method == "ocr"
    assert len(r.text) > 0
