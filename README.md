# sm2-flashcard-skill — 间隔重复记忆卡 Skill
> 一个可直接运行、带完整注释和单元测试的 **SM-2 间隔重复记忆卡** 技能项目。
> 它既是拿来就能用的背词/记概念工具，也是一份"如何写一个成熟 Skill"的学习资料。
## 它能做什么
人学了东西一定会忘。SM-2 算法会在"快要忘掉的那一刻"自动安排复习，
用最少的复习次数达到长期记忆（Anki 等知名软件正是基于这个算法）。
- 随手添加卡片：单词、概念、公式……任何想长期记住的内容
- 每天花几分钟复习"今天到期的"卡片，自评回忆质量 0~5
- 查看学习统计：总卡数、到期数、已掌握数、平均难度
- 内置 8 个考研英语高频词 + 8 个 408 计算机概念卡，克隆即可体验
## 快速开始（无需安装任何第三方依赖）
```bash
git clone https://github.com/coniern/sm2-flashcard-skill.git
cd sm2-flashcard-skill
# 查看示例卡组统计
python3 scripts/review.py stats
# 添加一张自己的卡片
python3 scripts/review.py add "时间复杂度" "描述算法运行时间随输入规模的增长趋势"
# 开始复习（交互式：先看正面，回车翻背面，自评 0~5）
python3 scripts/review.py review
# 跑单元测试，验证算法正确（11 个用例）
python3 tests/test_sm2.py
```
## 目录结构
```
sm2-flashcard-skill/
├── SKILL.md                  # 技能说明书（AI 助手必读，含完整注释）
├── scripts/
│   ├── sm2.py                # SM-2 算法核心（纯函数，最易测试）
│   └── review.py             # 命令行入口：add / review / stats
├── data/
│   ├── deck.json             # 卡组数据（内置示例卡组）
│   └── review_log.json       # 复习历史（自动生成）
├── references/
│   └── SM2_algorithm.md      # 算法原理文档
├── tests/
│   └── test_sm2.py           # 单元测试（11 个用例，覆盖全部算法规则）
└── images/                   # 配图（由 scripts/gen_diagrams.py 生成，可复现）
```
## 核心算法（SM-2）
| 规则 | 说明 |
|---|---|
| 间隔推进 | 第 1 次记住 1 天 → 第 2 次 6 天 → 之后 上次间隔 × 难度系数 |
| 难度系数 EF | 初始 2.5，质量越高涨得越多；下限 1.3 |
| 忘记 | q < 3 时回到起点重学（间隔 1 天），难度不变 |
| 公式 | `EF' = EF + (0.1 - (5-q)×(0.08+(5-q)×0.02))` |
详见 [`references/SM2_algorithm.md`](references/SM2_algorithm.md)。
## 为什么它是"成熟"的 Skill
- **使用场景广泛**：不限于某种考试，所有"长期记忆"场景通用
- **逻辑有依据**：SM-2 是被验证几十年的标准算法，可复算
- **能跑通、可验证**：11 个单元测试一键运行，算法正确性有证明
- **拿来就用**：内置示例卡组 + 3 条命令，零依赖开箱即用
- **代码可读**：常量命名、函数文档、数据字段说明齐全
- **数据安全**：写入前自动备份 `.bak`，文件损坏时回退默认值不崩
- **可扩展**：卡组/日志为纯 JSON，方便接界面、接 AI、换存储
## 如何把这个示例变成你自己的 Skill
1. 复制整个文件夹到你的技能目录（如 `~/.super_doubao/super-doubao-runtime/workspace/skills/`）
2. 改 `SKILL.md` 里的 `name` 和 `description`，描述你的具体使用场景
3. 清空 `data/deck.json` 里的示例卡，用 `add` 命令加入你自己的卡
4. 让 AI 助手读 `SKILL.md`，它就能在你需要复习时自动调用
## License
MIT
