# -*- coding: utf-8 -*-
"""生成两张"口径可审计"SI 表（审稿人自证用）：

- si_table_s7_caliber.md  : 口径敏感性表 —— 归一化 vs 逐字，逐字段 tp/fp/fn + F1 + 聚合量
- si_table_s8_dispersion.md: 100 篇逐篇一致率分布（band + 十分位），human / db 双侧

数据源：workbench/evall_out/_cross_validate.json（100/102 篇三重对齐）
复算方式：与 workbench/_strict_probe.py 同法，直接调用 workbench.align / cross_validate。

运行：D:/conda/python.exe workbench/_caliber_tables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench import cross_validate as cv
from workbench.align import EVAL_FIELDS, _build_report, _values_match

OUT_DIR = ROOT / "paper_drafts"

# 三张口径差异字段的论文用语
FIELD_LABEL = {
    "metal_type": "Metal identity (`metal_type`)",
    "shape": "Morphology (`shape`)",
    "size_nm": "Particle size (`size_nm`)",
}
AGG_LABEL = [
    ("pooled field-level F1", lambda o: o["f1"]),
    ("pooled precision", lambda o: o["precision"]),
    ("pooled recall", lambda o: o["recall"]),
    ("macro-F1 over compared fields", lambda o: o["macro_f1"]),
    ("pooled field accuracy", lambda o: o["accuracy"]),
]


def rerun(src_by_doi, matcher):
    """按给定 matcher 复算一边（human 或 db）。"""
    agg = {f: {"tp": 0, "fp": 0, "fn": 0} for f in EVAL_FIELDS}
    per_paper = []
    cv._records_match = matcher
    for doi, sys_list in sorted(cv.load_records_dir(cv.DEFAULT_SYS).items()):
        src = src_by_doi.get(doi)
        if not src:
            continue
        r = cv.compare_side(sys_list, src)
        for f in EVAL_FIELDS:
            for k in ("tp", "fp", "fn"):
                agg[f][k] += r["stats"][f][k]
        per_paper.append(r["report"]["overall"]["macro_f1"])
    rep = _build_report(agg, [])
    return {"stats": agg, "overall": rep["overall"],
            "field_level": rep["field_level"], "per_paper_macro": per_paper}


def f3(x):
    return f"{x:.3f}"


def build_s7(hum_n, hum_v, db_n, db_v):
    L = []
    L.append("## Table S7. Comparison-rule sensitivity of the 100-paper agreement")
    L.append("")
    L.append("The same 100 papers (102 DOI-level matches on the database side) scored twice: "
             "once with the three representation normalisations used throughout this work "
             "(*normalised*), and once verbatim, comparing field values as written "
             "(*verbatim*). Only three fields can differ; the remaining fourteen are "
             "identical under both rules, which is why the two aggregate values bracket the "
             "result rather than contradicting it.")
    L.append("")
    L.append("| Metric | Human side, normalised | Human side, verbatim | "
             "Database side, normalised | Database side, verbatim |")
    L.append("|---|---|---|---|---|")

    for label, get in AGG_LABEL:
        L.append(f"| {label} | {f3(get(hum_n['overall']))} | {f3(get(hum_v['overall']))} | "
                 f"{f3(get(db_n['overall']))} | {f3(get(db_v['overall']))} |")
    L.append(f"| mean per-paper macro-F1 | {f3(sum(hum_n['per_paper_macro'])/len(hum_n['per_paper_macro']))} | "
             f"{f3(sum(hum_v['per_paper_macro'])/len(hum_v['per_paper_macro']))} | "
             f"{f3(sum(db_n['per_paper_macro'])/len(db_n['per_paper_macro']))} | "
             f"{f3(sum(db_v['per_paper_macro'])/len(db_v['per_paper_macro']))} |")
    L.append("")

    L.append("Field-level detail for the three fields that differ "
             "(`tp` / `fp` / `fn` counts, then F1):")
    L.append("")
    L.append("| Field | Human, normalised | Human, verbatim | Database, normalised | Database, verbatim |")
    L.append("|---|---|---|---|---|")
    for f, lab in FIELD_LABEL.items():
        cells = []
        for res in (hum_n, hum_v, db_n, db_v):
            st = res["stats"][f]
            if st["tp"] + st["fp"] + st["fn"] == 0:
                cells.append("n/a — not stored by the databases")
                continue
            fl = res["field_level"][f]
            cells.append(f"{st['tp']} / {st['fp']} / {st['fn']} → {f3(fl['f1'])}")
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("The three fields below are absent from the public-database records, so the "
             "database columns of this table are compared over the six fields that the "
             "databases do carry (material, mimicked activity, pH, temperature, Km, Vmax).")
    L.append("")

    # 归一化实际做了什么，逐条列出
    L.append("The three normalisations, stated exactly as implemented "
             "(`workbench/cross_validate.py`, `_records_match`):")
    L.append("")
    L.append("1. **Metal identity** — an element symbol and its atomic number are treated as "
             "one annotation: both sides are converted to the atomic number before "
             "comparison (`Pd` ↔ 46). Under verbatim comparison this field scores 0 by "
             "construction, because gold stores symbols (1,038 string values) and the "
             "pipeline stores numbers (353 integer values).")
    L.append("2. **Morphology** — a generic annotation is not charged against a more specific "
             "prediction: if either side is one of {`nanoparticle`, `polyhedral`, `particle`}, "
             "the pair matches; otherwise a substring test applies (`nanocube` ⊂ "
             "`hollow nanocube`). This rule carries weight, because the gold morphology "
             "column is generic in 611 of 1,057 rows (58%). It is a tolerance policy, not a "
             "notation equivalence, and is therefore reported explicitly rather than folded "
             "into a single score.")
    L.append("3. **Particle size** — relative tolerance widened from 10% to 30%, matching the "
             "spread of TEM and XRD reporting conventions.")
    L.append("")
    L.append("Fields *not* listed above are compared verbatim under both rules. The verbatim "
             "column is the conservative bound; the normalised column is the figure used in "
             "Section 3.4 because it is the caliber under which the 67-paper gold evaluation "
             "of Section 3.2 is also scored.")
    return L


def build_s8(hum_n, db_n):
    def bands(vals):
        edges = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]
        out = []
        for lo, hi in edges:
            c = sum(1 for v in vals if lo <= v < hi)
            out.append((f"{lo:.1f}–{'1.0' if hi > 1 else f'{hi:.1f}'}", c))
        return out

    def deciles(vals):
        s = sorted(vals)
        n = len(s)
        return [s[min(n - 1, int(p * n))] for p in
                (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]

    L = []
    L.append("## Table S8. Per-paper dispersion of the 100-paper agreement")
    L.append("")
    L.append("An aggregate F1 hides how the agreement is distributed over papers. Both "
             "figures below are computed over the same runs as Table S7 (normalised rule), "
             "weighting every paper equally.")
    L.append("")
    L.append("| Statistic | Human side (100 papers) | Database side (102 papers) |")
    L.append("|---|---|---|")
    for lab, fn in (("mean", lambda v: sum(v) / len(v)),
                    ("median", lambda v: sorted(v)[len(v) // 2]),
                    ("minimum", min), ("maximum", max)):
        L.append(f"| Per-paper macro-F1, {lab} | {f3(fn(hum_n['per_paper_macro']))} | "
                 f"{f3(fn(db_n['per_paper_macro']))} |")
    hq = sorted(hum_n["per_paper_macro"])
    dq = sorted(db_n["per_paper_macro"])
    L.append(f"| Per-paper macro-F1, interquartile range | "
             f"{f3(hq[len(hq)//4])}–{f3(hq[3*len(hq)//4])} | "
             f"{f3(dq[len(dq)//4])}–{f3(dq[3*len(dq)//4])} |")
    L.append(f"| Papers at or above 0.80 | "
             f"{sum(1 for v in hq if v >= 0.8)} / 100 | {sum(1 for v in dq if v >= 0.8)} / 102 |")
    L.append(f"| Papers at or above 0.90 | "
             f"{sum(1 for v in hq if v >= 0.9)} / 100 | {sum(1 for v in dq if v >= 0.9)} / 102 |")
    L.append("")
    L.append("Distribution of per-paper macro-F1:")
    L.append("")
    L.append("| Band | Human side | Database side |")
    L.append("|---|---|---|")
    hb, db_ = bands(hum_n["per_paper_macro"]), bands(db_n["per_paper_macro"])
    for (lab, c1), (_, c2) in zip(hb, db_):
        L.append(f"| {lab} | {c1} | {c2} |")
    L.append("")
    L.append("Deciles of per-paper macro-F1 (human side): "
             + ", ".join(f3(x) for x in deciles(hum_n["per_paper_macro"])) + ".")
    L.append("")
    L.append("Deciles of per-paper macro-F1 (database side): "
             + ", ".join(f3(x) for x in deciles(db_n["per_paper_macro"])) + ".")
    return L


def main():
    hum_src = cv.load_records_dir(cv.DEFAULT_HUMAN)
    db_src = cv.load_records_dir(cv.DEFAULT_DB)
    hum_n = rerun(hum_src, cv._records_match)
    hum_v = rerun(hum_src, _values_match)
    db_n = rerun(db_src, cv._records_match)
    db_v = rerun(db_src, _values_match)

    p7 = OUT_DIR / "si_table_s7_caliber.md"
    p8 = OUT_DIR / "si_table_s8_dispersion.md"
    p7.write_text("\n".join(build_s7(hum_n, hum_v, db_n, db_v)) + "\n", encoding="utf-8")
    p8.write_text("\n".join(build_s8(hum_n, db_n)) + "\n", encoding="utf-8")

    print(f"saved -> {p7.name}")
    print(f"saved -> {p8.name}")
    print("check: human pooled F1", f"{hum_n['overall']['f1']:.4f}", "vs verbatim",
          f"{hum_v['overall']['f1']:.4f}")
    print("check: db    pooled F1", f"{db_n['overall']['f1']:.4f}", "vs verbatim",
          f"{db_v['overall']['f1']:.4f}")


if __name__ == "__main__":
    main()
