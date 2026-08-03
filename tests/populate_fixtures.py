# -*- coding: utf-8 -*-
"""从 D:\综测证明材料\大一 拷贝 5 个代表性 fixture 到 tests/fixtures（手动跑一次）。"""
import shutil, sys
from pathlib import Path

SRC = Path(r"D:\综测证明材料\大一")
DST = Path(__file__).parent / "fixtures"
DST.mkdir(exist_ok=True)

FILES = [
    "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf",
    "2026河源校区计科杯篮球比赛后勤综测证明(盖章版）.pdf",
    "第二十三届五一数学建模竞赛三等奖.pdf",
    "2026新年音乐会志愿服务活动工作人员证明.pdf",
    "校第一届班BA篮球联赛甲组第三名(校级）.jpg",
]

for name in FILES:
    s = SRC / name
    if not s.exists():
        print(f"[skip] 源不存在: {s}")
        continue
    shutil.copy2(s, DST / name)
    print(f"[ok] {name}")
print("done ->", DST)
