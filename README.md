# sm2-flashcard-skill — 间隔重复记忆卡（Web + CLI）
> 一个可直接运行的 **SM-2 间隔重复记忆卡** 技能项目：带简洁美观的 Web UI、
> 完整单元测试和 **131 个考研必考词**（数据来自《红宝书·考研英语词汇（精缩版）》）。
> 既是拿来就能用的背单词工具，也是一份"如何写一个成熟 Skill"的学习资料。
## 它能做什么
人学了东西一定会忘。SM-2 算法会在"快要忘掉的那一刻"自动安排复习，
用最少的复习次数达到长期记忆（Anki 等知名软件正是基于这个算法）。
- **Web 界面**：卡片翻转复习、6 档回忆评分、学习统计、词库管理，界面简洁美观
- **考研词库**：内置 131 个考研必考词（含音标与释义），可继续批量扩充
- **命令行**：零依赖的 `add / review / stats` 三命令，方便脚本化与自动化
- **算法可信**：SM-2 核心算法 + 11 个单元测试，clone 即可一键验证
## 快速开始（无需安装任何第三方依赖）
### 方式一：Web 界面（推荐）
```bash
git clone https://github.com/coniern/sm2-flashcard-skill.git
cd sm2-flashcard-skill
python3 server.py                 # 首次启动自动生成内置词库；默认 http://127.0.0.1:8000
```
浏览器打开 http://127.0.0.1:8000 即可开始复习。数据自动保存在 `data/` 下。
### 方式二：命令行
```bash
# 查看学习统计
python3 scripts/review.py stats
# 添加一张自己的卡片
python3 scripts/review.py add "时间复杂度" "描述算法运行时间随输入规模的增长趋势"
# 开始复习（先看正面，回车翻背面，自评 0~5）
python3 scripts/review.py review
# 跑单元测试，验证算法正确（11 个用例）
python3 tests/test_sm2.py
```
## 目录结构
```
sm2-flashcard-skill/
├── SKILL.md                  # 技能说明书（AI 助手必读）
├── server.py                 # Web 服务（标准库实现，零依赖）
├── scripts/
│   ├── sm2.py                # SM-2 算法核心（纯函数，最易测试）
│   ├── review.py             # CLI 入口：add / review / stats
│   ├── build_deck.py         # 重建内置词库
│   └── deck_raw.py           # 考研必考词原始词表（131 词，含音标）
├── web/
│   └── index.html            # 单页应用 UI（内嵌 CSS/JS，无外部依赖）
├── data/
│   ├── deck.json             # 卡组数据（首次运行自动生成，131 词）
│   └── review_log.json       # 复习历史（自动生成）
├── references/
│   └── SM2_algorithm.md      # 算法原理文档
├── tests/
│   └── test_sm2.py           # 单元测试（11 个用例，覆盖全部算法规则）
└── images/                   # 配图（由 scripts/gen_diagrams.py 生成）
```
## Web 界面功能
| 视图 | 功能 |
|---|---|
| 学习 | 卡片 3D 翻转复习；6 档评分（忘记/很难/勉强/模糊/想起/完美）；实时进度 |
| 统计 | 总词数、今日到期、已掌握、今日已复习；最近 7 天复习量柱状图 |
| 词库 | 搜索、添加单词、删除单词、重置进度；掌握状态一目了然 |
> UI 截图见本地 `images/` 目录（`ui-learn.png` 学习视图、`ui-deck.png` 词库视图）。
> 本地 clone 后可直接 `python3 server.py` 打开体验。
## 核心算法（SM-2）
| 规则 | 说明 |
|---|---|
| 间隔推进 | 第 1 次记住 1 天 → 第 2 次 6 天 → 之后 上次间隔 × 难度系数 |
| 难度系数 EF | 初始 2.5，质量越高涨得越多；下限 1.3 |
| 忘记 | q < 3 时回到起点重学（间隔 1 天），难度不变 |
| 公式 | `EF' = EF + (0.1 - (5-q)×(0.08+(5-q)×0.02))` |
详见 [`references/SM2_algorithm.md`](references/SM2_algorithm.md)。
## 词库数据说明
`data/deck.json`（**首次运行 `python3 server.py` 或 `python3 scripts/build_deck.py` 自动生成**）
内置 131 个考研必考词，整理自《红宝书·考研英语词汇（精缩版）》必考词部分
（Unit 2-3），覆盖 stand / state / com- / dis- / trans- / prim- / liber- / ann-
等考研高频词根词缀词族。每条含：单词、音标、中文释义。词表源码在
`scripts/deck_raw.py`（GitHub 仓库自带，可离线生成词库）。
- 想扩充词库：编辑 `scripts/deck_raw.py`，然后运行 `python3 scripts/build_deck.py`
- 或在 Web「词库」页直接添加单词
## 为什么它是"成熟"的 Skill
- **使用场景广泛**：所有"长期记忆"场景通用，不只针对一种考试
- **逻辑有依据**：SM-2 是被验证几十年的标准算法，可复算
- **能跑通、可验证**：11 个单元测试一键运行；Web + CLI 双入口均可实际使用
- **拿来就用**：内置 131 个真实考研词，开箱即用
- **代码可读**：常量命名、函数文档、数据字段说明齐全
- **数据安全**：写入前自动备份 `.bak`，文件损坏时回退默认值不崩
- **零依赖**：Web 服务用 Python 标准库实现，无任何第三方包
## License
MIT
