# -*- coding: utf-8 -*-
"""端到端流水线：提取、预测、导出。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .export import export_excel, organize_files
from .extract import IMG_EXT, PDF_EXT, extract
from .grades import GradeInputError, read_grade_files
from .predict import Prediction, predict
from .score import ScoreInputError, ScoreReport, calculate_score


@dataclass
class Report:
    name: str
    predictions: list[Prediction]
    excel_path: Path
    organized_dir: Path
    score_report: ScoreReport | None = None
    score_error: str | None = None


def _iter_inputs(input_dir: Path):
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in PDF_EXT | IMG_EXT:
            yield path


def run_pipeline(name: str, input_dir, output_dir, cache_dir=None, grade_files=None, class_max_raw=None) -> Report:
    input_dir = Path(input_dir)
    person_dir = Path(output_dir) / name
    person_dir.mkdir(parents=True, exist_ok=True)

    predictions: list[Prediction] = []
    for source in _iter_inputs(input_dir):
        try:
            extraction = extract(source, cache_dir=cache_dir)
        except Exception as exc:
            predictions.append(
                Prediction(str(source), "待确认", None, None, None, "", "待确认", f"提取失败：{exc}")
            )
            continue
        extraction.source = str(source)
        predictions.append(predict(extraction, name))

    score_report = None
    score_error = None
    if grade_files:
        try:
            grades = read_grade_files(grade_files)
            score_report = calculate_score(predictions, grades, class_max_raw)
        except (GradeInputError, ScoreInputError) as exc:
            # P2 评分失败不阻塞 P1 产出：明细 xlsx 与板块文件夹照常生成，仅评分页跳过。
            score_report = None
            score_error = str(exc)

    excel_path = export_excel(predictions, person_dir / "综测加分明细.xlsx", score_report=score_report)
    organized_dir = organize_files(predictions, person_dir)
    return Report(name, predictions, excel_path, organized_dir, score_report, score_error)
