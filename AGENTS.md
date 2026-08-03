# AGENTS.md — 给 Codex（接手 agent）的项目指令

> 这是 Codex 桌面版接手本项目时读的第一份文件（等价于 CLAUDE.md）。开始任何工作前先读完本文。

## 这个项目是什么

**综测加分预测工具**——给用户邓达俊（广东技术师范大学 计科/人工智能学院，每个班约 25 人的创学生）做的本地工具，每学年做综测与奖学金分析用。

分三期：
- **P1（已完成）**：PDF/图片活动证明 → 按姓名筛文件 → 归三板块（品德/学业/文体）→ 4 模式预测加分 → 导出「综测加分明细.xlsx」+ 按板块物理复制文件。
- **P2（未开始）**：评分引擎——基本分 + 附加封顶折算 + 总分（口径见下）。
- **P3（未开始）**：奖学金/门槛判定（专项奖学金 4 道门槛等）。

## 当前状态（截至 master = f600708）

- P1 全 7 任务完成，**40/40 测试绿**，已过 opus 最终整分支 review（判「可合入」，无 Critical）。
- 工作分支就是 `master`（无 remote、从不 push）。每次任务经独立 review 后 ff-merge 进 master。
- 全部决策记录、裁决、parked follow-up 在 SDD ledger：`.superpowers/sdd/2026-08-03-P1-pdf-pipeline/progress.md`（**gitignored，但路径固定，改任意模块前先读对应任务的 history 段**）。
- P1 设计/规格：`docs/superpowers/plans/2026-08-03-P1-pdf-pipeline.md`。
- **综测领域口径（P2/P3 的事实依据）**：`docs/综测领域规则.md`——做 P2/P3 前必读。

## 硬约束（必须遵守）

1. **Python 3.14 全局**（`C:\Python314`，`python` 即它），**不建 venv**。依赖已装好：`pymupdf`/`rapidocr-onnxruntime`/`rapidfuzz`/`pandas`/`openpyxl`/`pytest`/`PIL`/`cv2`。
2. **全本地、不联网、不调云 API**——OCR 用本地 RapidOCR，这是隐私硬要求（处理同学 PII）。任何联网/云调用都是违规。
3. **`tests/fixtures/` 含同学 PII**（姓名等）——**gitignored，绝不提交、绝不复制出项目目录**。fixture 靠 `python tests/populate_fixtures.py`（一次性）从 `D:\综测证明材料\大一` 拷 5 个样本进来。
4. **稳 > 快 / 少返工**（用户明确要求，可靠性优先于首次速度）：
   - 交付的代码/脚本，写完自己先跑一遍。
   - 用第三方库/API 返回值，先 `print(type(x))`/看前几项确认结构，再处理。
   - 被质疑时先查证（读代码/查事实）再解释，别先编理由。
   - 不可逆操作（删文件、覆盖重要文件、对外发送）动手前确认。
5. **无 git remote，从不 push**；`master` 是工作分支，直接在上面经 review 合并。
6. **Windows 下 git 的 `LF will be replaced by CRLF` 警告无害**——**不要**加 `.gitattributes` 去"修"它。
7. **代码风格照搬既有模块**：文件头 `# -*- coding: utf-8 -*-` + 中文 docstring；`from __future__ import annotations`；用 `dataclass`；中文注释说清"为什么"；模块职责单一、文件聚焦。

## 怎么跑

```bash
# 装 deps（已装可跳）
python -m pip install -r requirements.txt
# 一次性拷测试 fixture（本机）
python tests/populate_fixtures.py
# 全量测试
python -m pytest
# 真用——把某同学某学年的活动证明文件夹转成综测加分明细
python -m zongce.cli 邓达俊 "D:\综测证明材料\大一" -o "D:\综测输出" --cache "D:\综测输出\.cache"
# 产出：D:\综测输出\邓达俊\综测加分明细.xlsx + 品德/学业/文体/待确认\ 四个文件夹
```

## 架构（P1）

模块链（依赖单向，无环）：`rules → extract → classify → name_match → predict → export → pipeline → cli`。

| 模块 | 职责 | 关键契约 |
|---|---|---|
| `rules.py` | 纯配置：板块关键词、模式正则、单次值默认 | `PANELS`/`PANEL_KEYWORDS`/`STMT_RE`/`COUNT_TOKEN_RE`/`PER_TIME_DEFAULT`/`normalize_panel` |
| `extract.py` | PDF/图片→文字+每行 bbox；扫描件走 RapidOCR(dpi=200)，有文字层走 fitz；按内容 sha256 缓存 | `extract(path,cache_dir=None)->ExtractionResult`；`IMG_EXT/PDF_EXT`；`OcrLine(cx,cy,h)`/`PageResult`/`ExtractionResult(source,pages,text,method,from_cache)` |
| `classify.py` | 4 模式识别 + 板块关键词投票 | `Mode` 枚举、`classify_mode(text)`、`classify_panel(text, filename)` |
| `name_match.py` | 模糊找姓名 + 同列邻近还原次数 | `find_name(extraction, name)->NameMatch(found,count,confidence,context,best_token,best_score)` |
| `predict.py` | 单文件组装加分预测 | `Prediction(file=完整源路径, panel, mode, points, count, basis, status, note)`；`predict(extraction, name)->Prediction` |
| `export.py` | 导出 xlsx + 按板块物理复制 | `export_excel(predictions, out_path)->Path`；`organize_files(predictions, out_dir)->Path` |
| `pipeline.py` | 端到端串联 | `Report(name,predictions,excel_path,organized_dir)`；`run_pipeline(name,input_dir,output_dir,cache_dir=None)->Report` |
| `cli.py` | 命令行入口 | `python -m zongce.cli <姓名> <输入目录> [-o 输出目录] [--cache 缓存目录]` |

### 4 种加分模式（detect 优先级 COUNT > GRADE > FIXED > RULE_REF）
- **COUNT 次数型**：陈述含「每场/每次/场次」→ 单次值 × 次数。
- **GRADE 获奖分级型**：含「一等奖/冠军/第一名…」→ 级别待按《学科竞赛分类表》人工认定，P1 不自动给分。
- **FIXED 固定值型**：陈述「加 X 分」（无数值后板块词时走 classify_panel 关键词兜底，见 predict.py 守卫）。
- **RULE_REF 细则参照型**：无数值/名次 → 待人工确认。

### ⚠️ 已知项目级风险（别当 bug 报）
真实件「同列邻近」次数还原**结构性失效**——OCR 出来姓名与 `(N)` 计数 token 常在不同列（x 重叠=0），`find_name` 拿不到 count → predict 走「次数配对失败→默认 1 次 + note 标注」兜底。canshi/houqin 两个真实件都落这条（points=1.0/0.5 而非 4.0/1.0）。这是 OCR 布局问题，不是阈值问题，调 name_match 的重叠阈值没用。P2 若要更准，可加 `fuzz.partial_ratio` 回流 name_match（见 ledger parked）。

## 下一步建议（P2）

P2 = 评分引擎，加在 P1 的 `Prediction` 列表之上：
1. **基本分**：品德 70、文体 60、学业 = 加权×0.8（学业成绩需新数据源——成绩单，P1 没有）。
2. **附加封顶折算**：学业附加 ≤20、文体附加 ≤40；超上限按 `个人 raw / 班最高 raw × 上限` 折算（需班级最高 raw，新输入）。
3. **总分** = 品德×0.20 + 学业×0.65 + 文体×0.15（各项 100 分制）。

口径全文：`docs/综测领域规则.md`。**P2 涉及成绩单/班级最高分等 P1 没有的数据源，先和用户确认数据从哪来、怎么输入，再设计**（建议先 brainstorm spec，别直接写代码）。

## 已知 parked follow-up（非阻塞，记在 ledger）
- partial_ratio 回流 name_match（短 CJK 姓名拼长行 WRatio 失效）；届时可移除 predict 子串兜底。
- `extract()` 命中缓存时返回 stale `source`——pipeline 层已兜底（pipeline.py 重绑），更稳的修法是挪进 extract()。
- export.py 若干 brief-verbatim 代码风格项（seen→set、三元 setdefault 冗余等）。
- houqin 源 PDF 真实次数待人工核对（工具输出走默认 1，自洽）。
- Streamlit UI（P1 明确推迟）。
