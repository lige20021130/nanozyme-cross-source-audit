# -*- coding: utf-8 -*-
"""Why does the Fig-5 caption's pooled figure (0.0028-1175.3 mM = 4.2e5x) not
reproduce from the current data?  List the extreme Km points so we can see
which entry moved.

Source of record: manuscript_sections3_6_merged.md
  "| Fe3O4 同条件 2434x / 全局 4.2x10^5 | 2026-09-10 重建 conflict_by_condition
   (atlas_records+multi_records 合并) | pH4.0/25C 五篇 0.076~185；
   全局 26 篇 0.0028~1175.3（pH3.0-4.5） |"

NOTE flat_values() keys are lowercase: km_mm / ph / temperature_c / doi.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from build_wiki import load_papers, collect_entries, flat_values  # noqa: E402

papers = load_papers(ROOT / "workbench" / "atlas_records")
multi = load_papers(ROOT / "workbench" / "db_records")
merged = {}
for p in list(papers) + list(multi):
    merged.setdefault(p.get("doi", ""), []).extend(p.get("records", []))
papers_merged = [{"doi": k, "records": v} for k, v in merged.items()]
entries = collect_entries(papers_merged)


def is_fe3o4_entry(e):
    mk = str(e.get("mat_key") or "").lower()
    act = str(e.get("act") or "").lower()
    sub = str(e.get("sub") or "").lower()
    return (("fe3o4" in mk or "ironoxide" in mk)
            and "peroxidase" in act and "h2o2" in sub)


pts = []
for e in entries:
    if not is_fe3o4_entry(e):
        continue
    f = flat_values(e)
    v = f.get("km_mm")
    if v is None:
        continue
    pts.append({"doi": f.get("doi") or e.get("paper_doi") or "?",
                "ph": f.get("ph"), "t": f.get("temperature_c"),
                "km": float(v), "prov": f.get("provenance")})

pts.sort(key=lambda d: d["km"])
print(f"Fe3O4/peroxidase/H2O2 Km points: {len(pts)}")
print(f"distinct DOIs                 : {len({d['doi'] for d in pts})}  (caption: '26 papers')")
print(f"min Km = {pts[0]['km']:g} mM      (source of record: 0.0028)")
print(f"max Km = {pts[-1]['km']:g} mM    (source of record: 1175.3)")
print(f"overall fold = {pts[-1]['km']/pts[0]['km']:,.0f}x")

print("\n-- 8 LOWEST --")
for d in pts[:8]:
    print(f"  Km={d['km']:<12g} pH={str(d['ph']):>5s} T={str(d['t']):>5s} "
          f"{str(d['doi'])[:40]}")

print("\n-- 8 HIGHEST --")
for d in pts[-8:][::-1]:
    print(f"  Km={d['km']:<12g} pH={str(d['ph']):>5s} T={str(d['t']):>5s} "
          f"{str(d['doi'])[:40]}")

for target in (0.0028, 1175.3, 1175.4, 2951.1):
    hit = [d for d in pts if abs(d["km"] - target) / target < 2e-3]
    print(f"\ntarget {target:g} mM -> {len(hit)} point(s)")
    for d in hit:
        print(f"   pH={d['ph']} T={d['t']} {str(d['doi'])[:42]}")

# ---- fold under the source-of-record's pH window ----
inwin = [d for d in pts if d["ph"] is not None and 3.0 <= float(d["ph"]) <= 4.5]
print(f"\n-- points with pH in [3.0, 4.5]: {len(inwin)} --")
if inwin:
    lo = min(d["km"] for d in inwin)
    hi = max(d["km"] for d in inwin)
    print(f"   range = {lo:g}-{hi:g} mM   fold = {hi/lo:,.0f}x")
    print(f"   pH span = {min(float(d['ph']) for d in inwin)}-"
          f"{max(float(d['ph']) for d in inwin)}")

print(f"\npH values present overall: "
      f"{sorted({float(d['ph']) for d in pts if d['ph'] is not None})}")
