# P3 专项奖学金（竞赛类）判定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 P1/P2 之上，判定单个学生可申报的普通奖学金（竞赛类），输出每个竞赛的认定级别 / 4 道硬门槛 / 奖金 / 待确认项；五一数模作黄金端到端用例（库内零联网全自动）。

**Architecture:** 新增四个纯计算模块 `catalog.py`（分类表解析）/ `level.py`（定级）/ `ratio.py`（获奖比例 + 受限联网）/ `scholarship.py`（4 门槛 + 奖金）；`pipeline.py` 负责把 P1 的学业-GRADE 证明解析成竞赛候选并串联四模块；`export.py` 新增「专项奖学金预估」sheet。P1/P2 行为与全本地约束不变，仅 `ratio.py` 在显式 `--allow-online` 时联网查公开赛事公示。

**Tech Stack:** Python 3.14、dataclasses、enum、pandas/openpyxl（读 .xls/.xlsx）、stdlib `urllib`（联网）、pytest；不新增第三方依赖。

## Global Constraints

- Python 使用全局 `C:\Python314`，不建 venv。
- P1/P2 旧调用 `run_pipeline(name, input_dir, output_dir, cache_dir=None)` 与 CLI 不传竞赛参数时行为**完全不变**。
- 联网默认关闭；仅 `ratio.award_ratio(online=True)` 时 fetch 公开赛事公示 URL，**禁止传任何学生 PII**。
- 分类表 .xls 与真实认定文件**不进仓库/fixture**；测试用合成工作簿。
- 校 C 无专项奖金标准；定级/比例/门槛缺数据一律标「待确认」，不崩、不静默给 0 或假值。
- 代码风格照搬既有模块：`# -*- coding: utf-8 -*-` + 中文 docstring、`from __future__ import annotations`、dataclass、中文注释说清「为什么」。
- 稳 > 快：交付代码先自跑；用库/API 返回值先 inspect；不可逆操作先确认。

---

### Task 1: catalog.py — 分类表白名单解析

**Files:**
- Create: `zongce/catalog.py`
- Create: `tests/test_catalog.py`

**Interfaces:**
- Consumes: 分类表工作簿（首个 sheet，4 列：序号 / 竞赛名称 / 网址 / 主办单位；按「国家级A类 / 省级A类」等分段行切分，分段行特征是该行仅首列有值且含「类」）。
- Produces: `Level` 枚举、`LevelHit`、`Catalog`、`load_catalog(path)`、`Catalog.lookup(competition, host)`；`DESCRIPTION_KEYWORDS` 常量。供 Task 2 消费。

- [ ] **Step 1: 写失败测试 — 白名单解析 + lookup + 描述关键词常量**

```python
# tests/test_catalog.py
from pathlib import Path
from openpyxl import Workbook
from zongce.catalog import DESCRIPTION_KEYWORDS, Level, load_catalog


def _write_catalog(path: Path, rows: list) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(["序号", "竞赛名称", "网址", "主办单位"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_load_catalog_parses_whitelist_and_matches(tmp_path):
    p = _write_catalog(tmp_path / "catalog.xlsx", [
        ["国家级A类", None, None, None],                                   # 分段行
        ["1", "全国大学生数学建模竞赛", "http://x", "中国工业与应用数学学会"],
        ["省级A类", None, None, None],
        ["1", "广东省大学生数学建模竞赛", "http://y", "中山大学"],
        ["省级B类", None, None, None],
        [None, None, None, "省级B类竞赛：省一级学会组织的全省性竞赛。"],       # 描述行（跳过）
    ])
    cat = load_catalog(p)

    hit = cat.lookup("全国大学生数学建模竞赛", "中国工业与应用数学学会")
    assert hit.level == Level.NATIONAL_A
    assert hit.matched_by == "白名单"

    lower = cat.lookup("广东省大学生数学建模竞赛", "中山大学")
    assert lower.level == Level.PROVINCIAL_A

    miss = cat.lookup("五一数学建模竞赛", "江苏省工业与应用数学学会")
    assert miss.level is None
    assert miss.matched_by == "未匹配"


def test_description_keywords_covers_provincial_b():
    # 描述性匹配的关键词预定义（描述行文字不可靠，不从其动态解析）
    assert "省一级学会" in DESCRIPTION_KEYWORDS[Level.PROVINCIAL_B]
    assert "国家一级学会" in DESCRIPTION_KEYWORDS[Level.NATIONAL_B]
    assert Level.SCHOOL_C in DESCRIPTION_KEYWORDS
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_catalog.py -q`
Expected: FAIL — `zongce.catalog` 尚不存在。

- [ ] **Step 3: 实现 Level 枚举与 Catalog**

```python
# zongce/catalog.py
# -*- coding: utf-8 -*-
"""解析学科竞赛分类表，提供白名单查询与描述性匹配关键词。"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


class Level(enum.Enum):
    """综测竞赛定级序列（专项奖学金只覆盖前六级，校 C 不覆盖）。"""
    WORLD = "世界级"
    NATIONAL_A = "国A"
    NATIONAL_B = "国B"
    PROVINCIAL_A = "省A"
    PROVINCIAL_B = "省B"
    MUNICIPAL = "市级"
    SCHOOL_C = "校C"


# 级别分段标题 → Level 映射（分类表里只有这两段是白名单；其余段为描述性）
_SECTION_LEVEL = {"国家级A类": Level.NATIONAL_A, "省级A类": Level.PROVINCIAL_A}

# 描述性匹配关键词：从分类表各段文字描述提炼，供 level.py 按主办方性质判级
DESCRIPTION_KEYWORDS: dict[Level, tuple[str, ...]] = {
    Level.NATIONAL_B: ("教育部", "教指委", "国家一级学会", "中国科协", "全国学会", "中国文联", "全国文艺家协会"),
    Level.PROVINCIAL_B: ("省级", "省一级学会", "省级教指委", "省级政府部门"),
    Level.SCHOOL_C: ("教务处", "学生处", "团委", "校级", "选拔赛"),
}


@dataclass(frozen=True)
class LevelHit:
    level: Level | None
    matched_by: str  # "白名单" / "未匹配"


@dataclass(frozen=True)
class Catalog:
    whitelist: dict[str, tuple[Level, str]]  # 竞赛名 → (级别, 主办方)

    def lookup(self, competition: str, host: str) -> LevelHit:
        if competition in self.whitelist:
            return LevelHit(self.whitelist[competition][0], "白名单")
        return LevelHit(None, "未匹配")


def load_catalog(path: str | Path) -> Catalog:
    """读分类表，抽取国家级A类/省级A类白名单。其余段为描述性，由 DESCRIPTION_KEYWORDS 覆盖。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"分类表不存在：{path}")
    frame = pd.read_excel(path, header=None)
    whitelist: dict[str, tuple[Level, str]] = {}
    current: Level | None = None
    for _, row in frame.iterrows():
        first = "" if pd.isna(row[0]) else str(row[0]).strip()
        name = "" if pd.isna(row[1]) else str(row[1]).strip()
        # 分段行：首列含「类」、且竞赛名列为空
        if name == "" and "类" in first:
            current = _SECTION_LEVEL.get(first)
            continue
        if current is None or name == "":
            continue
        host = "" if pd.isna(row[3]) else str(row[3]).strip()
        whitelist[name] = (current, host)
    return Catalog(whitelist=whitelist)
```

- [ ] **Step 4: 跑测试确认通过 + 真实表 smoke**

Run: `python -m pytest tests/test_catalog.py -q`
Expected: PASS。

另起一条只读 smoke（不进仓库）确认真实表解析：
```bash
python -c "from zongce.catalog import load_catalog; c=load_catalog(r'D:\综测证明材料\附件1.广东技术师范大学学科竞赛分类表（2026） .xls'); print(len(c.whitelist)); print(c.lookup('全国大学生数学建模竞赛','').level)"
```
Expected: 白名单条目数 ≥ 60；数模 → `Level.NATIONAL_A`。

- [ ] **Step 5: 提交**

```bash
git add zongce/catalog.py tests/test_catalog.py
git commit -m "feat(catalog): 学科竞赛分类表白名单解析"
```

---

### Task 2: level.py — 定级引擎（白名单 + 描述性 + 降一级）

**Files:**
- Create: `zongce/level.py`
- Create: `tests/test_level.py`

**Interfaces:**
- Consumes: Task 1 的 `Level` / `Catalog` / `DESCRIPTION_KEYWORDS`；已知竞赛库（本任务内建的 `KNOWN_COMPETITIONS`）。
- Produces: `LevelDecision`、`decide_level(competition, host, catalog, known=None)`、`KNOWN_COMPETITIONS` 常量、`drop_one_level(level)`。供 Task 4 消费。

- [ ] **Step 1: 写失败测试 — 白名单 / 描述性 / 已知库降级 / 歧义**

```python
# tests/test_level.py
from zongce.catalog import Catalog, DESCRIPTION_KEYWORDS, Level
from zongce.level import KNOWN_COMPETITIONS, LevelDecision, decide_level, drop_one_level


def _empty_catalog() -> Catalog:
    return Catalog(whitelist={})


def test_whitelist_match_returns_national_a():
    cat = Catalog(whitelist={"全国大学生数学建模竞赛": (Level.NATIONAL_A, "中国工业与应用数学学会")})
    d = decide_level("全国大学生数学建模竞赛", "中国工业与应用数学学会", cat)
    assert d.level == Level.NATIONAL_A
    assert d.basis == "白名单"
    assert d.confidence == "高"


def test_descriptive_match_provincial_b_for_province_society():
    # 五一数模主办方=省一级学会 → 描述性命中省B（已知库未提供时）
    d = decide_level("五一数学建模竞赛", "江苏省工业与应用数学学会", _empty_catalog())
    assert d.level == Level.PROVINCIAL_B
    assert d.basis == "描述性"


def test_known_competition_wuyi_drops_to_school_c():
    # 已知库直接给完整路径：五一数模 → 省B → 行业协会主办降一级 → 校C
    d = decide_level("五一数学建模竞赛", "江苏省工业与应用数学学会", _empty_catalog(), known=KNOWN_COMPETITIONS)
    assert d.level == Level.SCHOOL_C
    assert d.confidence == "高"


def test_drop_one_level_sequence():
    assert drop_one_level(Level.NATIONAL_A) == Level.NATIONAL_B
    assert drop_one_level(Level.PROVINCIAL_B) == Level.SCHOOL_C


def test_ambiguous_host_marks_pending():
    d = decide_level("某神秘比赛", "某公司", _empty_catalog())
    assert d.level is None
    assert d.confidence == "低"
    assert "待" in d.note
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_level.py -q`
Expected: FAIL — `zongce.level` 尚不存在。

- [ ] **Step 3: 实现定级引擎**

```python
# zongce/level.py
# -*- coding: utf-8 -*-
"""竞赛定级：已知库 → 白名单 → 主办方性质描述性匹配 → 行业协会降一级。"""
from __future__ import annotations

from dataclasses import dataclass

from .catalog import DESCRIPTION_KEYWORDS, Catalog, Level


# 降级序列（高 → 低）：分类表 5 级（国A>国B>省A>省B>校C）。
# 世界级/市级是「奖金折算档」，不来自分类表定级、不参与「降一级」。
_DROP_ORDER: tuple[Level, ...] = (
    Level.NATIONAL_A, Level.NATIONAL_B,
    Level.PROVINCIAL_A, Level.PROVINCIAL_B, Level.SCHOOL_C,
)


def drop_one_level(level: Level) -> Level:
    """分类表定级序列中退一格；已是最低、或不在此序列（世界/市级）则原样返回。"""
    if level not in _DROP_ORDER:
        return level
    idx = _DROP_ORDER.index(level)
    return _DROP_ORDER[min(idx + 1, len(_DROP_ORDER) - 1)]


# 已知竞赛库：竞赛名 → (主办方关键词, 描述性命中级别, 是否行业协会主办降一级, 最终级别, 说明)
# 首条：五一数模——省一级学会→省B→点名降一级→校C（见综测领域规则.md §3）
KNOWN_COMPETITIONS: dict[str, dict] = {
    "五一数学建模竞赛": {
        "aliases": ("五一数模", "五一数学建模", "五一"),
        "host_keyword": "工业与应用数学学会",
        "base_level": Level.PROVINCIAL_B,
        "drop_one": True,
        "final_level": Level.SCHOOL_C,
        "note": "省一级学会→省B→行业协(学)会主办降一级→校C；综测加分不受影响，专项奖金不覆盖",
    },
}


@dataclass(frozen=True)
class LevelDecision:
    level: Level | None
    basis: str          # "已知库" / "白名单" / "描述性" / "未匹配"
    confidence: str     # "高" / "中" / "低"
    note: str


def _match_known(competition: str, host: str, known) -> dict | None:
    if not known:
        return None
    for key, info in known.items():
        if key in competition or any(a in competition for a in info["aliases"]):
            return info
    return None


def _descriptive_level(host: str) -> Level | None:
    # 按级别从高到低匹配主办方性质关键词；国A/省A 需走白名单，这里只判国B/省B/校C
    for level in (Level.NATIONAL_B, Level.PROVINCIAL_B, Level.SCHOOL_C):
        if any(kw in host for kw in DESCRIPTION_KEYWORDS[level]):
            return level
    return None


def decide_level(competition: str, host: str, catalog: Catalog, known=None) -> LevelDecision:
    """按 已知库 → 白名单 → 描述性 → 降级 的顺序定级。"""
    known_hit = _match_known(competition, host, known)
    if known_hit:
        return LevelDecision(
            level=known_hit["final_level"], basis="已知库",
            confidence="高", note=known_hit["note"],
        )

    white = catalog.lookup(competition, host)
    if white.level is not None:
        return LevelDecision(level=white.level, basis="白名单", confidence="高", note="")

    desc = _descriptive_level(host)
    if desc is None:
        return LevelDecision(level=None, basis="未匹配", confidence="低",
                             note="主办方性质不明，待辅导员认定级别")
    # 行业协(学)会主办且非政府直管 → 降一级（影响奖金序列）
    if "学会" in host and "政府" not in host:
        dropped = drop_one_level(desc)
        return LevelDecision(level=dropped, basis="描述性", confidence="中",
                             note=f"{desc.value} → 行业协(学)会主办降一级 → {dropped.value}")
    return LevelDecision(level=desc, basis="描述性", confidence="中", note="")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_level.py -q`
Expected: 5 项 PASS。

- [ ] **Step 5: 提交**

```bash
git add zongce/level.py tests/test_level.py
git commit -m "feat(level): 竞赛定级引擎（白名单+描述性+降一级）"
```

---

### Task 3: ratio.py — 获奖比例（已知库 / 联网 / 用户填）

**Files:**
- Create: `zongce/ratio.py`
- Create: `tests/test_ratio.py`

**Interfaces:**
- Consumes: `KNOWN_COMPETITIONS`（Task 2）。
- Produces: `RatioResult`、`award_ratio(competition, online=False, url=None, user_ratio=None)`、`_fetch_ratio_from_url(url)`（可被测试 monkeypatch）。供 Task 4 消费。

- [ ] **Step 1: 写失败测试 — 已知库天然过 / 联网 mock / 失败兜底 / 默认不联网**

```python
# tests/test_ratio.py
import pytest
from zongce.ratio import RatioResult, award_ratio


def test_known_competition_wuyi_naturally_under_cap():
    r = award_ratio("五一数学建模竞赛")  # 默认 online=False
    assert r.source == "已知库"
    assert r.ratio < 0.5
    assert r.passes_cap is True


def test_online_fetch_parses_ratio(monkeypatch):
    # mock _fetch_ratio_from_url 返回 0.3
    import zongce.ratio as rm
    monkeypatch.setattr(rm, "_fetch_ratio_from_url", lambda url, timeout=10: 0.3)
    r = award_ratio("某未知竞赛", online=True, url="http://official/results")
    assert r.source == "联网"
    assert r.ratio == pytest.approx(0.3)
    assert r.passes_cap is True


def test_online_fetch_failure_marks_pending(monkeypatch):
    import zongce.ratio as rm
    monkeypatch.setattr(rm, "_fetch_ratio_from_url", lambda url, timeout=10: None)
    r = award_ratio("某未知竞赛", online=True, url="http://official/results")
    assert r.source == "待确认"
    assert r.ratio is None


def test_unknown_offline_marks_pending():
    r = award_ratio("某未知竞赛")  # online=False 且非已知库
    assert r.source == "待确认"
    assert r.ratio is None
    assert "联网" in r.note
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_ratio.py -q`
Expected: FAIL — `zongce.ratio` 尚不存在。

- [ ] **Step 3: 实现比例获取**

```python
# zongce/ratio.py
# -*- coding: utf-8 -*-
"""获奖比例（≤50% 生死线）获取：已知库 → 联网 → 用户填 → 待确认。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .level import KNOWN_COMPETITIONS


CAP = 0.5  # 获奖比例生死线（含 50%，不含优秀奖）


@dataclass(frozen=True)
class RatioResult:
    ratio: float | None          # None 表示未取到
    source: str                  # "已知库" / "联网" / "用户填" / "待确认"
    passes_cap: bool             # ratio is not None and ratio <= CAP
    note: str


def _fetch_ratio_from_url(url: str, timeout: int = 10) -> float | None:
    """fetch 官网公示并尝试解析获奖比例。公示结构各异、不稳定，解析失败返回 None（上层标待确认）。"""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    # 启发式：找形如「2205/5307」或「41.5%」的片段；不可靠则返回 None
    pct = re.search(r"(\d+(?:\.\d+)?)\s*%", html)
    if pct:
        return float(pct.group(1)) / 100
    frac = re.search(r"(\d+)\s*/\s*(\d+)", html)
    if frac:
        return int(frac.group(1)) / int(frac.group(2))
    return None


def award_ratio(
    competition: str,
    online: bool = False,
    url: str | None = None,
    user_ratio: float | None = None,
) -> RatioResult:
    # 1) 用户手填优先（认定文件覆盖）
    if user_ratio is not None:
        return RatioResult(user_ratio, "用户填", user_ratio <= CAP, "")
    # 2) 已知库（五一数模天然过 45% 上限）
    if competition in KNOWN_COMPETITIONS or any(
        competition in k or any(a in competition for a in v["aliases"])
        for k, v in KNOWN_COMPETITIONS.items()
    ):
        return RatioResult(0.45, "已知库", True, "章程规定一/二/三等≤5%/15%/25%，合计≤45%<50%")
    # 3) 联网
    if online and url:
        ratio = _fetch_ratio_from_url(url)
        if ratio is not None:
            return RatioResult(ratio, "联网", ratio <= CAP, "")
        return RatioResult(None, "待确认", False, "联网解析失败，请手填或核对公式")
    # 4) 兜底
    return RatioResult(None, "待确认", False, "未知竞赛，需联网（--allow-online + URL）或手填比例")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_ratio.py -q`
Expected: 4 项 PASS。

- [ ] **Step 5: 提交**

```bash
git add zongce/ratio.py tests/test_ratio.py
git commit -m "feat(ratio): 获奖比例获取（已知库/联网/用户填/待确认）"
```

---

### Task 4: scholarship.py — 4 门槛 + 奖金计算 + 组装

**Files:**
- Create: `zongce/scholarship.py`
- Create: `tests/test_scholarship.py`

**Interfaces:**
- Consumes: Task 2 `LevelDecision` / `Level`；Task 3 `RatioResult`。
- Produces: `Award` 枚举、`CompetitionCandidate`、`ScholarshipItem`、`GATE_*` 常量、`PRIZE_TABLE` / `LEVEL_SCALE` / `team_factor` / `map_award` / `prize_for` / `evaluate_competition`。供 Task 5 消费。

- [ ] **Step 1: 写失败测试 — 奖金公式 / 校C无奖金 / 4门槛 / 奖项映射**

```python
# tests/test_scholarship.py
import pytest
from zongce.catalog import Level
from zongce.level import LevelDecision
from zongce.ratio import RatioResult
from zongce.scholarship import (
    Award, LEVEL_SCALE, PRIZE_TABLE, evaluate_competition, map_award, prize_for, team_factor,
)
from zongce.scholarship import CompetitionCandidate


def test_prize_provincial_b_third_3person_team_800_total():
    # 省B 三等 3 人队 = 800(国三等基准) × 0.5(省) × (3+1)/2 = 800 总额
    total, per = prize_for(Level.PROVINCIAL_B, Award.THIRD, team_size=3)
    assert total == pytest.approx(800.0)
    assert per == pytest.approx(800.0 / 3)


def test_prize_school_c_not_covered():
    total, per = prize_for(Level.SCHOOL_C, Award.THIRD, team_size=3)
    assert total == 0
    assert per == 0


def test_team_factor_boundaries():
    assert team_factor(1) == 1.0
    assert team_factor(2) == pytest.approx(1.5)   # (2+1)/2
    assert team_factor(4) == pytest.approx(2.5)   # (4+1)/2
    assert team_factor(5) == pytest.approx(3.0)   # 5 人及以上 ×3


def test_map_award_keywords():
    assert map_award("荣获一等奖") == Award.FIRST
    assert map_award("冠军") == Award.FIRST
    assert map_award("三等奖") == Award.THIRD
    assert map_award("优秀奖") is None


def test_evaluate_competition_records_gates_and_pending():
    cand = CompetitionCandidate(competition="五一数学建模竞赛", host="江苏省工业与应用数学学会",
                                award_text="三等奖", team_size=3, source="五一.pdf")
    level_d = LevelDecision(level=Level.SCHOOL_C, basis="已知库", confidence="高", note="x")
    ratio_r = RatioResult(ratio=0.45, source="已知库", passes_cap=True, note="")
    item = evaluate_competition(cand, level_d, ratio_r,
                                organized_by_school=True, in_time_window=True)
    assert item.level == Level.SCHOOL_C
    assert item.gates["主办方资质"] == "通过"
    assert item.gates["获奖比例"] == "通过"
    assert item.gates["学校组织备案"] == "通过"
    assert item.gates["申报时间"] == "通过"
    assert item.prize_total == 0  # 校C 不覆盖
    assert item.confidence == "高"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_scholarship.py -q`
Expected: FAIL — `zongce.scholarship` 尚不存在。

- [ ] **Step 3: 实现奖金与门槛**

```python
# zongce/scholarship.py
# -*- coding: utf-8 -*-
"""专项奖学金（竞赛类）4 门槛判定与奖金计算。"""
from __future__ import annotations

import enum
from dataclasses import dataclass

from .catalog import Level
from .level import LevelDecision
from .ratio import RatioResult


class Award(enum.Enum):
    SPECIAL = "特等"
    FIRST = "一等"
    SECOND = "二等"
    THIRD = "三等"


# 管理办法第13条第2款：国家级基准（元/人）
PRIZE_TABLE: dict[Award, float] = {
    Award.SPECIAL: 3000, Award.FIRST: 2000, Award.SECOND: 1500, Award.THIRD: 800,
}

# 级别折算：世界×3、国×1、省×0.5、市×0.25；校C 不覆盖
LEVEL_SCALE: dict[Level, float] = {
    Level.WORLD: 3.0, Level.NATIONAL_A: 1.0, Level.NATIONAL_B: 1.0,
    Level.PROVINCIAL_A: 0.5, Level.PROVINCIAL_B: 0.5, Level.MUNICIPAL: 0.25,
}

# 门槛常量
GATE_HOST = "主办方资质"
GATE_RATIO = "获奖比例"
GATE_ORGANIZED = "学校组织备案"
GATE_TIME = "申报时间"


def team_factor(team_size: int) -> float:
    """组队系数：2-4 人 (n+1)/2；5 人及以上 ×3；个人 1。"""
    if team_size <= 1:
        return 1.0
    if team_size <= 4:
        return (team_size + 1) / 2
    return 3.0


def prize_for(level: Level, award: Award, team_size: int) -> tuple[float, float]:
    """返回 (总额, 人均)。校C/未知奖项 → (0, 0)。"""
    if level == Level.SCHOOL_C or award is None:
        return 0.0, 0.0
    base = PRIZE_TABLE.get(award, 0.0)
    scale = LEVEL_SCALE.get(level, 0.0)
    total = base * scale * team_factor(team_size)
    return total, (total / team_size if team_size > 0 else total)


_AWARD_KEYWORDS = (
    (Award.SPECIAL, ("特等",)),
    (Award.FIRST, ("一等", "冠军", "第一名", "金奖")),
    (Award.SECOND, ("二等", "亚军", "第二名", "银奖")),
    (Award.THIRD, ("三等", "季军", "第三名", "铜奖")),
)


def map_award(text: str) -> Award | None:
    for award, kws in _AWARD_KEYWORDS:
        if any(kw in text for kw in kws):
            return award
    return None


@dataclass(frozen=True)
class CompetitionCandidate:
    competition: str
    host: str
    award_text: str
    team_size: int
    source: str


@dataclass(frozen=True)
class ScholarshipItem:
    competition: str
    award: Award | None
    level: Level | None
    gates: dict[str, str]            # 门槛名 → "通过"/"不通过"/"待确认"
    prize_total: float
    prize_per_capita: float
    confidence: str                  # "高"/"中"/"低"
    pending_notes: list[str]
    source: str


def _gate(value, ok_flag=True) -> str:
    if value is None:
        return "待确认"
    return "通过" if (value if ok_flag else True) else "不通过"


def evaluate_competition(
    candidate: CompetitionCandidate,
    level_decision: LevelDecision,
    ratio_result: RatioResult,
    organized_by_school: bool | None,
    in_time_window: bool | None,
) -> ScholarshipItem:
    award = map_award(candidate.award_text)
    total, per = prize_for(level_decision.level, award, candidate.team_size) if award else (0.0, 0.0)

    # 主办方资质：公司/企业主办不通过；学会/协会/政府/教指委/部门 通过；不明 待确认
    host = candidate.host
    if any(kw in host for kw in ("公司", "企业")):
        host_gate = "不通过"
    elif any(kw in host for kw in ("学会", "协会", "政府", "部", "委员会", "教指委", "大学", "学院")):
        host_gate = "通过"
    else:
        host_gate = "待确认"

    ratio_gate = "通过" if ratio_result.passes_cap else ("不通过" if ratio_result.ratio is not None else "待确认")

    gates = {
        GATE_HOST: host_gate,
        GATE_RATIO: ratio_gate,
        GATE_ORGANIZED: _gate(organized_by_school),
        GATE_TIME: _gate(in_time_window),
    }

    pending = []
    if level_decision.level is None:
        pending.append("级别待辅导员认定")
    if ratio_result.ratio is None:
        pending.append("获奖比例待确认（--allow-online + URL 或手填）")
    if organized_by_school is None:
        pending.append("学校组织备案待确认")
    if in_time_window is None:
        pending.append("申报时间范围待确认")
    if level_decision.level == Level.SCHOOL_C:
        pending.append("校C：专项奖金不覆盖，综测加分不受影响")
    if award is None:
        pending.append(f"奖项未识别：{candidate.award_text}")

    all_decided = all(g != "待确认" for g in gates.values())
    confidence = "高" if (all_decided and level_decision.confidence == "高") else ("中" if all_decided else "低")

    return ScholarshipItem(
        competition=candidate.competition, award=award, level=level_decision.level,
        gates=gates, prize_total=total, prize_per_capita=per,
        confidence=confidence, pending_notes=pending, source=candidate.source,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_scholarship.py -q`
Expected: 5 项 PASS。

- [ ] **Step 5: 提交**

```bash
git add zongce/scholarship.py tests/test_scholarship.py
git commit -m "feat(scholarship): 4门槛判定与奖金计算"
```

---

### Task 5: pipeline / cli / export 接入 + 五一数模端到端

**Files:**
- Modify: `zongce/pipeline.py`
- Modify: `zongce/cli.py`
- Modify: `zongce/export.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_export.py`

**Interfaces:**
- Consumes: Task 1-4 的全部接口。
- Produces: `run_pipeline(..., competition_file=None, catalog_path=None, allow_online=False)`；`Report` 增 `scholarship_items: list[ScholarshipItem] | None = None`；CLI 增 `--competition-file` / `--catalog` / `--allow-online`；export 增「专项奖学金预估」sheet。

- [ ] **Step 1: 写失败测试 — P1/P2 回归不变 + 五一数模端到端产出专项 sheet**

```python
# tests/test_pipeline.py 追加
def test_pipeline_without_competition_args_keeps_p1_p2_output(tmp_path):
    _ensure_all_fixtures()
    report = run_pipeline("邓达俊", FIX, tmp_path, cache_dir=tmp_path / ".cache")
    assert report.scholarship_items is None  # 不传竞赛参数 → 不进 P3


def test_pipeline_wuyi_end_to_end_produces_scholarship_sheet(tmp_path):
    import pandas as pd
    _ensure_all_fixtures()
    catalog_path = "D:/综测证明材料/附件1.广东技术师范大学学科竞赛分类表（2026） .xls"
    # 仅当真实分类表存在时跑（否则 skip）
    import os
    if not os.path.exists(catalog_path):
        import pytest
        pytest.skip("真实分类表不存在，跳过端到端")
    report = run_pipeline(
        "邓达俊", FIX, tmp_path, cache_dir=tmp_path / ".cache",
        catalog_path=catalog_path,
    )
    assert report.scholarship_items is not None
    wuyi = [i for i in report.scholarship_items if "五一" in i.competition or "数学建模" in i.competition]
    assert wuyi, "应识别出五一数模"
    item = wuyi[0]
    assert item.level.name == "SCHOOL_C"  # 五一数模 → 校C
    assert item.gates["获奖比例"] == "通过"
    sheets = pd.ExcelFile(report.excel_path).sheet_names
    assert "专项奖学金预估" in sheets
```

```python
# tests/test_export.py 追加
def test_export_excel_adds_scholarship_sheet_when_items_given(tmp_path):
    import pandas as pd
    from zongce.catalog import Level
    from zongce.scholarship import ScholarshipItem
    from zongce.export import export_excel
    # 复用现有 predictions fixture；这里只验证 sheet 出现
    item = ScholarshipItem(
        competition="五一数学建模竞赛", award=None, level=Level.SCHOOL_C,
        gates={"主办方资质": "通过", "获奖比例": "通过", "学校组织备案": "待确认", "申报时间": "待确认"},
        prize_total=0.0, prize_per_capita=0.0, confidence="中",
        pending_notes=["校C：专项奖金不覆盖"], source="五一.pdf",
    )
    out = export_excel([], tmp_path / "r.xlsx", score_report=None, scholarship_items=[item])
    sheets = pd.ExcelFile(out).sheet_names
    assert "专项奖学金预估" in sheets
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_pipeline.py tests/test_export.py -q`
Expected: 新增 P3 测试 FAIL（接口未存在），P1/P2 旧测试仍 PASS。

- [ ] **Step 3: 实现接入**

`pipeline.py`：
- `Report` 增 `scholarship_items: list[ScholarshipItem] | None = None`。
- `run_pipeline` 增 `competition_file=None, catalog_path=None, allow_online=False`。
- 在 P1 predictions 完成后：若 `catalog_path` 提供，则筛 `panel=="学业" and mode==GRADE` 的 predictions → 对每个构造 `CompetitionCandidate`（竞赛身份/主办方从文件名+陈述启发式或认定文件；五一数模靠 KNOWN_COMPETITIONS alias 命中）→ `decide_level` → `award_ratio(online=allow_online)` → `evaluate_competition` → 收集 `scholarship_items`。
- P3 失败（如分类表读不出）不抛——`scholarship_items=None`，沿用 P2 的 `score_error` 兜底风格，记一条 note。
- 传 `scholarship_items` 给 `export_excel`。

`cli.py`：增 `--competition-file` / `--catalog` / `--allow-online`（`action="store_true"`），透传 pipeline；末尾若 `scholarship_items` 非空打印专项数，若 P3 失败打印提示。

`export.py`：`export_excel(..., scholarship_items=None)`；items 非空时追加「专项奖学金预估」sheet：每行一竞赛（竞赛 / 奖项 / 级别 / 4 门槛 / 奖金总额 / 人均 / 把握度 / 待确认），末尾附互斥叠加提示行。

- [ ] **Step 4: 跑全量 + 五一数模端到端**

Run: `python -m pytest -q`
Expected: P1/P2 全部 PASS + P3 新增 PASS；五一数模端到端（真实分类表在时）非 skip 通过。

另跑真实材料 smoke（不进仓库）：
```bash
python -m zongce.cli 邓达俊 "D:\综测证明材料\大一" -o "D:\综测输出\p3-e2e-20260805" --cache "D:\综测输出\p3-e2e-20260805\.cache" --catalog "D:\综测证明材料\附件1.广东技术师范大学学科竞赛分类表（2026） .xls" --grade-file "D:\综测证明材料\大一\邓达俊2025-2026学年上学期成绩表.xlsx" --grade-file "D:\综测证明材料\大一\邓达俊2025-2026学年下学期成绩表.xlsx"
```
核对输出 xlsx 的「专项奖学金预估」sheet 含五一数模行（级别校C、获奖比例通过、奖金 0、待确认含校C说明）。

- [ ] **Step 5: 提交**

```bash
git add zongce/pipeline.py zongce/cli.py zongce/export.py tests/test_pipeline.py tests/test_export.py
git commit -m "feat(pipeline): 接入专项奖学金判定，五一数模端到端"
```

---

## 验收

- 全量 `pytest` PASS（P1 40 + P2 14 + P3 新增 ≈ 19，约 73 项）。
- 五一数模真实材料端到端：专项奖学金预估 sheet 正确，级别校C、比例通过、奖金 0、待确认项合理。
- P1/P2 输出与行为零回归。
- AGENTS.md 硬约束 #2 补充 P3 联网例外说明（`ratio.py` 仅查公开赛事公示、禁传 PII、默认关闭）。
