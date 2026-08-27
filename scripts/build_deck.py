# -*- coding: utf-8 -*-
"""
build_deck.py — 重建内置考研词汇卡组
=====================================
把 data/deck_raw.py 中整理好的考研必考词写入 data/deck.json。
数据来源：《红宝书·考研英语词汇（精缩版）》必考词部分（Unit 2-3 扫描页 OCR 整理）。
词条字段：front(单词) / phonetic(音标) / back(中文释义)。
运行方式：
    python3 scripts/build_deck.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.deck_raw import DECK_RAW  # noqa: E402

DECK_COMMENT = (
    "sm2-flashcard-skill 卡组。字段：front(单词)/phonetic(音标)/"
    "back(释义)/repetitions(连续记住次数)/interval(间隔天)/"
    "ease(难度系数)/due(到期日 ISO 格式)"
)


def build() -> None:
    cards = []
    for front, phonetic, back in DECK_RAW:
        cards.append({
            "front": front,
            "phonetic": phonetic or "",
            "back": back,
            "repetitions": 0,
            "interval": 0,
            "ease": 2.5,
            "due": None,
            "last_reviewed": None,
        })
    data = {"_comment": DECK_COMMENT, "cards": cards}
    path = os.path.join(ROOT, "data", "deck.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已生成 {path}，共 {len(cards)} 个词条。")


if __name__ == "__main__":
    build()
