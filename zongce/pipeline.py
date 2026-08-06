# -*- coding: utf-8 -*-
"""端到端流水线：提取、预测、评分（P2）、专项奖学金判定（P3）、导出。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .catalog import Catalog, Level, load_catalog
from .classify import Mode
from .export import export_excel, organize_files
from .extract import IMG_EXT, PDF_EXT, extract
from .grades import GradeInputError, read_grade_files
from .level import KNOWN_COMPETITIONS, decide_level
from .predict import Prediction, predict
from .ratio import award_ratio
from .scholarship import CompetitionCandidate, ScholarshipItem, evaluate_competition
from .score import ScoreInputError, ScoreReport, calculate_score


@dataclass
class Report:
    name: str
    predictions: list[Prediction]
    excel_path: Path
    organized_dir: Path
    score_report: ScoreReport | None = None
    score_error: str | None = None
    scholarship_items: list[ScholarshipItem] | None = None
    scholarship_error: str | None = None


def _iter_inputs(input_dir: Path):
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in PDF_EXT | IMG_EXT:
            yield path


# ── P3 启发式：从 P1 Prediction 构造 CompetitionCandidate ──────────────────────

# 届数前缀：「第二十三届」「第23届」
_ORDINAL_RE = re.compile(r"第[一二三四五六七八九十百千零\d]+届")
# 奖项词（用于清洗竞赛名 + 识别 award_text）
_AWARD_WORDS = (
    "特等奖", "一等奖", "二等奖", "三等奖", "优秀奖",
    "冠军", "亚军", "季军", "金奖", "银奖", "铜奖",
    "第一名", "第二名", "第三名",
)
# 主办方性质关键词：用于从 OCR 文本启发式找主办方串
_HOST_KEYWORDS = (
    "学会", "协会", "委员会", "教指委", "科协", "文联",
    "大学", "学院", "中心", "厅", "部", "政府",
)


def _clean_competition_name(stem: str) -> str:
    """从文件名 stem 启发式清洗出竞赛核心名（去届数前缀 + 末尾奖项词）。

    五一示例：「第二十三届五一数学建模竞赛三等奖」→「五一数学建模竞赛」。
    清洗后为空则原样返回 stem（保证已知库 alias 子串仍能命中）。
    """
    name = _ORDINAL_RE.sub("", stem)
    for w in _AWARD_WORDS:
        if name.endswith(w):
            name = name[: -len(w)]
    name = name.strip()
    return name or stem


def _extract_host(basis: str) -> str:
    """从 OCR 证据文本启发式找含主办方性质关键词的片段。

    找到关键词后向左取最多 20 字符作为主办方名片段；找不到返回空串
    （evaluate_competition 会把空 host 判为「待确认」，可接受）。
    """
    for kw in _HOST_KEYWORDS:
        idx = basis.find(kw)
        if idx >= 0:
            start = max(0, idx - 20)
            end = idx + len(kw)
            return basis[start:end].strip()
    return ""


def _extract_award_text(filename: str, basis: str) -> str:
    """从文件名与 OCR 文本找含奖项词的片段（map_award 会解析为 Award 枚举）。"""
    for w in _AWARD_WORDS:
        if w in filename:
            return w
    for w in _AWARD_WORDS:
        if w in basis:
            return w
    return ""


def _load_competition_overrides(path):
    """best-effort 读认定文件 yaml；无 PyYAML 或读失败 → 各字段 None。

    认定文件字段（若解析到）：组队人数 / 是否学校统一组织备案 / 申报时间范围 /
    官网公示URL / 已知参赛总数或比例。缺省 None。不新增硬依赖。
    """
    empty = {
        "team_size": None,
        "organized_by_school": None,
        "in_time_window": None,
        "url": None,
        "user_ratio": None,
    }
    if not path:
        return empty
    try:
        import yaml  # noqa: F401  — best-effort，环境无 PyYAML 则降级
    except ImportError:
        return empty
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return empty
    return {
        "team_size": data.get("team_size") or data.get("组队人数"),
        "organized_by_school": data.get("organized_by_school", data.get("是否学校统一组织备案")),
        "in_time_window": data.get("in_time_window", data.get("申报时间范围")),
        "url": data.get("url") or data.get("官网公示URL"),
        "user_ratio": data.get("user_ratio") or data.get("已知参赛总数或比例") or data.get("获奖比例"),
    }


def _build_scholarship_items(
    predictions: list[Prediction],
    catalog: Catalog,
    overrides: dict,
    allow_online: bool,
) -> list[ScholarshipItem]:
    """筛学业 GRADE 型 predictions → 构造 candidate → 4 门槛判定 → 收集 items。

    仅处理 panel=="学业" and mode==GRADE 的 predictions（竞赛获奖分级型）。
    """
    items: list[ScholarshipItem] = []
    for pr in predictions:
        if pr.panel != "学业" or pr.mode != Mode.GRADE:
            continue
        filename = Path(pr.file).name
        stem = Path(pr.file).stem
        competition = _clean_competition_name(stem)
        host = _extract_host(pr.basis)
        award_text = _extract_award_text(filename, pr.basis)
        team_size = overrides.get("team_size") or 1
        try:
            team_size = max(1, int(team_size))
        except (ValueError, TypeError):
            # 认定文件写成非数字串（如「3人」）不应炸掉整个 P3 段——降级为单人。
            team_size = 1

        candidate = CompetitionCandidate(
            competition=competition,
            host=host,
            award_text=award_text,
            team_size=team_size,
            source=filename,
        )
        level_d = decide_level(competition, host, catalog, known=KNOWN_COMPETITIONS)
        ratio_r = award_ratio(
            competition,
            online=allow_online,
            url=overrides.get("url"),
            user_ratio=overrides.get("user_ratio"),
        )
        item = evaluate_competition(
            candidate,
            level_d,
            ratio_r,
            organized_by_school=overrides.get("organized_by_school"),
            in_time_window=overrides.get("in_time_window"),
        )
        items.append(item)
    return items


def run_pipeline(
    name: str,
    input_dir,
    output_dir,
    cache_dir=None,
    grade_files=None,
    class_max_raw=None,
    competition_file=None,
    catalog_path=None,
    allow_online=False,
) -> Report:
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

    # P2 评分引擎
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

    # P3 专项奖学金判定：仅当 catalog_path 提供时进入
    scholarship_items = None
    scholarship_error = None
    if catalog_path:
        try:
            try:
                catalog = load_catalog(catalog_path)
            except Exception:
                # 分类表读不出 → 空白名单兜底（描述性路径仍可走）
                catalog = Catalog(whitelist={})
            overrides = _load_competition_overrides(competition_file)
            scholarship_items = _build_scholarship_items(
                predictions, catalog, overrides, allow_online
            )
        except Exception as exc:
            # P3 失败隔离：绝不影响 P1/P2 已有输出（沿用 score_error 兜底风格）
            scholarship_items = None
            scholarship_error = str(exc)

    excel_path = export_excel(
        predictions, person_dir / "综测加分明细.xlsx",
        score_report=score_report, scholarship_items=scholarship_items,
    )
    organized_dir = organize_files(predictions, person_dir)
    return Report(
        name, predictions, excel_path, organized_dir,
        score_report, score_error, scholarship_items, scholarship_error,
    )
