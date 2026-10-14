# paper-readnote

把一篇论文 PDF 变成一份中文阅读笔记 PDF —— 一个 Codex skill。

## 产出的笔记长什么样

固定四部分：

1. **摘要 · 框架模型 · 研究思路与方法** —— 中文重写的摘要；框架数据流；模块拆解（含类比）；从问题到方法的推理链；数据/模型/训练/评测的具体做法
2. **图表：关键结论 · 核心公式 · 框架思维导图** —— 结论卡片（结论 → 机制 → 为何如此 → 证据锚点）、关键指标表、核心公式（公式图 + 符号表 + 直观含义 + 作用 + 类比）、整篇框架流程导图
3. **十个问题** —— 只有真读懂这篇论文才答得出来的问题
4. **十个答案** —— 每题 3–6 句，讲机制而不是复述问题，附章节/图表锚点

第 1、2 部分里的淡蓝色圆角框是笔记作者补的**类比**，不是论文原文；论文内容一律带章节或图表锚点。

## 安装

把 `paper-readnote/` 整个目录放进 skills 目录即可：

- Codex：`~/.codex/skills/` 或 `~/.agents/skills/`

也可以用 skill-installer / find-skills 从本仓库安装。

## 用法

给 Codex 一句「用 $paper-readnote 给这篇论文做阅读笔记」并附上 PDF 路径即可。

脚本也能单独跑：

```bash
python scripts/build_readnote.py --extract paper.pdf        # 抽正文，带 ===== [p.N] ===== 页标记
python scripts/build_readnote.py readnote.json -o note.pdf  # 由 JSON 渲染 PDF
python scripts/build_readnote.py --selftest                 # 自检渲染管线
```

内容全部写在 `readnote.json` 里，PDF 随时可重建，不用重读论文。字段就写在自己科研论文文件夹里的一份 JSON 中，格式见 `SKILL.md` 的 JSON schema 一节。

## 依赖

- Python 3.10+，需要 `pypdf`（抽正文）与 `matplotlib`（渲染公式）
- 打印 PDF 需要一个 Chromium 内核浏览器：Edge 或 Chrome，脚本自动探测常见安装路径
- 中文字体：Windows 用 `msyh.ttc`，macOS 用 PingFang，Linux 用 Noto Sans CJK
- 无网络依赖：公式用 matplotlib mathtext 本地渲染，思维导图是纯 CSS 树

## 已知限制

- 公式只支持 matplotlib mathtext 子集：不支持 `\begin{}` 环境、`\bm`、`\bigl`/`\bigr`；`\ge`/`\le` 必须写成 `\geq`/`\leq`。脚本遇到不支持的写法会回退成纯文字并报警告。
- 扫描版 PDF（无文本层）需要先做 OCR。
- 页数随内容变化，例：18 页的论文大约产出 16 页笔记。

## 目录结构

```
paper-readnote/
├── SKILL.md                 # skill 指令：工作流 / JSON schema / 内容规则
├── scripts/
│   └── build_readnote.py    # 抽取、渲染、自检
└── agents/
    └── openai.yaml          # UI 元数据
```