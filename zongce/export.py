# -*- coding: utf-8 -*-
"""导出邓达俊式 xlsx + 按板块物理复制文件。"""
from __future__ import annotations
import shutil
from pathlib import Path
import pandas as pd
from .predict import Prediction
from . import rules

COLUMNS = ["类别", "项目", "级别/明细", "细则依据", "加分", "认定状态", "备注"]
_ORDER = ["品德", "学业", "文体", "待确认"]

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

def export_excel(predictions: list[Prediction], out_path) -> Path:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(_rows(predictions), columns=COLUMNS)
    with pd.ExcelWriter(out_path, engine="openpyxl") as x:
        df.to_excel(x, index=False, sheet_name="综测加分明细")
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
