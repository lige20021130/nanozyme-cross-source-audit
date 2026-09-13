# -*- coding: utf-8 -*-
"""Brute-force which caliber produces the Fig-5 caption's pooled 4.2e5x.

Target:  min = 0.0028 mM, max = 1175.3 mM, fold = 419,750x  (~4.2e5)
Also target the caption's "26 papers".

Fact established already:
  0.0028 lives at pH 4.6 (10.1088/1361-6463/aa5bf6)
  1175.3 lives at pH 4.4 (10.1016/j.matlet.2013.04.020)
  2951.1 / 2528.4 live at pH 4.5 (10.1039/c6cc08542c)
  2480      lives at pH 4.5 (10.1021/acsami.8b20942)
so ANY window that includes pH 4.5 and excludes pH 4.6 shoots past 1175.3.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from build_wiki import load_papers, collect_entries, flat_values  # noqa: E402

TARGET_LO, TARGET_HI, TARGET_FOLD = 0.0028, 1175.3, 1175.3 / 0.0028


def build(include_atlas=True, include_db=True, mat_filter="fe3o4+ironoxide"):
    srcs = []
    if include_atlas:
        srcs += load_papers(ROOT / "workbench" / "atlas_records")
    if include_db:
        srcs += load_papers(ROOT / "workbench" / "db_records")
    merged = {}
    for p in srcs:
        merged.setdefault(p.get("doi", ""), []).extend(p.get("records", []))
    entries = collect_entries([{"doi": k, "records": v} for k, v in merged.items()])

    pts = []
    for e in entries:
        mk = str(e.get("mat_key") or "").lower()
        act = str(e.get("act") or "").lower()
        sub = str(e.get("sub") or "").lower()
        if "peroxidase" not in act or "h2o2" not in sub:
            continue
        if mat_filter == "fe3o4" and "fe3o4" not in mk:
            continue
        if mat_filter == "fe3o4+ironoxide" and not ("fe3o4" in mk or "ironoxide" in mk):
            continue
        f = flat_values(e)
        if f.get("km_mm") is None:
            continue
        pts.append({"doi": f.get("doi") or "?", "ph": f.get("ph"),
                    "km": float(f["km_mm"]), "mat": mk})
    return pts


def report(tag, pts, ph_lo=None, ph_hi=None, use_pool=True):
    sel = pts
    if ph_lo is not None:
        sel = [d for d in sel if d["ph"] is not None
               and ph_lo <= float(d["ph"]) <= ph_hi]
    if not sel:
        print(f"  {tag:46s} -> EMPTY")
        return False
    lo = min(d["km"] for d in sel)
    hi = max(d["km"] for d in sel)
    n_doi = len({d["doi"] for d in sel})
    fold = hi / lo
    hit = (abs(lo - TARGET_LO) < 0.2 * TARGET_LO
           and abs(hi - TARGET_HI) / TARGET_HI < 0.05)
    mark = "  <== MATCH" if hit else ""
    print(f"  {tag:46s} -> n_pts={len(sel):4d} n_doi={n_doi:3d} "
          f"range={lo:g}-{hi:g} fold={fold:,.0f}x{mark}")
    return hit


found = []
print("TARGET: n_doi=26, range=0.0028-1175.3, fold=419,750x\n")

for matf in ("fe3o4+ironoxide", "fe3o4"):
    for combo, (a, d) in (("atlas only", (True, False)),
                          ("db only", (False, True)),
                          ("atlas+db", (True, True))):
        pts = build(a, d, matf)
        print(f"[mat={matf} | {combo}]  total pts={len(pts)} "
              f"n_doi={len({p['doi'] for p in pts})}")
        for lo, hi in ((None, None), (3.0, 4.5), (3.0, 4.4), (3.0, 4.6),
                       (3.5, 4.6), (4.0, 4.6)):
            tag = "all pH" if lo is None else f"pH {lo}-{hi}"
            if report(f"    {tag}", pts, lo, hi):
                found.append((matf, combo, tag))

print("\nMATCHES:", found if found else "none")
