# -*- coding: utf-8 -*-
"""Fig 6 (paper): Fe3O4-peroxidase-H2O2 冲突簇重绘（复用 conflict_atlas.conflict_by_condition）。

与 §4.4/§5.2 同口径（pH±0.2 / T±2°C 贪心聚类，n_papers>=2 才算簇）。
输出两图：
- fig6_fe3o4_cluster.png：全图（所有 Fe3O4 POD H2O2 簇叠加，(pH, Km log) 散点，DOI 标注）
- 控制台打印同条件 2434× 簇明细，与正文核对。
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from build_wiki import load_papers, collect_entries, flat_values  # noqa: E402
from kg import conflict_atlas as ca  # noqa: E402

OUT = ROOT / "workbench" / "figs"

# 重建集成层 entries（atlas_records + db_records 合并，与 build_kg_atlas main 相同）
papers = load_papers(ROOT / "workbench" / "atlas_records")
multi = load_papers(ROOT / "workbench" / "db_records")
merged: dict[str, list] = {}
for p in list(papers) + list(multi):
    merged.setdefault(p.get("doi", ""), []).extend(p.get("records", []))
papers_merged = [{"doi": k, "records": v} for k, v in merged.items()]
entries = collect_entries(papers_merged)
flat = []
for e in entries:
    f = flat_values(e)
    f["act"] = e.get("act", "")
    f["sub"] = e.get("sub", "")
    flat.append(f)

# Fe3O4 POD H2O2 限定
def is_fe3o4(name: str) -> bool:
    n = str(name or "").lower().replace(" ", "").replace("_", "-")
    return "fe3o4" in n or "ironoxide" in n

sel = [f for f in flat
       if is_fe3o4(f.get("material")) and "peroxidase" in str(f.get("act") or "").lower()
       and "h2o2" in str(f.get("sub") or "").lower()]
print(f"selected rows: {len(sel)}")

# 直接用 conflict_atlas 对所有 entry 建簇（得到多簇），再筛 fe3o4 POD H2O2
# 注意：conflict_by_condition 消费 flat_values 摊平后的 entry（ph/km 在顶层），
# 与 build_kg_atlas.main 的 flat_entries 构造一致。
def to_flat_entry(e):
    f = flat_values(e)
    f["act"] = e.get("act", "")
    f["sub"] = e.get("sub", "")
    return f

def is_fe3o4_entry(e):
    mk = str(e.get("mat_key") or "").lower()
    act = str(e.get("act") or "").lower()
    sub = str(e.get("sub") or "").lower()
    return (("fe3o4" in mk or "ironoxide" in mk)
            and "peroxidase" in act and "h2o2" in sub)

clusters = ca.conflict_by_condition(
    [to_flat_entry(e) for e in entries if is_fe3o4_entry(e)], metric="km_mm")
print(f"Fe3O4 POD/H2O2 条件簇: {len(clusters)}")

target = None
for cl in clusters:
    print(f"  cluster n_points={cl['n_points']} n_papers={cl['n_papers']}  "
          f"pH {min(p['ph'] for p in cl['ph_points']):.2f}-{max(p['ph'] for p in cl['ph_points']):.2f}")
    # 找 pH4.0±0.3 且 n_papers>=3 的主簇（对应 2434× 案例）
    if 3.7 <= (min(p["ph"] for p in cl["ph_points"])
               + max(p["ph"] for p in cl["ph_points"])) / 2 <= 4.3 and cl["n_papers"] >= 3:
        target = cl
        vals = [p["value"] for p in cl["ph_points"] if p.get("value")]
        print(f"    >>> 主簇: values {min(vals):g}-{max(vals):g}  "
              f"fold={max(vals)/min(vals):,.0f}x  papers={cl['n_papers']}")

# 渲染主簇
fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=300)
plotted = 0
for cl in clusters:
    pts = [(p["ph"], p.get("value")) for p in cl["ph_points"] if p.get("value") is not None]
    for x, y in pts:
        ax.scatter(x, y, s=46, color="#4C72B0", edgecolor="black", linewidth=0.4, zorder=3)
    for p in cl["ph_points"]:
        if p.get("value") is None:
            continue
        lab = p["doi"].split("/")[-1][:11]
        ax.annotate(lab, (p["ph"], p["value"]), textcoords="offset points",
                    xytext=(3, 3), fontsize=5.5, color="#333333")
        plotted += 1
ax.set_yscale("log")
ax.set_xlabel("pH")
ax.set_ylabel(r"$K_m$ (mM), log scale")
ax.set_title(r"Fe$_3$O$_4$ · peroxidase × H$_2$O$_2$ — condition-resolved $K_m$",
             fontsize=11, loc="left")
if target:
    vals = [p["value"] for p in target["ph_points"] if p.get("value")]
    lo, hi = min(vals), max(vals)
    ax.text(0.03, 0.95,
            f"same-condition cluster ({target['n_papers']} papers, "
            f"pH {min(p['ph'] for p in target['ph_points']):.1f}\u2013"
            f"{max(p['ph'] for p in target['ph_points']):.1f}):\n"
            f"$K_m$ {lo:g}\u2013{hi:g} mM \u00b7 fold {hi/lo:,.0f}\u00d7",
            transform=ax.transAxes, fontsize=8.5, color="#C44E52",
            va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.35", fc="#FBE3E4", ec="#C44E52", alpha=0.85))
ax.grid(True, which="both", ls=":", alpha=0.35)
fig.tight_layout()
out = OUT / "fig6_fe3o4_cluster.png"
fig.savefig(out, bbox_inches="tight")
plt.close(fig)
print(f"saved -> {out} (points={plotted})")