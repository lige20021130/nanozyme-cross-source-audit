# -*- coding: utf-8 -*-
"""生成 SI 缺失的两张表（2026-09-12 round 14）。

背景：正文/SI 文件清单承诺了 Table S4（166 簇审计台账）与 Table S5（57 对无控条件
普查），但 SI.docx 里只有指向 workbench/atlas_out_multi/*.csv 的路径，表格本身未交付。
审稿人按 SI 找表会落空，核心证据链断裂。本脚本把两张 CSV 确定性转成英文 Markdown
表，供 build_full_manuscript.py 并入 SI。

输入：
- workbench/atlas_out_multi/audit.csv                 （166 行，中文列名）
- workbench/atlas_out_multi/cross_source_conflicts.csv （57 行）
输出：
- paper_drafts/si_table_s4_audit_register.md
- paper_drafts/si_table_s5_census.md

注意：输出必须是纯英文——构建链没有针对 SI 正文的 CJK 剥离逻辑，中文字符会原样
进入 SI.docx。
运行：D:/conda/python.exe workbench/figs/gen_si_extra_tables.py
"""
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "workbench" / "atlas_out_multi"
OUTDIR = ROOT / "paper_drafts"

METRIC = {
    "km_mm": "K\u2098",
    "vmax_um_s": "Vmax",
    "kcat_s": "kcat",
    "catalytic_efficiency": "kcat/K\u2098",
}
SEVERITY = {"严重": "severe", "可疑": "suspicious", "一致": "consistent"}
CAUSE = {
    "跨文献": "cross-literature",
    "单位量级错配?/跨文献": "unit-magnitude mismatch (suspected) / cross-literature",
}


def fmt_fold(x: str) -> str:
    f = float(x)
    if f >= 1e5:
        return f"{f:,.0f}"
    if f >= 100:
        return f"{f:,.0f}"
    return f"{f:.2f}".rstrip("0").rstrip(".")


def fmt_val(x: str) -> str:
    try:
        return f"{float(x):g}"
    except (TypeError, ValueError):
        return str(x)


def s4() -> str:
    rows = list(csv.DictReader((ATLAS / "audit.csv").open(encoding="utf-8-sig")))
    rows.sort(key=lambda r: (-int(r["tier"]), -float(r["倍数"])))
    out = [
        "## Table S4. Full audit register of the 166 conflict clusters",
        "",
        "Every cluster produced by the condition-indexed atlas (`workbench/atlas_out_multi/audit.csv`). "
        "Rows are sorted by audit tier (3 = severe, 2 = suspicious, 1 = consistent) and then by "
        "descending cross-source fold. **Values** lists each underlying record as `DOI=value`, so any "
        "disputed number can be walked back to its paper. **Fold** is max/min across the values in the "
        "cluster; **Metric** names the kinetic constant the cluster is built on. Severity thresholds are "
        "the (max - min)/median relative spread: consistent < 30%, suspicious 30-100%, severe > 100%. A "
        "cross-source fold ladder that coincides with a power of ten carries the "
        "'unit-magnitude mismatch (suspected)' tag; that tag is a screening flag, not a verdict, and the "
        "cases recovered from the source publications are adjudicated group by group in Table S6.",
        "",
        "| # | Material | Activity | Substrate | pH | T (C) | Metric | Severity | Tier | Papers | Fold | Suspected cause | Values (DOI=value) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        vals = " ".join(
            f"`{v.strip()}`" for v in r["逐条取值(DOI=值)"].replace("；", ";").split(";") if v.strip()
        )
        out.append(
            "| {i} | {mat} | {act} | {sub} | {ph} | {t} | {metric} | {sev} | {tier} | {np} | {fold} | {cause} | {vals} |".format(
                i=i,
                mat=r["材料"],
                act=r["酶活"],
                sub=r["底物"],
                ph=r["pH"],
                t=r["温度(℃)"],
                metric=METRIC.get(r["指标"], r["指标"]),
                sev=SEVERITY.get(r["等级"], r["等级"]),
                tier=r["tier"],
                np=r["文献数"],
                fold=fmt_fold(r["倍数"]),
                cause=CAUSE.get(r["疑因标签"], r["疑因标签"]),
                vals=vals or "n/a",
            )
        )
    out += [
        "",
        "*Reading note.* The tier counts are 26 consistent, 43 suspicious and 97 severe. The "
        "unit-magnitude tag appears on 7 clusters. Vmax-based clusters (64 of 166) rest on the field "
        "with the lowest extraction F1 (0.896); Section 5.5 states this reading limit and Table S9 "
        "reports the K\u2098-only sensitivity of the tier distribution.",
        "",
    ]
    return "\n".join(out)


def s5() -> str:
    rows = list(csv.DictReader((ATLAS / "cross_source_conflicts.csv").open(encoding="utf-8-sig")))
    rows.sort(key=lambda r: -float(r["fold"]))
    out = [
        "## Table S5. Cross-source conflict census without condition control (57 pairs)",
        "",
        "Material-substrate pairs for which two or more sources disagree, **without** requiring the "
        "sources to have measured at the same pH (`workbench/atlas_out_multi/cross_source_conflicts.csv`). "
        "This is the looser census; Section 4.3 reports the stricter same-pH census instead (17 of 949 "
        "same-pH buckets above 10-fold; Tables S3 and S6). The two are related by construction and not in "
        "tension: all 17 same-pH groups appear among the 57, and requiring pH agreement removes the other "
        "40, which are conflicts between sources that measured under different conditions.",
        "",
        "| # | DOI | Material | Substrate | Sources | K\u2098 min (mM) | K\u2098 max (mM) | Fold | n sources | Unit uncertain |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        out.append(
            "| {i} | {doi} | {mat} | {sub} | {src} | {lo} | {hi} | {fold} | {n} | {unc} |".format(
                i=i,
                doi=r["doi"],
                mat=r["material"],
                sub=r["substrate"],
                src=r["sources"].replace(";", ", "),
                lo=fmt_val(r["min_km"]),
                hi=fmt_val(r["max_km"]),
                fold=fmt_fold(r["fold"]),
                n=r["n_sources"],
                unc=(r.get("unit_uncertain") or "no"),
            )
        )
    folds = sorted(float(r["fold"]) for r in rows)
    out += [
        "",
        "*Summary.* 57 pairs spanning {lo} - {hi} fold; {a} pairs >= 5x, {b} >= 10x, {c} >= 100x.".format(
            lo=fmt_fold(folds[0]),
            hi=fmt_fold(folds[-1]),
            a=sum(1 for x in folds if x >= 5),
            b=sum(1 for x in folds if x >= 10),
            c=sum(1 for x in folds if x >= 100),
        ),
        "",
    ]
    return "\n".join(out)


def s9() -> str:
    rows = list(csv.DictReader((ATLAS / "audit.csv").open(encoding="utf-8-sig")))
    hasna = lambda r: "na-" in r["逐条取值(DOI=值)"]  # noqa: E731

    def block(sel):
        c = collections.Counter(r["等级"] for r in sel)
        folds = [float(r["倍数"]) for r in sel]
        return (
            len(sel), c["一致"], c["可疑"], c["严重"],
            sum(1 for x in folds if x >= 1e4), sum(1 for x in folds if x >= 1e6),
        )

    def share(sel):
        c = collections.Counter(r["等级"] for r in sel)
        return 100.0 * c["严重"] / len(sel) if sel else 0.0

    out = [
        "## Table S9. Robustness of the conflict-atlas tier distribution",
        "",
        "Panel (a) breaks the 166 clusters down by kinetic metric. Panel (b) recomputes the "
        "tier distribution with every cluster that contains a record from the one source which "
        "publishes no DOIs (nanozymenet-k) removed. Panel (c) does the same for Vmax, the "
        "weakest extracted field (F1 0.896, Section 3.2). Panels (b) and (c) are the two ways "
        "in which the severity structure could have been an artifact of our own weak inputs; "
        "in both cases it survives.",
        "",
        "**(a) By kinetic metric**",
        "",
        "| Metric | Clusters | Consistent | Suspicious | Severe | Severe share | Max fold | Unit-magnitude tag |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, label in (("km_mm", "K\u2098"), ("vmax_um_s", "Vmax"), ("kcat_s", "kcat")):
        sel = [r for r in rows if r["指标"] == key]
        n, cc, cs, sv, _, _ = block(sel)
        mx = max(float(r["倍数"]) for r in sel)
        tag = sum(1 for r in sel if r["疑因标签"].startswith("单位"))
        out.append(f"| {label} | {n} | {cc} | {cs} | {sv} | {share(sel):.1f}% | {mx:,.0f} | {tag} |")
    n, cc, cs, sv, ge4, ge6 = block(rows)
    mx = max(float(r["倍数"]) for r in rows)
    tag = sum(1 for r in rows if r["疑因标签"].startswith("单位"))
    out.append(f"| **all metrics** | **{n}** | **{cc}** | **{cs}** | **{sv}** | **{share(rows):.1f}%** | **{mx:,.0f}** | **{tag}** |")

    keep = [r for r in rows if not hasna(r)]
    drop = [r for r in rows if hasna(r)]
    out += [
        "",
        "**(b) Excluding every cluster that contains a non-DOI record**",
        "",
        "| Set | Clusters | Consistent | Suspicious | Severe | Clusters >= 10\u2074x | Clusters >= 10\u2076x |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, sel in (("all clusters", rows), ("excluding the non-DOI clusters", keep), ("the clusters removed", drop)):
        n, cc, cs, sv, ge4, ge6 = block(sel)
        out.append(f"| {label} | {n} | {cc} | {cs} | {sv} | {ge4} | {ge6} |")

    out += [
        "",
        "**(c) Reading limit of the weakest field**",
        "",
        "| Set | Clusters | Severe share |",
        "|---|---|---|",
    ]
    for label, sel in (
        ("K\u2098 clusters only", [r for r in rows if r["指标"] == "km_mm"]),
        ("Vmax clusters only", [r for r in rows if r["指标"] == "vmax_um_s"]),
        ("all clusters", rows),
    ):
        out.append(f"| {label} | {len(sel)} | {share(sel):.1f}% |")
    out += [
        "",
        "*Reading.* Removing every cluster touched by the no-DOI source costs 6 of the 97 severe "
        "clusters and 6 of the 11 clusters at or above 10\u2076-fold, but leaves 91 severe clusters "
        "standing; restricting to K\u2098 alone leaves 48 of 91 severe clusters. The audit's "
        "conclusion therefore does not depend on the unverified source or on the weak Vmax field. "
        "Generated from `workbench/atlas_out_multi/audit.csv`; thresholds as in Section 5.2 "
        "(consistent < 30%, suspicious 30-100%, severe > 100% relative spread).",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    p4 = OUTDIR / "si_table_s4_audit_register.md"
    p5 = OUTDIR / "si_table_s5_census.md"
    p9 = OUTDIR / "si_table_s9_atlas_robustness.md"
    p4.write_text(s4(), encoding="utf-8")
    p5.write_text(s5(), encoding="utf-8")
    p9.write_text(s9(), encoding="utf-8")
    n4 = sum(1 for l in p4.read_text(encoding="utf-8").splitlines() if l.startswith("| ") and "---" not in l)
    n5 = sum(1 for l in p5.read_text(encoding="utf-8").splitlines() if l.startswith("| ") and "---" not in l)
    print(f"saved -> {p4} (data rows ~{n4 - 1})")
    print(f"saved -> {p5} (data rows ~{n5 - 1})")
    print(f"saved -> {p9}")
    for p in (p4, p5, p9):
        txt = p.read_text(encoding="utf-8")
        bad = [c for c in txt if "\u4e00" <= c <= "\u9fff"]
        print(f"[cjk-check] {p.name}: CJK chars = {len(bad)}")


if __name__ == "__main__":
    main()
