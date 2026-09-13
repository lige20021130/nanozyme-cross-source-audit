# -*- coding: utf-8 -*-
"""一链 CLI：records → 冲突谱 PNG（X）→ 指纹网络 graphml（Y）→ 审计 CSV（Z）。

v2：`--multi-records`（source_registry.prepare 产物）与原 records 并集计算 X/Y/Z，
并以 provenance 分布 + lineage 三件套（谱系矩阵/跨源冲突/覆盖盲区）收口。
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="知识图谱产出一链（X/Y/Z，v2 支持多源）")
    ap.add_argument("--records", required=True, help="records 目录（excel_source.prepare 产物）")
    ap.add_argument("--multi-records", help="（v2）source_registry.prepare 产出目录，与 records 并集计算 X/Y/Z")
    ap.add_argument("--lineage-out", help="（v2）谱系矩阵/跨源冲突 CSV 输出目录（默认 --out）")
    ap.add_argument("--out", required=True, help="产出目录（放 png/graphml/csv）")
    ap.add_argument("--metric", default="km_mm", choices=("km_mm", "vmax_um_s", "kcat_s"))
    ap.add_argument("--limit-atlas", type=int, default=12)
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from build_wiki import load_papers, collect_entries, flat_values
    from kg import conflict_atlas as ca, fingerprint as fp, audit_state as aus

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    papers = load_papers(Path(args.records))
    multi_dir = Path(args.multi_records) if args.multi_records else None
    if multi_dir and multi_dir.exists():
        multi_papers = load_papers(multi_dir)
        merged: dict[str, list] = {}
        for p in list(papers) + list(multi_papers):
            merged.setdefault(p.get("doi", ""), []).extend(p.get("records", []))
        papers = [{"doi": k, "records": v} for k, v in merged.items()]
        print(f"[atlas] multi-source merged: excel_papers={len(papers) - len(multi_papers)} + db_papers={len(multi_papers)}")
    entries = collect_entries(papers)
    print(f"[atlas] papers={len(papers)} entries={len(entries)}")

    # conflict_atlas / fingerprint 消费"摊平"的条目（ph/temperature_c/指标值在顶层）。
    # collect_entries 的 entry 把这些值嵌在 rec 里，故先 flat_values 摊平并补上 act/sub。
    flat_entries = []
    for e in entries:
        f = flat_values(e)
        f["act"] = e.get("act", "")
        f["sub"] = e.get("sub", "")
        flat_entries.append(f)

    # X: 冲突谱
    clusters = ca.conflict_by_condition(flat_entries, metric=args.metric)
    made = ca.render_all(clusters, out / "atlas", limit=args.limit_atlas)
    print(f"[X] 条件簇={len(clusters)} PNG={len(made)}")

    # Y: 指纹网络（fingerprint 对 ph 做 float()，缺 ph 的行跳过以避免 TypeError）
    rows = [f for f in flat_entries if f.get("ph") is not None and f.get("km_mm") is not None]
    g = fp.material_similarity(rows)
    gml = out / "material_similarity.graphml"
    fp.write_graphml(g, gml)
    print(f"[Y] 材料节点={g.number_of_nodes()} 相似边={g.number_of_edges()} -> {gml.name}")

    # Z: 审计 CSV（复用 conflict 判定簇）
    from kg.conflict import find_conflicts
    groups = {m: find_conflicts(entries, metric=m) for m in ("km_mm", "vmax_um_s", "kcat_s")}
    allc = [c for g in groups.values() for c in g]
    csvp = out / "audit.csv"
    n = aus.write_audit_csv(allc, csvp)
    print(f"[Z] 审计簇={n} -> {csvp.name}")

    # v2: provenance 分布 + lineage 三件套（spec §3.2）
    prov = dict(Counter(f.get("provenance", "?") for f in flat_entries))
    lineage_stats = None
    if multi_dir and multi_dir.exists():
        from kg import lineage
        excel_rows = [r for p in load_papers(Path(args.records)) for r in p.get("records", [])]
        db_rows = [r for p in load_papers(multi_dir) for r in p.get("records", [])]
        conflicts = lineage.cross_source_conflicts(excel_rows + db_rows)
        lineage_out = Path(args.lineage_out) if args.lineage_out else out
        lineage_stats = lineage.write_stats(lineage_out, excel_rows, db_rows, conflicts)
        print(f"[lineage] multi-source DOI={lineage_stats['n_multi_source_doi']} "
              f"conflicts={lineage_stats['n_cross_source_conflicts']} "
              f"materials_db_only={lineage_stats['n_materials_db_only']}")

    # 汇总
    summary = {
        "papers": len(papers), "entries": len(entries),
        "metric": args.metric,
        "n_conflict_clusters": len(allc),
        "atlas_png": made,
        "similarity_nodes": g.number_of_nodes(),
        "similarity_edges": g.number_of_edges(),
        "provenance": prov,
    }
    if lineage_stats:
        summary["lineage"] = lineage_stats
    (out / "atlas_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())