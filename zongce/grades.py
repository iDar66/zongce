# -*- coding: utf-8 -*-
"""读取成绩 Excel 并汇总全年学分加权成绩。"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Sequence

import pandas as pd


REQUIRED_COLUMNS = {"学年", "学期", "课程代码", "课程名称", "学分", "成绩分项", "成绩"}


class GradeInputError(ValueError):
    """成绩文件不满足评分所需结构时抛出。"""


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

    @property
    def course_count(self) -> int:
        return len(self.courses)


def read_grade_files(paths: Sequence[str | Path]) -> GradeSummary:
    """从上下学期成绩表的总评行计算全年加权平均成绩。"""
    courses: list[CourseGrade] = []
    academic_years: set[str] = set()
    semesters: set[int] = set()
    source_files: list[Path] = []

    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            raise GradeInputError(f"成绩文件不存在：{path}")
        frame = pd.read_excel(path)
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise GradeInputError(f"成绩文件缺少列：{', '.join(sorted(missing))}")

        total_rows = frame[frame["成绩分项"].astype(str).str.strip() == "总评"]
        if total_rows.duplicated(subset=["学期", "课程代码"], keep=False).any():
            raise GradeInputError(f"成绩文件有重复总评：{path}")
        for _, row in total_rows.iterrows():
            try:
                credits = float(row["学分"])
                score = float(row["成绩"])
                semester = int(row["学期"])
            except (TypeError, ValueError) as exc:
                raise GradeInputError(f"课程成绩/学分/学期不是数值：{row['课程名称']}") from exc
            if not math.isfinite(credits) or not math.isfinite(score) or credits < 0 or score < 0:
                raise GradeInputError(f"课程成绩或学分不是有效数值：{row['课程名称']}")
            academic_years.add(str(row["学年"]).strip())
            semesters.add(semester)
            courses.append(
                CourseGrade(
                    semester=semester,
                    course_code=str(row["课程代码"]),
                    course_name=str(row["课程名称"]),
                    credits=credits,
                    score=score,
                    source=path,
                )
            )
        source_files.append(path)

    if semesters != {1, 2}:
        raise GradeInputError("成绩文件必须包含学期 1 和学期 2")
    if len(academic_years) != 1:
        raise GradeInputError("成绩文件的学年必须一致")

    total_credits = sum(course.credits for course in courses)
    if total_credits <= 0:
        # 全年总学分为 0（如所有总评行学分都填 0）时无法算加权平均，给明确错误而非 ZeroDivisionError
        raise GradeInputError("成绩文件总学分为 0，无法计算加权平均")
    weighted_score = sum(course.credits * course.score for course in courses)
    return GradeSummary(
        academic_year=next(iter(academic_years)),
        courses=tuple(courses),
        total_credits=total_credits,
        weighted_score=weighted_score,
        weighted_average=weighted_score / total_credits,
        source_files=tuple(source_files),
        semesters=tuple(sorted(semesters)),
    )
