# -*- coding: utf-8 -*-
"""按综测口径计算单个学生的三板块分数和总分。"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from .grades import GradeSummary
from .predict import Prediction


class ScoreInputError(ValueError):
    """评分输入不符合折算规则时抛出。"""


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


def _raw_and_pending(predictions: Sequence[Prediction], panel: str) -> tuple[float, int]:
    selected = [prediction for prediction in predictions if prediction.panel == panel]
    return (
        sum(float(prediction.points) for prediction in selected if prediction.points is not None),
        sum(prediction.points is None for prediction in selected),
    )


def _capped_panel(
    raw: float,
    base: float,
    cap: float,
    pending_count: int,
    actual_denominator: float | None,
) -> PanelScore:
    if actual_denominator is None:
        # 无全班最高 raw 时按封顶值×1.25 作估算分母（P2 design 约定）：假定班最高附加约为
        # 常见个人 raw 的 1.25 倍，让多数人 raw 落在分母以下、折算后接近"直接计入"，同时仍受
        # 下方 cap 封顶约束；拿到真实班最高 raw 后经 class_max_raw 切到实测分支。
        denominator = cap * 1.25
        source = "估算"
    else:
        try:
            denominator = float(actual_denominator)
        except (TypeError, ValueError) as exc:
            raise ScoreInputError("班级最高 raw 分母必须是数值") from exc
        if not math.isfinite(denominator) or denominator < 0:
            raise ScoreInputError("班级最高 raw 分母必须是非负有限数值")
        source = "实测"

    if denominator <= cap:
        additional = min(max(raw, 0.0), cap)
    else:
        additional = min(max(raw / denominator * cap, 0.0), cap)
    return PanelScore(raw, base, cap, additional, base + additional, denominator, source, pending_count)


def calculate_score(
    predictions: Sequence[Prediction],
    grades: GradeSummary,
    class_max_raw: Mapping[str, float] | None = None,
) -> ScoreReport:
    """根据 P1 raw 加分和全年成绩计算综测总分。"""
    class_max_raw = class_max_raw or {}
    moral_raw, moral_pending = _raw_and_pending(predictions, "品德")
    academic_raw, academic_pending = _raw_and_pending(predictions, "学业")
    sports_raw, sports_pending = _raw_and_pending(predictions, "文体")

    moral = PanelScore(moral_raw, 70.0, None, moral_raw, 70.0 + moral_raw, None, "不适用", moral_pending)
    academic = _capped_panel(
        academic_raw, grades.weighted_average * 0.8, 20.0, academic_pending, class_max_raw.get("学业")
    )
    sports = _capped_panel(sports_raw, 60.0, 40.0, sports_pending, class_max_raw.get("文体"))
    total = moral.final * 0.20 + academic.final * 0.65 + sports.final * 0.15
    return ScoreReport(grades, moral, academic, sports, total)
