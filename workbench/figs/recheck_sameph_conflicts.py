# -*- coding: utf-8 -*-
"""复核 §4.3 同 pH 跨源冲突口径（2026-09-10 复核脚本的存档化重写）。

口径：按 (doi, nanozyme, kinetic_substrate, buffer_ph_value) 精确分组，
组内跨源（provenance ≥2）且 Km≥10× → 计入；统计 fold≥10 / ≥100 组数，
与正文 §4.3 的 17 组 / 14 组核对。输出 fig4a 用的 fold 分布 json。
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from build_wiki import load_papers  # noqa: E402

folds = []
for records_dir in ("workbench/atlas_records", "workbench/db_records"):
    for p in load_papers(ROOT / records_dir):
        for r in p.get("records", []):
            if not (r.get("Km_mM") and r.get("buffer_ph_value") is not None
                    and r.get("nanozyme")):
                continue
            folds.append((str(r.get("doi") or ""), str(r["nanozyme"]),
                          str(r.get("kinetic_substrate") or ""),
                          round(float(r["buffer_ph_value"]), 2),
                          str(r.get("provenance") or ""), float(r["Km_mM"])))

groups = defaultdict(list)
for doi, mat, sub, ph, src, km in folds:
    groups[(doi, mat, sub, ph)].append((src, km))

rows = []
for key, items in groups.items():
    if len({s for s, _ in items}) < 2:
        continue
    by_src = defaultdict(list)
    for s, km in items:
        by_src[s].append(km)
    combined = sorted(v for vs in by_src.values() for v in vs)
    lo, hi = combined[0], combined[-1]
    if lo <= 0 or hi <= 0:
        continue
    rows.append({"key": key, "sources": sorted(by_src), "min_km": lo,
                 "max_km": hi, "fold": hi / lo,
                 "n_sources": len(by_src)})

over10 = [r for r in rows if r["fold"] >= 10]
over100 = [r for r in rows if r["fold"] >= 100]
# 同 DOI+材料 可能拆出多个 pH 桶，论文口径是"材料-底物对"级冲突组，
# 故按 (doi, material, substrate) 去重后再计数：
seen = set()
grp_uniq = [r for r in over10 if not
            (r["key"][0], r["key"][1], r["key"][2]) in seen and not
            seen.add((r["key"][0], r["key"][1], r["key"][2]))]
print(f"同pH冲突桶（fold>=10）：{len(over10)} 桶 / 去重后 {len(grp_uniq)} 组")
print(f"fold>=100：{len(over100)} 桶")
import json as _j
(ROOT / "workbench" / "figs" / "fig4_conflicts_sameph.json").write_text(
    _j.dumps({"total_groups": len(rows), "over10": len(grp_uniq),
              "over10_buckets": len(over10), "over100": len(over100),
              "rows": [{**{k: v for k, v in r.items() if k != "key"},
                        "doi": r["key"][0], "material": r["key"][1],
                        "substrate": r["key"][2], "ph": r["key"][3]}
                       for r in sorted(rows, key=lambda x: -x["fold"])]},
    ensure_ascii=False, indent=2), encoding="utf-8")
print("saved -> workbench/figs/fig4_conflicts_sameph.json")