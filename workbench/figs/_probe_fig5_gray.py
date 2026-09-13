# -*- coding: utf-8 -*-
"""Assert that the Fig-5 caption's numbers are reproducible from the corpus.

Published caption (since 2026-09-11):
  target cluster : 5 papers, pH 4.0, Km 0.076-185 mM, 2,434-fold
  pooled (gray)  : 130 points / 34 DOIs, Km 0.0028-2951.1 mM, 1,053,964-fold

The previous values ("26 papers", "0.0028-1175.3 mM", "4.2e5-fold") were
unreproducible and were replaced; see memory log 2026-09-11 round 10.

fig_fe3o4 draws:
  - target  : one condition cluster (pH 4.0, 25 C)
  - gray    : EVERY point of EVERY cluster returned by conflict_by_condition
              (which drops singleton clusters, len(c) < 2)

So the "pooled" set is the cluster-point set, NOT all selected entries.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from build_wiki import load_papers, collect_entries, flat_values  # noqa: E402
from kg import conflict_atlas as ca  # noqa: E402

papers = load_papers(ROOT / "workbench" / "atlas_records")
multi = load_papers(ROOT / "workbench" / "db_records")
merged = {}
for p in list(papers) + list(multi):
    merged.setdefault(p.get("doi", ""), []).extend(p.get("records", []))
entries = collect_entries([{"doi": k, "records": v} for k, v in merged.items()])


def to_flat(e):
    f = flat_values(e)
    f["act"] = e.get("act", "")
    f["sub"] = e.get("sub", "")
    return f


sel = [to_flat(e) for e in entries
       if ("fe3o4" in str(e.get("mat_key") or "").lower()
           or "ironoxide" in str(e.get("mat_key") or "").lower())
       and "peroxidase" in str(e.get("act") or "").lower()
       and "h2o2" in str(e.get("sub") or "").lower()]

withph = [e for e in sel if e.get("ph") is not None and e.get("km_mm") is not None]
print(f"selected entries (Km + pH present) : {len(withph)}")
print(f"  distinct DOIs                     : {len({e['doi'] for e in withph})}")

clusters = ca.conflict_by_condition(sel, metric="km_mm")
cpts = [p for cl in clusters for p in cl["ph_points"] if p.get("value") is not None]
print(f"\nclusters returned (>=2 pts each)    : {len(clusters)}")
print(f"cluster points (the gray cloud)     : {len(cpts)}")
print(f"  distinct DOIs behind gray cloud   : {len({p['doi'] for p in cpts})}"
      f"   <-- caption (since 2026-09-11) says '34 papers'")

lo = min(p["value"] for p in cpts)
hi = max(p["value"] for p in cpts)
print(f"  range = {lo:g}-{hi:g} mM")
print(f"  fold  = {hi/lo:,.0f}x     <-- caption says 1.05e6 (= 1,053,964x)")

# same, restricted to pH 3.0-4.5
inwin = [p for p in cpts if 3.0 <= p["ph"] <= 4.5]
if inwin:
    wlo = min(p["value"] for p in inwin)
    whi = max(p["value"] for p in inwin)
    print(f"\npH 3.0-4.5 subset: n={len(inwin)} "
          f"doi={len({p['doi'] for p in inwin})} "
          f"range={wlo:g}-{whi:g} fold={whi/wlo:,.0f}x")

# how many entries were dropped as singletons
print(f"\nsingleton points NOT plotted        : {len(withph) - len(cpts)}")

# ------------------------------------------------------------------ assertion
# These are the numbers now published in the Fig-5 caption / §4.4 / §5.2.
# If the corpus changes, this fails loudly instead of letting the caption drift.
CLAIM_DOI = 34
CLAIM_LO, CLAIM_HI = 0.0028, 2951.1
CLAIM_FOLD = 1053964

# target (same-condition) cluster, same selection rule as fig_fe3o4
target = None
for cl in clusters:
    phs = [p["ph"] for p in cl["ph_points"]]
    if 3.7 <= (min(phs) + max(phs)) / 2 <= 4.3 and cl["n_papers"] >= 3:
        target = cl

print("\n-- caption assertion (Figure 5) --")
checks = [
    ("pooled n_doi == 34", len({p['doi'] for p in cpts}), CLAIM_DOI),
    ("pooled min Km == 0.0028", round(lo, 4), CLAIM_LO),
    ("pooled max Km == 2951.1", round(hi, 1), CLAIM_HI),
    ("pooled fold == 1,053,964", round(hi / lo), CLAIM_FOLD),
]
if target is None:
    print("  [FAIL] target (same-condition) cluster not found")
    checks.append(("target cluster present", False, True))
else:
    tv = [p["value"] for p in target["ph_points"] if p.get("value")]
    checks += [
        ("target n_papers == 5", target["n_papers"], 5),
        ("target min Km == 0.076", round(min(tv), 3), 0.076),
        ("target max Km == 185", round(max(tv), 1), 185.0),
        ("target fold == 2,434", round(max(tv) / min(tv)), 2434),
    ]

ok = True
for name, got, want in checks:
    good = got == want
    ok &= good
    print(f"  [{'OK  ' if good else 'FAIL'}] {name:26s} got={got}  want={want}")
print("RESULT:", "CAPTION REPRODUCIBLE" if ok else "CAPTION DRIFTED — update caption")


