# AGENTS.md — 给 Codex（接手 agent）的项目指令

> 这是 Codex 桌面版接手本项目时读的第一份文件（等价于 CLAUDE.md）。开始任何工作前先读完本文。

## 这个项目是什么

**综测加分预测工具**——给用户邓达俊（广东技术师范大学 计科/人工智能学院，每个班约 25 人的创学生）做的本地工具，每学年做综测与奖学金分析用。

分三期（**三期均已完成，78 测试绿**）：
- **P1（已完成）**：PDF/图片活动证明 → 按姓名筛文件 → 归三板块（品德/学业/文体）→ 4 模式预测加分 → 导出「综测加分明细.xlsx」+ 按板块物理复制文件。
- **P2（已完成）**：评分引擎——成绩单→基本分 + 附加封顶折算 + 总分（品德×0.20 + 学业×0.65 + 文体×0.15）。模块 `grades.py`/`score.py`，CLI `--grade-file`。
- **P3（已完成）**：专项奖学金（竞赛类）判定——4 门槛（主办方资质 / 获奖比例≤50% / 学校组织备案 / 申报时间）+ 奖金公式 + 五一数模端到端（库内零联网→校C）。模块 `catalog.py`/`level.py`/`ratio.py`/`scholarship.py`，CLI `--catalog`/`--competition-file`/`--allow-online`，导出增「专项奖学金预估」sheet。

## 当前状态（截至 master = 4903997）

- P1/P2/P3 三期均完成，**全量 78 测试绿**；每期都经「每任务独立 review + 整分支 final review」后 ff-merge 进 master，零 Critical/Important。
- 工作分支就是 `master`（无 remote、从不 push）。P1 直接在 master 上做；P2/P3 在独立 git worktree 里做、完成后 ff-merge 回 master。
- SDD ledger（**gitignored、随 worktree 存在，worktree 删了就没**）：主工作树里只有 P1 的 `.superpowers/sdd/2026-08-03-P1-pdf-pipeline/progress.md`；P2/P3 的 ledger 在各自 worktree。**parked follow-up 已沉淀到本文件末尾「已知 parked follow-up」段，不依赖 ledger**。
- 设计/规格/计划（已提交、durable）：`docs/superpowers/specs/`（P2/P3 设计）+ `docs/superpowers/plans/`（P1/P2/P3 实现计划）。
- **综测领域口径**：`docs/综测领域规则.md`——事实依据，改 P2/P3 前必读。

## 硬约束（必须遵守）

1. **Python 3.14 全局**（`C:\Python314`，`python` 即它），**不建 venv**。依赖已装好：`pymupdf`/`rapidocr-onnxruntime`/`rapidfuzz`/`pandas`/`openpyxl`/`pytest`/`PIL`/`cv2`。
2. **全本地、不联网、不调云 API**——OCR 用本地 RapidOCR，这是隐私硬要求（处理同学 PII）。任何联网/云调用都是违规。
   - **P3 唯一受限例外**：`zongce/ratio.py` 的 `_fetch_ratio_from_url` 可在 `online=True`（CLI `--allow-online` 显式开启，默认关）时 GET **公开的赛事官网公示 URL**，仅读获奖/参赛总数算比例。**仅公开赛事数据，绝不传输学生 PII**（姓名/学号/成绩/证明内容）；GET-only、不 POST、不提交表单；失败返回 None 不崩。除此之外任何模块不得联网。详见 `docs/superpowers/specs/2026-08-05-P3-scholarship-design.md` 与 `docs/综测领域规则.md §3`。
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

## 架构

模块链（依赖单向，无环）：
- **P1**：`rules → extract → classify → name_match → predict → export → pipeline → cli`
- **P2**（加在 predict 之上）：`grades`/`score` → 由 `pipeline` 在 P1 predictions 之上算总分
- **P3**（加在 pipeline 末段）：`catalog → level → ratio → scholarship` → `pipeline` 筛学业 GRADE 型 predictions 走 4 门槛判定

P1 模块明细表见下；P2/P3 模块契约见各自 spec/plan 与模块头 docstring。

| 模块 | 职责 | 关键契约 |
|---|---|---|
| `rules.py` | 纯配置：板块关键词、模式正则、单次值默认 | `PANELS`/`PANEL_KEYWORDS`/`STMT_RE`/`COUNT_TOKEN_RE`/`PER_TIME_DEFAULT`/`normalize_panel` |
| `extract.py` | PDF/图片→文字+每行 bbox；扫描件走 RapidOCR(dpi=200)，有文字层走 fitz；按内容 sha256 缓存 | `extract(path,cache_dir=None)->ExtractionResult`；`IMG_EXT/PDF_EXT`；`OcrLine(cx,cy,h)`/`PageResult`/`ExtractionResult(source,pages,text,method,from_cache)` |
| `classify.py` | 4 模式识别 + 板块关键词投票 | `Mode` 枚举、`classify_mode(text)`、`classify_panel(text, filename)` |
| `name_match.py` | 模糊找姓名 + 同列邻近还原次数 | `find_name(extraction, name)->NameMatch(found,count,confidence,context,best_token,best_score)` |
| `predict.py` | 单文件组装加分预测 | `Prediction(file=完整源路径, panel, mode, points, count, basis, status, note)`；`predict(extraction, name)->Prediction` |
| `export.py` | 导出 xlsx + 按板块物理复制 | `export_excel(predictions, out_path)->Path`；`organize_files(predictions, out_dir)->Path` |
| `pipeline.py` | 端到端串联 | `Report(name,predictions,excel_path,organized_dir,score_report,score_error,scholarship_items,scholarship_error)`；`run_pipeline(...,grade_files=None,class_max_raw=None,competition_file=None,catalog_path=None,allow_online=False)->Report` |
| `cli.py` | 命令行入口 | `python -m zongce.cli <姓名> <输入目录> [-o 输出目录] [--cache 缓存目录] [--grade-file ...] [--catalog ...] [--competition-file ...] [--allow-online]` |

### 4 种加分模式（detect 优先级 COUNT > GRADE > FIXED > RULE_REF）
- **COUNT 次数型**：陈述含「每场/每次/场次」→ 单次值 × 次数。
- **GRADE 获奖分级型**：含「一等奖/冠军/第一名…」→ 级别待按《学科竞赛分类表》人工认定，P1 不自动给分；P3 在此之上做专项奖学金判定。
- **FIXED 固定值型**：陈述「加 X 分」（无数值后板块词时走 classify_panel 关键词兜底，见 predict.py 守卫）。
- **RULE_REF 细则参照型**：无数值/名次 → 待人工确认。

### ⚠️ 已知项目级风险（别当 bug 报）
真实件「同列邻近」次数还原**结构性失效**——OCR 出来姓名与 `(N)` 计数 token 常在不同列（x 重叠=0），`find_name` 拿不到 count → predict 走「次数配对失败→默认 1 次 + note 标注」兜底。canshi/houqin 两个真实件都落这条（points=1.0/0.5 而非 4.0/1.0）。这是 OCR 布局问题，不是阈值问题，调 name_match 的重叠阈值没用。要更准，可加 `fuzz.partial_ratio` 回流 name_match（见末尾 parked）。

## 下一步建议（P3 之后）

三期核心功能已完成。可能的后续方向（做之前先和用户确认优先级，别直接写）：
1. **Streamlit UI**（P1 起就推迟）——把 CLI 包成表单，降低非技术用户使用门槛。
2. **扩充已知竞赛库**（`level.py` `KNOWN_COMPETITIONS`）——目前只有「五一数模」一条；加第 2 条（如泰迪杯）前先重构已知库匹配（见末尾 parked：dead fields + 子串方向不一致）。
3. **真实公示页解析鲁棒性**——`ratio.py` 联网解析目前对 GBK 页面/无关百分比会失效（启发式局限，spec 已接受）；如要提升命中率，加编码探测 + 语义定位。
4. **name_match 次数还原**——OCR 布局导致真实件次数常丢（见上「已知项目级风险」），可加 `fuzz.partial_ratio` 回流。

口径全文：`docs/综测领域规则.md`。

## 已知 parked follow-up（非阻塞）

**P1**：
- partial_ratio 回流 name_match（短 CJK 姓名拼长行 WRatio 失效）；届时可移除 predict 子串兜底。
- `extract()` 命中缓存时返回 stale `source`——pipeline 层已兜底（pipeline.py 重绑），更稳的修法是挪进 extract()。
- export.py 若干 brief-verbatim 代码风格项（seen→set、三元 setdefault 冗余等）。
- houqin 源 PDF 真实次数待人工核对（工具输出走默认 1，自洽）。

**P3**（整分支 final review triage 后的可延后项，详见 P3 ledger；合并前必修的 2 条已在 4903997 修复）：
- `level.py` `KNOWN_COMPETITIONS` 的 `host_keyword`/`base_level`/`drop_one` 三字段未被读取（dead data），`_match_known` 的 host 参数也未用——**加第 2 条已知竞赛前必须先处理**（删字段 or 让匹配真正用上 host）。
- 已知库子串匹配方向不一致：`level.py` 用 `key in competition`，`ratio.py` 用 `competition in k`——加第 2 条已知竞赛时统一。
- `ratio.py` 联网解析：正则命中页面任意百分比无语义裁决、decode 硬编码 utf-8（GBK 公示页→乱码→返 None）、user_ratio 无 [0,1] 范围校验（误填 45→4500%）。均已通过 source="联网"→人工核对 + 失败返 None 缓解。
- `pipeline.py` `_HOST_KEYWORDS` 含过宽词「部」「中心」（「部分」「中心思想」误命中 host_gate）；`_clean_competition_name` 只剥一个末尾奖项词。仅影响非已知竞赛。
- `scholarship.py` confidence 语义：当前条件是「4 门槛全有定论 + 级别高信心」，未要求 4 门槛全「通过」——理论上一个不通过 + 三个通过会给「高」。实际不可达（白名单/已知库主办方便然合规），后续可加 `all(g=="通过")` 校验。
- 若干 dead import / 类型标注 drift（catalog.py `Iterable`、pipeline.py `Level`、scholarship.py `prize_for` 标注、`_gate` 的 `ok_flag` 参数）——风格项。
- `ratio.py` `award_ratio` 的 `user_ratio <= CAP` 对 yaml 传字符串（如 `"45%"`）会 TypeError（与已修的 team_size 同类）；同 try/except 兜住、P1/P2 安全，但 UX 差，可加 float coercion。
- Streamlit UI（三期均推迟）。
