# -*- coding: utf-8 -*-
"""
gen_diagrams.py — 为飞书文档生成 3 张确定性配图
==============================================
用 matplotlib 绘制（而非 AI 生图），保证中文文字精准、结构清晰：
  1. images/dir-tree.png      技能目录结构树
  2. images/sm2-flow.png      SM-2 复习调度流程图
  3. images/skill-workflow.png Skill 调用工作流图
统一风格：米白底、墨蓝主色、橙金点缀，带"学习笔记"感。
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
# ---------------------------------------------------------------------------
# 全局风格
# ---------------------------------------------------------------------------
# 项目根目录 = scripts/ 的上一级；图片统一输出到项目根的 images/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
os.makedirs(OUT, exist_ok=True)
# 中文字体（Noto Sans CJK SC）
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSerifCJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
INK = "#1F3864"        # 墨蓝（主色）
BLUE = "#5B8DD9"       # 浅蓝（次级）
GOLD = "#E8A33D"       # 橙金（强调）
LIGHT = "#F7F4EE"      # 米白底
GRAY = "#8A8F98"       # 次要文字
GREEN = "#4C8C6A"      # 成功/记住
RED = "#C0504D"        # 忘记
def box(ax, x, y, w, h, text, fc=LIGHT, ec=INK, fontsize=11, tc=INK,
        lw=1.6, style="round,pad=0.2,rounding_size=0.06", bold=False):
    """画一个圆角矩形 + 文字，返回中心坐标。"""
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=tc, fontweight="bold" if bold else "normal")
    return (x + w / 2, y + h / 2)
def arrow(ax, p1, p2, color=INK, lw=1.8, style="-|>", ms=14):
    """两点间箭头。"""
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms,
                        color=color, lw=lw)
    ax.add_patch(a)
def new_fig(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax
# ---------------------------------------------------------------------------
# 图 1：目录结构树
# ---------------------------------------------------------------------------
def draw_dir_tree():
    fig, ax = new_fig(10, 6.4)
    # 标题
    ax.text(50, 96, "sm2-flashcard-skill 项目结构", ha="center", va="center",
            fontsize=17, color=INK, fontweight="bold")
    ax.plot([18, 82], [92.5, 92.5], color=GOLD, lw=2.5)
    # 目录树（用等宽字体绘制 + 右侧注释）
    mono = {"family": "DejaVu Sans Mono", "size": 12.5}
    note = {"family": ["Noto Sans CJK SC"], "size": 10, "color": GRAY}
    rows = [
        (18, 84, "sm2-flashcard-skill/", True, None),
        (22, 77, "SKILL.md", False, "技能说明书 · AI 助手必读"),
        (22, 70, "scripts/", True, None),
        (26, 63, "sm2.py", False, "SM-2 算法核心（纯函数）"),
        (26, 56, "review.py", False, "命令行入口 add / review / stats"),
        (22, 49, "data/", True, None),
        (26, 42, "deck.json", False, "卡组数据（内置示例卡组）"),
        (26, 35, "review_log.json", False, "复习历史（自动生成）"),
        (22, 28, "references/", True, None),
        (26, 21, "SM2_algorithm.md", False, "算法原理文档"),
        (22, 14, "tests/", True, None),
        (26, 7, "test_sm2.py", False, "单元测试（11 个用例）"),
    ]
    for x, y, label, is_dir, comment in rows:
        ax.text(x, y, label, fontsize=mono["size"], family=mono["family"],
                color=INK if is_dir else "#2E2E2E",
                fontweight="bold" if is_dir else "normal", va="center")
        if comment:
            ax.text(x + 34, y, "← " + comment, fontsize=note["size"],
                    family=note["family"], color=note["color"], va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "dir-tree.png"), bbox_inches="tight")
    plt.close(fig)
# ---------------------------------------------------------------------------
# 图 2：SM-2 复习调度流程图
# ---------------------------------------------------------------------------
def draw_sm2_flow():
    fig, ax = new_fig(11, 9.5)
    ax.text(50, 97.5, "SM-2 一次复习的调度逻辑", ha="center", va="center",
            fontsize=17, color=INK, fontweight="bold")
    ax.plot([18, 82], [94, 94], color=GOLD, lw=2.5)
    bw, bh = 40, 7.5
    cx = 50
    y_start = 86
    # 节点
    n1 = box(ax, cx - bw / 2, y_start, bw, bh, "开始复习今天到期的卡片", fc=LIGHT, bold=True)
    n2 = box(ax, cx - bw / 2, y_start - 10, bw, bh, "自评回忆质量 q（0~5）", fc=LIGHT)
    # 判断框
    dj = box(ax, cx - bw / 2, y_start - 20, bw, bh, "q ≥ 3 ？（记住了吗）", fc="#EAF0FA", ec=BLUE, bold=True)
    # 记住分支（右）
    r1 = box(ax, cx + 2, y_start - 28.5, 40, 8, "记住：repetitions + 1", fc="#EDF6F0", ec=GREEN, tc=GREEN)
    r2 = box(ax, cx + 2, y_start - 38, 40, 8, "间隔推进\n第1次 1天 / 第2次 6天 /\n之后 上次×EF", fc="#EDF6F0", ec=GREEN, tc=GREEN, fontsize=9)
    r3 = box(ax, cx + 2, y_start - 48.5, 40, 8, "更新难度系数\nEF' = EF + (0.1-(5-q)(0.08+(5-q)0.02))", fc="#EDF6F0", ec=GREEN, tc=GREEN, fontsize=9)
    # 忘记分支（左）
    f1 = box(ax, cx - 42, y_start - 28.5, 40, 8, "忘记：回到起点重学", fc="#FBEFEE", ec=RED, tc=RED)
    f2 = box(ax, cx - 42, y_start - 38, 40, 8, "repetitions = 0\n间隔回到 1 天\nEF 保持不变", fc="#FBEFEE", ec=RED, tc=RED, fontsize=9)
    # 汇合
    n3 = box(ax, cx - bw / 2, y_start - 58.5, bw, bh, "写入下次复习日期\ndue = 今天 + interval 天", fc=LIGHT, bold=True)
    n4 = box(ax, cx - bw / 2, y_start - 68.5, bw, bh, "加入待复习队列，完成", fc="#EAF0FA", ec=BLUE)
    # 箭头
    arrow(ax, n1, n2)
    arrow(ax, n2, dj)
    arrow(ax, (dj[0], dj[1] - bh / 2), (cx + 22, y_start - 28.5 + 8), color=GREEN)          # 是 → 记住
    arrow(ax, (dj[0], dj[1] - bh / 2), (cx - 22, y_start - 28.5 + 8), color=RED)            # 否 → 忘记
    arrow(ax, (cx + 22, y_start - 28.5), (cx + 22, y_start - 38 + 8), color=GREEN)
    arrow(ax, (cx + 22, y_start - 38), (cx + 22, y_start - 48.5 + 8), color=GREEN)
    arrow(ax, (cx + 22, y_start - 48.5), (cx + 22, y_start - 58.5), color=GREEN)
    arrow(ax, (cx - 22, y_start - 28.5), (cx - 22, y_start - 38 + 8), color=RED)
    arrow(ax, (cx - 22, y_start - 38), (cx - 22, y_start - 58.5), color=RED)
    arrow(ax, (cx - 22, y_start - 58.5), (cx, y_start - 58.5), color=INK)
    arrow(ax, n3, n4)
    # 判断分支标签
    ax.text(cx + 22, y_start - 23, "是", color=GREEN, fontsize=12, fontweight="bold", ha="center")
    ax.text(cx - 22, y_start - 23, "否", color=RED, fontsize=12, fontweight="bold", ha="center")
    # 底部：间隔推进示意
    ax.text(50, 6.5, "间隔推进示意：1 天 → 6 天 → 15 天 → 38 天（EF=2.5，连续记住）",
            ha="center", va="center", fontsize=11, color=GRAY)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "sm2-flow.png"), bbox_inches="tight")
    plt.close(fig)
# ---------------------------------------------------------------------------
# 图 3：Skill 调用工作流
# ---------------------------------------------------------------------------
def draw_skill_workflow():
    fig, ax = new_fig(11, 7.5)
    ax.text(50, 97, "一个 Skill 是怎么被用起来的", ha="center", va="center",
            fontsize=17, color=INK, fontweight="bold")
    ax.plot([18, 82], [93.5, 93.5], color=GOLD, lw=2.5)
    bw, bh = 44, 8
    cx = 50
    y = 84
    nodes = [
        ("用户：" + "该复习什么了？", LIGHT, INK, False),
        ("AI 助手检索技能库\n（description 命中 sm2-flashcard-skill）", "#EAF0FA", BLUE, True),
        ("读取 SKILL.md 说明书\n（何时用 / 怎么用 / 目录结构）", "#EAF0FA", BLUE, True),
        ("调用 python3 scripts/review.py review", LIGHT, INK, False),
        ("读 deck.json → 今天到期的卡\n交互打分 → 写回 deck.json / review_log.json", "#EAF0FA", BLUE, True),
        ("把复习结果反馈给用户", LIGHT, INK, False),
    ]
    prev = None
    for i, (text, fc, ec, bold) in enumerate(nodes):
        p = box(ax, cx - bw / 2, y - i * 13, bw, bh, text, fc=fc, ec=ec, bold=bold,
                fontsize=10.5)
        if prev:
            arrow(ax, prev, (p[0], p[1] + bh / 2))
        prev = (p[0], p[1] - bh / 2)
    # 侧边说明
    ax.text(8, 70, "关键点", fontsize=12, color=GOLD, fontweight="bold", va="center")
    tips = [
        "① 触发靠 description：写清\n   \"什么时候用\"才能被命中",
        "② 一切以 SKILL.md 为准：\n   它是 AI 的唯一说明书",
        "③ 数据落盘用 JSON：\n   可读、可追溯、可扩展",
    ]
    for i, t in enumerate(tips):
        ax.text(8, 62 - i * 12, t, fontsize=9.5, color=GRAY, va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "skill-workflow.png"), bbox_inches="tight")
    plt.close(fig)
if __name__ == "__main__":
    draw_dir_tree()
    draw_sm2_flow()
    draw_skill_workflow()
    print("已生成：", sorted(os.listdir(OUT)))
