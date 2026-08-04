# P2 综测评分引擎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留 P1 单人活动证明流程兼容性的前提下，读取上下学期成绩 Excel，计算基本分、附加折算和综测总分，并把结果写入现有 Excel 输出。

**Architecture:** 新增 `grades.py` 作为纯成绩输入边界，新增 `score.py` 作为纯评分计算层；`pipeline.py` 只负责把 P1 predictions、成绩摘要和可选班级分母串起来，`export.py` 负责新增评分工作表。未传成绩参数时，pipeline 和现有 P1 输出保持不变。

**Tech Stack:** Python 3.14、dataclasses、pandas/openpyxl、pytest；不新增依赖，不联网，不复制真实成绩文件进仓库。

## Global Constraints

- Python 使用全局 `C:\Python314`，不创建 venv。
- P1 旧调用 `run_pipeline(name, input_dir, output_dir, cache_dir=None)` 和旧 CLI 行为必须保持兼容。
- 成绩 Excel 只读取 `成绩分项 == "总评"` 的行；上下学期要求同一学年且学期分别为 1、2。
- 无真实班级最高 raw 时，学业/文体分母分别使用封顶值的 1.25 倍，并在报告中标记“估算”。
- 品德基本分 70、文体基本分 60、学业基本分为全年学分加权平均乘 0.8；总分权重为 20%/65%/15%。
- 测试 fixture 不包含用户真实成绩或活动证明；真实 Excel 仅做本地端到端验证。

---

### Task 1: 成绩 Excel 读取与校验

**Files:**
- Create: `zongce/grades.py`
- Create: `tests/test_grades.py`

**Interfaces:**
- Consumes: 一份或多份成绩 `.xlsx`，每份包含 `学年`、`学期`、`课程代码`、`课程名称`、`学分`、`成绩分项`、`成绩`。
- Produces: `GradeInputError(ValueError)`、`CourseGrade`、`GradeSummary` 和 `read_grade_files(paths)`，供 Task 2 调用。

- [ ] **Step 1: 写失败测试，先锁定总评筛选和全年加权公式**

```python
def test_read_grade_files_uses_total_score_rows(tmp_path):
    upper = _write_grade_book(tmp_path / "upper.xlsx", semester=1,
                              rows=[("A", 3, "平时", 100), ("A", 3, "总评", 90)])
    lower = _write_grade_book(tmp_path / "lower.xlsx", semester=2,
                              rows=[("B", 1, "总评", 80)])

    summary = read_grade_files([upper, lower])

    assert summary.course_count == 2
    assert summary.total_credits == 4
    assert summary.weighted_average == pytest.approx(87.5)
```

测试 helper 用 `openpyxl` 在 `tmp_path` 生成最小工作簿，不读取真实成绩文件。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_grades.py -q`

Expected: FAIL，因为 `zongce.grades` 和读取接口尚不存在。

- [ ] **Step 3: 实现最小成绩模型和解析器**

实现：

```python
@dataclass(frozen=True)
class CourseGrade:
    semester: int
    course_code: str
    course_name: str
    credits: float
    score: float
    source: Path

@dataclass(frozen=True)
class GradeSummary:
    academic_year: str
    courses: tuple[CourseGrade, ...]
    total_credits: float
    weighted_score: float
    weighted_average: float
    source_files: tuple[Path, ...]
    semesters: tuple[int, ...]

read_grade_files(paths: Sequence[str | Path]) -> GradeSummary
```

用 `pandas.read_excel` 读取首个工作表；检查文件存在、必需列、学年一致、学期集合为 `{1, 2}`、每学期每课程代码只有一个总评、成绩/学分为有限非负数。`weighted_average` 为 `weighted_score / total_credits`。

- [ ] **Step 4: 补齐错误分支测试并运行**

覆盖缺列、上下学期缺失、学年不一致、重复总评、非法成绩/学分和空文件。

Run: `python -m pytest tests/test_grades.py -q`

Expected: 所有成绩读取测试 PASS。

- [ ] **Step 5: 提交独立变更**

```bash
git add zongce/grades.py tests/test_grades.py
git commit -m "feat: add grade workbook parser"
```

---

### Task 2: 纯评分计算引擎

**Files:**
- Create: `zongce/score.py`
- Create: `tests/test_score.py`

**Interfaces:**
- Consumes: Task 1 的 `GradeSummary` 和 P1 `Prediction` 序列。
- Produces: `PanelScore`、`ScoreReport` 和 `calculate_score(predictions, grades, class_max_raw=None)`。

- [ ] **Step 1: 写失败测试，锁定无折算、估算折算和总分权重**

```python
def test_calculate_score_uses_estimated_caps():
    grades = GradeSummary(
        academic_year="2025-2026",
        courses=(),
        total_credits=1.0,
        weighted_score=86.0,
        weighted_average=86.0,
        source_files=(),
        semesters=(1, 2),
    )
    predictions = [
        Prediction("moral.pdf", "品德", Mode.FIXED, 3.0, 1, "", "自动", ""),
        Prediction("study.pdf", "学业", Mode.FIXED, 25.0, 1, "", "自动", ""),
        Prediction("sports.pdf", "文体", Mode.FIXED, 10.0, 1, "", "自动", ""),
    ]

    report = calculate_score(predictions, grades)

    assert report.academic.denominator_source == "估算"
    assert report.academic.additional == pytest.approx(20.0)
    assert report.total == pytest.approx(
        report.moral.final * .20
        + report.academic.final * .65
        + report.sports.final * .15
    )
```

测试中使用已有 `Prediction`/`Mode` 构造方式和最小 `GradeSummary` fixture。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_score.py -q`

Expected: FAIL，因为 `zongce.score` 尚不存在。

- [ ] **Step 3: 实现纯 dataclass 计算层**

定义：

```python
@dataclass(frozen=True)
class PanelScore:
    raw: float
    base: float
    cap: float | None
    additional: float
    final: float
    denominator: float | None
    denominator_source: str
    pending_count: int

@dataclass(frozen=True)
class ScoreReport:
    grades: GradeSummary
    moral: PanelScore
    academic: PanelScore
    sports: PanelScore
    total: float
```

按板块汇总数值 `points`；`None` 不进入 raw，但按板块记录待确认数量。品德为 `70 + raw`。学业基本分为 `grades.weighted_average * 0.8`，文体基本分为 60。学业 cap=20、文体 cap=40：真实分母不超过 cap 时直接计入并以 cap 限制；真实分母超过 cap 时使用 `raw / denominator * cap`；未提供分母时使用 `cap * 1.25` 并标记“估算”。折算结果限制在 `[0, cap]`。校验分母为有限非负数，最后按 0.20/0.65/0.15 计算 total。

- [ ] **Step 4: 补齐边界测试并运行**

覆盖 raw 为 0、分母等于 cap、分母低于 cap、实测分母高于 cap、个人 raw 超估算分母、待确认项目、负数分母和总分计算。

Run: `python -m pytest tests/test_score.py -q`

Expected: 所有评分计算测试 PASS。

- [ ] **Step 5: 提交独立变更**

```bash
git add zongce/score.py tests/test_score.py
git commit -m "feat: add comprehensive score engine"
```

---

### Task 3: P2 评分工作表导出

**Files:**
- Modify: `zongce/export.py`
- Modify: `tests/test_export.py`

**Interfaces:**
- Consumes: 现有 predictions 和可选 `ScoreReport`。
- Produces: `export_excel(predictions, out_path, score_report=None)`；不传 report 时保持 P1 单工作表行为。

- [ ] **Step 1: 写失败测试，验证评分页和 P1 回归**

```python
def test_export_excel_adds_score_sheet_when_report_is_given(tmp_path):
    output = export_excel(predictions, tmp_path / "result.xlsx", score_report=report)
    book = pd.ExcelFile(output)
    assert book.sheet_names == ["综测加分明细", "综测评分预测"]
    score = pd.read_excel(output, sheet_name="综测评分预测")
    assert "班级最高 raw 来源" in score.columns
    assert "估算" in score.to_string()
```

同时保留现有“不传 report 只有加分明细页”的断言。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_export.py -q`

Expected: FAIL，因为 `export_excel` 目前没有 `score_report` 参数或评分页。

- [ ] **Step 3: 实现最小评分页导出**

给 `export_excel` 增加可选 `score_report` 参数；现有明细 DataFrame 写入 `综测加分明细`，report 存在时追加 `综测评分预测`。评分页至少包含全年加权平均、三板块 raw、基本分、折算附加、最终板块分、总分、分母来源和待确认提示。保持现有板块文件复制逻辑不变。

- [ ] **Step 4: 运行导出测试并检查工作表内容**

Run: `python -m pytest tests/test_export.py -q`

Expected: P1 和 P2 导出测试 PASS，原明细页列顺序不变。

- [ ] **Step 5: 提交独立变更**

```bash
git add zongce/export.py tests/test_export.py
git commit -m "feat: export score prediction sheet"
```

---

### Task 4: 流水线与 CLI 接入

**Files:**
- Modify: `zongce/pipeline.py`
- Modify: `zongce/cli.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_smoke.py`

**Interfaces:**
- Consumes: Task 1-3 的接口；旧调用仍只传 `name/input_dir/output_dir/cache_dir`。
- Produces: `run_pipeline(name, input_dir, output_dir, cache_dir=None, grade_files=None, class_max_raw=None)` 和 CLI 的重复 `--grade-file`、`--academic-class-max-raw`、`--sports-class-max-raw` 参数。

- [ ] **Step 1: 写失败测试，验证 P1 兼容和 P2 端到端**

```python
def test_pipeline_without_grade_files_keeps_p1_report(tmp_path):
    report = run_pipeline("邓达俊", fixture_dir, tmp_path)
    assert report.score_report is None
    assert report.excel_path.exists()

def test_pipeline_with_two_grade_files_writes_score_sheet(tmp_path, grade_books):
    report = run_pipeline(
        "邓达俊", fixture_dir, tmp_path,
        grade_files=grade_books,
    )
    assert report.score_report is not None
    assert "综测评分预测" in pd.ExcelFile(report.excel_path).sheet_names
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_pipeline.py tests/test_smoke.py -q`

Expected: 新增 P2 测试 FAIL，现有 P1 测试继续 PASS。

- [ ] **Step 3: 接入可选 P2 分支**

在 `Report` 增加默认值为 `None` 的 `score_report` 字段；pipeline 生成 P1 predictions 后，只有 `grade_files` 非空时才调用 `read_grade_files`、`calculate_score` 和带 report 的 `export_excel`。保持 P1 的 `Prediction` 和组织文件行为不变。CLI 用 `action="append"` 接收两个 `--grade-file`，并将两个可选板块分母参数组装为映射；缺少成绩参数时不进入 P2。

- [ ] **Step 4: 运行流水线、CLI 和回归测试**

Run: `python -m pytest tests/test_pipeline.py tests/test_smoke.py -q`

Expected: P1 兼容测试和 P2 端到端测试全部 PASS；无成绩参数的 CLI 输出仍只有 P1 结果。

- [ ] **Step 5: 提交独立变更**

```bash
git add zongce/pipeline.py zongce/cli.py tests/test_pipeline.py tests/test_smoke.py
git commit -m "feat: wire score engine into pipeline"
```

---

### Task 5: 全量验证与真实成绩端到端核验

**Files:**
- Modify: `tests/test_predict.py` or `tests/test_export.py` only if a focused regression test is discovered during integration.
- No real user files are added to the repository.

**Interfaces:** 使用已完成的 P1/P2 CLI 和模块接口。

- [ ] **Step 1: 运行全量测试**

Run: `python -m pytest`

Expected: 原有 P1 40 项测试全部 PASS，新增 P2 测试也 PASS。

- [ ] **Step 2: 用真实上下学期 Excel 做本地端到端核验**

使用 `D:\综测证明材料\大一\邓达俊2025-2026学年上学期成绩表.xlsx` 和下学期文件作为 `--grade-file`，活动证明目录仍作为 P1 输入；输出到临时目录，不把真实文件复制到仓库。核对全年加权平均约 `86.02`、学业基本分约 `68.82`，并确认评分页显示学业/文体分母来源为“估算”。

- [ ] **Step 3: 检查输出和工作区**

确认原 P1 明细页、四个板块文件夹、P2 评分页均存在；运行 `git diff --check` 和 `git status --short`，确保没有成绩文件、fixture PII 或临时依赖目录被纳入变更。

- [ ] **Step 4: 提交验证结果**

```bash
git add docs/superpowers/plans/2026-08-03-P2-score-engine.md
git commit -m "docs: add P2 score engine implementation plan"
```
