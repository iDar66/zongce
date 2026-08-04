from pathlib import Path
import shutil

from openpyxl import Workbook

from conftest import need
from zongce.classify import Mode
from zongce.pipeline import run_pipeline


FIX = Path(__file__).parent / "fixtures"


def _write_grade_book(path: Path, semester: int) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["学年", "学期", "课程代码", "课程名称", "学分", "成绩分项", "成绩"])
    sheet.append(["2025-2026", semester, f"C{semester}", "课程", 1.0, "总评", 80 + semester])
    workbook.save(path)
    return path


def _ensure_all_fixtures():
    for filename in (
        "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf",
        "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf",
        "第二十三届五一数学建模竞赛三等奖.pdf",
        "2026新年音乐会志愿服务活动工作人员证明.pdf",
        "校第一届班BA篮球联赛甲组第三名(校级）.jpg",
    ):
        need(FIX / filename)


def test_pipeline_processes_fixtures_and_writes_outputs(tmp_path):
    _ensure_all_fixtures()

    report = run_pipeline("邓达俊", FIX, tmp_path, cache_dir=tmp_path / ".cache")

    by_file = {Path(prediction.file).name: prediction for prediction in report.predictions}
    canshi = by_file["2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf"]
    assert canshi.panel == "文体"
    assert canshi.mode == Mode.COUNT
    assert canshi.points == 1.0

    houqin = by_file["2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf"]
    assert houqin.panel == "品德"
    assert houqin.points == 0.5

    wuyi = by_file["第二十三届五一数学建模竞赛三等奖.pdf"]
    assert wuyi.panel == "学业"
    assert wuyi.points is None
    assert wuyi.status == "待确认"

    xinnian = by_file["2026新年音乐会志愿服务活动工作人员证明.pdf"]
    assert xinnian.panel == "品德"
    assert xinnian.points is None

    image_name = "校第一届班BA篮球联赛甲组第三名(校级）.jpg"
    assert image_name in by_file

    assert report.excel_path.exists()
    for panel in ("文体", "品德", "学业"):
        assert (report.organized_dir / panel).is_dir()


def test_pipeline_rebinds_source_after_shared_cache(tmp_path):
    source = FIX / "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf"
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    shutil.copy2(source, first)
    shutil.copy2(source, second)

    report = run_pipeline("邓达俊", tmp_path, tmp_path / "output", cache_dir=tmp_path / ".cache")
    files = {Path(prediction.file).name for prediction in report.predictions}
    assert files == {"first.pdf", "second.pdf"}


def test_cli_accepts_arguments_and_reports_completion(tmp_path, capsys):
    from zongce.cli import main

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    assert main(["邓达俊", str(input_dir), "-o", str(tmp_path / "output")]) == 0
    assert "完成：0 个文件，0 个自动估分" in capsys.readouterr().out


def test_pipeline_with_grade_files_writes_score_report(tmp_path):
    import pandas as pd

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    grade_files = [_write_grade_book(tmp_path / "upper.xlsx", 1), _write_grade_book(tmp_path / "lower.xlsx", 2)]

    report = run_pipeline("邓达俊", input_dir, tmp_path / "output", grade_files=grade_files)

    assert report.score_report is not None
    assert "综测评分预测" in pd.ExcelFile(report.excel_path).sheet_names


def test_cli_accepts_grade_files_and_class_maximums(tmp_path):
    from zongce.cli import main

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    upper = _write_grade_book(tmp_path / "upper.xlsx", 1)
    lower = _write_grade_book(tmp_path / "lower.xlsx", 2)

    assert main([
        "邓达俊",
        str(input_dir),
        "-o",
        str(tmp_path / "output"),
        "--grade-file",
        str(upper),
        "--grade-file",
        str(lower),
        "--academic-class-max-raw",
        "10",
        "--sports-class-max-raw",
        "80",
    ]) == 0


def test_pipeline_p2_failure_keeps_p1_output(tmp_path):
    _ensure_all_fixtures()
    # 传一个缺必需列的成绩文件触发 GradeInputError；P1 明细和板块文件夹仍必须产出
    bad_grade = tmp_path / "bad.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["只有一列"])
    workbook.save(bad_grade)

    report = run_pipeline("邓达俊", FIX, tmp_path / "output", grade_files=[bad_grade])

    assert report.score_report is None
    assert report.score_error is not None
    assert report.excel_path.exists()
    for panel in ("文体", "品德", "学业"):
        assert (report.organized_dir / panel).is_dir()
