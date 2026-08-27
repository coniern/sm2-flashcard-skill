# -*- coding: utf-8 -*-
"""
test_sm2.py — sm2-flashcard-skill 的单元测试
============================================
为什么"成熟"的 Skill 一定要带测试？
因为只有测试能证明：算法是对的、改动不会悄悄把逻辑改坏、
别人（和 AI 助手）clone 下来能一键验证"这东西能跑"。
本文件同时兼容两种运行方式：
    python3 tests/test_sm2.py      # 不需要装 pytest，直接跑
    pytest tests/test_sm2.py       # 装了 pytest 也可以
测试用例覆盖 SM-2 算法的全部关键规则：
  1. 第一次记住 → 间隔 1 天
  2. 第二次记住 → 间隔 6 天
  3. 第三次起 → 上次间隔 × 难度系数
  4. 质量 5 比质量 3 的难度系数涨得更多（复习越顺，间隔放大越快）
  5. 忘记（quality < 3）→ 回到 1 天重学，难度不变
  6. 难度系数有下限 1.3
  7. 卡片到期判断（新卡立即到期 / due 当天到期 / due 未到不到期）
  8. 完整场景：连续 4 次"记住"，间隔正确推进到 15 天
"""
from __future__ import annotations
import datetime as dt
import os
import sys
from typing import List, Tuple
# 让脚本能 import 到 scripts/sm2.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from sm2 import (  # noqa: E402
    DEFAULT_EASE,
    FIRST_INTERVAL,
    MIN_EASE,
    SECOND_INTERVAL,
    adjust_ease,
    is_due,
    next_interval,
    schedule_card,
)
TODAY = dt.date(2026, 8, 27)
def _card(**overrides) -> dict:
    """构造一张测试用卡片，字段可覆盖。"""
    base = {
        "front": "测试正面",
        "back": "测试背面",
        "repetitions": 0,
        "interval": 0,
        "ease": DEFAULT_EASE,
        "due": None,
    }
    base.update(overrides)
    return base
# ---------------------------------------------------------------------------
# 1. 间隔推进规则
# ---------------------------------------------------------------------------
def test_first_remember_interval_is_1():
    """第一次记住：间隔应为 1 天。"""
    c = schedule_card(_card(), quality=4, today=TODAY)
    assert c["interval"] == FIRST_INTERVAL
    assert c["repetitions"] == 1
    assert c["due"] == (TODAY + dt.timedelta(days=1)).isoformat()
def test_second_remember_interval_is_6():
    """第二次记住：间隔应为 6 天。"""
    c = schedule_card(_card(repetitions=1, interval=1), quality=4, today=TODAY)
    assert c["interval"] == SECOND_INTERVAL
    assert c["repetitions"] == 2
def test_third_remember_interval_scales_by_ease():
    """第三次起：间隔 = 上次间隔 × 难度系数。"""
    # 上次间隔 6 天，ease 2.5 → 6 × 2.5 = 15
    c = schedule_card(_card(repetitions=2, interval=6, ease=2.5), quality=4, today=TODAY)
    assert c["interval"] == 15
def test_quality_3_slightly_decreases_ease():
    """质量 3（勉强想起）时难度系数微降（2.5 → 2.36）。"""
    # Δ = 0.1 - (5-3)*(0.08+(5-3)*0.02) = 0.1 - 2*0.12 = -0.14 → 2.36
    assert adjust_ease(2.5, 3) == 2.36
def test_quality_5_increases_ease_more_than_quality_3():
    """质量越高，难度系数涨得越多。"""
    ease_q5 = adjust_ease(2.5, 5)
    ease_q3 = adjust_ease(2.5, 3)
    assert ease_q5 > ease_q3, f"期望 q5 涨更多：q5={ease_q5}, q3={ease_q3}"
# ---------------------------------------------------------------------------
# 2. 忘记规则
# ---------------------------------------------------------------------------
def test_forget_resets_to_start_and_keeps_ease():
    """忘记（quality<3）：repetitions 归零、间隔回 1 天、难度系数不变。"""
    before_ease = 2.5
    c = schedule_card(
        _card(repetitions=3, interval=15, ease=before_ease),
        quality=1, today=TODAY,
    )
    assert c["repetitions"] == 0
    assert c["interval"] == FIRST_INTERVAL
    assert c["ease"] == before_ease
def test_ease_has_floor():
    """难度系数下限 1.3，不会无限变小。"""
    # 连续用很低但 >= 3 的质量分复习，ease 会一直降，但不能低于 1.3
    ease = DEFAULT_EASE
    for _ in range(20):
        ease = adjust_ease(ease, 3)
    assert ease >= MIN_EASE
# ---------------------------------------------------------------------------
# 3. 到期判断
# ---------------------------------------------------------------------------
def test_new_card_is_due():
    """新卡片（无 due）应立即可复习。"""
    assert is_due(_card(), today=TODAY)
def test_due_card_on_same_day_is_due():
    """due 日期 = 今天，应到期。"""
    assert is_due(_card(due=(TODAY - dt.timedelta(days=1)).isoformat()), today=TODAY)
    assert is_due(_card(due=TODAY.isoformat()), today=TODAY)
def test_future_due_card_not_due():
    """due 日期在未来，不应到期。"""
    assert not is_due(_card(due=(TODAY + dt.timedelta(days=1)).isoformat()), today=TODAY)
# ---------------------------------------------------------------------------
# 4. 完整场景：连续 4 次记住
# ---------------------------------------------------------------------------
def test_full_progression_four_remembers():
    """完整推演：一张新卡连续 4 次记住，间隔应为 1 → 6 → 15 → 38。"""
    c = _card()
    intervals: List[int] = []
    for quality in (4, 4, 4, 4):
        c = schedule_card(c, quality=quality, today=TODAY)
        intervals.append(c["interval"])
    assert intervals == [1, 6, 15, 38], f"实际间隔序列：{intervals}"
# ---------------------------------------------------------------------------
# 简易测试运行器（无 pytest 也能跑）
# ---------------------------------------------------------------------------
def _collect_tests() -> List[Tuple[str, callable]]:
    return [(name, fn) for name, fn in globals().items()
            if name.startswith("test_") and callable(fn)]
def main() -> int:
    tests = _collect_tests()
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {name}: {e!r}")
    print(f"\n共 {len(tests)} 个用例，通过 {len(tests) - failed} 个，失败 {failed} 个")
    return 1 if failed else 0
if __name__ == "__main__":
    sys.exit(main())
