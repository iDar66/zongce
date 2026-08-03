# -*- coding: utf-8 -*-
"""PDF/图片 → 文字 + 每行 bbox。扫描件走 RapidOCR；有文字层的 PDF 走 fitz；按内容 hash 缓存。"""
from __future__ import annotations
import hashlib, json, os, tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

import fitz

IMG_EXT = {".jpg", ".jpeg", ".png"}
PDF_EXT = {".pdf"}
MIN_TEXT_CHARS = 10        # 文字层少于此 → 视为扫描件
OCR_DPI = 200

@dataclass
class OcrLine:
    text: str
    bbox: tuple[float, float, float, float]
    conf: float
    @property
    def cx(self) -> float: return (self.bbox[0] + self.bbox[2]) / 2
    @property
    def cy(self) -> float: return (self.bbox[1] + self.bbox[3]) / 2
    @property
    def h(self) -> float: return self.bbox[3] - self.bbox[1]

@dataclass
class PageResult:
    lines: list[OcrLine]
    text: str
    width: float
    height: float

@dataclass
class ExtractionResult:
    source: str
    pages: list[PageResult]
    text: str
    method: str            # "text_layer" | "ocr"
    from_cache: bool

_ENGINE = None
def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _ENGINE = RapidOCR()
    return _ENGINE

def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _ocr_image(path: Path) -> PageResult:
    res, _elapse = _engine()(str(path))
    lines, texts = [], []
    width = height = 0.0
    if res:
        for box, txt, conf in res:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            lines.append(OcrLine(text=txt, bbox=bbox, conf=float(conf)))
            texts.append(txt)
            width = max(width, max(xs)); height = max(height, max(ys))
    return PageResult(lines=lines, text="\n".join(texts), width=width, height=height)

def _ocr_page(pix) -> PageResult:
    fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
    try:
        pix.save(tmp)
        return _ocr_image(Path(tmp))
    finally:
        os.remove(tmp)

def _from_text_layer(page) -> PageResult:
    d = page.get_text("dict")
    lines, texts = [], []
    for blk in d.get("blocks", []):
        for ln in blk.get("lines", []):
            spans = ln.get("spans", [])
            txt = "".join(s.get("text", "") for s in spans)
            if not txt.strip():
                continue
            x0, y0, x1, y1 = ln.get("bbox", (0, 0, 0, 0))
            lines.append(OcrLine(text=txt, bbox=tuple(map(float, (x0, y0, x1, y1))), conf=1.0))
            texts.append(txt)
    return PageResult(lines=lines, text="\n".join(texts),
                      width=page.rect.width, height=page.rect.height)

def _extract_no_cache(path: Path) -> ExtractionResult:
    ext = path.suffix.lower()
    if ext in IMG_EXT:
        pg = _ocr_image(path)
        return ExtractionResult(source=str(path), pages=[pg], text=pg.text, method="ocr", from_cache=False)
    if ext in PDF_EXT:
        doc = fitz.open(str(path))
        layer_text = "".join(pg.get_text() for pg in doc)
        use_ocr = len(layer_text.strip()) < MIN_TEXT_CHARS
        pages = []
        for pg in doc:
            pages.append(_ocr_page(pg.get_pixmap(dpi=OCR_DPI)) if use_ocr else _from_text_layer(pg))
        doc.close()
        return ExtractionResult(source=str(path), pages=pages,
                                text="\n".join(p.text for p in pages),
                                method="ocr" if use_ocr else "text_layer", from_cache=False)
    raise ValueError(f"不支持的文件类型: {ext}（仅支持 pdf/jpg/png）")

def _serialize(r: ExtractionResult) -> dict:
    return {"source": r.source, "method": r.method,
            "pages": [{"lines": [asdict(ln) for ln in p.lines], "text": p.text,
                       "width": p.width, "height": p.height} for p in r.pages]}

def _deserialize(d: dict) -> ExtractionResult:
    pages = [PageResult(lines=[OcrLine(text=ln["text"], bbox=tuple(ln["bbox"]), conf=ln["conf"])
                               for ln in p["lines"]], text=p["text"],
                        width=p["width"], height=p["height"]) for p in d["pages"]]
    return ExtractionResult(source=d["source"], pages=pages,
                            text="\n".join(p.text for p in pages),
                            method=d["method"], from_cache=True)

def extract(path, cache_dir=None) -> ExtractionResult:
    path = Path(path)
    if cache_dir is not None:
        cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
        key = _file_hash(path)
        cf = cache_dir / f"{key}.json"
        if cf.exists():
            with open(cf, encoding="utf-8") as f:
                return _deserialize(json.load(f))
    r = _extract_no_cache(path)
    if cache_dir is not None:
        with open(cache_dir / f"{_file_hash(path)}.json", "w", encoding="utf-8") as f:
            json.dump(_serialize(r), f, ensure_ascii=False)
    return r
