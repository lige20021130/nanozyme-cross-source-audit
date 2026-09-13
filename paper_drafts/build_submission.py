# -*- coding: utf-8 -*-
"""生成 Track 1 的投稿包（目标：ACS 系 / JCIM 为主，兼容其他 ACS 刊）。

产出目录 `submission_JCIM/`：
  manuscript.docx     正文（Title + 作者 + 单位 + Abstract + Keywords + §1-7
                       + Author Information + References）
  SI.docx             支持信息（SI 说明 + Table S1-S8）
  figures/Figure1..8.png   300 dpi 图件副本
  cover_letter.docx   投稿信
  TOC_graphic.png     TOC 图（3.25 x 1.75 in @ 600 dpi）
  README.md           投稿前人工待填清单

输入：`paper_drafts/manuscript_full_track1.md`（由 build_full_manuscript.py 生成）
      `paper_drafts/paper_meta.py`（作者/单位/基金/投稿信，需人工填写）

运行：D:/conda/python.exe paper_drafts/build_submission.py
"""
import re
import shutil
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_meta as M

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = HERE / "manuscript_full_track1.md"
OUTDIR = ROOT / "submission_JCIM"
FIGDIR = OUTDIR / "figures"

FONT = "Times New Roman"
MAX_FIG_WIDTH = 6.5          # in（单栏审稿稿，页宽 8.5 - 2*1 = 6.5）


# ----------------------------------------------------------------- 基础工具
def set_base_style(doc):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(12)
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), FONT)
    pf = st.paragraph_format
    pf.line_spacing = 2.0            # 双行距（ACS 初稿要求）
    pf.space_after = Pt(0)


def set_margins(doc, inches=1.0):
    for s in doc.sections:
        s.top_margin = Inches(inches)
        s.bottom_margin = Inches(inches)
        s.left_margin = Inches(inches)
        s.right_margin = Inches(inches)


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|(?<!\*)\*(?!\*)[^*]+\*(?!\*)|<sup>[^<]*</sup>)")


def add_runs(par, text, size=12, bold=False, italic=False):
    """渲染内联标记：**bold** *italic* `code` <sup>n</sup>"""
    for seg in INLINE.split(text):
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**"):
            r = par.add_run(seg[2:-2]); r.bold = True
        elif seg.startswith("<sup>") and seg.endswith("</sup>") and len(seg) > 11:
            r = par.add_run(seg[5:-6]); r.font.superscript = True
        elif seg.startswith("`") and seg.endswith("`"):
            r = par.add_run(seg[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(size - 1)
        elif len(seg) > 2 and seg.startswith("*") and seg.endswith("*"):
            r = par.add_run(seg[1:-1]); r.italic = True
        else:
            r = par.add_run(seg)
        r.font.size = Pt(size)
        if bold:
            r.bold = True
        if italic:
            r.italic = True
    return par


def md_table_rows(lines, i):
    """从 markdown 管道表第 i 行开始，收集到表结束；返回 (rows, next_i)"""
    rows = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        raw = lines[i].strip()
        cells = [c.strip() for c in raw.strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    return rows, i


def add_table(doc, rows, size=8):
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncol)
    t.style = "Table Grid"
    t.autofit = True
    for ri, r in enumerate(rows):
        cells = t.add_row().cells
        for ci in range(ncol):
            txt = r[ci] if ci < len(r) else ""
            txt = txt.replace("**", "")
            p = cells[ci].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            add_runs(p, txt, size=size, bold=(ri == 0))
    doc.add_paragraph()


def add_figure(doc, path, max_width=MAX_FIG_WIDTH):
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    ratio = h / w
    width = min(max_width, w / 300.0)
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.line_spacing = 1.0


# ----------------------------------------------------------------- md 解析
HEAD_STYLE = {1: "Heading 1", 2: "Heading 1", 3: "Heading 2", 4: "Heading 3"}

CAPTION_RE = re.compile(r"^\*\*(Figure|Table|Scheme)\b")
FOOTNOTE_RE = re.compile(r"^\*Footnotes?\.\*")
ITEM_RE = re.compile(r"^(\d+\.\s|[-*]\s)")


def theme_heading(doc):
    """让 Word 标题样式保持 Times 黑色，同时保留大纲级别（导航窗格可用）。"""
    spec = [("Heading 1", 12, True, False),
            ("Heading 2", 12, True, True),
            ("Heading 3", 12, False, True)]
    for name, size, bold, italic in spec:
        st = doc.styles[name]
        st.font.name = FONT
        st.font.size = Pt(size)
        st.font.bold = bold
        st.font.italic = italic
        st.font.color.rgb = RGBColor(0, 0, 0)
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), FONT)
        pf = st.paragraph_format
        pf.line_spacing = 1.0
        pf.space_before = Pt(14)
        pf.space_after = Pt(6)
        pf.keep_with_next = True


def emit_paragraph(doc, text):
    """段落级渲染：识别图注 / 表注 / 普通正文，分别设定字号与行距。"""
    if CAPTION_RE.match(text):
        p = doc.add_paragraph()
        add_runs(p, text, size=9)
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_after = Pt(8)
        pf.space_before = Pt(4)
        return
    if FOOTNOTE_RE.match(text):
        p = doc.add_paragraph()
        add_runs(p, text, size=8)
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_after = Pt(10)
        return
    if ITEM_RE.match(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs(p, text, size=12)
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_runs(p, text, size=12)


def parse_md(lines, doc, start=0, end=None, figmap=None):
    """按 markdown 段落语义渲染：**硬换行不换段**，空行才分段。

    早期版本把源文件的每一行都当成一个段落，导致一篇 150 段的稿件被切成
    789 段（摘要被拆成 15 行），在 Word 里完全不可读。
    """
    end = end if end is not None else len(lines)
    buf = []

    def flush():
        if not buf:
            return
        text = re.sub(r"\s+", " ", " ".join(buf)).strip()
        buf.clear()
        if text:
            emit_paragraph(doc, text)

    i = start
    while i < end:
        s = lines[i].strip()
        if not s:
            flush()
            i += 1
            continue

        if s.startswith("|"):
            flush()
            rows, i = md_table_rows(lines, i)
            add_table(doc, rows)
            continue

        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", s)
        if m:
            flush()
            p = (HERE / m.group(1)).resolve()
            if not p.exists():
                p = (ROOT / m.group(1)).resolve()
            target = figmap.get(p.name, p) if figmap else p
            if Path(target).exists():
                add_figure(doc, target)
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush()
            doc.add_paragraph(m.group(2).replace("**", ""),
                              style=HEAD_STYLE[len(m.group(1))])
            i += 1
            continue

        if re.fullmatch(r"-{3,}", s):
            flush()
            i += 1
            continue

        if ITEM_RE.match(s):
            flush()
            buf.append(s)
            i += 1
            continue

        buf.append(s)
        i += 1

    flush()


# ----------------------------------------------------------------- 元数据块
def title_page(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(p, M.TITLE, size=15, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    names = []
    for a in M.AUTHORS:
        nm = a["name"]
        sup = "".join(chr(0x2070 + x) if x in (1, 2, 3) else str(x)
                      for x in a["affil"])
        sup = "".join({1: "\u00b9", 2: "\u00b2", 3: "\u00b3",
                       4: "\u2074", 5: "\u2075"}.get(x, str(x)) for x in a["affil"])
        names.append(f"{nm}{sup}")
    add_runs(p, ", ".join(names), size=12)

    for k, aff in enumerate(M.AFFILIATIONS, start=1):
        sup = {1: "\u00b9", 2: "\u00b2", 3: "\u00b3",
               4: "\u2074", 5: "\u2075"}.get(k, str(k))
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_runs(p, f"{sup}{aff}", size=10)

    orcid = [f"{a['name']}: https://orcid.org/{a['orcid']}"
             for a in M.AUTHORS if a.get("orcid") and not a["orcid"].startswith("[[")]
    if orcid:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_runs(p, "ORCID " + "; ".join(orcid), size=9)

    doc.add_paragraph()


def author_information(doc):
    p = doc.add_paragraph()
    add_runs(p, "Author Information", size=12, bold=True)

    p = doc.add_paragraph()
    add_runs(p, "Corresponding Author", size=11, bold=True)
    ca = M.CORRESPONDING_AUTHOR
    lines = [f"{ca['name']} — {ca['address']}; Email: {ca['email']}"]
    if ca.get("orcid"):
        lines.append(f"ORCID: {ca['orcid']}")
    if ca.get("phone"):
        lines.append(f"Phone: {ca['phone']}")
    for t in lines:
        add_runs(doc.add_paragraph(), t, size=11)

    p = doc.add_paragraph()
    add_runs(p, "Author Contributions", size=11, bold=True)
    add_runs(doc.add_paragraph(), M.AUTHOR_CONTRIBUTIONS, size=11)

    p = doc.add_paragraph()
    add_runs(p, "Funding", size=11, bold=True)
    add_runs(doc.add_paragraph(), M.FUNDING, size=11)

    p = doc.add_paragraph()
    add_runs(p, "Notes", size=11, bold=True)
    add_runs(doc.add_paragraph(), M.CONFLICT_OF_INTEREST, size=11)

    p = doc.add_paragraph()
    add_runs(p, "Data Availability Statement", size=11, bold=True)
    add_runs(doc.add_paragraph(), M.DATA_AVAILABILITY, size=11)

    p = doc.add_paragraph()
    add_runs(p, "Acknowledgment", size=11, bold=True)
    add_runs(doc.add_paragraph(), M.ACKNOWLEDGMENT, size=11)


# ----------------------------------------------------------------- TOC 图
def make_toc_graphic(path):
    """ACS TOC 图：3.25 x 1.75 in @ 600 dpi。

    只用正文中已出现的数字（5,027 entries / 25 fields / 166 clusters），
    避免引入稿件里无法追溯的统计量。
    文字按 3.25 in 实宽排布，标签不溢出框。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    BLUE, ORANGE, VERM, GRAY = "#0072B2", "#E69F00", "#D55E00", "#333333"

    fig, ax = plt.subplots(figsize=(3.25, 1.75), dpi=600)
    ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis("off")

    boxes = [
        (0.15, "25", "condition-bound", BLUE),
        (4.25, "5,027", "entries \u00b7 761 DOIs", ORANGE),
        (8.35, "166", "conflict clusters", VERM),
    ]
    BW, BH, BY = 3.5, 3.0, 2.3
    for x, big, sub, col in boxes:
        ax.add_patch(FancyBboxPatch((x, BY), BW, BH,
                                    boxstyle="square,pad=0",
                                    linewidth=0, facecolor=col))
        ax.text(x + BW / 2, BY + BH * 0.62, big, ha="center", va="center",
                fontsize=15, fontweight="bold", color="white")
        ax.text(x + BW / 2, BY + BH * 0.24, sub, ha="center", va="center",
                fontsize=6.3, color="white")

    for x0 in (3.65, 7.75):
        ax.add_patch(FancyArrowPatch((x0, BY + BH / 2), (x0 + 0.6, BY + BH / 2),
                                     arrowstyle="-|>", mutation_scale=8,
                                     linewidth=1.4, color=GRAY))

    ax.text(6.0, 1.15, "$K_\\mathrm{m}$ bound to pH, T, substrate, DOI",
            ha="center", va="center", fontsize=8.2, color=GRAY)

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(path, dpi=600, facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------- 主流程
def main():
    lines = SRC.read_text(encoding="utf-8").splitlines()

    si_idx = next(i for i, l in enumerate(lines) if l.strip() == "## Supporting Information")
    ref_idx = next(i for i, l in enumerate(lines) if l.strip() == "## References")
    body_end = ref_idx            # 正文 + 参考文献进 manuscript.docx
    main_lines = lines[:body_end]
    # 跳过 md 里的标题行（docx 用元数据里的 TITLE）
    main_lines = [l for l in main_lines if not l.startswith("# Cross-Source Audit")]

    # 摘要字数实测（2026-09-12）：此前投稿信里的 "abstract 198 words" 是硬编码，
    # 与实际 197 词不符。改为从源文件现算，避免措辞改动后再次漂移。
    abs_start = next(i for i, l in enumerate(lines) if l.strip() == "## Abstract")
    abs_txt = []
    for l in lines[abs_start + 1:]:
        if l.startswith("## "):
            break
        abs_txt.append(l)
    abs_words = len(" ".join(abs_txt).split())

    OUTDIR.mkdir(parents=True, exist_ok=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)

    # --- 图件副本 ---
    figmap = {}
    for k in range(1, 9):
        src = ROOT / "workbench" / "figs" / f"fig{k}_"
        cand = sorted((ROOT / "workbench" / "figs").glob(f"fig{k}_*.png"))
        if not cand:
            raise SystemExit(f"[figures] no png for fig{k}")
        dst = FIGDIR / f"Figure{k}.png"
        shutil.copy2(cand[0], dst)
        figmap[cand[0].name] = dst
    print(f"[figures] copied {len(figmap)} -> {FIGDIR}")

    # --- TIFF 副本（ACS 首选图件格式；LZW 无损，300 dpi）---
    from PIL import Image
    tifdir = OUTDIR / "figures_tiff"
    tifdir.mkdir(exist_ok=True)
    for k in range(1, 9):
        im = Image.open(FIGDIR / f"Figure{k}.png").convert("RGB")
        im.save(tifdir / f"Figure{k}.tif", compression="tiff_lzw", dpi=(300, 300))
    print(f"[figures] wrote 8 TIFF -> {tifdir}")

    # --- manuscript.docx ---
    doc = Document()
    set_base_style(doc)
    theme_heading(doc)
    set_margins(doc)
    title_page(doc)
    parse_md(main_lines, doc, start=0, end=len(main_lines), figmap=figmap)
    author_information(doc)
    # 参考文献已在 main_lines 中（## References 之前截断 → 不含）— 单独渲染
    ref_end = next(i for i, l in enumerate(lines) if l.strip().startswith("## Supporting Information"))
    parse_md(lines, doc, start=ref_idx, end=ref_end)
    doc.save(OUTDIR / "manuscript.docx")
    print("[docx] manuscript.docx")

    # --- SI.docx ---
    si = Document()
    set_base_style(si)
    theme_heading(si)
    set_margins(si)
    p = si.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(p, "Supporting Information", size=15, bold=True)
    p = si.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(p, M.SHORT_TITLE, size=12, bold=True)
    p = si.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(p, ", ".join(a["name"] for a in M.AUTHORS), size=11)
    si.add_paragraph()
    parse_md(lines, si, start=si_idx + 1, end=len(lines))
    si.save(OUTDIR / "SI.docx")
    print("[docx] SI.docx")

    # --- cover letter ---
    cl = Document()
    set_base_style(cl)
    theme_heading(cl)
    set_margins(cl)
    cl.add_paragraph("Cover Letter")
    cl.add_paragraph()
    add_runs(cl.add_paragraph(),
             f"Dear {M.COVER_LETTER['editor_name']},", size=12)
    cl.add_paragraph()
    main_words = sum(len(l.split()) for l in lines[:body_end])
    add_runs(cl.add_paragraph(),
             f"Please find enclosed our manuscript titled \"{M.TITLE}\" "
             f"({main_words:,} words of main text excluding references and the "
             f"Supporting Information; abstract {abs_words} words), which we submit for "
             f"consideration as an Article in "
             f"{M.COVER_LETTER['journal']}.", size=12)
    cl.add_paragraph()
    add_runs(cl.add_paragraph(), M.COVER_LETTER["paragraph_2"], size=12)
    cl.add_paragraph()
    add_runs(cl.add_paragraph(),
             "We confirm that this manuscript is original, has not been published "
             "previously, and is not under consideration elsewhere. All kinetic values "
             "reported are traceable to a DOI, and the code and data underlying the "
             "analyses are described in the Data Availability Statement.", size=12)
    cl.add_paragraph()
    # 2026-09-12：自审关系在投稿信中同步声明，避免编辑在审稿阶段才发现。
    add_runs(cl.add_paragraph(),
             "Disclosure. AI-ZYMES, one of the five source resources audited here, is "
             "described in refs 7 and 8 of the manuscript, of which our corresponding "
             "author is a co-author. We disclose this relationship explicitly and have "
             "kept the audit protocol deterministic and fully specified in the "
             "Supporting Information so that the result can be checked independently of "
             "us.", size=12)
    cl.add_paragraph()
    if M.COVER_LETTER.get("figure_note"):
        add_runs(cl.add_paragraph(), M.COVER_LETTER["figure_note"], size=12)
        cl.add_paragraph()
    cl.add_paragraph()
    add_runs(cl.add_paragraph(),
             "Suggested reviewers: " + "; ".join(M.COVER_LETTER["suggested_editors"])
             + ".", size=12)
    add_runs(cl.add_paragraph(),
             "Reviewers to exclude: " + "; ".join(M.COVER_LETTER["exclude_reviewers"])
             + ".", size=12)
    cl.add_paragraph()
    add_runs(cl.add_paragraph(), "Sincerely,", size=12)
    for a in M.AUTHORS:
        tag = " (corresponding author)" if a["corresponding"] else ""
        add_runs(cl.add_paragraph(), f"{a['name']}{tag}", size=12)
    add_runs(cl.add_paragraph(), M.AFFILIATIONS[0], size=11)
    add_runs(cl.add_paragraph(), f"Email: {M.CORRESPONDING_AUTHOR['email']}", size=11)
    cl.save(OUTDIR / "cover_letter.docx")
    print("[docx] cover_letter.docx")

    # --- TOC graphic ---
    make_toc_graphic(OUTDIR / "TOC_graphic.png")
    print("[fig] TOC_graphic.png")

    # --- README ---
    fills = sorted(set(re.findall(r"\[\[FILL: [^\]]+\]\]",
                                  (HERE / "paper_meta.py").read_text(encoding="utf-8"))))
    readme = [
        "# Submission package — Track 1",
        "",
        f"Built from `paper_drafts/manuscript_full_track1.md`.",
        f"Target: {M.JOURNAL_SPECS['target']}",
        "",
        "## Files",
        "",
        "| File | What it is |",
        "|---|---|",
        "| `manuscript.docx` | Main text: title, authors, affiliations, abstract, keywords, Sections 1-7, Author Information, References |",
        "| `SI.docx` | Supporting Information: SI file list + Tables S1-S8 |",
        "| `figures/Figure1.png` ... `Figure8.png` | Figure files, 300 dpi |",
        "| `figures_tiff/Figure1.tif` ... `Figure8.tif` | Same figures as LZW TIFF (ACS preferred) |",
        "| `cover_letter.docx` | Cover letter |",
        "| `TOC_graphic.png` | TOC graphic, 3.25 x 1.75 in @ 600 dpi |",
        "",
        "## BLOCKING: fill these before submitting",
        "",
        "All `[[FILL: ...]]` slots in `paper_drafts/paper_meta.py` must be replaced. "
        "Current slots:",
        "",
    ] + [f"{i}. `{f}`" for i, f in enumerate(fills, 1)] + [
        "",
        "Re-run `D:/conda/python.exe paper_drafts/build_submission.py` after editing.",
        "",
        "## Journal specs used",
        "",
    ] + [f"- {k}: {v}" for k, v in M.JOURNAL_SPECS.items()]
    (OUTDIR / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print(f"[readme] {len(fills)} FILL slots listed")
    print(f"done -> {OUTDIR}")


if __name__ == "__main__":
    main()
