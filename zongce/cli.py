# -*- coding: utf-8 -*-
"""命令行入口：python -m zongce.cli <姓名> <输入目录>。"""
from __future__ import annotations

import argparse

from .pipeline import run_pipeline


def main(argv=None):
    parser = argparse.ArgumentParser(prog="zongce", description="综测加分预测工具")
    parser.add_argument("name", help="姓名，例如 邓达俊")
    parser.add_argument("input_dir", help="活动证明所在文件夹（pdf/jpg/png）")
    parser.add_argument("-o", "--output", default="综测输出", help="输出目录，默认 ./综测输出")
    parser.add_argument("--cache", default=None, help="OCR 缓存目录")
    parser.add_argument("--grade-file", action="append", default=None, help="成绩 Excel，可重复传入上下学期文件")
    parser.add_argument("--academic-class-max-raw", type=float, default=None, help="学业班级最高 raw")
    parser.add_argument("--sports-class-max-raw", type=float, default=None, help="文体班级最高 raw")
    parser.add_argument("--competition-file", default=None, help="竞赛认定文件 yaml（组队人数/组织备案/时间窗口/URL/比例）")
    parser.add_argument("--catalog", default=None, help="学科竞赛分类表 Excel，提供后进入 P3 专项奖学金判定")
    parser.add_argument("--allow-online", action="store_true", help="允许联网查公开赛事获奖比例（默认关闭）")
    args = parser.parse_args(argv)

    class_max_raw = {
        panel: value
        for panel, value in (("学业", args.academic_class_max_raw), ("文体", args.sports_class_max_raw))
        if value is not None
    }
    report = run_pipeline(
        args.name,
        args.input_dir,
        args.output,
        cache_dir=args.cache,
        grade_files=args.grade_file,
        class_max_raw=class_max_raw or None,
        competition_file=args.competition_file,
        catalog_path=args.catalog,
        allow_online=args.allow_online,
    )
    automatic = sum(prediction.status == "自动" for prediction in report.predictions)
    print(f"完成：{len(report.predictions)} 个文件，{automatic} 个自动估分")
    print(f"  Excel: {report.excel_path}")
    print(f"  归类:  {report.organized_dir}")
    if report.score_error is not None:
        print(f"  ⚠ 评分页未生成：{report.score_error}（P1 加分明细已正常输出）")
    if report.scholarship_items is not None:
        print(f"  专项奖学金预估：{len(report.scholarship_items)} 项（见专项奖学金预估 sheet）")
    elif report.scholarship_error is not None:
        print(f"  ⚠ 专项奖学金预估未生成：{report.scholarship_error}（P1/P2 已正常输出）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
