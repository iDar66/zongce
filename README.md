# 综测加分预测工具

本地、隐私、纯规则+OCR 的综测加分预测工具。P1：PDF/图片 → 按姓名筛 → 归板块 → 预测加分 → 导出 xlsx + 4 文件夹。

## 安装
    python -m pip install -r requirements.txt

## 拷测试 fixture（一次性，本机）
    python tests/populate_fixtures.py

## 跑测试
    pytest

## 用
    python -m zongce.cli 邓达俊 "D:\综测证明材料\大一" -o "D:\综测输出"
