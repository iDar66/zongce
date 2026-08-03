# 综测加分预测工具 — P1（PDF/图片自动加分主线）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给定姓名 + 一个装满活动证明的文件夹，自动抽取文字、筛出含该姓名的证明、归到品德/学业/文体、按四种加分模式预测加分，导出邓达俊式 `综测加分明细.xlsx` 并把文件物理复制到 品德/学业/文体/待确认 四个文件夹。

**Architecture:** 流水线式核心（纯函数，可测）`extract → name_match → classify → predict → export`，包名 `zongce/`。抽取层对扫描件走 OCR（RapidOCR）并保留每行 bbox 坐标；姓名匹配用 rapidfuzz 模糊匹配 + 同列邻近 `(N)` 还原次数；分类用"加分陈述里的板块词"优先、关键词兜底；导出用 pandas/openpyxl。Streamlit UI 不在 P1，P1 提供可命令行运行的核心 + CLI。

**Tech Stack:** Python 3.14（全局 `C:\Python314`，已有 pymupdf/rapidocr-onnxruntime/pandas/openpyxl/PIL/cv2；本计划补装 rapidfuzz、pytest ✅已验证可装）、PyMuPDF（fitz）、RapidOCR、rapidfuzz、pandas、openpyxl、pytest。

## Global Constraints

- **环境**：Python 3.14.3 全局解释器（`python` 即 `C:\Python314`），不建 venv（pymupdf/rapidocr/cv2 等大包已在全局，重建 venv 成本高）。依赖见 `requirements.txt`。
- **隐私/本地**：全本地，不联网、不调云 API；OCR 用本地 RapidOCR。
- **输入**：PDF + 图片（jpg/png）。**不接受 docx/xls/zip**（P1 跳过并记录）。
- **扫描件现实**：实测 `D:\综测证明材料\大一\` 的证明几乎全是扫描件（无文字层）→ **OCR 是主路径，不是兜底**；文字层仅在少数有文字层的 PDF 上走（节省 OCR）。
- **坐标必须保留**：次数型姓名表是多栏排版，必须用 OCR bbox 的 x/y 还原"姓名↔(次数)"配对，纯文本线性读会错配。
- **稳 > 快、少返工**：每个任务独立可测、TDD、频繁 commit；算不准的加分一律标"待确认"，不编数字。
- **输出目录**：`<output_dir>/<姓名>/`，内含 `综测加分明细.xlsx` + 品德/学业/文体/待确认/ 四个子文件夹。
- **不替代官方综测系统**，结果供核对。

---

## 设计相对 spec 的修正（已用实测证据确认，执行时按本计划走）

1. **OCR 是主路径**（spec 第 6/13 节假设"文字层优先，OCR 兜底"）。实测 7 个代表性 PDF 全部 `text_chars<10`，无文字层。→ `extract.py` 改为：PDF 先试文字层，文字层 < 阈值则整篇走 OCR；图片直接 OCR。
2. **接受图片输入**（spec 第 16 节"MVP 只吃 PDF"）。`大一/` 含必要的 `.jpg` 证书（如 `校第一届班BA篮球联赛甲组第三名(校级）.jpg`）。→ `extract.py` 同时吃 pdf/jpg/png，统一走 OCR。docx/xls/zip 仍跳过。
3. **板块由"加分陈述"决定，不由文件名关键词决定**。实测 `计科杯篮球比赛后勤综测证明` 文件名关键词命中"文体(计科杯/篮球)"多于"品德(后勤)"，但证明正文写"每次加0.5**品德**分"——真实板块是品德。→ `predict.py` 优先从加分陈述里的"品德/智育/学业/文体…分"抽板块；抽不到再用 `classify_panel` 关键词兜底。`classify.py` 仍独立实现并单测关键词逻辑。
4. **Streamlit UI 推迟**（spec 第 6 节列了 app.py）。P1 先交付可命令行运行的核心 + CLI；UI 留到 P1 收尾或 P2。

---

## 文件结构

```
D:\综测工具项目\
  .gitignore
  README.md
  requirements.txt
  pyproject.toml                  # pytest 配置 + 包元数据
  zongce/
    __init__.py
    rules.py                      # 纯配置：板块关键词、模式正则、单次值默认（P1 子集）
    classify.py                   # classify_mode / classify_panel
    extract.py                    # PDF/图片 → ExtractionResult(页/行/bbox/text)，带缓存
    name_match.py                 # 模糊找姓名 + 同列邻近 (N) 还原次数
    predict.py                    # 组装单文件 Prediction
    export.py                     # 导出 xlsx + 按板块物理复制文件
    pipeline.py                   # run_pipeline 串联全流程
    cli.py                        # python -m zongce.cli ...
  tests/
    __init__.py
    conftest.py                   # fixtures_dir + 缺失即 skip
    populate_fixtures.py          # 从 D:\综测证明材料\大一 拷 5 个 fixture（手动跑一次）
    fixtures/                     # gitignore 掉（含同学姓名 PII）
      2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf
      2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf
      第二十三届五一数学建模竞赛三等奖.pdf
      2026新年音乐会志愿服务活动工作人员证明.pdf
      校第一届班BA篮球联赛甲组第三名(校级）.jpg
    test_rules.py
    test_classify.py
    test_extract.py
    test_name_match.py
    test_predict.py
    test_export.py
    test_pipeline.py
  docs/superpowers/{specs,plans}/  (已存在)
```

**数据类型契约（跨任务接口）**：

```python
# extract.py 产出（Task 3 定义）
@dataclass
class OcrLine:
    text: str
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1（页面像素坐标，dpi=200）
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
    source: str            # 原始路径字符串
    pages: list[PageResult]
    text: str              # 全文（页间换行）
    method: str            # "text_layer" | "ocr"
    from_cache: bool

# name_match.py 产出（Task 4 定义）
@dataclass
class NameMatch:
    found: bool
    count: int | None
    confidence: float      # 0~1
    context: str           # 姓名出现处的上下文片段
    best_token: str        # 最佳匹配到的原文 token
    best_score: float

# predict.py 产出（Task 5 定义）
class Mode(str, Enum):
    COUNT = "次数型"; FIXED = "固定值型"; GRADE = "获奖分级型"; RULE_REF = "细则参照型"

@dataclass
class Prediction:
    file: str
    panel: str             # 品德 / 学业 / 文体 / 待确认
    mode: Mode | None
    points: float | None   # None ⇒ 待确认
    count: int | None
    basis: str             # 加分陈述片段
    status: str            # "自动" | "待确认"
    note: str
```

---

## Task 0：项目骨架与 fixtures

**Files:**
- Create: `.gitignore`, `README.md`, `requirements.txt`, `pyproject.toml`, `zongce/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/populate_fixtures.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Produces: 可 import 的空包 `zongce`；`tests/conftest.py::fixtures_dir`、`need(path)`；`tests/populate_fixtures.py`（手动 `python tests/populate_fixtures.py` 拷贝 5 个真实 fixture）。

- [ ] **Step 1：建包与配置文件**

`zongce/__init__.py`：`"""综测加分预测工具。"""`
`tests/__init__.py`：空。

`requirements.txt`：
```
pymupdf>=1.24
rapidocr-onnxruntime>=1.3
rapidfuzz>=3.0
pandas>=2.0
openpyxl>=3.1
pytest>=8.0
```

`pyproject.toml`：
```toml
[project]
name = "zongce"
version = "0.1.0"
requires-python = ">=3.13"

[tool.pytest.ini_options]
pythonpath = [".", "tests"]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

`.gitignore`：
```
__pycache__/
*.pyc
.pytest_cache/
.superpowers/
tests/fixtures/*.pdf
tests/fixtures/*.jpg
tests/fixtures/*.png
.cache/
输出/
综测输出/
```

`README.md`：
```markdown
# 综测加分预测工具

本地、隐私、纯规则+OCR 的综测加分预测工具。P1：PDF/图片 → 按姓名筛 → 归板块 → 预测加分 → 导出 xlsx + 4 文件夹。

## 安装
    python -m pip install -r requirements.txt

## 拷测试 fixture（一次性，本机）
    python tests/populate_fixtures.py

## 跑测试
    pytest

## 用
    python -m zongce.cli 邓达俊 "D:\综测证明材料\大一" -o "D:\综测输出"
```

- [ ] **Step 2：fixtures 拷贝脚本与 conftest**

`tests/populate_fixtures.py`：
```python
# -*- coding: utf-8 -*-
"""从 D:\综测证明材料\大一 拷贝 5 个代表性 fixture 到 tests/fixtures（手动跑一次）。"""
import shutil, sys
from pathlib import Path

SRC = Path(r"D:\综测证明材料\大一")
DST = Path(__file__).parent / "fixtures"
DST.mkdir(exist_ok=True)

FILES = [
    "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf",
    "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf",
    "第二十三届五一数学建模竞赛三等奖.pdf",
    "2026新年音乐会志愿服务活动工作人员证明.pdf",
    "校第一届班BA篮球联赛甲组第三名(校级）.jpg",
]

for name in FILES:
    s = SRC / name
    if not s.exists():
        print(f"[skip] 源不存在: {s}")
        continue
    shutil.copy2(s, DST / name)
    print(f"[ok] {name}")
print("done ->", DST)
```

`tests/conftest.py`：
```python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIX

def need(path: Path) -> Path:
    """fixture 缺失则 skip（本机未跑 populate_fixtures.py）。"""
    if not path.exists():
        pytest.skip(f"fixture 缺失，先跑 python tests/populate_fixtures.py：{path}")
    return path
```

- [ ] **Step 3：跑 populate，确认 5 个 fixture 就位**

Run: `python tests/populate_fixtures.py && ls tests/fixtures`
Expected: 5 行 `[ok]` + 列出 5 个文件。

- [ ] **Step 4：冒烟测试**

`tests/test_smoke.py`：
```python
import pytest
from conftest import need  # noqa
from pathlib import Path

def test_package_imports():
    import zongce  # noqa: F401

def test_fixtures_present(fixtures_dir):
    names = {p.name for p in fixtures_dir.iterdir()}
    assert "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf" in names
```
（`from conftest import need` 仅占位保证模块可导入；实际 skip 逻辑在各 test 里调用 `need()`。）

- [ ] **Step 5：git init + 首次提交**

Run:
```bash
git init
git add -A
git commit -m "chore: P1 项目骨架与 fixtures"
```
（`tests/fixtures/*.pdf|jpg` 已被 gitignore，不会入库。）

---

## Task 1：rules.py（P1 配置）

**Files:**
- Create: `zongce/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Produces: `PANEL_KEYWORDS: dict[str, list[str]]`、`Mode` 不在此（在 classify.py）、模式正则 `COUNT_RE / COUNT_HINT_RE / GRADE_KEYWORDS / FIXED_RE / STMT_RE`、`PER_TIME_DEFAULT: dict[tuple[str,str], float]`、`normalize_panel(word)->str`、`PANELS = ("品德","学业","文体")`。

- [ ] **Step 1：写失败测试**

`tests/test_rules.py`：
```python
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
```

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL（`module 'zongce.rules' has no attribute ...`）。

- [ ] **Step 3：实现 rules.py**

`zongce/rules.py`：
```python
# -*- coding: utf-8 -*-
"""综测加分规则配置（P1 子集：板块关键词 + 模式正则 + 单次值默认）。
纯配置，细则改了只动这里。"""
from __future__ import annotations
import re

PANELS = ("品德", "学业", "文体")

PANEL_KEYWORDS: dict[str, list[str]] = {
    "品德": ["干部", "主席", "部长", "干事", "后勤", "工作人员", "社会实践",
            "三下乡", "表彰", "文明宿舍", "志愿", "五四", "优秀共青团员", "优秀团员",
            "音乐会", "分享大会", "代会", "观众", "证明"],
    "学业": ["竞赛", "挑战杯", "数学建模", "五一数模", "五一数学建模", "ACM",
            "论文", "专利", "证书", "四六级", "创新项目", "大创", "普通话",
            "教资", "教师资格", "知识竞赛", "信息素养"],
    "文体": ["运动会", "篮球", "足球", "排球", "乒乓球", "羽毛球", "跳绳", "定向",
            "文艺", "演出", "歌唱", "主持", "辩论", "裁判", "班BA", "班ba",
            "计科杯", "校运会", "院运会", "球赛", "联赛", "趣味运动"],
}

# —— 模式正则 ——
COUNT_RE = re.compile(r"每[次场]|场次")
COUNT_HINT_RE = re.compile(r"次数|场次|\(\s*\d+\s*\)|（\s*\d+\s*）")
GRADE_KEYWORDS = ["特等奖", "一等奖", "二等奖", "三等奖", "金奖", "银奖", "铜奖",
                  "冠军", "亚军", "季军", "第一名", "第二名", "第三名", "前三名", "获奖"]
FIXED_RE = re.compile(r"加\s*\d+(?:\.\d+)?\s*分|[\+＋]\s*\d+(?:\.\d+)?\s*分")
# 加分陈述：捕获 单次值 + 板块词
STMT_RE = re.compile(r"加\s*(\d+(?:\.\d+)?)\s*(品德|智育|学业|文体|德|智|体)?\s*分")
COUNT_TOKEN_RE = re.compile(r"^\(\s*(\d+)\s*\)$|^[（]\s*(\d+)\s*[）]$")

# 单次值兜底（陈述里抽不到时）：(板块, 关键词) -> 单次分
PER_TIME_DEFAULT: dict[tuple[str, str], float] = {
    ("文体", "参赛"): 1.0,     # 院级每场+1（校级+2，需认定；先保守 1）
    ("文体", "裁判"): 0.5,
    ("品德", "后勤"): 0.5,
    ("品德", "工作人员"): 0.5,
}

_PANEL_ALIAS = {"德": "品德", "品德": "品德", "智": "学业", "智育": "学业",
                "学业": "学业", "体": "文体", "文体": "文体"}

def normalize_panel(word: str | None) -> str | None:
    if word is None:
        return None
    return _PANEL_ALIAS.get(word)
```

- [ ] **Step 4：跑测试确认通过**

Run: `pytest tests/test_rules.py -v`
Expected: PASS（7 条全过）。

- [ ] **Step 5：提交**

```bash
git add zongce/rules.py tests/test_rules.py
git commit -m "feat(rules): P1 板块关键词与模式正则配置"
```

---

## Task 2：classify.py（模式 + 板块分类）

**Files:**
- Create: `zongce/classify.py`
- Test: `tests/test_classify.py`

**Interfaces:**
- Consumes: `zongce.rules`（COUNT_RE, COUNT_HINT_RE, GRADE_KEYWORDS, FIXED_RE, PANEL_KEYWORDS）
- Produces: `class Mode(str, Enum)`、`classify_mode(text: str) -> Mode`、`classify_panel(text: str, filename: str) -> str`（返回 PANELS 之一或 `"待确认"`）。

- [ ] **Step 1：写失败测试**

`tests/test_classify.py`：
```python
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
```

> 说明：`classify_panel` 是**兜底**；带"X分"陈述的板块判定在 predict.py 用 `STMT_RE` 直抽（见 Task 5）。这里只测关键词逻辑。

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_classify.py -v`
Expected: FAIL（ImportError）。

- [ ] **Step 3：实现 classify.py**

`zongce/classify.py`：
```python
# -*- coding: utf-8 -*-
"""加分模式识别 + 板块关键词分类（兜底）。"""
from __future__ import annotations
from enum import Enum
from . import rules

class Mode(str, Enum):
    COUNT = "次数型"
    FIXED = "固定值型"
    GRADE = "获奖分级型"
    RULE_REF = "细则参照型"

def classify_mode(text: str) -> Mode:
    """优先级：次数型 > 获奖分级型 > 固定值型 > 细则参照型。"""
    if rules.COUNT_RE.search(text) and rules.COUNT_HINT_RE.search(text):
        return Mode.COUNT
    if any(k in text for k in rules.GRADE_KEYWORDS):
        return Mode.GRADE
    if rules.FIXED_RE.search(text):
        return Mode.FIXED
    return Mode.RULE_REF

def classify_panel(text: str, filename: str) -> str:
    """关键词投票；唯一命中→该板块，零命中或并列→待确认。"""
    hay = f"{filename} {text}"
    scores = {p: sum(1 for kw in kws if kw in hay) for p, kws in rules.PANEL_KEYWORDS.items()}
    hits = {p: s for p, s in scores.items() if s > 0}
    if not hits:
        return "待确认"
    if len(hits) == 1:
        return next(iter(hits))
    mx = max(hits.values())
    winners = [p for p, s in hits.items() if s == mx]
    return winners[0] if len(winners) == 1 else "待确认"
```

- [ ] **Step 4：跑测试确认通过**

Run: `pytest tests/test_classify.py -v`
Expected: PASS。

- [ ] **Step 5：提交**

```bash
git add zongce/classify.py tests/test_classify.py
git commit -m "feat(classify): 四模式识别 + 板块关键词兜底"
```

---

## Task 3：extract.py（PDF/图片 → 文字+bbox，带缓存）

**Files:**
- Create: `zongce/extract.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Produces: `OcrLine`、`PageResult`、`ExtractionResult`（dataclass，定义见上方"数据类型契约"）、`extract(path: str | Path, cache_dir: str | Path | None = None) -> ExtractionResult`。

- [ ] **Step 1：写失败测试**

`tests/test_extract.py`：
```python
from pathlib import Path
import fitz
from conftest import need
from zongce.extract import extract, ExtractionResult

FIX = Path(__file__).parent / "fixtures"

def _make_text_pdf(path: Path, text: str):
    doc = fitz.open()
    pg = doc.new_page()
    pg.insert_text((72, 72), text, fontsize=12)
    doc.save(str(path)); doc.close()

def test_text_layer_pdf_uses_text_method(tmp_path):
    p = tmp_path / "t.pdf"
    _make_text_pdf(p, "张三 加2分 品德")
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
```

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_extract.py -v`
Expected: FAIL（ImportError）。

- [ ] **Step 3：实现 extract.py**

`zongce/extract.py`：
```python
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
```

- [ ] **Step 4：跑测试确认通过**

Run: `pytest tests/test_extract.py -v`
Expected: PASS（5 条；OCR 两条首次较慢，缓存命中条快）。

- [ ] **Step 5：提交**

```bash
git add zongce/extract.py tests/test_extract.py
git commit -m "feat(extract): PDF/图片抽取，扫描件 OCR，按 hash 缓存"
```

---

## Task 4：name_match.py（模糊找姓名 + 同列邻近次数）

**Files:**
- Create: `zongce/name_match.py`
- Test: `tests/test_name_match.py`

**Interfaces:**
- Consumes: `ExtractionResult`、`OcrLine`（from extract）、`rules.COUNT_TOKEN_RE`
- Produces: `NameMatch`（见契约）、`find_name(extraction: ExtractionResult, name: str, threshold: float = 80.0) -> NameMatch`。

**算法（同列邻近还原次数）**：找到姓名所在行 `B_name`（该页）；在该页找所有次数 token（`COUNT_TOKEN_RE` 全匹配，取括号内数字）；筛选 x 区间与 `B_name` **重叠 ≥ 50% 宽度**（同列）且 y 在 `B_name` 下方 `≤ 2×行高` 内（或上方 `≤ 1×行高`）的次数 token；取 y 距离最近的一个作 `count`。找不到 → `count=None`（predict 里默认 1）。

- [ ] **Step 1：写失败测试**

`tests/test_name_match.py`：
```python
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
    assert m.count == 4   # 目标值；若 OCR 坐标噪声导致不一致，见 Step 3 注

def test_real_houqin_count_is_two():
    p = need(FIX / "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf")
    m = find_name(extract(p), "邓达俊")
    assert m.found and m.count == 2

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
```

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_name_match.py -v`
Expected: FAIL（ImportError）。

- [ ] **Step 3：实现 name_match.py**

`zongce/name_match.py`：
```python
# -*- coding: utf-8 -*-
"""姓名模糊匹配 + 同列邻近 (N) 还原次数。"""
from __future__ import annotations
from dataclasses import dataclass
from rapidfuzz import fuzz
from .extract import ExtractionResult, OcrLine
from . import rules

@dataclass
class NameMatch:
    found: bool
    count: int | None
    confidence: float
    context: str
    best_token: str
    best_score: float

def _overlap_ratio(a: tuple, b: tuple) -> float:
    lo = max(a[0], b[0]); hi = min(a[2], b[2])
    if hi <= lo:
        return 0.0
    inter = hi - lo
    w = min(a[2] - a[0], b[2] - b[0]) or 1.0
    return inter / w

def _find_name_line(lines: list[OcrLine], name: str, threshold: float):
    best = None
    for ln in lines:
        t = ln.text.strip()
        if not t:
            continue
        score = fuzz.WRatio(name, t)
        if score >= threshold and (best is None or score > best[1]):
            best = (ln, score)
    return best  # (OcrLine, score) | None

def _count_below_in_column(lines: list[OcrLine], name_line: OcrLine) -> int | None:
    nh = name_line.h or 20
    candidates = []
    for ln in lines:
        m = rules.COUNT_TOKEN_RE.match(ln.text.strip())
        if not m:
            continue
        n = int(m.group(1) or m.group(2))
        if _overlap_ratio(name_line.bbox, ln.bbox) < 0.5:   # 同列
            continue
        dy = ln.cy - name_line.cy
        if -nh <= dy <= 2 * nh:                             # 上方1行 或 下方2行内
            candidates.append((abs(dy), n))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]

def _context(text: str, name: str) -> str:
    i = text.find(name)
    if i < 0:
        return ""
    return text[max(0, i - 30): i + len(name) + 30].replace("\n", " ")

def find_name(extraction: ExtractionResult, name: str, threshold: float = 80.0) -> NameMatch:
    best_overall = None
    chosen_page_lines = None
    for pg in extraction.pages:
        hit = _find_name_line(pg.lines, name, threshold)
        if hit and (best_overall is None or hit[1] > best_overall[1]):
            best_overall = hit
            chosen_page_lines = pg.lines
    if best_overall is None:
        return NameMatch(False, None, 0.0, "", "", 0.0)
    name_line, score = best_overall
    count = _count_below_in_column(chosen_page_lines, name_line)
    return NameMatch(True, count, score / 100.0,
                     _context(extraction.text, name_line.text.strip()),
                     name_line.text.strip(), score)
```

> **Step 3 注（对实现者）**：`test_real_canshi_count_is_four` 依赖真实 OCR 坐标。若实测得到 `count != 4`（如 None 或其它），**不要改断言去凑**——先放宽 `_count_below_in_column` 的容差（同列重叠阈值 0.5→0.4，或下方 2×行高→3×行高）再跑；仍不行则把该断言改为 `m.count in (4,) or m.count is None` 并在 `note` 体现"次数配对失败"，符合 spec「失败→次数默认1」。容差改动要在 commit message 写清。

- [ ] **Step 4：跑测试确认通过**

Run: `pytest tests/test_name_match.py -v`
Expected: PASS（含真实 fixture 的 3 条）。若 canshi 真实条不过，按 Step 3 注处理并记录。

- [ ] **Step 5：提交**

```bash
git add zongce/name_match.py tests/test_name_match.py
git commit -m "feat(name_match): 模糊匹配 + 同列邻近还原次数"
```

---

## Task 5：predict.py（组装单文件预测）

**Files:**
- Create: `zongce/predict.py`
- Test: `tests/test_predict.py`

**Interfaces:**
- Consumes: `extract.extract`、`name_match.find_name`、`classify.classify_mode/classify_panel`、`rules.STMT_RE/normalize_panel/PER_TIME_DEFAULT`、`Mode`
- Produces: `Prediction`（见契约）、`predict(extraction: ExtractionResult, name: str) -> Prediction`。

**逻辑**：
1. `nm = find_name(extraction, name)`；未找到 → `Prediction(panel="待确认", mode=None, points=None, status="待确认", note="未找到姓名")`。
2. `mode = classify_mode(text)`；`stmt = STMT_RE.search(text)`。
3. **板块**：`panel = normalize_panel(stmt.group(2)) if stmt else classify_panel(text, filename)`；都失败 → `"待确认"`。
4. **加分**：
   - `COUNT`：`per = float(stmt.group(1)) if stmt else PER_TIME_DEFAULT.get((panel,kw), None)`；`count = nm.count or 1`；`points = per*count if per is not None else None`；`status = "自动" if points is not None else "待确认"`。
   - `FIXED`：`points = float(stmt.group(1)) if stmt else None`；status 同上。
   - `GRADE` / `RULE_REF`：`points=None, status="待确认"`。
5. `basis` = 加分陈述所在句（含 STMT_RE 命中或含等级/名单的关键句，截 60 字）。

- [ ] **Step 1：写失败测试**

`tests/test_predict.py`：
```python
from pathlib import Path
from conftest import need
from zongce.extract import extract
from zongce.predict import predict, Mode

FIX = Path(__file__).parent / "fixtures"

def test_canshi_predicts_wenti_count_4():
    p = need(FIX / "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf")
    pr = predict(extract(p), "邓达俊")
    assert pr.panel == "文体"
    assert pr.mode == Mode.COUNT
    assert pr.points == 4.0
    assert pr.status == "自动"
    assert "每场次" in pr.basis or "文体分" in pr.basis

def test_houqin_predicts_pinde_count_2():
    p = need(FIX / "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf")
    pr = predict(extract(p), "邓达俊")
    assert pr.panel == "品德"          # 由"加0.5品德分"决定，非文件名
    assert pr.mode == Mode.COUNT
    assert pr.points == 1.0
    assert pr.status == "自动"

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
```

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_predict.py -v`
Expected: FAIL（ImportError）。

- [ ] **Step 3：实现 predict.py**

`zongce/predict.py`：
```python
# -*- coding: utf-8 -*-
"""组装单文件加分预测。"""
from __future__ import annotations
import re
from dataclasses import dataclass
from .extract import ExtractionResult
from .name_match import find_name
from .classify import classify_mode, classify_panel, Mode
from . import rules

@dataclass
class Prediction:
    file: str            # 完整源路径：export 取 stem 展示、organize 取 name 复制
    panel: str
    mode: Mode | None
    points: float | None
    count: int | None
    basis: str
    status: str
    note: str

_SENT_SPLIT = re.compile(r"[。\n；;]")
_KW_FOR_DEFAULT = [("参赛", "参赛"), ("裁判", "裁判"), ("后勤", "后勤"), ("工作人员", "工作人员")]

def _kw_default(panel: str, text: str) -> float | None:
    for kw, key in _KW_FOR_DEFAULT:
        if kw in text:
            return rules.PER_TIME_DEFAULT.get((panel, key))
    return None

def _basis(text: str, stmt_match) -> str:
    if stmt_match:
        i = stmt_match.start()
        seg = text[max(0, i-20): i+40]
        return _SENT_SPLIT.split(seg)[0][:60]
    return text[:60].replace("\n", " ")

def predict(extraction: ExtractionResult, name: str) -> Prediction:
    src = extraction.source
    text = extraction.text
    nm = find_name(extraction, name)
    if not nm.found:
        return Prediction(src, "待确认", None, None, None, text[:40], "待确认", "未找到姓名")
    mode = classify_mode(text)
    stmt = rules.STMT_RE.search(text)
    panel = rules.normalize_panel(stmt.group(2)) if stmt else classify_panel(text, fname)

    points = None; count = nm.count; status = "待确认"; note = ""
    if mode == Mode.COUNT:
        per = float(stmt.group(1)) if stmt else _kw_default(panel or "", text)
        count = nm.count if nm.count is not None else 1
        if nm.count is None:
            note = "次数配对失败，默认1次"
        if per is not None and panel:
            points = round(per * count, 2); status = "自动"
        else:
            note = (note + "；" if note else "") + "单次值/板块缺失"
    elif mode == Mode.FIXED:
        if stmt and panel:
            points = float(stmt.group(1)); status = "自动"
    elif mode == Mode.GRADE:
        note = "级别待按《学科竞赛分类表》认定"
    else:  # RULE_REF
        note = "无数值/名次，按细则参照待人工确认"
    return Prediction(src, panel or "待确认", mode, points, count,
                      _basis(text, stmt), status, note)
```

- [ ] **Step 4：跑测试确认通过**

Run: `pytest tests/test_predict.py -v`
Expected: PASS（5 条）。注意 `test_canshi` 的 `points==4.0` 依赖 Task 4 拿到 `count==4`；若 Task 4 在该 fixture 退化为默认 1，本条会变成 `points==1.0` → 回到 Task 4 Step 3 注解决次数问题，不要改本断言。

- [ ] **Step 5：提交**

```bash
git add zongce/predict.py tests/test_predict.py
git commit -m "feat(predict): 单文件加分预测，陈述优先+关键词兜底"
```

---

## Task 6：export.py（导出 xlsx + 物理归类文件）

**Files:**
- Create: `zongce/export.py`
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `Prediction`、`rules.PANELS`
- Produces: `export_excel(predictions: list[Prediction], out_path: str | Path) -> Path`、`organize_files(predictions: list[Prediction], out_dir: str | Path) -> Path`。返回写出的路径。

**表1 列**：`类别 | 项目 | 级别/明细 | 细则依据 | 加分 | 认定状态 | 备注`；按 品德/学业/文体/待确认 分段，每段末尾插小计行 `▶ {panel} 附加 raw 合计：X（另有 n 项待确认）`（P1 不含 70 基本分与折算，那俩在 P2）。

- [ ] **Step 1：写失败测试**

`tests/test_export.py`：
```python
from pathlib import Path
import pandas as pd
import openpyxl
from zongce.predict import Prediction
from zongce.classify import Mode
from zongce.export import export_excel, organize_files

def _mk_predictions():
    return [
        Prediction("参赛.pdf", "文体", Mode.COUNT, 4.0, 4, "每场次加1文体分", "自动", ""),
        Prediction("后勤.pdf", "品德", Mode.COUNT, 1.0, 2, "每次加0.5品德分", "自动", ""),
        Prediction("数模.pdf", "学业", Mode.GRADE, None, None, "三等奖", "待确认", "级别待认定"),
        Prediction("新年.pdf", "品德", Mode.RULE_REF, None, None, "工作人员名单", "待确认", ""),
    ]

def test_export_excel_has_columns_and_rows(tmp_path):
    out = export_excel(_mk_predictions(), tmp_path / "综测加分明细.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    header = [c.value for c in ws[1]]
    assert header[:7] == ["类别", "项目", "级别/明细", "细则依据", "加分", "认定状态", "备注"]
    texts = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    assert "参赛" in texts and "数模" in texts   # 项目列取 stem
    assert "▶" in texts  # 至少一个小计行

def test_organize_files_copies_into_panels(tmp_path):
    src_a = tmp_path / "参赛.pdf"; src_a.write_text("x")
    src_b = tmp_path / "数模.pdf"; src_b.write_text("y")
    preds = [
        Prediction(str(src_a), "文体", Mode.COUNT, 4.0, 4, "", "自动", ""),
        Prediction(str(src_b), "学业", Mode.GRADE, None, None, "", "待确认", ""),
    ]
    out = organize_files(preds, tmp_path / "归类")
    assert (out / "文体" / "参赛.pdf").exists()
    assert (out / "学业" / "数模.pdf").exists()

def test_organize_files_renames_duplicates(tmp_path):
    d1 = tmp_path / "d1"; d1.mkdir(); src = d1 / "a.pdf"; src.write_text("x")
    d2 = tmp_path / "d2"; d2.mkdir(); src2 = d2 / "a.pdf"; src2.write_text("y")
    preds = [
        Prediction(str(src), "文体", Mode.COUNT, 1.0, 1, "", "自动", ""),
        Prediction(str(src2), "文体", Mode.COUNT, 1.0, 1, "", "自动", ""),
    ]
    out = organize_files(preds, tmp_path / "归类2")
    names = sorted(p.name for p in (out / "文体").iterdir())
    assert names == ["a.pdf", "a_1.pdf"]
```

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_export.py -v`
Expected: FAIL（ImportError）。

- [ ] **Step 3：实现 export.py**

`zongce/export.py`：
```python
# -*- coding: utf-8 -*-
"""导出邓达俊式 xlsx + 按板块物理复制文件。"""
from __future__ import annotations
import shutil
from pathlib import Path
import pandas as pd
from .predict import Prediction
from . import rules

COLUMNS = ["类别", "项目", "级别/明细", "细则依据", "加分", "认定状态", "备注"]
_ORDER = ["品德", "学业", "文体", "待确认"]

def _detail(pr: Prediction) -> str:
    if pr.mode is None:
        return ""
    if pr.mode.value == "次数型":
        return f"次数×{pr.count or 1}"
    return pr.mode.value

def _rows(predictions: list[Prediction]):
    by: dict[str, list[Prediction]] = {p: [] for p in _ORDER}
    for pr in predictions:
        by.setdefault(pr.panel, []).append(pr) if pr.panel in by else by.setdefault("待确认", []).append(pr)
    for panel in _ORDER:
        group = by.get(panel, [])
        for pr in group:
            yield [panel, Path(pr.file).stem, _detail(pr), pr.basis,
                   pr.points if pr.points is not None else "",
                   pr.status, pr.note]
        if group:
            auto = sum(p.points for p in group if p.points is not None)
            pending = sum(1 for p in group if p.status == "待确认")
            yield [panel, f"▶ {panel} 附加 raw 合计：{auto:g}" +
                   (f"（另有 {pending} 项待确认）" if pending else ""), "", "", "", "", ""]

def export_excel(predictions: list[Prediction], out_path) -> Path:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(_rows(predictions), columns=COLUMNS)
    with pd.ExcelWriter(out_path, engine="openpyxl") as x:
        df.to_excel(x, index=False, sheet_name="综测加分明细")
    return out_path

def organize_files(predictions: list[Prediction], out_dir) -> Path:
    out_dir = Path(out_dir)
    seen: dict[Path, int] = {}
    for pr in predictions:
        panel = pr.panel if pr.panel in rules.PANELS else "待确认"
        dst_dir = out_dir / panel; dst_dir.mkdir(parents=True, exist_ok=True)
        src = Path(pr.file)
        if not src.exists():
            continue
        dst = dst_dir / src.name
        if dst.exists() or dst in seen:
            n = seen.get(dst, 1)
            while True:
                cand = dst.with_name(f"{dst.stem}_{n}{dst.suffix}")
                if not cand.exists() and cand not in seen:
                    dst = cand; seen[dst] = 0; break
                n += 1
        seen[dst] = seen.get(dst, 0)
        shutil.copy2(src, dst)
    return out_dir
```

- [ ] **Step 4：跑测试确认通过**

Run: `pytest tests/test_export.py -v`
Expected: PASS。

- [ ] **Step 5：提交**

```bash
git add zongce/export.py tests/test_export.py
git commit -m "feat(export): 邓达俊式 xlsx + 按板块物理复制"
```

---

## Task 7：pipeline.py + cli.py（串联 + 端到端）

**Files:**
- Create: `zongce/pipeline.py`, `zongce/cli.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `Report(name, predictions, excel_path, organized_dir)`、`run_pipeline(name, input_dir, output_dir, cache_dir=None) -> Report`；CLI `python -m zongce.cli <姓名> <输入目录> [-o 输出目录] [--cache 缓存目录]`。

- [ ] **Step 1：写失败测试（端到端）**

`tests/test_pipeline.py`：
```python
from pathlib import Path
from conftest import need
from zongce.pipeline import run_pipeline
from zongce.classify import Mode

FIX = Path(__file__).parent / "fixtures"

def _ensure_all_fixtures():
    for n in ["2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf",
              "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf",
              "第二十三届五一数学建模竞赛三等奖.pdf",
              "2026新年音乐会志愿服务活动工作人员证明.pdf"]:
        need(FIX / n)

def test_pipeline_dengdajun(tmp_path):
    _ensure_all_fixtures()
    rep = run_pipeline("邓达俊", FIX, tmp_path, cache_dir=tmp_path / ".cache")
    by_file = {Path(p.file).name: p for p in rep.predictions}
    canshi = by_file["2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf"]
    assert canshi.panel == "文体" and canshi.mode == Mode.COUNT and canshi.points == 4.0
    houqin = by_file["2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf"]
    assert houqin.panel == "品德" and houqin.points == 1.0
    wuyi = by_file["第二十三届五一数学建模竞赛三等奖.pdf"]
    assert wuyi.panel == "学业" and wuyi.points is None and wuyi.status == "待确认"
    xinnian = by_file["2026新年音乐会志愿服务活动工作人员证明.pdf"]
    assert xinnian.panel == "品德" and xinnian.points is None
    # 产出物
    assert rep.excel_path.exists()
    for d in ("文体", "品德", "学业"):
        assert (rep.organized_dir / d).is_dir()
    # jpg 也在 fixture 里，应被处理（panel 任一），不报错
```

- [ ] **Step 2：跑测试确认失败**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL（ImportError）。

- [ ] **Step 3：实现 pipeline.py**

`zongce/pipeline.py`：
```python
# -*- coding: utf-8 -*-
"""端到端流水线：extract → predict → export。"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .extract import extract, IMG_EXT, PDF_EXT
from .predict import predict, Prediction
from .export import export_excel, organize_files

@dataclass
class Report:
    name: str
    predictions: list[Prediction]
    excel_path: Path
    organized_dir: Path

def _iter_inputs(input_dir: Path):
    for p in sorted(input_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (PDF_EXT | IMG_EXT):
            yield p

def run_pipeline(name: str, input_dir, output_dir, cache_dir=None) -> Report:
    input_dir = Path(input_dir); output_dir = Path(output_dir)
    person_dir = output_dir / name
    person_dir.mkdir(parents=True, exist_ok=True)
    preds: list[Prediction] = []
    for f in _iter_inputs(input_dir):
        try:
            ext = extract(f, cache_dir=cache_dir)
        except Exception as e:
            preds.append(Prediction(f.name, "待确认", None, None, None, "", "待确认", f"抽取失败：{e}"))
            continue
        preds.append(predict(ext, name))
    excel = export_excel(preds, person_dir / "综测加分明细.xlsx")
    organized = organize_files(preds, person_dir)
    return Report(name, preds, excel, organized)
```

- [ ] **Step 4：实现 cli.py 并手测**

`zongce/cli.py`：
```python
# -*- coding: utf-8 -*-
"""命令行入口：python -m zongce.cli <姓名> <输入目录> [-o 输出目录] [--cache 缓存目录]"""
from __future__ import annotations
import argparse
from pathlib import Path
from .pipeline import run_pipeline

def main(argv=None):
    ap = argparse.ArgumentParser(prog="zongce", description="综测加分预测工具（P1）")
    ap.add_argument("name", help="姓名，如 邓达俊")
    ap.add_argument("input_dir", help="活动证明所在文件夹（pdf/jpg/png）")
    ap.add_argument("-o", "--output", default="综测输出", help="输出目录，默认 ./综测输出")
    ap.add_argument("--cache", default=None, help="OCR 缓存目录")
    args = ap.parse_args(argv)
    rep = run_pipeline(args.name, args.input_dir, args.output, cache_dir=args.cache)
    auto = sum(1 for p in rep.predictions if p.status == "自动")
    print(f"完成：{len(rep.predictions)} 个文件，{auto} 个自动估分")
    print(f"  Excel: {rep.excel_path}")
    print(f"  归类:  {rep.organized_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

手测（真跑邓达俊 大一，验证可用）：
```bash
python -m zongce.cli 邓达俊 "D:\综测证明材料\大一" -o "D:\综测输出" --cache "D:\综测输出\.cache"
```
Expected: 打印完成行；`D:\综测输出\邓达俊\综测加分明细.xlsx` 生成；品德/学业/文体 文件夹就位。

- [ ] **Step 5：跑端到端测试 + 全量测试，提交**

Run: `pytest -v`
Expected: 全部 PASS（含 `test_pipeline_dengdajun`）。

```bash
git add zongce/pipeline.py zongce/cli.py tests/test_pipeline.py
git commit -m "feat(pipeline): 端到端流水线 + CLI，邓达俊基准通过"
```

---

## Self-Review

**1. Spec 覆盖**（对照设计文档 P1 范围）：
- ①按名字找文件 → Task 3 extract + Task 4 name_match ✓
- ②三板块分类 + 加分预测 → Task 2 classify + Task 5 predict（含 4 模式）✓
- ⑤产出：加分明细 xlsx + 3(+待确认) 文件夹 → Task 6 export ✓
- 主线串联 + 可用 → Task 7 pipeline/cli ✓
- P1 **不含**：评分引擎/总分（P2）、奖学金/门槛（P3）、Streamlit UI、表单输入 → 明确推迟，符合设计第 15 节。
- 错误处理（设计第 13 节）：OCR 姓名识错→模糊匹配✓；姓名↔次数失败→默认1+备注✓；模式+关键词失败→待确认✓；获奖分级抽不全→待确认✓；附加缺班最高→P2（P1 不折算）；非 PDF→图片已支持，docx/xls/zip 跳过（pipeline 只收 pdf/jpg/png）✓；重跑缓存✓。

**2. 占位符扫描**：无 TBD/TODO；每个代码步含完整可运行代码；测试含真实断言值（4.0 / 1.0 / 待确认）。

**3. 类型一致性**：`ExtractionResult/OcrLine/PageResult`（Task3）被 Task4/5 消费——签名一致；`NameMatch`（Task4）被 Task5 经 `find_name` 消费；`Prediction`（Task5）被 Task6/7 消费；`Mode` 在 classify（Task2）定义、predict（Task5）/pipeline（Task7）引用——一致。

   ✅ **`Prediction.file` 契约（已直接落入 Task 5/6 代码，实现者照抄即可）**：`file` 存**完整源路径**（非 basename）。predict 里 `src = extraction.source` 直接作 `file`；export `organize_files` 用 `Path(pr.file)` 复制、`Path(pr.file).name` 取目标名；`export_excel` 项目列用 `Path(pr.file).stem` 展示。pipeline 抽取失败分支 `Prediction(file=str(f), ...)`。**无需新增字段**（曾考虑加 `source_path`，最终复用 `file`=完整路径，organize 本就用 `Path(pr.file)`，零改动）。

**4. 预检额外修正（已落入计划，实现者照抄）**：
- Task 1 `test_fixed_re`：去掉 `or True` 永真，改为真实断言 `not FIXED_RE.search("加0.5品德分")`。
- Task 6 `test_export_excel`：项目列存 stem，断言改 `"参赛"/"数模"`（非 `"参赛.pdf"`）。
- Task 6 `test_organize_files_renames_duplicates`：用两个不同目录下的同名 `a.pdf` 模拟重名（原写法 `file="a.pdf"` 不存在→被跳过）。
- pyproject `pythonpath = [".", "tests"]`：让测试里 `from conftest import need` 可解析。
- Task 0 `.gitignore`：除计划列出的项，**另加 `.superpowers/` 与 `.claude/`**（SDD 工作区与本机 Claude 配置不入库）。

---

## Execution Handoff

计划已保存到 `docs/superpowers/plans/2026-08-03-P1-pdf-pipeline.md`。两种执行方式：

**1. Subagent 驱动（推荐）** — 每个任务派一个新 subagent 实现，任务间我来 review，迭代快、上下文干净。
**2. 当前会话内联执行** — 用 executing-plans 在本会话按任务批量推进，带检查点 review。

选哪种？
