# -*- coding: utf-8 -*-
"""Fig 2 + Fig 4 + Fig 7 数据图生成（Track 1 论文）。

输出：workbench/figs/fig2_scale.png / fig4_units.png / fig7_tiers.png（300 dpi）
数据源：
- Fig2: workbench/atlas_out_multi/atlas_summary.json（entries/doi/provenance/lineage）
- Fig4a: workbench/atlas_out_multi/cross_source_conflicts.csv（fold 分布）
- Fig4b/c: workbench/db_records/10.1038_s41467-018-03903-8.json + 10.1021_acsami.6b05354.json
- Fig7: workbench/atlas_out_multi/audit.csv（tier/指标分布）
运行：conda run -n base python workbench/figs/figs_data.py
"""
import json
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "workbench" / "atlas_out_multi"
OUT = ROOT / "workbench" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

# 统一字体/样式（期刊基调）
plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
})

# 审计 tier 的有序配色（与 figs_v2.py 保持同步，2026-09-11）：Okabe-Ito 蓝→橙→朱红。
# 原 green/yellow/red 在红绿色盲下 tier 1 与 tier 3 不可区分；两图共用同一组才可互读。
TIER_COLOR = {1: "#0072B2", 2: "#E69F00", 3: "#D55E00"}


# ---------------------------------------------------------------- Fig 2
def fig2():
    s = json.loads((ATLAS / "atlas_summary.json").read_text(encoding="utf-8"))
    prov = s["provenance"]           # {human, db:ai-zymes, ...}
    entries = s["entries"]           # 5027
    doi_total = s["lineage"]["n_doi"]          # 761
    doi_multi = s["lineage"]["n_multi_source_doi"]  # 388

    labels = ["Human Excel", "AI-ZYMES", "DiZyme", "NanozymeDB", "nanozymenet-k"]
    raw = [prov.get("human", 0),   prov.get("db:ai-zymes", 0),
           prov.get("db:dizyme", 0), prov.get("db:nanozymedb", 0),
           prov.get("db:nanozymenet-k", 0)]

    # 2026-09-12：原 (b) 面板（761 DOI 的单源/多源堆叠）与 Fig 1 集成层框里的
    # "761 DOIs · 388 multi-source" 完全重复，属同一数字出两图；而 Fig 7 的
    # tier/metric 分布别处无覆盖，不宜与来源覆盖硬拼（一个讲来源、一个讲冲突严重度，
    # 读者无法互读）。故 Fig 2 收为单面板，重叠数字移入图注并以 "see also Figure 1" 留痕。
    fig, ax = plt.subplots(1, 1, figsize=(4.8, 3.4), dpi=300)
    # 配色为 Okabe-Ito 五色（2026-09-11）：原 [蓝,绿,红,紫,黄] 让 AI-ZYMES（绿）
    # 与 DiZyme（红）相邻，红绿相邻正是色盲下最不可区分的组合。改用 Okabe-Ito 并
    # 调序，使绿与朱红之间隔一个天蓝。柱高有数值标注兜底。
    colors = ["#0072B2", "#E69F00", "#009E73", "#56B4E9", "#D55E00"]
    bars = ax.bar(labels, raw, color=colors, width=0.62)
    ax.set_ylabel("Condition-bound entries")
    ax.set_title("Entries per provenance group", loc="left")
    for b, v in zip(bars, raw):
        ax.text(b.get_x() + b.get_width()/2, v + 15, f"{v:,}",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(raw) * 1.15)
    ax.tick_params(axis="x", rotation=20, labelsize=9)

    fig.tight_layout()
    fig.savefig(OUT / "fig2_scale.png", bbox_inches="tight")
    plt.close(fig)
    print(f"[fig2] entities={entries} doi={doi_total} multi={doi_multi} -> fig2_scale.png")


# ---------------------------------------------------------------- Fig 4
# 已迁移到 figs_v2.py（2026-09-11）：fig4 需要两行布局才能保证双栏下字号 >= 6.5 pt，
# 且 (b)(c) 改为按阵营（camp）上色 + 斜纹。本文件保留旧实现会让"只跑 figs_data.py"
# 的人拿到被覆盖前的退稿风险版本（seaborn 红绿），故整段删除，只留此指针。
# 见：FIGS_DIR/figs_v2.py -> fig4()


# ---------------------------------------------------------------- Fig 7
def fig7():
    tiers = {1: 0, 2: 0, 3: 0}
    metrics = {"km_mm": 0, "vmax_um_s": 0, "kcat_s": 0}
    with open(ATLAS / "audit.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t = str(row.get("tier", "")).strip()
            m = str(row.get("指标", "")).strip()
            try:
                t = int(t)
            except ValueError:
                continue
            if t in tiers:
                tiers[t] += 1
            if m == "km_mm":
                metrics["km_mm"] += 1
            elif m == "vmax_um_s":
                metrics["vmax_um_s"] += 1
            elif m == "kcat_s":
                metrics["kcat_s"] += 1

    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.2), dpi=300)
    # (a) tier 分布
    ax = axes[0]
    names = ["tier 1\nconsistent", "tier 2\nsuspicious", "tier 3\nsevere"]
    vals = [tiers[1], tiers[2], tiers[3]]
    # tier 配色与 fig6_atlas 共用同一 Okabe-Ito 有序三元组（2026-09-11 起，
    # 替换原 green/yellow/red：红绿在色盲下不可区分，且与图集图必须可互读）
    colors = [TIER_COLOR[1], TIER_COLOR[2], TIER_COLOR[3]]
    bars = ax.bar(names, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha="center", fontsize=9)
    ax.set_ylabel("Clusters")
    ax.set_title(f"(a) Audit tiers ({sum(vals):d} clusters)", loc="left")
    ax.set_ylim(0, max(vals) * 1.15)

    # (b) 指标构成
    ax = axes[1]
    mnames = ["Km", "Vmax", "Kcat"]
    mvals = [metrics["km_mm"], metrics["vmax_um_s"], metrics["kcat_s"]]
    bars = ax.bar(mnames, mvals, color="#0072B2")
    for b, v in zip(bars, mvals):
        ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha="center", fontsize=9)
    ax.set_ylabel("Clusters")
    ax.set_title("(b) By kinetic metric", loc="left")
    ax.set_ylim(0, max(mvals) * 1.15)

    fig.tight_layout()
    fig.savefig(OUT / "fig7_tiers.png", bbox_inches="tight")
    plt.close(fig)
    print(f"[fig7] tiers={tiers} metrics={metrics} -> fig7_tiers.png")


if __name__ == "__main__":
    # fig4 已于 2026-09-11 迁移到 figs_v2.py（两行布局，双栏字号 >= 6.5 pt）
    fig2()
    fig7()
    print("all done -> workbench/figs/")