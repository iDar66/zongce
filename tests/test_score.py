# -*- coding: utf-8 -*-
"""综测评分计算测试。"""
from __future__ import annotations

import pytest

from zongce.grades import GradeSummary
from zongce.predict import Prediction


def _grades() -> GradeSummary:
    return GradeSummary(
        academic_year="2025-2026",
        courses=(),
        total_credits=53.0,
        weighted_score=4559.0,
        weighted_average=86.0,
        source_files=(),
        semesters=(1, 2),
    )


def test_calculate_score_uses_estimated_cap_denominators():
    from zongce.score import calculate_score

    predictions = [
        Prediction("moral.pdf", "品德", None, 3.0, None, "", "自动", ""),
        Prediction("study.pdf", "学业", None, 25.0, None, "", "自动", ""),
        Prediction("sports.pdf", "文体", None, 10.0, None, "", "自动", ""),
    ]

    report = calculate_score(predictions, _grades())

    assert report.moral.final == 73.0
    assert report.academic.additional == 20.0
    assert report.academic.denominator == 25.0
    assert report.academic.denominator_source == "估算"
    assert report.sports.additional == 8.0
    assert report.total == pytest.approx(82.52)


def test_calculate_score_uses_actual_class_maximum_when_provided():
    from zongce.score import calculate_score

    predictions = [
        Prediction("study.pdf", "学业", None, 10.0, None, "", "自动", ""),
        Prediction("sports.pdf", "文体", None, 20.0, None, "", "自动", ""),
    ]

    report = calculate_score(predictions, _grades(), {"学业": 10.0, "文体": 80.0})

    assert report.academic.additional == 10.0
    assert report.academic.denominator_source == "实测"
    assert report.sports.additional == 10.0
    assert report.sports.denominator == 80.0


def test_calculate_score_rejects_negative_actual_class_maximum():
    from zongce.score import ScoreInputError, calculate_score

    with pytest.raises(ScoreInputError, match="分母"):
        calculate_score([], _grades(), {"学业": -1.0})


def test_calculate_score_reports_pending_predictions_by_panel():
    from zongce.score import calculate_score

    report = calculate_score([Prediction("award.pdf", "学业", None, None, None, "", "待确认", "")], _grades())

    assert report.academic.raw == 0.0
    assert report.academic.pending_count == 1


def test_calculate_score_clamps_negative_raw_to_zero():
    from zongce.score import calculate_score

    # 公共 API 层面 points 可能为负；denominator<=cap 分支应把负 raw clamp 到 0，而非给负附加分
    predictions = [Prediction("study.pdf", "学业", None, -5.0, None, "", "自动", "")]
    report = calculate_score(predictions, _grades(), {"学业": 10.0})

    assert report.academic.raw == -5.0
    assert report.academic.additional == 0.0
