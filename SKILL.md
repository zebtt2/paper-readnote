---
name: paper-readnote
description: 把一篇论文 PDF 变成一份中文阅读笔记 PDF，固定四部分——①摘要+框架模型+研究思路/研究方法，②图表（关键结论卡片、指标表、核心公式图+符号表+说明）与整篇框架思维导图，③看懂这篇论文才能答出的十个问题，④十个问题的答案。Use when the user hands over a paper PDF (or paper text/link) and asks for 阅读笔记 / 读书笔记 / readnote / 精读总结 / 总结成 PDF / 论文总结，or wants the framework, key formulas, conclusions, mind map and self-test questions as a deliverable PDF. Not for bilingual full-text translation readers (use nature-reader), not for literature search, not for plain single-paragraph summaries.
metadata:
  version: "1.1.1"
---

# Paper Read-Note PDF

Deliver exactly one PDF with four parts, in this order. Chinese prose, English terms kept in brackets on first use.

## Workflow

### 1. Get the text

```bash
python "<SKILL_DIR>/scripts/build_readnote.py" --extract "<paper.pdf>"
```

Writes `<paper>.txt` with `===== [p.N] =====` page markers. Read the whole file before writing anything.

- Scanned PDF (fewer than ~200 chars/page, or text that is noise): stop and tell the user the PDF has no text layer and needs OCR or a text version. Never invent content.
- If the paper is long, read it in chunks but keep page numbers: every claim in the note needs a page/section anchor.

### 2. Write the note spec

Author a `readnote.json` next to the source PDF (schema below). The JSON is the source of truth; all content lives there so the PDF can be rebuilt without re-reading the paper.

### 3. Render the PDF

```bash
python "<SKILL_DIR>/scripts/build_readnote.py" "<readnote.json>" -o "<paper_stem>_readnote.pdf"
```

The script renders formulas to images with matplotlib mathtext, builds the mind map as a CSS tree, prints A4 via headless Edge/Chrome, and reports any formula that fell back to plain text. Fix fallbacks by simplifying the LaTeX, then re-run. matplotlib mathtext is a subset: no `\begin{}` environments, no `\bm`, no `\bigl`/`\bigr`, and `\ge`/`\le` must be written `\geq`/`\leq` (`\ge` is a parse error). Do not hand-write HTML or CSS.

### 4. Verify, then hand over

- `--selftest` proves the toolchain works, not this note. For this note, read the build output: page count is sane, the formula-fallback list is empty, and Parts 3/4 both hold 10 items (the script refuses to build otherwise).
- Report the absolute PDF path, then open it for the user with the app's `open_in_codex` tool (`{"type":"file","path":"<abs path>"}`). The user asked for a PDF back, so never just describe the note in chat.

## JSON schema

```json
{
  "title": "中文标题｜English Title",
  "meta": {"source_pdf": "abs path", "venue_year": "会议或期刊 + 年份，例如 NeurIPS 2024 / arXiv 2501.00001", "task": "一句话任务定义"},
  "part1": {
    "abstract": ["摘要的中文重写，2-4 段"],
    "framework_model": ["框架总览：输入→模块→输出，一段话说清数据流"],
    "framework_analogy": "把整篇框架压成一句话类比（可选，见「类比」一节）",
    "modules": [{"name": "模块名", "role": "它在框架里干什么", "detail": "机制细节、为什么这样做", "analogy": "这个模块像什么（可选）"}],
    "research_approach": ["研究思路：从问题出发的推理链，为什么走这条路，每一步解决了什么"],
    "methods": [{"aspect": "数据/模型/训练/目标函数/评测", "detail": "具体做法与关键设置"}],
    "contributions": ["论文自己宣称的贡献，逐条"]
  },
  "part2": {
    "conclusions": [{"title": "结论短标题", "claim": "一句话结论", "detail": "这条结论怎么来的、意味着什么", "evidence": "Tab.2 / p.5 / Sec 4.3", "why": "为什么会得到这个结果", "analogy": "用一个场景说明它意味着什么（可选）"}],
    "formulas": [{"name": "损失函数/评分/更新式", "latex": "\\mathcal{L}=-\\sum_i y_i\\log p_i", "symbols": [{"sym": "N", "mean": "样本数"}], "intuition": "直观含义", "role": "在框架中的作用与它决定的东西", "analogy": "这个式子像什么（可选）"}],
    "metrics": [{"name": "指标/数据集", "value": "数值", "note": "对比对象或条件"}],
    "mindmap": {"text": "论文一句话核心", "children": [{"text": "第一层模块", "note": "可选短注", "children": [{"text": "子步骤"}]}]}
  },
  "part3": {"questions": [{"q": "问题", "tests": "考的是什么能力"}]},
  "part4": {"answers": [{"a": "答案", "anchor": "Sec 4.2 / Tab.3"}]},
  "glossary": [{"term": "term", "cn": "中文"}]
}
```

Every field accepts a string instead of a list when there is only one item. Omitted optional fields (`modules`, `metrics`, `glossary`, `why`, `tests`, `note`, `analogy`, `framework_analogy`) are simply not rendered — omit rather than pad.

## Content rules

**Grounding.** Every number, dataset name and claim comes from the paper. If something is not stated, write 论文未给出 instead of guessing. Attach `evidence` / `anchor` to claims and answers.

**Part 1.** Abstract is a rewrite, not a translation of the first paragraph. `research_approach` is the part readers cannot get from the abstract: the chain of reasoning from problem to method, including what earlier approaches failed at. `methods` covers data, model, training objective and evaluation protocol in enough detail to reproduce the setup.

**Part 2.** Conclusions are the load-bearing ones (5-8), each with the mechanism behind it, not a restatement of the abstract. Formulas are the ones the paper actually turns on (3-6), typeset in mathtext-compatible LaTeX, with a symbol table for every symbol used and an explanation of what the formula decides — each formula is rendered to an image, so keep it on one line. The mind map is the framework flow: root = the paper's one-sentence idea, then branches for data/architecture/objective/training/evaluation, ending in leaf nodes that are concrete mechanisms rather than section names.

**类比（`analogy` / `framework_analogy`）。** 类比只写在第 1.2/1.3 节、2.1 节和 2.3 节这三处，渲染成淡蓝圆角框——框内文字一律是笔记作者补的类比、不是论文内容，读者靠底色区分来源，所以不逐框加标注。写类比要守两条：写完必须落回机制（一句话说清它在论文里对应哪个组件、哪个量或哪一步），并且必须指出这个类比在哪里失效。只给顺耳的比喻，等于递给读者一个可以复述但不理解的句子。第三、四部分禁止使用类比，那里检验的正是能不能讲出机制。

**Part 3-4.** Exactly 10 questions, 1:1 with 10 answers, same order. Questions must be answerable only after understanding the paper and must cover: motivation and problem setting; the core mechanism; what a key formula or symbol actually means; a design choice and its alternative; the evidence chain in experiments and ablations; interpretation of a counter-intuitive result; generalization or transfer; failure modes and limits. No trivia (author names, exact hyperparameter recall, "what is the title"), no yes/no questions, no questions answerable by reading only the abstract. Answers run 3-6 sentences, state the mechanism rather than restating the question, cite the anchor, and admit uncertainty when the paper is silent.

## Failure modes

- No browser found: tell the user which browser path is missing instead of dumping HTML at them.
- Formula fallback warnings: simplify the LaTeX and re-render; a formula image rendered as plain text is a defect worth one retry.
- `part3`/`part4` length mismatch: the script fails the build on purpose — fix the JSON.