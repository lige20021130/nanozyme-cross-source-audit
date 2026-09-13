# -*- coding: utf-8 -*-
"""Fig 3 (paper): 三智能体提取架构 + 评估（30 篇 F1 与 3 模型横比）。

面板：
(a) 三智能体流程示意（text/image/metadata → integrator → FlatRecord 25 字段）
(b) 30 篇 gold 的核心字段 F1（生产组合 D-V4-Flash × K-K2.6，210016 口径）
(c) 文本骨干横比（18 字段口径 F1：flash 0.9521 / qwen 0.9443；pro 仅 5 篇冒烟不列）
数据源：workbench/model_swap_out/*/_eval_30.json + _summary.json。
运行：conda run -n base python workbench/figs/fig3_extract_eval.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "workbench" / "figs"
MS = ROOT / "workbench" / "model_swap_out"

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
})

PROD = MS / "deepseek-v4-flash__kimi-k2.6__20260816_210016" / "_eval_30.json"
eval30 = json.loads(PROD.read_text(encoding="utf-8"))
field = eval30["field_level"]

# (b) 选定核心字段（与 §3.2 一致）
CORE_FIELDS = [
    ("nanozyme", "$nanozyme$"), ("mimic_enzyme_activity", "activity"),
    ("metal_type", "metal type"), ("metal_ratio", "metal ratio"),
    ("metal_valence", "metal valence"), ("shape", "shape"),
    ("size_nm", "size (nm)"), ("buffer_ph_value", "buffer pH"),
    ("temperature_c", "temperature"), ("Km_mM", "$K_m$"),
    ("Vmax_uM_s_minus1", "$V_{max}$"),
]
labels_b = [lab for _, lab in CORE_FIELDS]
f1s_b = [field[k]["f1"] for k, _ in CORE_FIELDS if k in field]

# (c) 横比（18 字段口径）
flash = json.loads((MS / "deepseek-v4-flash__kimi-k2.6__20260812_124035" / "_eval_30.json")
                   .read_text(encoding="utf-8"))["overall"]
qwen = json.loads((MS / "qwen3-235b-modelscope__kimi-k2.6__20260810_103914" / "_eval_30.json")
                  .read_text(encoding="utf-8"))["overall"]
prod = eval30["overall"]

fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.6), dpi=300,
                         gridspec_kw={"width_ratios": [1.15, 1.5, 1]})

# (a) 流程示意（纯 matplotlib 框线图）
ax = axes[0]
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
def box(x, y, w, h, t, fc="#ffffff", fs=8.5, tc="#111111"):
    ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="#333333", lw=1.1))
    ax.text(x + w/2, y + h/2, t, ha="center", va="center", fontsize=fs, color=tc)
def carrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.1))
# 三智能体
box(0.4, 6.6, 2.6, 1.0, "text agent\n(full text + tables)")
box(0.4, 4.4, 2.6, 1.0, "image agent\n(VLM, figures)")
box(0.4, 2.2, 2.6, 1.0, "metadata agent\n(title, DOI, SI)")
carrow(3.2, 7.1, 4.4, 5.5); carrow(3.2, 4.9, 4.4, 5.5); carrow(3.2, 2.7, 4.4, 5.5)
box(4.4, 4.9, 2.4, 1.3, "integrator", fs=9)
ax.text(5.6, 4.55, "deterministic\nmerger + post-filter", fontsize=6.8,
        ha="center", va="top", color="#555555")
carrow(7.0, 5.55, 8.2, 5.55)
box(8.2, 5.0, 1.7, 1.1, "FlatRecord\n25 fields")
ax.set_title("(a) Three-agent pipeline", loc="left")

# (b) 字段 F1 横向条形
ax = axes[1]
colors_b = ["#C44E52" if f < 0.85 else "#4C72B0" for f in f1s_b]
ypos = np.arange(len(labels_b))[::-1]
ax.barh(ypos, f1s_b, color=colors_b, height=0.62)
ax.set_yticks(ypos); ax.set_yticklabels(labels_b, fontsize=8)
ax.set_xlim(0, 1.0)
ax.set_xlabel("F1 (record-level, 30 gold papers)")
ax.set_title("(b) Field-level F1, production combo", loc="left")
for y, f in zip(ypos, f1s_b):
    ax.text(f + 0.01, y, f"{f:.3f}", va="center", fontsize=7.5)
ax.axvline(0.9, ls="--", c="#888888", lw=0.8)

# (c) 模型横比
ax = axes[2]
models = ["D-V4-Flash\n(prod, 210016)", "D-V4-Flash\n(20260812)", "Qwen3-235B\n(20260810)"]
f1s = [prod["f1"], flash["f1"], qwen["f1"]]
ps = [prod["precision"], flash["precision"], qwen["precision"]]
rs = [prod["recall"], flash["recall"], qwen["recall"]]
x = np.arange(len(models)); w = 0.26
ax.bar(x - w, f1s, w, label="F1", color="#4C72B0")
ax.bar(x, ps, w, label="Precision", color="#55A868")
ax.bar(x + w, rs, w, label="Recall", color="#CCB974")
ax.set_xticks(x); ax.set_xticklabels(models, fontsize=8)
ax.set_ylim(0.85, 1.0)
ax.set_ylabel("Score")
ax.set_title("(c) Text-backbone comparison (18 fields)", loc="left")
ax.legend(fontsize=7.5, loc="lower left", frameon=False)
for xi, (f, p, r) in enumerate(zip(f1s, ps, rs)):
    ax.text(xi - w, f + 0.002, f"{f:.3f}", ha="center", fontsize=7)
    ax.text(xi, p + 0.002, f"{p:.3f}", ha="center", fontsize=7)
    ax.text(xi + w, r + 0.002, f"{r:.3f}", ha="center", fontsize=7)

fig.tight_layout()
out = OUT / "fig3_extract_eval.png"
fig.savefig(out, bbox_inches="tight")
plt.close(fig)
print(f"saved -> {out} | prod F1={prod['f1']:.4f} flash={flash['f1']:.4f} qwen={qwen['f1']:.4f}")
for k, _ in CORE_FIELDS:
    if k not in field:
        print(f"  missing field in eval30: {k}")