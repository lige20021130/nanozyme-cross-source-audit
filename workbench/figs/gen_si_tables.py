# -*- coding: utf-8 -*-
"""生成 SI 三表（Track 1 投稿）：
T1  25 字段 schema 表（字段/类型/语义/示例）——从 schema.py FIELD_NAMES 自动派生
T2  与 DiZyme / Wei 2022 / AI-ZYMES 对比表（数据/特征/验证口径/性能/局限）
T3  同 pH 跨源冲突明细表（17 组逐 DOI 值）——从 fig4_conflicts_sameph.json + records 数值
输出：paper_drafts/si_tables_track1.md
运行：conda run -n base python workbench/figs/gen_si_tables.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from schema import FIELD_NAMES, FlatRecord  # noqa: E402

OUT = ROOT / "paper_drafts" / "si_tables_track1.md"

# ---------------- T1: 25 字段表 ----------------
# 按 schema.py 注释分组（六组语义块）
GROUPS = [
    ("Identity", ["nanozyme", "mimic_enzyme_activity", "doi"]),
    ("Non-metal doping", ["doped_N", "doped_P", "doped_S", "doped_B", "doped_F"]),
    ("Primary metal", ["metal_ratio", "metal_type", "metal_valence"]),
    ("Physical", ["shape", "size_nm", "surface_modification"]),
    ("Reaction conditions", ["dispersion_medium", "buffer_ph_value", "temperature_c", "substrate1"]),
    ("Kinetic core", ["substrate2", "Km_mM", "Vmax_uM_s_minus1", "Kcat_s_minus1",
                      "catalytic_efficiency_M_s_minus1", "kinetic_substrate", "kinetic_method"]),
]
assert sum(len(g[1]) for g in GROUPS) == len(FIELD_NAMES) == 25, \
    f"schema mismatch: {len(FIELD_NAMES)}"

FIELD_DESC = {
    "nanozyme": "Material name as reported in the paper",
    "mimic_enzyme_activity": "Enzyme-like activity (POD / OXD / CAT / SOD / ...)",
    "doi": "Paper DOI",
    "doped_N": "Lattice N doping flag (0/1)",
    "doped_P": "Lattice P doping flag (0/1)",
    "doped_S": "Lattice S doping flag (0/1)",
    "doped_B": "Lattice B doping flag (0/1)",
    "doped_F": "Lattice F doping flag (0/1)",
    "metal_ratio": "Primary metal molar percentage (single metal = 100)",
    "metal_type": "Primary metal atomic number",
    "metal_valence": "Primary metal valence (mixed valence: highest)",
    "shape": "Morphology",
    "size_nm": "Particle size in nm",
    "surface_modification": "Surface modification",
    "dispersion_medium": "Dispersion medium (without pH)",
    "buffer_ph_value": "Buffer pH",
    "temperature_c": "Reaction temperature in \u00b0C",
    "substrate1": "Primary substrate",
    "substrate2": "Second substrate (None for single-substrate)",
    "Km_mM": "Michaelis\u2013Menten constant in mM",
    "Vmax_uM_s_minus1": "Maximum velocity in \u00b5M\u00b7s\u207b\u00b9",
    "Kcat_s_minus1": "Turnover number in s\u207b\u00b9",
    "catalytic_efficiency_M_s_minus1": "Catalytic efficiency in M\u207b\u00b9\u00b7s\u207b\u00b9",
    "kinetic_substrate": "Substrate the kinetic constant is bound to",
    "kinetic_method": "Assay method (UV-vis / SERS / ...)",
}
EXAMPLES = {
    "nanozyme": "Fe3O4", "mimic_enzyme_activity": "peroxidase", "doi": "10.1021/...",
    "doped_N": "1", "doped_P": "0", "doped_S": "0", "doped_B": "0", "doped_F": "0",
    "metal_ratio": "100.0", "metal_type": "26 (Fe)", "metal_valence": "3",
    "shape": "nanoparticle", "size_nm": "12.5", "surface_modification": "PEG",
    "dispersion_medium": "water", "buffer_ph_value": "4.0", "temperature_c": "25.0",
    "substrate1": "H2O2", "substrate2": "TMB",
    "Km_mM": "0.076", "Vmax_uM_s_minus1": "1.25",
    "Kcat_s_minus1": "1.7e3", "catalytic_efficiency_M_s_minus1": "2.2e4",
    "kinetic_substrate": "H2O2", "kinetic_method": "UV-vis",
}

lines = ["# SI Tables (Track 1) \u2014 T1/T2/T3", "",
         "> 生成：2026-09-11（`workbench/figs/gen_si_tables.py`，确定性）。",
         "> T1 派生自 `schema.py FIELD_NAMES`（实测 25）；T2 派生自 m8-2 精读；",
         "> T3 派生自 `fig4_conflicts_sameph.json`（同 pH 口径，17 组）。", ""]

# T1
lines += ["## T1. The 25-field FlatRecord schema", ""]
t1_ordered = []
for gname, fields in GROUPS:
    t1_ordered += [(gname, f) for f in fields]
lines += ["| Field | Type | Description | Example |", "|---|---|---|---|"]
TYPE_OF = {}
for f in FIELD_NAMES:
    ann = FlatRecord.model_fields[f].annotation
    s = str(ann).replace("typing.Optional[", "").replace("]", "").replace("None | ", "")
    s = s.replace("<class '", "").replace("'>", "")
    TYPE_OF[f] = s
for gname, f in t1_ordered:
    lines.append(f"| `{f}` | {TYPE_OF.get(f,'')} | {FIELD_DESC.get(f,'')} | {EXAMPLES.get(f,'\u2014')} |")
lines += [""]

# ---------------- T2 ----------------
lines += ["## T2. Comparison with prior nanozyme ML works", ""]
lines += ["| Aspect | Wei et al. 2022 | DiZyme (Razlivina 2024) | AI-ZYMES (Xuan et al. 2025) | This work |",
          "|---|---|---|---|---|"]
lines += [
    "| Data source | 920 hand-curated records (5355 screened) | 1210 samples, 390 compositions (400 papers, manual) | 1085 entries, 400 types | 5027 entries \u00b7 761 DOIs \u00b7 5 provenance groups |",
    "| Condition axis | pH/T as features only | pH/T as features only | pH/T as features only | pH/T first-class; records condition-bound |",
    "| Cross-source audit | none | none | claims standardized curation; no cross-DB audit | 17 same-pH groups \u226510\u00d7; 166-cluster atlas |",
    "| Evaluation split | random 80/20 | random holdout | not disclosed | DOI-grouped 5-fold (+ random for comparison) |",
    "| Classification | 90.6% (random split) | \u2014 | type classifier (AdaBoost) | baseline-level acc under DOI-grouped folds |",
    "| Regression | R\u00b2 up to 0.80 | Km R\u00b2 0.75, Vmax 0.77 | GBR R\u00b2 \u2264 0.85 (Km/Vmax/Kcat) | external Km R\u00b2 0.387 \u2192 0.023 after DOI isolation |",
    "| Extraction automation | none (manual) | none (manual; LLM 'looked forward to') | ChatGPT-assisted curation (67.55%) | three-agent LLM pipeline, F1 0.965 |",
    "| Reproducibility | not stated | not stated | not stated | deterministic normalization; scripts archived |",
]
lines += [""]

# ---------------- T3 ----------------
j = json.loads((ROOT / "workbench" / "figs" / "fig4_conflicts_sameph.json")
               .read_text(encoding="utf-8"))
rows = [r for r in j["rows"] if r["fold"] >= 10]
rows.sort(key=lambda r: -r["fold"])
lines += [f"## T3. Same-pH cross-source K\u2098 conflicts ({len(rows)} groups \u226510\u00d7)", ""]
lines += ["| Rank | Fold | DOI | Material | Substrate | pH | Sources | K\u2098 range (mM) |",
          "|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    srcs = ", ".join(s.replace("db:", "") for s in r["sources"])
    fr = f"{r['fold']:,.0f}\u00d7"
    lines.append(f"| {i} | {fr} | {r['doi']} | {r['material']} | {r['substrate']} | "
                 f"{r['ph']} | {srcs} | {r['min_km']:g} \u2013 {r['max_km']:g} |")
lines += [""]

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"saved -> {OUT} ({len(lines)} lines)")