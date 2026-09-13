# -*- coding: utf-8 -*-
"""Track 1 论文图 v2：新增 fig1/fig5/fig8，重做 fig3/fig6，修订 fig4。

产出（workbench/figs/）：
- fig1_overview.png        论文总览（黑白无填充框图，§1/投稿 Fig. 1）
- fig3_extract_eval.png    重做：(a) 管线示意规整化 + (b)(c) 评估（§3, Fig. 3）
- fig4_units.png           修订：阈值线标注移图框上方、(c) 标题改 two-camp（§4, Fig. 4）
- fig5_fe3o4_cluster.png   重做：主簇高亮、取消逐点 DOI 标注（§4.4, Fig. 5）
- fig6_atlas.png           新增：166 簇 (pH, T) 投影，tier 着色（§5.1, Fig. 6）
- fig8_leakage.png         新增：随机 vs DOI 分组 分类/回归对比（§6, Fig. 8）
fig2/fig7 由 figs_data.py 生成，保留。

运行：D:/conda/python.exe workbench/figs/figs_v2.py
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "workbench" / "atlas_out_multi"
OUT = ROOT / "workbench" / "figs"
MS = ROOT / "workbench" / "model_swap_out"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
})

# 全局调色板（2026-09-11 二次修订）：原为 seaborn-deep（#4C72B0/#55A868/#C44E52/
# #CCB974），其中 #55A868（绿）与 #C44E52（红）同时出现在 fig3 的 (b)(c) 两面板，
# 构成红绿相邻——正是红绿色盲下最不可区分的一对，与稿件"采用 Okabe-Ito 色盲安全
# 配色"的声明不符，属期刊退稿风险点。统一换成 Okabe-Ito（Wong 2011, Nat Methods 8:441）
# 六色：蓝 / 蓝绿 / 朱红 / 橙 / 紫红 / 中性灰。语义顺序不变（RED 仍是"越界/高风险"，
# BLUE 仍是"基准/正常"），因此各面板的读数逻辑无需改动。
BLUE, GREEN, RED, YELLOW, PURPLE, GRAY = ("#0072B2", "#009E73", "#D55E00",
                                          "#E69F00", "#CC79A7", "#999999")

# 审计 tier 的有序配色（2026-09-11）：原 green/yellow/red 是红绿对比，在
# 红绿色盲下 tier 1 与 tier 3 不可区分，属期刊常见退稿原因。改用 Okabe-Ito
# （Wong 2011, Nat Methods 8:441）的蓝→橙→朱红三元组：色盲安全且保留"冷→热"
# 的严重度次序语义。fig6_atlas 与 fig7_tiers 必须使用同一组，否则两图不可互读。
TIER_COLOR = {1: "#0072B2", 2: "#E69F00", 3: "#D55E00"}


# ---------------------------------------------------------------- Fig 1
def fig1():
    fig, ax = plt.subplots(figsize=(8.8, 4.9), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, lines, lw=1.1, ls="-", fs=9.0, ec="#111111"):
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec=ec, lw=lw, ls=ls))
        n = len(lines)
        for i, (t, bold) in enumerate(lines):
            yy = y + h * (n - i - 0.5) / n
            ax.text(x + w / 2, yy, t, ha="center", va="center", fontsize=fs,
                    fontweight="bold" if bold else "normal", color="#111111")

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#111111", lw=1.0))

    # 左列：五源
    ax.text(1.25, 9.6, "Provenance sources", ha="center", fontsize=9, style="italic")
    # "Human spreadsheets" 在 2.0 数据单位宽的框内溢出约 8%（实测 243 px 文字 / 225 px
    # 框宽）—— 改为与 fig2 完全一致的 "Human Excel"（2026-09-11），跨图称呼也统一。
    box(0.25, 7.9, 2.0, 1.1, [("Human Excel", True), ("2 curated sets", False)])
    box(0.25, 6.5, 2.0, 1.0, [("AI-ZYMES", True), ("public database", False)])
    box(0.25, 5.2, 2.0, 1.0, [("DiZyme", True), ("public database", False)])
    box(0.25, 3.9, 2.0, 1.0, [("NanozymeDB", True), ("public database", False)])
    box(0.25, 2.6, 2.0, 1.0, [("nanozymenet-k", True), ("kinetics subset", False)])

    # 中列：集成层
    box(3.4, 4.4, 2.7, 3.0, [
        ("Integrated layer", True),
        ("condition-bound schema", False),
        ("25 flat fields", False),
        ("pH / T first-class", False),
        ("5,027 entries", False),
        ("761 DOIs · 388 multi-source", False),
    ], lw=1.5)

    # 五条来源箭头分别落在目标框左缘的不同高度（2026-09-11 修）：原先全部收敛到
    # 同一点 (3.4, 5.9)，箭头头部叠成一个黑团并遮住该点，读者看不出是五路输入。
    for y, ty in zip((8.4, 7.0, 5.7, 4.4, 3.1), (7.05, 6.48, 5.92, 5.36, 4.80)):
        arrow(2.25, y, 3.4, ty)

    # 右列：三大产出
    ax.text(8.05, 9.6, "Analyses built on the layer", ha="center", fontsize=9, style="italic")
    # 2026-09-11：原图只给 30 篇的 0.965 与 100 篇的 0.907，缺摘要主口径 0.946 (67 篇)，
    # 读者从图上看不到正文头条数字。补入主口径，并把另两个口径缩为一行对照。
    box(6.9, 7.0, 2.9, 1.8, [
        ("LLM extraction (§3)", True),
        ("three agents, one schema", False),
        ("F1 = 0.946 (67 gold papers)", False),
        ("0.965 (30) · 0.907 (100)", False),
    ])
    box(6.9, 4.3, 2.9, 1.9, [
        ("Cross-source audit (§4–5)", True),
        ("17 same-pH groups ≥ 10×", False),
        ("166-cluster conflict atlas", False),
        ("97 severe / 43 / 26", False),
    ])
    box(6.9, 1.6, 2.9, 1.9, [
        ("Leakage re-evaluation (§6)", True),
        ("DOI-grouped folds", False),
        ("accuracy → baseline level", False),
        ("Kₘ R²: 0.387 → 0.023", False),
    ])

    arrow(6.1, 6.4, 6.9, 7.9)
    arrow(6.1, 5.9, 6.9, 5.25)
    arrow(6.1, 5.2, 6.9, 2.55)

    # 底部：未来工作（虚线）
    box(3.4, 0.4, 6.4, 0.8, [
        ("Evidence-grading answering protocol (§7, future work)", False)],
        ls=(0, (4, 3)), ec="#555555", fs=8.4)
    ax.annotate("", xy=(8.35, 1.2), xytext=(8.35, 1.6),
                arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.0,
                                ls=(0, (3, 2))))

    fig.savefig(OUT / "fig1_overview.png", bbox_inches="tight")
    plt.close(fig)
    print("[fig1] -> fig1_overview.png")


# ---------------------------------------------------------------- Fig 3
def fig3():
    PROD = MS / "deepseek-v4-flash__kimi-k2.6__20260816_210016" / "_eval_30.json"
    eval30 = json.loads(PROD.read_text(encoding="utf-8"))
    # (b) 用 67 篇 gold 评估（主口径，与 §3.2 一致）
    GOLD67 = ROOT / "workbench" / "evall_out" / "_eval_gold67.json"
    field = json.loads(GOLD67.read_text(encoding="utf-8"))["field_level"]

    CORE_FIELDS = [
        ("nanozyme", "nanozyme"), ("mimic_enzyme_activity", "activity"),
        ("metal_type", "metal type"), ("metal_ratio", "metal ratio"),
        ("metal_valence", "metal valence"), ("shape", "shape"),
        ("size_nm", "size (nm)"), ("buffer_ph_value", "buffer pH"),
        ("temperature_c", "temperature"), ("Km_mM", "$K_m$"),
        ("Vmax_uM_s_minus1", "$V_{max}$"),
    ]
    labels_b = [lab for _, lab in CORE_FIELDS if _ in field]
    f1s_b = [field[k]["f1"] for k, _ in CORE_FIELDS if k in field]

    flash = json.loads((MS / "deepseek-v4-flash__kimi-k2.6__20260812_124035" / "_eval_30.json")
                       .read_text(encoding="utf-8"))["overall"]
    qwen = json.loads((MS / "qwen3-235b-modelscope__kimi-k2.6__20260810_103914" / "_eval_30.json")
                      .read_text(encoding="utf-8"))["overall"]
    prod = eval30["overall"]

    # 两行布局（(a) 整行 + (b)(c) 并排），保证期刊双栏下字号 >= 6.5 pt
    fig = plt.figure(figsize=(8.6, 6.3), dpi=300)
    gs = fig.add_gridspec(2, 2, height_ratios=[0.78, 1.3], hspace=0.55, wspace=0.30)
    ax0 = fig.add_subplot(gs[0, :])
    ax1 = fig.add_subplot(gs[1, 0])
    ax2 = fig.add_subplot(gs[1, 1])

    # (a) 三智能体管线（规整版：输入 -> 三 agent -> integrator -> FlatRecord）
    ax = ax0
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, lines, lw=1.1, fs=9.2):
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="#111111", lw=lw))
        n = len(lines)
        for i, t in enumerate(lines):
            yy = y + h * (n - i - 0.5) / n
            ax.text(x + w / 2, yy, t, ha="center", va="center", fontsize=fs)

    def arrow(x1, y1, x2, y2, ls="-", c="#111111"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=1.0, ls=ls))

    ax.text(5.0, 9.7, "PDF + SI", ha="center", fontsize=9.2, style="italic", color="#555555")
    arrow(5.0, 9.4, 5.0, 8.7, ls=(0, (3, 2)), c="#555555")

    box(0.2, 7.3, 3.1, 1.3, ["text agent", "full text + tables"])
    box(0.2, 4.6, 3.1, 1.3, ["image agent", "VLM on figures"])
    box(0.2, 1.9, 3.1, 1.3, ["metadata agent", "title, DOI, SI"])
    for y in (7.95, 5.25, 2.55):
        arrow(3.3, y, 4.3, 5.35)
    box(4.3, 4.0, 3.1, 2.0, ["integrator", "deterministic", "merger + post-filter"], fs=8.8)
    arrow(7.4, 5.0, 7.7, 5.0)
    box(7.7, 3.9, 2.3, 2.0, ["FlatRecord", "25 fields", "condition-bound"], lw=1.4, fs=8.8)
    ax.set_title("(a) Three-agent pipeline", loc="left")

    # (b) 字段 F1
    ax = ax1
    colors_b = [RED if f < 0.85 else BLUE for f in f1s_b]
    ypos = np.arange(len(labels_b))[::-1]
    ax.barh(ypos, f1s_b, color=colors_b, height=0.62)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels_b, fontsize=8.8)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("F1 (record-level, 67 gold papers)")
    ax.set_title("(b) Field-level F1, production combo (n=67)", loc="left")
    for y, f in zip(ypos, f1s_b):
        ax.text(f + 0.01, y, f"{f:.3f}", va="center", fontsize=8.8)
    ax.axvline(0.9, ls="--", c="#888888", lw=0.8)

    # (c) 模型横比
    ax = ax2
    models = ["D-V4-Flash\n(prod)", "D-V4-Flash\n(earlier)", "Qwen3-235B"]
    f1s = [prod["f1"], flash["f1"], qwen["f1"]]
    ps = [prod["precision"], flash["precision"], qwen["precision"]]
    rs = [prod["recall"], flash["recall"], qwen["recall"]]
    x = np.arange(len(models))
    w = 0.26
    ax.bar(x - w, f1s, w, label="F1", color=BLUE)
    ax.bar(x, ps, w, label="Precision", color=GREEN)
    ax.bar(x + w, rs, w, label="Recall", color=YELLOW)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=8.8)
    ax.set_ylim(0.85, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("(c) Text-backbone comparison (18 fields, n=30)", loc="left")
    # 图例移到坐标轴外（2026-09-11 修）：三组柱都从 y=0.85 起满格绘制，轴内任何
    # 位置都会被柱体压住；原 lower left 直接盖在第一组柱上。
    ax.legend(fontsize=8.8, loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncol=3, frameon=False)
    for xi, (f, p, r) in enumerate(zip(f1s, ps, rs)):
        ax.text(xi - w, f + 0.002, f"{f:.3f}", ha="center", fontsize=8.6)
        ax.text(xi, p + 0.002, f"{p:.3f}", ha="center", fontsize=8.6)
        ax.text(xi + w, r + 0.002, f"{r:.3f}", ha="center", fontsize=8.6)

    fig.tight_layout()
    fig.savefig(OUT / "fig3_extract_eval.png", bbox_inches="tight")
    plt.close(fig)
    print(f"[fig3] prod F1={prod['f1']:.4f} flash={flash['f1']:.4f} qwen={qwen['f1']:.4f}")


# ---------------------------------------------------------------- Fig 4
def fig4():
    j = json.loads((OUT / "fig4_conflicts_sameph.json").read_text(encoding="utf-8"))
    folds = np.array([r["fold"] for r in j["rows"] if r["fold"] >= 10], dtype=float)
    over10 = j["over10"]
    over100 = int((folds >= 100).sum())

    npc = {"AI-ZYMES": 0.000154, "Human": 0.000154, "NanozymeDB": 154.0}
    cuo = {"AI-ZYMES": 0.4, "Human": 0.4, "DiZyme": 400.0, "NanozymeDB": 400.0}

    # 两行布局（(a) 整行 + (b)(c) 并排），保证期刊双栏下字号 >= 6.5 pt
    fig = plt.figure(figsize=(8.6, 6.0), dpi=300)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.95], hspace=0.58, wspace=0.30)
    ax0 = fig.add_subplot(gs[0, :])
    ax1 = fig.add_subplot(gs[1, 0])
    ax2 = fig.add_subplot(gs[1, 1])

    # 两个阵营的配色（2026-09-11）：原按来源索引上色（绿/蓝/黄/红）使 AI-ZYMES（绿）
    # 与 NanozymeDB（红）相邻，而这两者恰恰是两个阵营 —— 色盲下不可区分等于抹掉了
    # 本图唯一的论点。改为按阵营上色（Okabe-Ito 蓝/橙）并加斜纹作第二通道。
    CAMP_LOW, CAMP_HIGH = "#0072B2", "#E69F00"

    # (a) fold 分布 + 阈值线
    ax = ax0
    xs = np.arange(1, len(folds) + 1)
    cs = [RED if f >= 100 else BLUE for f in folds]
    ax.scatter(xs, folds, s=34, color=cs, zorder=3)
    ax.axhline(10, ls="--", c=RED, lw=1, alpha=0.8)
    ax.axhline(100, ls=":", c=RED, lw=1, alpha=0.8)
    ax.set_xlabel("Rank (descending fold)")
    # fold 定义写进轴标签（2026-09-11）：读者无法从 "cross-source fold" 推断是
    # max/min 还是 max/median —— 审计口径是 (max-min)/median，但本图排的是倍数。
    ax.set_ylabel("Cross-source $K_m$ fold (max / min)")
    ax.set_yscale("log")
    ax.set_ylim(1, max(folds) * 2.5)
    ax.set_title(f"(a) Same-pH conflicts\n≥10×: {over10} groups · ≥100×: {over100}",
                 loc="left", fontsize=10)
    # 阈值说明移入图框右上空白区（2026-09-11）：原放在图框下方，与 (b) 面板标题挤在
    # 同一行，看起来像 (b) 的标注；本图点位从左上的 10^6 降到右下的 10^1，右上必空。
    ax.text(0.985, 0.965, "dashed: 10×   dotted: 100×", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.6, color=RED)

    # (b) N-PCNSs
    ax = ax1
    names = list(npc.keys())
    vals = np.log10(np.array(list(npc.values()), dtype=float))
    bars = ax.bar(names, vals, color=[CAMP_LOW, CAMP_LOW, CAMP_HIGH])
    bars[2].set_hatch("///")
    ax.set_ylabel("$\\log_{10}$ $K_m$ (mM)")
    ax.set_title("(b) N-PCNSs · pH 7.0 · H$_2$O$_2$\ntwo camps · 10$^6$-fold",
                 loc="left", fontsize=10, pad=12)
    for i, (n, v) in enumerate(zip(names, vals)):
        ax.text(i, v + 0.05, f"{10**v:g}", ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(-5, 4)
    ax.tick_params(axis="x", rotation=20)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc=CAMP_LOW, label="camp A (lower $K_m$)"),
                       plt.Rectangle((0, 0), 1, 1, fc=CAMP_HIGH, hatch="///",
                                     label="camp B (higher $K_m$)")],
              fontsize=8.5, loc="upper left", frameon=False)

    # (c) CuO two camps
    ax = ax2
    names = list(cuo.keys())
    vals = np.log10(np.array(list(cuo.values()), dtype=float))
    bars = ax.bar(names, vals, color=[CAMP_LOW, CAMP_LOW, CAMP_HIGH, CAMP_HIGH])
    bars[2].set_hatch("///")
    bars[3].set_hatch("///")
    ax.set_ylabel("$\\log_{10}$ $K_m$ (mM)")
    ax.set_title("(c) CuO · pH 4.65 · H$_2$O$_2$\ntwo-camp ×1000 pattern", loc="left",
                 fontsize=10, pad=12)
    for i, (n, v) in enumerate(zip(names, vals)):
        ax.text(i, v + 0.05, f"{10**v:g}", ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(-1, 4)
    ax.tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(OUT / "fig4_units.png", bbox_inches="tight")
    plt.close(fig)
    print(f"[fig4] conflicts={len(folds)} over10={over10} over100={over100}")


# ---------------------------------------------------------------- Fig 6 (final numbering)
def fig_atlas():
    """166-cluster (pH, T) atlas, tier-coloured. Final figure number: 6
    (first cited in §5.1; renumbered 2026-09-11 so that figure numbers follow
    first-citation order)."""
    rows = list(csv.DictReader(open(ATLAS / "audit.csv", encoding="utf-8-sig")))
    tier_color = TIER_COLOR
    tier_name = {1: "tier 1 consistent", 2: "tier 2 suspicious", 3: "tier 3 severe"}
    marker = {"km_mm": "o", "vmax_um_s": "s", "kcat_s": "^"}
    metric_name = {"km_mm": "Kₘ", "vmax_um_s": "Vmax", "kcat_s": "kcat"}

    fig, ax = plt.subplots(figsize=(7.6, 4.4), dpi=300)
    counts = {1: 0, 2: 0, 3: 0}
    seen_marker = set()
    for r in rows:
        try:
            ph = float(r["pH"])
            t = float(r["温度(℃)"])
            tier = int(r["tier"])
            fold = float(r["倍数"])
            m = str(r["指标"]).strip()
        except (ValueError, KeyError):
            continue
        counts[tier] = counts.get(tier, 0) + 1
        # 面积编码封顶 + 白色分离晕（2026-09-11）：原 s=18+14*log10(fold) 在 fold 跨
        # 2→10^6 时面积差 4.6 倍，最大点吞掉邻近小点，pH≈4 处糊成一团。封顶后最大/
        # 最小面积比降到 3.1 倍，白色描边让重叠点仍可分辨。
        s = min(70.0, 20.0 + 8.0 * np.log10(max(fold, 1.0)))
        ax.scatter(ph, t, s=s, c=tier_color[tier],
                   marker=marker.get(m, "o"), alpha=0.92,
                   edgecolors="white", linewidths=0.9, zorder=3,
                   label=(metric_name.get(m) if m not in seen_marker else None))
        seen_marker.add(m)

    ax.set_xlabel("pH")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(f"(a) 166-cluster conflict atlas, (pH, T) projection\n"
                 f"tier 1: {counts.get(1, 0)} · tier 2: {counts.get(2, 0)} · "
                 f"tier 3: {counts.get(3, 0)}", loc="left", fontsize=10)
    # tier 图例（颜色）
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", markerfacecolor=tier_color[t],
                      markeredgecolor="#333333", label=tier_name[t]) for t in (1, 2, 3)]
    # metric 图例（marker 形状，黑色空心）
    handles += [Line2D([], [], marker=mk, ls="", markerfacecolor="none",
                       markeredgecolor="#111111", label=f"metric: {metric_name[mk2]}")
                for mk2, mk in marker.items()]
    # size 图例（2026-09-11 补）：此前面积编码无图例，读者无法解读大小 —— 必须给出刻度
    def _size_of(fold):
        return min(70.0, 20.0 + 8.0 * np.log10(max(fold, 1.0)))
    handles += [Line2D([], [], marker="o", ls="", markerfacecolor="#BBBBBB",
                       markeredgecolor="white", markersize=np.sqrt(_size_of(f)),
                       label=f"fold ≈ {lab}")
                for f, lab in ((10, "10×"), (1000, "10³×"), (10**6, "10⁶×"))]
    ax.legend(handles=handles, fontsize=8.6, loc="upper right", frameon=True,
              framealpha=0.9, ncol=1, labelspacing=0.75,
              title="color: tier · shape: metric · size: fold",
              title_fontsize=8.6)
    ax.grid(True, ls=":", alpha=0.35)
    fig.tight_layout()
    fig.savefig(OUT / "fig6_atlas.png", bbox_inches="tight")
    plt.close(fig)
    print(f"[fig6] clusters={len(rows)} tiers={counts}")


# ---------------------------------------------------------------- Fig 5 (final numbering)
def fig_fe3o4():
    """Condition-resolved Kₘ for Fe3O4/peroxidase/H2O2. Final figure number: 5
    (first cited in §4.4; renumbered 2026-09-11 so that figure numbers follow
    first-citation order)."""
    sys.path.insert(0, str(ROOT))
    from build_wiki import load_papers, collect_entries, flat_values  # noqa: E402
    from kg import conflict_atlas as ca  # noqa: E402

    papers = load_papers(ROOT / "workbench" / "atlas_records")
    multi = load_papers(ROOT / "workbench" / "db_records")
    merged = {}
    for p in list(papers) + list(multi):
        merged.setdefault(p.get("doi", ""), []).extend(p.get("records", []))
    papers_merged = [{"doi": k, "records": v} for k, v in merged.items()]
    entries = collect_entries(papers_merged)

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

    target = None
    for cl in clusters:
        phs = [p["ph"] for p in cl["ph_points"]]
        if 3.7 <= (min(phs) + max(phs)) / 2 <= 4.3 and cl["n_papers"] >= 3:
            target = cl

    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=300)
    n_pts = 0
    for cl in clusters:
        is_main = cl is target
        pts = [(p["ph"], p["value"]) for p in cl["ph_points"] if p.get("value") is not None]
        for x, y in pts:
            ax.scatter(x, y, s=48 if is_main else 30,
                       color=RED if is_main else GRAY,
                       edgecolor="black" if is_main else "#555555",
                       linewidth=0.5 if is_main else 0.3,
                       alpha=1.0 if is_main else 0.65, zorder=4 if is_main else 3)
            n_pts += 1
    if target:
        vals = [p["value"] for p in target["ph_points"] if p.get("value")]
        lo, hi = min(vals), max(vals)
        phs = [p["ph"] for p in target["ph_points"]]
        ax.text(0.03, 0.96,
                f"same-condition cluster ({target['n_papers']} papers, "
                f"pH {min(phs):.1f}\u2013{max(phs):.1f}):\n"
                f"$K_m$ {lo:g}\u2013{hi:g} mM \u00b7 fold {hi/lo:,.0f}\u00d7\n"
                f"(vermillion; all other points: other pH windows)",
                transform=ax.transAxes, fontsize=8.5, color=RED,
                va="top", ha="left",
                bbox=dict(boxstyle="square,pad=0.35", fc="white", ec=RED, alpha=0.9))
    ax.set_yscale("log")
    ax.set_xlabel("pH")
    ax.set_ylabel("$K_m$ (mM), log scale")
    ax.set_title(r"Fe$_3$O$_4$ · peroxidase · H$_2$O$_2$ — condition-resolved $K_m$",
                 fontsize=11, loc="left")
    ax.grid(True, which="both", ls=":", alpha=0.35)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_fe3o4_cluster.png", bbox_inches="tight")
    plt.close(fig)
    print(f"[fig5] clusters={len(clusters)} points={n_pts} "
          f"main={'yes' if target else 'no'}")


# ---------------------------------------------------------------- Fig 8
def fig8():
    # 2026-09-11 第三次修订：原 1x2 布局里 (b) 面板只有半栏宽，却要放 5 个两行
    # 刻度标签（External/Internal x random/DOI-grouped/DOI-isolated/material），
    # 在双栏 7.2 in 目标宽度下"DOI-grouped"与"DOI-isolated"必然压叠；放宽画布
    # 又会把有效字号压到 6.5 pt 边缘。改为 1x3：把"材料级"（每材料先取均值再评估）
    # 独立成 (c) 面板，每个面板最多 3 根柱，标签不再冲突，且材料级负值配零参考线
    # 单独立轴、不会被行级的正值压平。
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.4), dpi=300,
                             gridspec_kw={"width_ratios": [0.90, 1.30, 0.85]})

    # (a) 分类：random vs DOI-grouped；多数类基线画成参考线而非"第三个模型"
    ax = axes[0]
    names = ["Random 5-fold", "DOI-grouped"]
    vals = [0.816, 0.672]
    bars = ax.bar(names, vals, color=[BLUE, RED], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}",
                ha="center", fontsize=9.5)
    ax.axhline(0.695, ls="--", c="#555555", lw=1.1, zorder=1)
    # 基线标注改为图例句柄（2026-09-11）：两根柱都高于基线，轴内任何位置的文字
    # 都会压住柱体或柱顶数值（原 "…baseline 0.695" 正好穿过 0.672）。
    from matplotlib.lines import Line2D as _L2D
    ax.legend(handles=[_L2D([], [], ls="--", c="#555555", lw=1.1,
                            label="majority-class\nbaseline = 0.695")],
              fontsize=9.0, loc="upper right", frameon=False, handlelength=2.2)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Catalytic-type accuracy")
    # 面板宽度收窄后，长标题会压到 (b) 面板；macro-F1 的口径说明移到图注。
    ax.set_title("(a) Classification", loc="left", fontsize=10)

    # (b) 回归，行级（row level）
    ax = axes[1]
    names = ["External\n(random)", "Internal\n(DOI-grouped)",
             "External\n(DOI-isolated)"]
    vals = [0.387, 0.134, 0.023]
    colors = [BLUE, YELLOW, RED]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.3f}",
                ha="center", va="bottom", fontsize=9.0)
    ax.axhline(0, c="#333333", lw=1.0, zorder=0)
    ax.set_ylim(0, 0.46)
    ax.set_ylabel("R²")
    ax.set_title("(b) Row level\n(Kₘ regression, 978–2,637 rows)", loc="left",
                 fontsize=10)

    # (c) 回归，材料级（每材料先取均值再评估）
    # 原 1x2 布局把这两个负值并进 (b)，y 轴从 0 起 → 负值根本画不出来，而正文 §6.3
    # 恰恰以它们为最不利结果。独立成面板后 y 轴下探到 -0.10 并画出零参考线。
    ax = axes[2]
    names = ["Internal", "External"]
    vals = [-0.059, -0.043]
    bars = ax.bar(names, vals, color=PURPLE, width=0.5)
    for b, v in zip(bars, vals):
        # 负值标签放在柱底之下，避免文字压住柱体
        ax.text(b.get_x() + b.get_width() / 2, v - 0.010, f"{v:.3f}",
                ha="center", va="top", fontsize=9.0)
    ax.axhline(0, c="#333333", lw=1.0, zorder=0)
    ax.set_ylim(-0.10, 0.46)
    ax.set_ylabel("R²")
    ax.set_title("(c) Material level\n(Kₘ regression)", loc="left", fontsize=10)

    fig.tight_layout()
    fig.savefig(OUT / "fig8_leakage.png", bbox_inches="tight")
    plt.close(fig)
    print("[fig8] -> fig8_leakage.png")


if __name__ == "__main__":
    fig1()
    fig3()
    fig4()
    fig_atlas()
    fig8()
    try:
        fig_fe3o4()
    except Exception as e:  # noqa: BLE001
        print(f"[fig5] FAILED: {type(e).__name__}: {e}")
    print("all done -> workbench/figs/")
