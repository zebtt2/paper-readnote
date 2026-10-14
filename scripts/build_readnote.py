#!/usr/bin/env python3
"""Build a 4-part Chinese paper read-note PDF from a JSON spec.

  python build_readnote.py --extract paper.pdf
  python build_readnote.py readnote.json -o readnote.pdf [--keep-html]
  python build_readnote.py --selftest
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    shutil.which("chromium") or "",
    shutil.which("google-chrome") or "",
]
CJK_FONTS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

CSS = """
@page { size: A4; margin: 13mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
       font-size: 10.5pt; line-height: 1.6; color: #1b2430; margin: 0; }
h1 { font-size: 19pt; margin: 0 0 4px; line-height: 1.3; }
.sub { color: #5b6b7d; font-size: 9.5pt; margin-bottom: 10px; }
nav { border: 1px solid #ccd6e2; background: #f6f9fc; border-radius: 5px;
      padding: 8px 12px; font-size: 9.5pt; color: #33465c; margin-bottom: 14px; }
nav b { color: #2f6fb0; }
h2 { font-size: 14pt; color: #123; border-left: 5px solid #2f6fb0;
     padding-left: 9px; margin: 0 0 12px; }
h2.part { page-break-before: always; }
section:first-of-type h2.part { page-break-before: avoid; }
h3 { font-size: 11.5pt; color: #2f6fb0; margin: 16px 0 6px; }
h3:first-child { margin-top: 0; }
p { margin: 5px 0; }
li { margin: 3px 0; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 6px 0; }
th { background: #eef3f9; text-align: left; font-weight: 600; }
th, td { border: 1px solid #ccd6e2; padding: 5px 7px; vertical-align: top; }
td.sym { font-family: Consolas, monospace; white-space: nowrap; width: 1%; }
.card { border: 1px solid #ccd6e2; border-left: 4px solid #2f6fb0; border-radius: 4px;
        padding: 8px 11px; margin: 9px 0; page-break-inside: avoid; }
.card .ct { font-weight: 700; font-size: 10.5pt; }
.card .claim { color: #1d4f80; margin: 3px 0 5px; }
.meta-line { color: #6b7a8c; font-size: 9pt; }
.why { color: #4a5a6c; }
.src { color: #6b7a8c; font-size: 8.5pt; margin-top: 4px; }
.anlg { background: rgba(120, 170, 225, 0.15); border: 1px solid rgba(120, 170, 225, 0.45);
        border-radius: 8px; padding: 6px 10px; margin: 7px 0 3px; color: #626c78;
        font-style: italic; font-size: 9.5pt; line-height: 1.55; }
.fbox { border: 1px solid #ccd6e2; border-radius: 4px; padding: 9px 11px; margin: 10px 0;
        page-break-inside: avoid; }
.fbox .ct { font-weight: 700; font-size: 10.5pt; margin-bottom: 2px; }
img.f { display: block; margin: 6px auto 8px; max-width: 88%; max-height: 130px; }
ul.mm, ul.mm ul { list-style: none; margin: 0; }
ul.mm ul { padding-left: 20px; position: relative; }
ul.mm ul::before { content: ""; position: absolute; left: 7px; top: 2px; bottom: 10px;
                   border-left: 1.4px solid #c3cbd8; }
ul.mm li { position: relative; padding: 2px 0; }
ul.mm ul > li::before { content: ""; position: absolute; left: -13px; top: 14px;
                        width: 13px; border-top: 1.4px solid #c3cbd8; }
.node { display: inline-block; border: 1px solid #9fb4cb; background: #f4f8fc;
        border-radius: 4px; padding: 2px 8px; font-size: 9.5pt; }
.lvl2 > .node { background: #e9f1fa; border-color: #2f6fb0; font-weight: 600; }
.lvl3 > .node { background: #fff; border-color: #b9c6d6; }
.mnote { color: #6b7a8c; font-size: 8.5pt; margin-left: 6px; }
.qa { border-top: 1px dashed #d5dde7; padding-top: 8px; margin-top: 8px; }
.qa .q { font-weight: 700; }
.qa .echo { color: #6b7a8c; font-size: 9pt; }
.ans { margin: 4px 0 0; }
.anchor { color: #6b7a8c; font-size: 8.5pt; margin-top: 3px; }
ol.qlist > li { margin: 7px 0; page-break-inside: avoid; }
.tests { color: #6b7a8c; font-size: 8.5pt; }
"""


def log(*a):
    print(*a, flush=True)


def esc(v):
    return html.escape(str(v), quote=False).replace("\n", "<br>")


def analogy_box(text):
    t = str(text or "").strip()
    return f"<div class='anlg'>{esc(t)}</div>" if t else ""


def items(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def paras(v):
    return "".join(f"<p>{esc(x)}</p>" for x in items(v) if str(x).strip())


def ul(v):
    body = "".join(f"<li>{esc(x)}</li>" for x in items(v) if str(x).strip())
    return f"<ul>{body}</ul>" if body else ""


def ol(v):
    body = "".join(f"<li>{esc(x)}</li>" for x in items(v) if str(x).strip())
    return f"<ol>{body}</ol>" if body else ""


def dict_table(rows, pairs, raw_keys=()):
    """pairs: list of (key, header, css_class); raw_keys hold pre-rendered HTML."""
    rows = items(rows)
    if not rows:
        return ""
    head = "<tr>" + "".join(f"<th>{esc(h)}</th>" for _, h, _ in pairs) + "</tr>"
    body = ""
    for r in rows:
        if not isinstance(r, dict):
            body += f"<tr><td colspan='{len(pairs)}'>{esc(r)}</td></tr>"
            continue
        body += "<tr>" + "".join(
            f"<td{' class=\"sym\"' if cls else ''}>"
            f"{r.get(k, '') if k in raw_keys else esc(r.get(k, ''))}</td>" for k, _, cls in pairs
        ) + "</tr>"
    return f"<table>{head}{body}</table>"


def mindmap(node, level=1):
    if not isinstance(node, dict):
        return f'<li class="lvl{level}"><span class="node">{esc(node)}</span></li>'
    note = f'<span class="mnote">{esc(node["note"])}</span>' if node.get("note") else ""
    kids = items(node.get("children")) + items(node.get("items"))
    inner = ""
    if kids:
        inner = "<ul>" + "".join(mindmap(k, level + 1) for k in kids) + "</ul>"
    return f'<li class="lvl{level}"><span class="node">{esc(node.get("text", ""))}</span>{note}{inner}</li>'


def strip_math(s):
    s = s.strip().strip("$")
    subs = {
        r"\sum": "Σ", r"\prod": "Π", r"\int": "∫", r"\log": "log", r"\ln": "ln",
        r"\exp": "exp", r"\times": "×", r"\cdot": "·", r"\leq": "≤", r"\geq": "≥",
        r"\approx": "≈", r"\in": "∈", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
        r"\lambda": "λ", r"\mu": "μ", r"\sigma": "σ", r"\theta": "θ", r"\pi": "π",
        r"\phi": "φ", r"\mathcal": "", r"\mathrm": "", r"\text": "", r"\left": "",
        r"\right": "", r"\ell": "ℓ", r"\nabla": "∇", r"\partial": "∂", r"\sim": "~",
    }
    for k, v in subs.items():
        s = s.replace(k, v)
    s = s.replace("{", "").replace("}", "").replace("\\", "")
    return s


def render_formula(latex, out_png, warn):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    cjk = next((p for p in CJK_FONTS if Path(p).exists()), None)
    fp = font_manager.FontProperties(fname=cjk) if cjk else None
    body = latex.strip()
    if not body.startswith("$"):
        body = f"${body}$"
    attempts = [("math", body), ("plain", strip_math(latex))]
    for mode, txt in attempts:
        try:
            fig = plt.figure(figsize=(6.2, 1.4))
            fig.text(0.02, 0.5, txt, fontsize=17, va="center",
                     fontproperties=None if mode == "math" else fp)
            fig.savefig(out_png, dpi=200, bbox_inches="tight", pad_inches=0.14,
                        facecolor="white")
            plt.close(fig)
            if mode == "plain":
                warn(f"formula fell back to plain text: {latex[:70]}")
            return mode
        except Exception:
            plt.close("all")
    warn(f"formula could not be rendered: {latex[:70]}")
    return "failed"


def build_html(spec, tmpdir, warn):
    p1 = spec.get("part1", {}) or {}
    p2 = spec.get("part2", {}) or {}
    p3 = spec.get("part3", {}) or {}
    p4 = spec.get("part4", {}) or {}
    meta = spec.get("meta", {}) or {}

    qs = items(p3.get("questions"))
    ans = items(p4.get("answers"))
    if len(qs) != 10 or len(ans) != 10:
        sys.exit(f"FAIL: part3.questions has {len(qs)} and part4.answers has {len(ans)}; both must be exactly 10.")

    out = []
    out.append("<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'>")
    out.append(f"<title>{esc(spec.get('title', 'Read Note'))}</title>")
    out.append(f"<style>{CSS}</style></head><body>")
    out.append(f"<h1>{esc(spec.get('title', 'Read Note'))}</h1>")
    meta_bits = [meta.get("source_pdf", ""), meta.get("venue_year", ""), meta.get("task", "")]
    out.append(f"<div class='sub'>{' · '.join(esc(b) for b in meta_bits if b)}</div>")
    out.append("<nav><b>第一部分</b> 摘要 · 框架模型 · 研究思路与方法　|　"
               "<b>第二部分</b> 关键结论 · 指标表 · 核心公式 · 框架思维导图　|　"
               "<b>第三部分</b> 十个问题　|　<b>第四部分</b> 十个答案</nav>")

    # Part 1
    out.append("<section><h2 class='part'>第一部分　摘要 · 框架模型 · 研究思路与方法</h2>")
    out.append("<h3>1.1 论文摘要（中文重写）</h3>" + paras(p1.get("abstract")))
    if p1.get("framework_model"):
        out.append("<h3>1.2 框架模型总览</h3>" + paras(p1.get("framework_model"))
                   + analogy_box(p1.get("framework_analogy")))
    if p1.get("modules"):
        mods = []
        for m in items(p1.get("modules")):
            m = m if isinstance(m, dict) else {"name": m}
            mods.append({"name": m.get("name", ""), "role": m.get("role", ""),
                         "detail": esc(m.get("detail", "")) + analogy_box(m.get("analogy"))})
        out.append("<h3>1.3 框架模块拆解</h3>" + dict_table(
            mods, [("name", "模块", 0), ("role", "在框架中的作用", 0), ("detail", "机制与设计理由", 0)],
            raw_keys=("detail",)))
    if p1.get("research_approach"):
        out.append("<h3>1.4 研究思路</h3>" + ol(p1.get("research_approach")))
    if p1.get("methods"):
        rows = items(p1.get("methods"))
        if rows and isinstance(rows[0], dict):
            out.append("<h3>1.5 研究方法</h3>" + dict_table(rows, [("aspect", "方面", 0), ("detail", "具体做法与关键设置", 0)]))
        else:
            out.append("<h3>1.5 研究方法</h3>" + ul(rows))
    if p1.get("contributions"):
        out.append("<h3>1.6 论文自述贡献</h3>" + ul(p1.get("contributions")))
    out.append("</section>")

    # Part 2
    out.append("<section><h2 class='part'>第二部分　图表：关键结论 · 核心公式 · 框架思维导图</h2>")
    cons = items(p2.get("conclusions"))
    if cons:
        out.append("<h3>2.1 关键结论</h3>")
        for i, c in enumerate(cons, 1):
            if not isinstance(c, dict):
                c = {"claim": c}
            bits = [f"<div class='ct'>结论 {i}　{esc(c.get('title', ''))}</div>"]
            if c.get("claim"):
                bits.append(f"<div class='claim'>{esc(c['claim'])}</div>")
            if c.get("detail"):
                bits.append(f"<p>{esc(c['detail'])}</p>")
            if c.get("why"):
                bits.append(f"<p class='why'>为何如此：{esc(c['why'])}</p>")
            bits.append(analogy_box(c.get("analogy")))
            if c.get("evidence"):
                bits.append(f"<div class='src'>证据锚点：{esc(c['evidence'])}</div>")
            out.append("<div class='card'>" + "".join(bits) + "</div>")
    if p2.get("metrics"):
        out.append("<h3>2.2 关键指标与数据</h3>" + dict_table(
            p2.get("metrics"), [("name", "指标 / 数据集", 0), ("value", "结果", 0), ("note", "条件或对比", 0)]))
    forms = items(p2.get("formulas"))
    if forms:
        out.append("<h3>2.3 核心公式与说明</h3>")
        for i, f in enumerate(forms, 1):
            if not isinstance(f, dict):
                f = {"latex": f}
            png = Path(tmpdir) / f"f{i}.png"
            mode = render_formula(str(f.get("latex", "")), png, warn)
            bits = [f"<div class='ct'>公式 {i}　{esc(f.get('name', ''))}</div>"]
            if mode != "failed":
                bits.append(f"<img class='f' src='{png.name}'>")
            else:
                bits.append(paras(f.get("latex")))
            if f.get("symbols"):
                bits.append("<table><tr><th>符号</th><th>含义</th></tr>" + "".join(
                    f"<tr><td class='sym'>{esc(s.get('sym', '') if isinstance(s, dict) else s)}</td>"
                    f"<td>{esc(s.get('mean', '') if isinstance(s, dict) else '')}</td></tr>"
                    for s in items(f.get("symbols"))) + "</table>")
            if f.get("intuition"):
                bits.append(f"<p>{esc(f['intuition'])}</p>")
            if f.get("role"):
                bits.append(f"<p class='why'>在框架中的作用：{esc(f['role'])}</p>")
            bits.append(analogy_box(f.get("analogy")))
            out.append("<div class='fbox'>" + "".join(bits) + "</div>")
    if p2.get("mindmap"):
        mm = p2["mindmap"]
        if not isinstance(mm, dict):
            mm = {"text": str(mm)}
        out.append("<h3>2.4 框架流程思维导图</h3><ul class='mm'>" + mindmap(mm) + "</ul>")
    out.append("</section>")

    # Part 3
    out.append("<section><h2 class='part'>第三部分　看懂这篇论文才能答出的十个问题</h2>")
    out.append("<ol class='qlist'>")
    for q in qs:
        q = q if isinstance(q, dict) else {"q": q}
        t = f"<div class='tests'>考察：{esc(q['tests'])}</div>" if q.get("tests") else ""
        out.append(f"<li>{esc(q.get('q', ''))}{t}</li>")
    out.append("</ol></section>")

    # Part 4
    out.append("<section><h2 class='part'>第四部分　十个问题的答案</h2>")
    for i, (q, a) in enumerate(zip(qs, ans), 1):
        a = a if isinstance(a, dict) else {"a": a}
        qq = q.get("q", "") if isinstance(q, dict) else q
        out.append("<div class='qa'>")
        out.append(f"<div class='echo'>问题 {i}：{esc(qq)}</div>")
        out.append(f"<p class='ans'><b>{i}.</b> {esc(a.get('a', ''))}</p>")
        if a.get("anchor"):
            out.append(f"<div class='anchor'>依据：{esc(a['anchor'])}</div>")
        out.append("</div>")
    out.append("</section>")

    if spec.get("glossary"):
        out.append("<section><h2 class='part'>附录　术语表</h2>" + dict_table(
            spec.get("glossary"), [("term", "术语", 0), ("cn", "中文", 0)]) + "</section>")

    out.append("</body></html>")
    return "\n".join(out)


def print_pdf(html_path, pdf_path):
    browser = next((b for b in BROWSERS if b and Path(b).exists()), None)
    if not browser:
        sys.exit("FAIL: no Edge/Chrome found to print the PDF. Tried:\n  " + "\n  ".join(BROWSERS))
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    url = html_path.resolve().as_uri()
    base = [browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
            "--disable-extensions", f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", url]
    for flag in ("--headless=new", "--headless"):
        cmd = [flag if a == "--headless=new" else a for a in base]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if pdf_path.exists():
            return browser
    sys.exit("FAIL: browser did not produce a PDF.")


def build(spec_path, out_path, keep_html=False):
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    warn_msgs = []
    tmpdir = Path(tempfile.mkdtemp(prefix="readnote_"))
    try:
        html_doc = build_html(spec, tmpdir, warn_msgs.append)
        html_path = tmpdir / "readnote.html"
        html_path.write_text(html_doc, encoding="utf-8")
        pdf_path = Path(out_path) if out_path else spec_path.with_suffix(".pdf")
        print_pdf(html_path, pdf_path)
        if keep_html:
            shutil.copy(html_path, pdf_path.with_suffix(".html"))
        for m in warn_msgs:
            log(m)
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(pdf_path)).pages)
        except Exception:
            pages = "?"
        log(f"OK: {pdf_path}  pages={pages}  size={pdf_path.stat().st_size // 1024}KB  "
            f"formula_fallbacks={len(warn_msgs)}")
        return pdf_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def extract(pdf_path, out_path=None):
    from pypdf import PdfReader
    pdf_path = Path(pdf_path)
    reader = PdfReader(str(pdf_path))
    chunks = []
    for i, page in enumerate(reader.pages, 1):
        chunks.append(f"===== [p.{i}] =====\n{(page.extract_text() or '').strip()}")
    text = "\n\n".join(chunks)
    out = Path(out_path) if out_path else pdf_path.with_suffix(".txt")
    out.write_text(text, encoding="utf-8")
    per_page = len(text) / max(len(reader.pages), 1)
    log(f"pages={len(reader.pages)} chars={len(text)} chars_per_page={per_page:.0f} -> {out}")
    if per_page < 200:
        log("WARNING: text layer looks empty; this PDF probably needs OCR before use.")
    return out


SAMPLE = {
    "title": "示例：把论文变成阅读笔记",
    "meta": {"source_pdf": "sample.pdf", "venue_year": "arXiv 2026", "task": "验证渲染管线"},
    "part1": {
        "abstract": ["这一段用来验证中文正文的字体与行距是否正确。"],
        "framework_model": ["输入 → 编码器 → 打分头 → 输出。"],
        "modules": [{"name": "编码器", "role": "抽取表示", "detail": "用 Transformer 堆叠 12 层。"}],
        "research_approach": ["先定位问题，再设计目标函数。"],
        "methods": [{"aspect": "训练", "detail": "AdamW，学习率 1e-4。"}],
        "contributions": ["提出一个自检用的渲染样例。"],
    },
    "part2": {
        "conclusions": [{"title": "渲染可用", "claim": "公式与表格都能正确排版。",
                         "detail": "结论卡片的描述文字跟在结论之后。", "why": "因为走的是同一套 CSS。",
                         "evidence": "p.1"}],
        "formulas": [{"name": "交叉熵", "latex": r"\mathcal{L}=-\sum_{i=1}^{N} y_i \log p_i",
                      "symbols": [{"sym": "N", "mean": "样本数"}],
                      "intuition": "衡量预测分布与真实标签的差距。", "role": "决定训练目标。"}],
        "metrics": [{"name": "Accuracy", "value": "91.2", "note": "在测试集上"}],
        "mindmap": {"text": "核心思想", "children": [
            {"text": "数据", "children": [{"text": "预处理", "note": "可选短注"}]},
            {"text": "模型", "children": [{"text": "编码器"}]},
            {"text": "评测", "children": [{"text": "消融实验"}]}]},
    },
    "part3": {"questions": [{"q": f"自检问题 {i}", "tests": "渲染"} for i in range(1, 11)]},
    "part4": {"answers": [{"a": f"自检答案 {i}。", "anchor": f"Sec {i}"} for i in range(1, 11)]},
    "glossary": [{"term": "ablation", "cn": "消融实验"}],
}


def selftest():
    tmp = Path(tempfile.mkdtemp(prefix="readnote_selftest_"))
    spec = tmp / "sample.json"
    spec.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    pdf = build(spec, tmp / "sample.pdf")
    size = pdf.stat().st_size
    from pypdf import PdfReader
    pages = len(PdfReader(str(pdf)).pages)
    ok = size > 20000 and pages >= 4
    log(f"SELFTEST {'PASS' if ok else 'FAIL'}: pages={pages} size={size} bytes ({tmp})")
    if not ok:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="readnote.json, or the PDF when --extract is used")
    ap.add_argument("-o", "--out", help="output path (default: input path with .pdf / .txt)")
    ap.add_argument("--extract", action="store_true", help="extract PDF text with page markers")
    ap.add_argument("--keep-html", action="store_true", help="also write the intermediate HTML")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args.selftest:
        selftest()
        return
    if not args.input:
        ap.error("input is required")
    if args.extract:
        extract(args.input, args.out)
    else:
        build(args.input, args.out, args.keep_html)


if __name__ == "__main__":
    main()