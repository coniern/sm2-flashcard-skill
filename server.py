# -*- coding: utf-8 -*-
"""
server.py — sm2-flashcard-skill 的 Web 服务入口
================================================
用 Python 标准库（http.server）实现一个零依赖的本地 Web 服务：
  - 静态托管 web/index.html（简洁美观的背单词 UI）
  - 提供 REST API 完成「复习调度 / 添加词条 / 统计 / 复习历史」
  - 复用 scripts/sm2.py 的 SM-2 核心算法与 data/*.json 数据文件

启动方式：
    python3 server.py              # 默认 http://127.0.0.1:8000
    python3 server.py --port 9000  # 指定端口

设计要点（延续"成熟 Skill"标准）：
  1. 零第三方依赖：http.server + json + threading，clone 即跑
  2. 写操作加线程锁 + 写前备份 .bak：数据安全优先
  3. 数据结构与 CLI 版完全兼容（同一份 deck.json / review_log.json）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# 让脚本能 import 到同目录/scripts 的 sm2.py
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from sm2 import DEFAULT_EASE, is_due, schedule_card  # noqa: E402

DATA_DIR = os.path.join(ROOT, "data")
DECK_PATH = os.path.join(DATA_DIR, "deck.json")
LOG_PATH = os.path.join(DATA_DIR, "review_log.json")
WEB_DIR = os.path.join(ROOT, "web")
BACKUP_SUFFIX = ".bak"

DECK_COMMENT = (
    "sm2-flashcard-skill 卡组。字段：front(正面)/back(背面)/"
    "repetitions(连续记住次数)/interval(间隔天)/ease(难度系数)/"
    "due(到期日 ISO 格式)/last_reviewed(上次复习日期)"
)

# 全局写锁：多线程下保证数据文件读写一致
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# 数据读写（与 CLI 版同一套约定）
# ---------------------------------------------------------------------------
def _ensure_data_dir() -> None:
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
        try:
            shutil.copy2(path, path + BACKUP_SUFFIX)
        except OSError:
            pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_deck() -> List[Dict[str, Any]]:
    """加载卡组，兼容 {cards:[...]} 与裸数组两种结构。"""
    data = load_json(DECK_PATH, {})
    cards = data.get("cards", []) if isinstance(data, dict) else (data or [])
    return cards if isinstance(cards, list) else []


def save_deck(deck: List[Dict[str, Any]]) -> None:
    save_json(DECK_PATH, {"_comment": DECK_COMMENT, "cards": deck})


def load_log() -> List[Dict[str, Any]]:
    return load_json(LOG_PATH, [])


def append_log(entry: Dict[str, Any]) -> None:
    log = load_log()
    log.append(entry)
    # 只保留最近 2000 条，避免日志无限膨胀
    if len(log) > 2000:
        log = log[-2000:]
    save_json(LOG_PATH, log)


# ---------------------------------------------------------------------------
# 业务逻辑
# ---------------------------------------------------------------------------
def _today_str() -> str:
    import datetime as dt
    return dt.date.today().isoformat()


def get_stats() -> Dict[str, Any]:
    """汇总学习统计。"""
    import datetime as dt
    deck = load_deck()
    today = dt.date.today().isoformat()
    due = sum(1 for c in deck if is_due(c, dt.date.today()))
    mastered = sum(1 for c in deck if int(c.get("repetitions", 0)) >= 5)
    learning = len(deck) - mastered
    avg_ease = (sum(float(c.get("ease", DEFAULT_EASE)) for c in deck) / len(deck)
                if deck else 0.0)
    log = load_log()
    # 最近 7 天复习量
    recent = [0] * 7
    for e in log:
        t = e.get("time", "")[:10]
        try:
            diff = (dt.date.fromisoformat(today) - dt.date.fromisoformat(t)).days
        except ValueError:
            continue
        if 0 <= diff < 7:
            recent[6 - diff] += 1
    return {
        "total": len(deck),
        "due": due,
        "mastered": mastered,
        "learning": learning,
        "avg_ease": round(avg_ease, 2),
        "reviewed_today": recent[-1],
        "recent7": recent,
        "today": today,
    }


def get_due_cards(limit: int = 20) -> List[Dict[str, Any]]:
    """今天到期的卡片（按到期时间排序，旧卡优先）。"""
    import datetime as dt
    deck = load_deck()
    due = [c for c in deck if is_due(c, dt.date.today())]
    # 稳定排序：从未复习的（due is None）排前面，已过期的按 overdue 天数排前面
    def _key(c: Dict[str, Any]) -> tuple:
        due_d = c.get("due")
        if due_d is None:
            return (0, 0)
        try:
            days = (dt.date.today() - dt.date.fromisoformat(str(due_d))).days
        except ValueError:
            days = 0
        return (1, -days)
    due.sort(key=_key)
    # 返回给前端时隐藏过长的干扰信息，只留需要渲染的字段
    out = []
    for c in due[:limit]:
        out.append({
            "front": c.get("front", ""),
            "back": c.get("back", ""),
            "repetitions": int(c.get("repetitions", 0)),
            "interval": int(c.get("interval", 0)),
            "ease": float(c.get("ease", DEFAULT_EASE)),
            "due": c.get("due"),
        })
    return out


def review_card(front: str, back: str, quality: int) -> Dict[str, Any]:
    """提交一次复习评分，更新卡组与日志。"""
    import datetime as dt
    quality = int(quality)
    if quality < 0 or quality > 5:
        raise ValueError("quality 必须在 0~5 之间")
    with _lock:
        deck = load_deck()
        idx = next((i for i, c in enumerate(deck)
                    if c.get("front") == front and c.get("back") == back), None)
        if idx is None:
            raise KeyError(f"卡片不存在：{front}")
        old = deck[idx]
        updated = schedule_card(old, quality, today=dt.date.today())
        updated["last_reviewed"] = dt.date.today().isoformat()
        deck[idx] = updated
        save_deck(deck)
        append_log({
            "time": dt.datetime.now().isoformat(timespec="seconds"),
            "front": front,
            "back": back,
            "quality": quality,
            "next_interval": updated["interval"],
            "ease": updated["ease"],
        })
    return {
        "front": front,
        "back": back,
        "quality": quality,
        "repetitions": updated["repetitions"],
        "interval": updated["interval"],
        "ease": updated["ease"],
        "due": updated["due"],
    }


def add_card(front: str, back: str) -> Dict[str, Any]:
    """新增一张卡片（去重）。"""
    front = (front or "").strip()
    back = (back or "").strip()
    if not front or not back:
        raise ValueError("front 与 back 都不能为空")
    with _lock:
        deck = load_deck()
        if any(c.get("front") == front and c.get("back") == back for c in deck):
            raise KeyError(f"卡片已存在：{front}")
        card = {
            "front": front,
            "back": back,
            "repetitions": 0,
            "interval": 0,
            "ease": DEFAULT_EASE,
            "due": None,
            "last_reviewed": None,
        }
        deck.append(card)
        save_deck(deck)
    return {"front": front, "back": back, "index": len(deck)}


def delete_card(front: str) -> Dict[str, Any]:
    """删除一张卡片。"""
    with _lock:
        deck = load_deck()
        new_deck = [c for c in deck if c.get("front") != front]
        if len(new_deck) == len(deck):
            raise KeyError(f"卡片不存在：{front}")
        save_deck(new_deck)
    return {"deleted": front}


def reset_progress() -> Dict[str, Any]:
    """清空所有复习进度（回到初始状态），保留词库。"""
    with _lock:
        deck = load_deck()
        for c in deck:
            c["repetitions"] = 0
            c["interval"] = 0
            c["ease"] = DEFAULT_EASE
            c["due"] = None
            c["last_reviewed"] = None
        save_deck(deck)
        save_json(LOG_PATH, [])
    return {"ok": True, "reset": len(deck)}


def get_all_cards(keyword: str = "") -> List[Dict[str, Any]]:
    """返回全部卡片（含进度），支持按关键词过滤。"""
    deck = load_deck()
    kw = (keyword or "").strip().lower()
    out = []
    for c in deck:
        if kw and kw not in str(c.get("front", "")).lower() \
                and kw not in str(c.get("back", "")).lower():
            continue
        out.append({
            "front": c.get("front", ""),
            "back": c.get("back", ""),
            "repetitions": int(c.get("repetitions", 0)),
            "interval": int(c.get("interval", 0)),
            "ease": float(c.get("ease", DEFAULT_EASE)),
            "due": c.get("due"),
        })
    # 按词头排序，方便浏览
    out.sort(key=lambda c: c["front"].lower())
    return out


def get_history(days: int = 7) -> Dict[str, Any]:
    """复习历史：每天复习次数 + 每次质量分布。"""
    import datetime as dt
    log = load_log()
    today = dt.date.today()
    per_day: Dict[str, Dict[str, Any]] = {}
    for e in log:
        day = e.get("time", "")[:10]
        if not day:
            continue
        try:
            diff = (today - dt.date.fromisoformat(day)).days
        except ValueError:
            continue
        if 0 <= diff < days:
            d = per_day.setdefault(day, {"count": 0, "q": [0] * 6, "mastered": 0})
            d["count"] += 1
            q = int(e.get("quality", 0))
            if 0 <= q <= 5:
                d["q"][q] += 1
            if int(e.get("repetitions", 0)) >= 5:
                d["mastered"] += 1
    return {"days": days, "per_day": per_day, "today": today.isoformat()}


# ---------------------------------------------------------------------------
# HTTP 层
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "sm2-flashcard/1.0"

    # -- 通用工具 ----------------------------------------------------------
    def _send_json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt: str, *args: Any) -> None:
        # 精简日志，避免刷屏
        sys.stderr.write("[server] %s\n" % (fmt % args))

    # -- 路由 ---------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/stats":
            self._send_json({"ok": True, "data": get_stats()})
            return
        if path == "/api/due":
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", ["20"])[0])
            self._send_json({"ok": True, "data": get_due_cards(limit)})
            return
        if path == "/api/cards":
            qs = parse_qs(parsed.query)
            kw = qs.get("q", [""])[0]
            self._send_json({"ok": True, "data": get_all_cards(kw)})
            return
        if path == "/api/history":
            self._send_json({"ok": True, "data": get_history()})
            return
        # 静态文件
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        try:
            if path == "/api/review":
                card = review_card(
                    str(body.get("front", "")),
                    str(body.get("back", "")),
                    int(body.get("quality", -1)),
                )
                self._send_json({"ok": True, "data": card})
                return
            if path == "/api/add":
                card = add_card(str(body.get("front", "")), str(body.get("back", "")))
                self._send_json({"ok": True, "data": card})
                return
            if path == "/api/delete":
                result = delete_card(str(body.get("front", "")))
                self._send_json({"ok": True, "data": result})
                return
            if path == "/api/reset":
                result = reset_progress()
                self._send_json({"ok": True, "data": result})
                return
        except (ValueError, KeyError) as e:
            self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        self._send_json({"ok": False, "error": "not found"}, status=404)

    # -- 静态文件 -----------------------------------------------------------
    def _serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        # 防目录穿越
        rel = os.path.normpath(path.lstrip("/"))
        full = os.path.join(WEB_DIR, rel)
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            self._send_json({"ok": False, "error": "not found"}, status=404)
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="sm2-flashcard-skill Web 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # 首次启动且卡组不存在时，给出提示（避免空库）
    _ensure_data_dir()
    if not os.path.exists(DECK_PATH):
        print("[warn] data/deck.json 不存在，请先放入卡组文件。")
        print("       可运行 scripts/build_deck.py 重建内置词库。")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"sm2-flashcard-skill 已启动：http://{args.host}:{args.port}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
