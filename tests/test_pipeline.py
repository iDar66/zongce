from pathlib import Path
import shutil

from conftest import need
from zongce.classify import Mode
from zongce.pipeline import run_pipeline


FIX = Path(__file__).parent / "fixtures"


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
