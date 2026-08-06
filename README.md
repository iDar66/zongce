# 综测加分预测工具 · zongce

> 本地、隐私优先的综测加分 / 总分 / 专项奖学金预估工具。
> 把一整个文件夹的活动证明（PDF / 图片）自动转成一份「综测加分明细.xlsx」——含加分预测、综测总分、可申报专项奖学金预估。

面向每学年要做综合素质测评（综测）与奖学金分析的学生。规则口径对齐《广东技术师范大学综合素质测评管理办法》（详见 [`docs/综测领域规则.md`](docs/综测领域规则.md)，可按本校细则改写）。

---

## 它解决什么问题

手工做综测：把几十张活动证明一张张打开、按姓名筛、归到品德/学业/文体、查细则算加分、套公式算总分、再比对奖学金门槛——又慢又容易漏算。本工具把**能自动化的部分**自动化，算不了的明确标「待人工确认」，每一步都留依据。

## 三期能力

| 期 | 能力 | 产出 |
|---|---|---|
| **P1** 加分预测 | PDF/图片 → OCR → 按姓名筛证明 → 归三板块 → 4 种模式预测加分 | `综测加分明细.xlsx` + 品德/学业/文体/待确认 四个实体文件夹 |
| **P2** 综测总分 | 成绩单 → 基本分 + 附加封顶折算 → 加权合成 | 「综测评分预测」工作表：总分 = 品德×0.20 + 学业×0.65 + 文体×0.15 |
| **P3** 专项奖学金（竞赛类） | 竞赛获奖证明 → 4 门槛判定 + 奖金公式 | 「专项奖学金预估」工作表 |

### 4 种加分模式（P1）

按优先级 `COUNT > GRADE > FIXED > RULE_REF` 自动识别：

- **COUNT 次数型**：陈述含「每场/每次」→ 单次值 × 次数（次数从证明表格坐标还原，失败默认 1 并标注）。
- **GRADE 获奖分级型**：含「一等奖/冠军/第一名…」→ 级别待按《学科竞赛分类表》人工认定，P1 不自动给分（P3 在此之上做奖学金判定）。
- **FIXED 固定值型**：陈述「加 X 分」。
- **RULE_REF 细则参照型**：无数值/名次 → 待人工确认。

### 专项奖学金 4 门槛（P3）

均需通过；数据缺失标「待确认」（不是「不通过」）：

1. **主办方资质**：学会/协会/政府/教指委/大学 → 通过；公司/企业 → 不通过；不明 → 待确认。
2. **获奖比例 ≤ 50%**：从已知库 / 联网公示（可选）/ 用户手填获取。
3. **学校组织备案**。
4. **申报时间**。

奖金公式：`总额 = 国家级基准(元/人) × 级别折算 × 组队系数`；校 C 级不覆盖（综测加分不受影响）。

---

## 安装

Python **3.13+**（开发用 3.14），无需虚拟环境。

```bash
git clone <本仓库地址>
cd 综测加分工具
python -m pip install -r requirements.txt
```

依赖：`pymupdf`（PDF 文字层）、`rapidocr-onnxruntime`（扫描件 OCR，**本地、中文友好**）、`rapidfuzz`（姓名模糊匹配）、`pandas` / `openpyxl`（Excel 读写）、`pytest`。

## 用法

### 基础：活动证明 → 加分明细（P1）

```bash
python -m zongce.cli <姓名> "<证明所在文件夹>" -o "<输出目录>"
```

产出：`<输出目录>/<姓名>/综测加分明细.xlsx` + 品德/学业/文体/待确认 四个文件夹（按预测结果物理复制原件）。

### 加上综测总分（P2）

```bash
python -m zongce.cli <姓名> "<证明文件夹>" \
  --grade-file "<上学期成绩表.xlsx>" \
  --grade-file "<下学期成绩表.xlsx>" \
  -o "<输出目录>"
```

可选 `--academic-class-max-raw` / `--sports-class-max-raw` 传入班级最高 raw（用于折算）；缺省时工具按规则估算并标注来源。

### 加上专项奖学金预估（P3）

```bash
python -m zongce.cli <姓名> "<证明文件夹>" \
  --grade-file "<成绩表.xlsx>" \
  --catalog "<学科竞赛分类表.xls>" \
  --competition-file "<竞赛认定.yaml>" \
  -o "<输出目录>"
```

`--competition-file`（可选）是手填的 YAML，补充组队人数 / 学校组织备案 / 申报时间 / 官网公示 URL / 已知比例等工具无法从证明里读到的信息；缺省时相关门槛标「待确认」。

`--allow-online`（**默认关闭**）：允许 `ratio.py` 联网 GET **公开赛事官网公示页**读获奖/参赛总数算比例。见下方「隐私与联网」。

## 测试

```bash
python -m pytest            # 全量 78 项
```

> 测试用到 5 张真实证明作 fixture（含同学姓名，**已 gitignore，不在仓库内**）。本机首次跑前执行一次 `python tests/populate_fixtures.py` 从本地材料拷入；他机无 fixture 时相关用例自动 skip。

---

## 项目结构

```
zongce/
├─ rules.py        # 板块关键词、模式正则、单次默认值（纯配置）
├─ extract.py      # PDF/图片 → 文字 + 每行 bbox（扫描件走 RapidOCR，按 sha256 缓存）
├─ classify.py     # 4 模式识别 + 板块关键词投票
├─ name_match.py   # 模糊找姓名 + 同列邻近还原次数
├─ predict.py      # 单文件组装加分预测
├─ grades.py       # 成绩表解析与校验            (P2)
├─ score.py        # 综测评分计算引擎            (P2)
├─ catalog.py      # 学科竞赛分类表白名单解析     (P3)
├─ level.py        # 竞赛定级（白名单 + 描述性 + 已知库降级）  (P3)
├─ ratio.py        # 获奖比例获取（已知库 / 联网 / 用户填 / 待确认）  (P3)
├─ scholarship.py  # 4 门槛判定与奖金计算         (P3)
├─ export.py       # 导出 xlsx + 按板块物理复制
├─ pipeline.py     # 端到端串联（P1 → P2 → P3，各段失败相互隔离）
└─ cli.py          # 命令行入口
docs/
├─ 综测领域规则.md                      # 事实口径，改 P2/P3 前必读
└─ superpowers/{specs,plans}/          # 三期的设计文档与实现计划
tests/                                # 单元 + 端到端测试
```

模块依赖单向无环：P1 `rules → extract → classify → name_match → predict → export → pipeline → cli`；P2 `grades/score` 接在 predict 之上；P3 `catalog → level → ratio → scholarship` 接在 pipeline 末段。

## 隐私与联网（重要）

- **全本地**：OCR 走本地 RapidOCR，**不上云、不调云 API**——这是处理同学 PII（姓名 / 学号 / 成绩 / 证明内容）的硬要求。
- **fixture 不入库**：`tests/fixtures/` 含真实证明，已在 `.gitignore`，**绝不提交、绝不外传**。
- **唯一受限联网例外**：仅 `zongce/ratio.py` 在显式加 `--allow-online`（默认关）时，GET **公开赛事官网公示 URL**，只读获奖/参赛总数算比例；**仅公开赛事数据，绝不传输任何学生 PII**；GET-only、不 POST、不提交表单；失败返回 `None` 不崩。除此之外任何模块不联网。

## 设计文档

- 领域规则：[`docs/综测领域规则.md`](docs/综测领域规则.md)
- P1 设计：[`docs/superpowers/specs/2026-08-03-综测加分预测工具-design.md`](docs/superpowers/specs/2026-08-03-综测加分预测工具-design.md)
- P2 设计 / 计划：[`specs/2026-08-03-P2-score-engine-design.md`](docs/superpowers/specs/2026-08-03-P2-score-engine-design.md) · [`plans/2026-08-03-P2-score-engine.md`](docs/superpowers/plans/2026-08-03-P2-score-engine.md)
- P3 设计 / 计划：[`specs/2026-08-05-P3-scholarship-design.md`](docs/superpowers/specs/2026-08-05-P3-scholarship-design.md) · [`plans/2026-08-05-P3-scholarship.md`](docs/superpowers/plans/2026-08-05-P3-scholarship.md)

## 已知限制

- 真实扫描件里「姓名｜次数」常因 OCR 列分离导致次数还原失败 → 工具走「默认 1 次 + 标注」，自洽但偏保守（详见 `docs/综测领域规则.md`）。
- 已知竞赛库目前仅「五一数学建模竞赛」一条；新增前需先重构匹配逻辑（见 `AGENTS.md` parked follow-up）。
- `ratio.py` 联网解析为启发式（正则命中页面百分比），GBK 公示页 / 无关百分比会失效 → 已用「联网结果须人工核对」+「失败返 None」缓解。

## 协议

[MIT](LICENSE) © 2026 邓达俊
