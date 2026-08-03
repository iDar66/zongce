# -*- coding: utf-8 -*-
"""端到端流水线：提取、预测、导出。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .export import export_excel, organize_files
from .extract import IMG_EXT, PDF_EXT, extract
from .predict import Prediction, predict


@dataclass
class Report:
    name: str
    predictions: list[Prediction]
    excel_path: Path
    organized_dir: Path


def _iter_inputs(input_dir: Path):
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in PDF_EXT | IMG_EXT:
            yield path


def run_pipeline(name: str, input_dir, output_dir, cache_dir=None) -> Report:
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

    excel_path = export_excel(predictions, person_dir / "综测加分明细.xlsx")
    organized_dir = organize_files(predictions, person_dir)
    return Report(name, predictions, excel_path, organized_dir)
