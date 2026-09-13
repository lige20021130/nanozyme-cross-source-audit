# -*- coding: utf-8 -*-
"""KEY-based reference renumbering + insertion of three audit/meta-science refs.

Round 12 (2026-09-11). Adds:
    himanen  Himanen 2019 Adv. Sci. (data veracity / standardisation)
    wangq    Wang 2026 arXiv:2609.01621 (literature data mislead AI)
    xu       Xu 2022 BMJ e069155 (data-extraction reproducibility)

Why KEY-based instead of number-based: the previous round's script
(workbench/_renumber_refs.py) mapped old number -> new number, which is fragile
once a citation's *first appearance position* moves (the AI-ZYMES release note in
Section 1.1 made ref [7] appear before ref [6]). Here every citation is first
rewritten to a stable KEY, the body is then scanned in reading order, and numbers
are assigned by first appearance. That is the rule the manuscript claims to follow.

Touches:
    paper_drafts/manuscript_sections3_6_merged.md   <sup> groups
    paper_drafts/si_tables_track1.md                [n] and "ref. [n]" forms
    paper_drafts/references_draft.md                entry blocks (reordered)

Run:  D:/conda/python.exe workbench/_insert_audit_refs.py [--apply]
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BODY = ROOT / "paper_drafts" / "manuscript_sections3_6_merged.md"
SI = ROOT / "paper_drafts" / "si_tables_track1.md"
REFS = ROOT / "paper_drafts" / "references_draft.md"

# 当前（改前）编号 -> 稳定 KEY
CUR2KEY = {
    1: "gao", 2: "dizyme2024", 3: "dizyme2022", 4: "wei2022", 5: "sun2024",
    6: "li2023", 7: "xuan2025", 8: "nanozymedb", 9: "nanozymesnet",
    10: "kamatchi", 11: "wangx", 12: "prasad", 13: "katsura", 14: "sklearn",
}
KEY2CUR = {v: k for k, v in CUR2KEY.items()}

CN = re.compile(r"[\u4e00-\u9fff]")
SUP = re.compile(r"<sup>([^<]+)</sup>")
KEYSUP = re.compile(r"<sup>((?:KEY)?[A-Za-z]+(?:\d+)?(?:,(?:KEY)?[A-Za-z]+\d*)*)</sup>")


def to_keys(group: str) -> str:
    """'2,5' -> 'dizyme2024,sun2024'; leaves KEY* tokens alone."""
    keys = []
    for tok in re.split(r"[,\s]+", group.strip()):
        if not tok:
            continue
        if tok.startswith("KEY"):
            keys.append(tok[3:].lower())
        elif tok.isdigit():
            keys.append(CUR2KEY[int(tok)])
        else:
            raise SystemExit(f"unexpected citation token: {tok!r}")
    return ",".join(keys)


def step1_keyify_body(text: str) -> str:
    def rep(m):
        return "<sup>" + to_keys(m.group(1)) + "</sup>"
    return SUP.sub(rep, text)


def step2_number_body(text: str) -> tuple[str, dict]:
    order, out = [], []
    pos = 0
    for m in KEYSUP.finditer(text):
        for k in m.group(1).split(","):
            k = k.lower()
            if k not in order:
                order.append(k)
    num = {k: i + 1 for i, k in enumerate(order)}

    def rep(m):
        keys = [k.lower() for k in m.group(1).split(",")]
        nums = sorted({num[k] for k in keys})
        return "<sup>" + ",".join(str(n) for n in nums) + "</sup>"

    return KEYSUP.sub(rep, text), num


def main() -> None:
    body = BODY.read_text(encoding="utf-8")
    body = step1_keyify_body(body)
    body, NUM = step2_number_body(body)

    missing = [k for k in KEY2CUR if k not in NUM]
    if missing:
        raise SystemExit(f"[FATAL] keys never cited: {missing}")

    print("new numbering (first-appearance order):")
    for k in sorted(NUM, key=NUM.get):
        print(f"  [{NUM[k]:>2}] {k}")

    # ---- SI tables: current numbers -> KEYs -> new numbers ----
    si = SI.read_text(encoding="utf-8")

    # 只改英文行；中文工作注记（会被构建脚本剥离）保持原样，避免注释与本轮编号脱节。
    si_lines = si.splitlines()
    si_new_lines = []
    for ln in si_lines:
        if CN.search(ln):
            si_new_lines.append(ln)
        else:
            si_new_lines.append(
                re.sub(r"\[(\d{1,2})\]",
                       lambda m: "[" + str(NUM[CUR2KEY[int(m.group(1))]]) + "]", ln))
    si_new = "\n".join(si_new_lines)

    # ---- references_draft.md: reorder entry blocks ----
    lines = REFS.read_text(encoding="utf-8").splitlines()
    first = next(i for i, ln in enumerate(lines) if re.match(r"^\*\*\[\d+\]", ln))
    last = next(i for i, ln in enumerate(lines[first:], start=first)
                if ln.startswith("---") and i > first)
    head, tail = lines[:first], lines[last:]

    blocks, cur = {}, None
    for ln in lines[first:last]:
        m = re.match(r"^\*\*\[(\d+)\]", ln)
        if m:
            cur = CUR2KEY[int(m.group(1))]
            blocks[cur] = [ln]
        elif cur:
            blocks[cur].append(ln)

    NEW_BLOCKS = {
        "himanen": [
            "**[N] Data veracity as a materials-informatics challenge (§1.1: the quality "
            "of the data resource has not kept pace with its volume)**",
            "Himanen, L.; Geurts, A.; Foster, A. S.; Rinke, P.",
            "Data-Driven Materials Science: Status, Challenges, and Perspectives.",
            "*Adv. Sci.* **2019**, *6*, 1900808. DOI: 10.1002/advs.201900808.",
            "> ✅ 2026-09-11 新增并核实：PubMed 31728276 / DOI 解析一致。原文把 data veracity、",
            "> standardisation、data longevity 列为阻碍该领域发展的核心挑战，用于支撑“数据质量是",
            "> 领域级问题而非纳米酶特有”的定位。DOI 有官方勘误（10.1002/advs.201903667），不影响本引用。",
        ],
        "wangq": [
            "**[N] Literature-derived data mislead AI (§1.1: ML models inherit the "
            "inconsistencies)**",
            "Wang, Q.; Li, Y.; Sato, R.; Kato, H.; Orimo, S.-i.; Li, H.; Cheng, E. J.",
            "When Literature Data Mislead Artificial Intelligence in Materials Discovery.",
            "*[arXiv]* **2026**, arXiv:2609.01621. https://doi.org/10.48550/arXiv.2609.01621.",
            "> ✅ 2026-09-11 新增并核实：arXiv 页面确认标题/作者/提交日期（2026-07-18）。",
            "> 原文以固态电解质电导率为案例，报告 text–figure mismatch、轴标注歧义、单位不一致，",
            "> 并给出一个跨库 100 倍电导率误差的例子 —— 与本工作“单位/条件口径错配造成跨源分歧”同构，",
            "> 且说明该失效模式并非纳米酶独有。投稿时按期刊政策确认预印本格式。",
        ],
        "xu": [
            "**[N] Reproducibility of data extraction (§3.1: human extraction is itself "
            "imperfect)**",
            "Xu, C.; Yu, T.; Furuya-Kanamori, L.; Lin, L.; Zorzela, L.; Zhou, X.; Dai, H.; "
            "Loke, Y.; Vohra, S.",
            "Validity of Data Extraction in Evidence Synthesis Practice of Adverse Events: "
            "Reproducibility Study.",
            "*BMJ* **2022**, *377*, e069155. DOI: 10.1136/bmj-2021-069155.",
            "> ✅ 2026-09-11 新增并核实：PubMed 35537752 / DOI 解析一致。原文报告 10,386 条试验记录中",
            "> 1,762 条（17.0%）无法从原始来源复现，误差以数值错误（49.2%）与定义歧义（29.9%）为主。",
            "> 用于给“人工抽取本身有误差率”提供可引证数字；同时是 §4.2 参考源本身可能含错的外部依据。",
        ],
    }

    out_blocks = []
    for k in sorted(NUM, key=NUM.get):
        block = blocks.get(k) or NEW_BLOCKS.get(k)
        if block is None:
            raise SystemExit(f"[FATAL] no reference block for key {k}")
        n = NUM[k]
        blk = list(block)
        blk[0] = re.sub(r"^\*\*\[N\]", f"**[{n}]", blk[0])
        blk[0] = re.sub(r"^\*\*\[\d+\]", f"**[{n}]", blk[0])
        out_blocks.append(blk)

    new_refs = head + [ln for blk in out_blocks for ln in (blk + [""])] + tail
    # 折叠三重空行
    collapsed = []
    for ln in new_refs:
        if ln == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(ln)

    if "--apply" in sys.argv:
        BODY.write_text(body, encoding="utf-8")
        SI.write_text(si_new, encoding="utf-8")
        REFS.write_text("\n".join(collapsed) + "\n", encoding="utf-8")
        print("\nAPPLIED to body / SI / references.")
    else:
        print("\nDRY RUN. Re-run with --apply.")
        print("\n-- SI diff preview --")
        for a, b in zip(si.splitlines(), si_new.splitlines()):
            if a != b:
                print(f"  - {a[:110]}\n  + {b[:110]}")


if __name__ == "__main__":
    main()
