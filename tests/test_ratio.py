# -*- coding: utf-8 -*-
"""ratio.py 单测：已知库天然过 / 联网 mock / 失败兜底 / 默认不联网。"""
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
