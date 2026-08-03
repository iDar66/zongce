# -*- coding: utf-8 -*-
"""命令行入口：python -m zongce.cli <姓名> <输入目录>。"""
from __future__ import annotations

import argparse

from .pipeline import run_pipeline


def main(argv=None):
    parser = argparse.ArgumentParser(prog="zongce", description="综测加分预测工具（P1）")
    parser.add_argument("name", help="姓名，例如 邓达俊")
    parser.add_argument("input_dir", help="活动证明所在文件夹（pdf/jpg/png）")
    parser.add_argument("-o", "--output", default="综测输出", help="输出目录，默认 ./综测输出")
    parser.add_argument("--cache", default=None, help="OCR 缓存目录")
    args = parser.parse_args(argv)

    report = run_pipeline(args.name, args.input_dir, args.output, cache_dir=args.cache)
    automatic = sum(prediction.status == "自动" for prediction in report.predictions)
    print(f"完成：{len(report.predictions)} 个文件，{automatic} 个自动估分")
    print(f"  Excel: {report.excel_path}")
    print(f"  归类:  {report.organized_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
