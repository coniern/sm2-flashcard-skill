# -*- coding: utf-8 -*-
"""
review.py — sm2-flashcard-skill 的命令行入口
============================================
这个文件把 sm2.py 里的纯算法接到真实的"卡组文件"上，
提供三个命令，让人（或 AI 助手）可以直接使用：
    python3 scripts/review.py add    <正面> <背面>   # 添加一张新卡片
    python3 scripts/review.py review                  # 开始今天的复习
    python3 scripts/review.py stats                   # 查看学习统计
数据文件约定（都在 data/ 目录）：
  deck.json          卡片库（front / back / repetitions / interval / ease / due）
  review_log.json    每次复习的历史记录（可追溯、可分析）
设计要点：
  1. 命令参数走 argparse，错误提示友好，AI 助手也能轻易解析输出
  2. 复习支持 --batch 批量模式：把质量分写进文件里，方便自动化/测试/演示
  3. 所有写操作前先备份旧文件，防止中途出错把数据搞丢
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from typing import Any, Dict, List, Optional
# 让脚本能 import 到同目录的 sm2.py（脚本目录加入 sys.path）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sm2 import DEFAULT_EASE, is_due, schedule_card  # noqa: E402
# 项目根目录 = scripts/ 的上一级
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DECK_PATH = os.path.join(DATA_DIR, "deck.json")
LOG_PATH = os.path.join(DATA_DIR, "review_log.json")
BACKUP_SUFFIX = ".bak"
# 卡组文件顶层注释，保存时保留，保证数据结构始终一致
DECK_COMMENT = ("sm2-flashcard-skill 卡组。字段：front(正面)/back(背面)/"
                "repetitions(连续记住次数)/interval(间隔天)/ease(难度系数)/"
                "due(到期日 ISO 格式)")
# ---------------------------------------------------------------------------
# 文件读写（带备份，数据安全优先）
# ---------------------------------------------------------------------------
def _ensure_data_dir() -> None:
    """确保 data/ 目录存在。"""
    os.makedirs(DATA_DIR, exist_ok=True)
def load_json(path: str, default: Any) -> Any:
    """读取 JSON；文件不存在或损坏时返回默认值，而不是崩掉。"""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default
def save_json(path: str, data: Any) -> None:
    """写入 JSON，写之前先把旧文件备份成 .bak。"""
    _ensure_data_dir()
    if os.path.exists(path):
        shutil.copy2(path, path + BACKUP_SUFFIX)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def load_deck() -> List[Dict[str, Any]]:
    """加载卡组。
    兼容两种结构：顶层为 {"_comment": ..., "cards": [...]}（本项目格式），
    或顶层直接是卡片数组。返回统一的卡片列表。
    """
    data = load_json(DECK_PATH, {})
    if isinstance(data, dict):
        cards = data.get("cards", [])
    else:
        cards = data or []
    return cards if isinstance(cards, list) else []
def save_deck(deck: List[Dict[str, Any]]) -> None:
    """保存卡组（保留顶层说明注释，保持文件结构一致）。"""
    save_json(DECK_PATH, {"_comment": DECK_COMMENT, "cards": deck})
def load_log() -> List[Dict[str, Any]]:
    """加载复习历史。"""
    return load_json(LOG_PATH, [])
def append_log(entry: Dict[str, Any]) -> None:
    """追加一条复习记录。"""
    log = load_log()
    log.append(entry)
    save_json(LOG_PATH, log)
# ---------------------------------------------------------------------------
# 命令一：add —— 添加卡片
# ---------------------------------------------------------------------------
def cmd_add(args: argparse.Namespace) -> int:
    """新增一张卡片到卡组。"""
    deck = load_deck()
    # 去重：正面 + 背面完全相同就视为重复，避免误加
    if any(c.get("front") == args.front and c.get("back") == args.back for c in deck):
        print(f"[跳过] 卡片已存在：{args.front} → {args.back}")
        return 0
    card = {
        "front": args.front,
        "back": args.back,
        "repetitions": 0,     # 连续记住的次数
        "interval": 0,        # 当前间隔（天）
        "ease": DEFAULT_EASE, # 难度系数
        "due": None,          # 新卡片立即到期，进今天的复习队列
    }
    deck.append(card)
    save_deck(deck)
    print(f"[已添加] #{len(deck)}  {args.front} → {args.back}")
    return 0
# ---------------------------------------------------------------------------
# 命令二：review —— 开始复习
# ---------------------------------------------------------------------------
def _ask_quality(prompt: str) -> int:
    """交互式问用户：这次回忆质量打几分（0~5）。"""
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 0 <= int(raw) <= 5:
            return int(raw)
        print("请输入 0~5 之间的整数（0=完全忘记，3=勉强想起，5=完美回忆）")
def cmd_review(args: argparse.Namespace) -> int:
    """复习今天到期的卡片。
    交互模式：一张一张出卡，先看正面，回车翻背面，再自评 0~5。
    批量模式（--batch <质量分文件>）：从文件按行读质量分，
    方便自动化测试 / 给 AI 助手演示，也方便一次性补录。
    """
    deck = load_deck()
    due_cards = [c for c in deck if is_due(c)]
    if not due_cards:
        print("今天没有到期的卡片，休息一下吧。")
        return 0
    # 批量模式：从文件读取质量分
    batch_ratings: Optional[List[int]] = None
    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            batch_ratings = [int(line.strip()) for line in f if line.strip()]
        if len(batch_ratings) < len(due_cards):
            print(f"[错误] 批量质量分只有 {len(batch_ratings)} 条，"
                  f"但今天到期 {len(due_cards)} 张")
            return 1
    print(f"今天到期 {len(due_cards)} 张卡片，开始复习：\n")
    reviewed = 0
    for i, card in enumerate(due_cards, 1):
        print(f"〔第 {i}/{len(due_cards)} 张〕正面：{card['front']}")
        if batch_ratings is None:
            input("    （回车查看背面）")
        print(f"    背面：{card['back']}")
        if batch_ratings is not None:
            quality = batch_ratings[reviewed]
            print(f"    [批量] 质量分：{quality}")
        else:
            quality = _ask_quality("    这次回忆质量（0~5）：")
        updated = schedule_card(card, quality)
        # 用 front 定位回 deck 里更新（同一张卡可能因引用关系有多个副本，这里按对象更新）
        for j, c in enumerate(deck):
            if c.get("front") == updated["front"] and c.get("back") == updated["back"]:
                deck[j] = updated
                break
        append_log({
            "time": updated["due"],   # 简化：记录本次调度后的 due 日期
            "front": updated["front"],
            "back": updated["back"],
            "quality": quality,
            "next_interval": updated["interval"],
            "ease": updated["ease"],
        })
        reviewed += 1
        print(f"    → 下次复习：{updated['due']}（间隔 {updated['interval']} 天）\n")
    save_deck(deck)
    print(f"完成！本次共复习 {reviewed} 张，进度已保存。")
    return 0
# ---------------------------------------------------------------------------
# 命令三：stats —— 学习统计
# ---------------------------------------------------------------------------
def cmd_stats(args: argparse.Namespace) -> int:
    """输出学习统计：总数、到期数、已掌握数、平均难度等。"""
    deck = load_deck()
    if not deck:
        print("卡组还是空的，先用 add 命令加卡片吧。")
        return 0
    due = sum(1 for c in deck if is_due(c))
    mastered = sum(1 for c in deck if c.get("repetitions", 0) >= 5)
    avg_ease = sum(c.get("ease", DEFAULT_EASE) for c in deck) / len(deck)
    print("========== 学习统计 ==========")
    print(f"总卡片数    : {len(deck)}")
    print(f"今天到期    : {due}")
    print(f"已掌握(≥5次): {mastered}")
    print(f"平均难度系数: {avg_ease:.2f}")
    print(f"数据文件    : {DECK_PATH}")
    return 0
# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="review.py",
        description="sm2-flashcard-skill：基于 SM-2 算法的间隔重复记忆卡",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_add = sub.add_parser("add", help="添加一张卡片")
    p_add.add_argument("front", help="卡片正面（问题/单词）")
    p_add.add_argument("back", help="卡片背面（答案/释义）")
    p_add.set_defaults(func=cmd_add)
    p_review = sub.add_parser("review", help="复习今天到期的卡片")
    p_review.add_argument("--batch", metavar="FILE",
                          help="批量模式：从文件按行读取质量分 0~5")
    p_review.set_defaults(func=cmd_review)
    p_stats = sub.add_parser("stats", help="查看学习统计")
    p_stats.set_defaults(func=cmd_stats)
    args = parser.parse_args(argv)
    return args.func(args)
if __name__ == "__main__":
    sys.exit(main())
