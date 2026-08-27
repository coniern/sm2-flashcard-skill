# -*- coding: utf-8 -*-
"""
sm2.py — SM-2 间隔重复算法核心
================================
这是整个技能最核心、也最值得讲清楚的一个文件。
SM-2 算法（SuperMemo 2，Piotr Wozniak 于 1987 年提出）是后来 Anki、
Mnemosyne 等知名记忆软件所基于的间隔重复算法。它解决一个很朴素的问题：
"人学东西一定会忘，那什么时候复习最省力？"
核心思想一句话：在快要忘掉的那一刻复习，用最少的次数把东西记住。
每次复习你给自己打一个"回忆质量分"（0~5），算法根据这个分数
自动算出下一次该隔多少天再复习。
本文件只做"纯算法"，不碰文件、不碰命令行，
这样它最容易被单元测试覆盖，也最容易讲清楚。
"""
from __future__ import annotations
import datetime as dt
from typing import Any, Dict, Optional
# ---------------------------------------------------------------------------
# 常量（把魔法数字起名字，是"成熟代码"的基本功）
# ---------------------------------------------------------------------------
DEFAULT_EASE = 2.5          # 初始难度系数：每复习一次，下次间隔放大 2.5 倍
MIN_EASE = 1.3              # 难度系数下限：防止间隔越缩越小
EASE_STEP = 0.1             # SM-2 公式里的常量步长
FIRST_INTERVAL = 1          # 第一次复习后的间隔：1 天
SECOND_INTERVAL = 6         # 第二次复习后的间隔：6 天
REMEMBER_THRESHOLD = 3      # 质量分 >= 3 视为"记住了"，>= 3 才推进间隔
MAX_QUALITY = 5             # 质量分上限
def adjust_ease(ease: float, quality: int) -> float:
    """根据本次复习质量调整难度系数（Ease Factor）。
    SM-2 原始公式：
        EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    直觉理解：
      - 质量越高（q 越接近 5），(5-q) 越小，EF 增长越多 → 间隔放大越快 → 复习越省力
      - 质量低（q < 3），EF 保持不变（算法规定忘记时不改难度）
      - 下限 1.3：防止难度无限变小导致每天都要复习
    参数
    ----
    ease : float
        当前难度系数，通常 >= 1.3
    quality : int
        本次回忆质量分，0（完全忘记）~ 5（完美回忆）
    返回
    ----
    float : 调整后的难度系数，不小于 MIN_EASE
    """
    if quality < REMEMBER_THRESHOLD:
        return ease
    delta = EASE_STEP - (MAX_QUALITY - quality) * (
        0.08 + (MAX_QUALITY - quality) * 0.02
    )
    return max(MIN_EASE, round(ease + delta, 2))
def next_interval(interval_days: int, repetitions: int, ease: float, quality: int) -> int:
    """计算本次复习后的下一次间隔（单位：天）。
    SM-2 的间隔规则：
      第 1 次复习：1 天
      第 2 次复习：6 天
      第 n 次复习（n>2）：上次间隔 × 难度系数
      忘记（quality < 3）：回到 1 天，重新学
    参数
    ----
    interval_days : int
        当前卡片的上次间隔（天）
    repetitions : int
        已经连续"记住了"的次数（从 0 开始）
    ease : float
        当前难度系数
    quality : int
        本次质量分
    返回
    ----
    int : 下一次间隔（天）
    """
    if quality < REMEMBER_THRESHOLD:
        return FIRST_INTERVAL
    if repetitions == 0:
        return FIRST_INTERVAL
    if repetitions == 1:
        return SECOND_INTERVAL
    return max(1, round(interval_days * ease))
def schedule_card(card: Dict[str, Any], quality: int,
                  today: Optional[dt.date] = None) -> Dict[str, Any]:
    """更新一张卡片的复习状态（核心调度逻辑）。
    这是一张卡片经过一次复习后的"状态机"：
      quality >= 3（记住）→ repetitions + 1，间隔按规则放大，EF 可能上调
      quality <  3（忘记）→ repetitions 归零，间隔回到 1 天，EF 不变
    参数
    ----
    card : dict
        卡片数据结构，至少包含：front, back, repetitions, interval, ease, due
    quality : int
        本次回忆质量分 0~5
    today : datetime.date
        今天的日期（便于测试时注入固定日期；不传则用系统今天）
    返回
    ----
    dict : 更新后的卡片（会写入 due、repetitions、interval、ease）
    """
    if today is None:
        today = dt.date.today()
    repetitions = int(card.get("repetitions", 0))
    interval = int(card.get("interval", 0))
    ease = float(card.get("ease", DEFAULT_EASE))
    if quality >= REMEMBER_THRESHOLD:
        # 记住了：推进间隔 + 调整难度
        repetitions += 1
        interval = next_interval(interval, repetitions - 1, ease, quality)
        ease = adjust_ease(ease, quality)
    else:
        # 忘记了：回到起点重学，难度不变
        repetitions = 0
        interval = FIRST_INTERVAL
    new_card = dict(card)
    new_card["repetitions"] = repetitions
    new_card["interval"] = interval
    new_card["ease"] = ease
    new_card["due"] = (today + dt.timedelta(days=interval)).isoformat()
    return new_card
def is_due(card: Dict[str, Any], today: Optional[dt.date] = None) -> bool:
    """判断一张卡片今天是否需要复习。
    规则：卡片记录的 due 日期 <= 今天，就该复习。
    新卡片（没有 due 字段）默认立即进入复习队列。
    """
    if today is None:
        today = dt.date.today()
    due = card.get("due")
    if due is None:
        return True
    return dt.date.fromisoformat(due) <= today
