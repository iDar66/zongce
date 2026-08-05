# -*- coding: utf-8 -*-
"""导出邓达俊式 xlsx + 按板块物理复制文件。"""
from __future__ import annotations
import shutil
from pathlib import Path
import pandas as pd
from .predict import Prediction
from .scholarship import ScholarshipItem
from .score import ScoreReport
from . import rules

COLUMNS = ["类别", "项目", "级别/明细", "细则依据", "加分", "认定状态", "备注"]
_ORDER = ["品德", "学业", "文体", "待确认"]
SCORE_COLUMNS = ["板块", "raw", "基本分", "折算附加", "最终板块分", "班级最高 raw", "班级最高 raw 来源", "待确认项目"]
SCHOLARSHIP_COLUMNS = [
    "竞赛", "奖项", "级别", "主办方资质", "获奖比例", "学校组织备案", "申报时间",
    "奖金总额", "人均", "把握度", "待确认",
]

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

def _score_rows(report: ScoreReport):
    for name, panel in (("品德", report.moral), ("学业", report.academic), ("文体", report.sports)):
        yield [
            name,
            panel.raw,
            panel.base,
            panel.additional,
            panel.final,
            panel.denominator if panel.denominator is not None else "",
            panel.denominator_source,
            panel.pending_count,
        ]
    yield ["综测总分", "", "", "", report.total, "", "", ""]


def _scholarship_rows(items: list[ScholarshipItem]):
    """每行一竞赛：竞赛/奖项/级别/4门槛/奖金总额/人均/把握度/待确认。"""
    for it in items:
        yield [
            it.competition,
            it.award.value if it.award is not None else "",
            it.level.value if it.level is not None else "",
            it.gates.get("主办方资质", ""),
            it.gates.get("获奖比例", ""),
            it.gates.get("学校组织备案", ""),
            it.gates.get("申报时间", ""),
            it.prize_total,
            it.prize_per_capita,
            it.confidence,
            "；".join(it.pending_notes) if it.pending_notes else "",
        ]
    # 末尾附互斥叠加提示行（管理办法：同一竞赛多奖取最高、不叠加）
    yield ["提示：同一竞赛多奖项取最高、不叠加；专项奖学金互斥，同年仅享一项。"] + [""] * (len(SCHOLARSHIP_COLUMNS) - 1)


def export_excel(
    predictions: list[Prediction],
    out_path,
    score_report: ScoreReport | None = None,
    scholarship_items: list[ScholarshipItem] | None = None,
) -> Path:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(_rows(predictions), columns=COLUMNS)
    with pd.ExcelWriter(out_path, engine="openpyxl") as x:
        df.to_excel(x, index=False, sheet_name="综测加分明细")
        if score_report is not None:
            score_df = pd.DataFrame(_score_rows(score_report), columns=SCORE_COLUMNS)
            score_df.to_excel(x, index=False, sheet_name="综测评分预测")
        if scholarship_items:
            sch_df = pd.DataFrame(_scholarship_rows(scholarship_items), columns=SCHOLARSHIP_COLUMNS)
            sch_df.to_excel(x, index=False, sheet_name="专项奖学金预估")
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
            n = 1                          # 裁决：从 1 起步（brief 原写 seen.get(dst,1) 会得 a_0）
            while True:
                cand = dst.with_name(f"{dst.stem}_{n}{dst.suffix}")
                if not cand.exists() and cand not in seen:
                    dst = cand; break      # 去掉 brief 的 seen[dst]=0（多余）
                n += 1
        seen[dst] = seen.get(dst, 0)
        shutil.copy2(src, dst)
    return out_dir
