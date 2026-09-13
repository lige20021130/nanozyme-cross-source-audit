# SI Tables (Track 1) — S1/S2/S3

> 生成：2026-09-11（`workbench/figs/gen_si_tables.py`，确定性）。
> T1 派生自 `schema.py FIELD_NAMES`（实测 25）；T2 派生自 m8-2 精读；
> T3 派生自 `fig4_conflicts_sameph.json`（同 pH 口径，17 组）。
> 2026-09-12 round 14：标题体系统一为 Table S1/S2/S3（原 T1/T2/T3 与正文 "Table Sn"
> 引用混用）；Table S1 增补 per-source 字段映射与规模面板（正文 §2.3、§7.4 承诺该表，
> 但此前 SI 里只有 schema 表，映射表根本不存在）。

## Table S1. The 25-field FlatRecord schema, per-source field mapping, and scale

Panel (a) gives the schema; panel (b) maps each provenance group onto it and states the
scale of its contribution. Two spreadsheets are merged into the single human-curated
group of panel (b), which is why the layer has five provenance groups built from six
source files.

**(a) Schema**

| Field | Type | Description | Example |
|---|---|---|---|
| `nanozyme` | str | Material name as reported in the paper | Fe₃O₄ |
| `mimic_enzyme_activity` | str | Enzyme-like activity (POD / OXD / CAT / SOD / ...) | peroxidase |
| `doi` | str | Paper DOI | 10.1021/... |
| `doped_N` | int | Lattice N doping flag (0/1) | 1 |
| `doped_P` | int | Lattice P doping flag (0/1) | 0 |
| `doped_S` | int | Lattice S doping flag (0/1) | 0 |
| `doped_B` | int | Lattice B doping flag (0/1) | 0 |
| `doped_F` | int | Lattice F doping flag (0/1) | 0 |
| `metal_ratio` | float | Primary metal molar percentage (single metal = 100) | 100.0 |
| `metal_type` | int | Primary metal atomic number | 26 (Fe) |
| `metal_valence` | int | Primary metal valence (mixed valence: highest) | 3 |
| `shape` | str | Morphology | nanoparticle |
| `size_nm` | float | Particle size in nm | 12.5 |
| `surface_modification` | str | Surface modification | PEG |
| `dispersion_medium` | str | Dispersion medium (without pH) | water |
| `buffer_ph_value` | float | Buffer pH | 4.0 |
| `temperature_c` | float | Reaction temperature in °C | 25.0 |
| `substrate1` | str | Primary substrate | H₂O₂ |
| `substrate2` | str | Second substrate (None for single-substrate) | TMB |
| `Km_mM` | float | Michaelis–Menten constant in mM | 0.076 |
| `Vmax_uM_s_minus1` | float | Maximum velocity in µM·s⁻¹ | 1.25 |
| `Kcat_s_minus1` | float | Turnover number in s⁻¹ | 1.7e3 |
| `catalytic_efficiency_M_s_minus1` | float | Catalytic efficiency in M⁻¹·s⁻¹ | 2.2e4 |
| `kinetic_substrate` | str | Substrate the kinetic constant is bound to | H₂O₂ |
| `kinetic_method` | str | Assay method (UV-vis / SERS / ...) | UV-vis |

**(b) Per-source field mapping and scale**

Each source is mapped into the fields above by deterministic column and unit normalization
that performs no conversion beyond what the source file header declares. "Fields carried"
lists how many of the 25 schema fields the source can populate at all; fields it does not
carry are left null rather than filled by inference. Entries are the contribution to the
5,027-entry layer (Figure 2).

| Provenance group | Source type | Source file(s) | Schema fields populated (of 25) | Entries | Records without a DOI | Unit-uncertain records |
|---|---|---|---|---|---|---|
| human | 2 curated spreadsheets | domain-researcher workbooks, maintained independently | 23 | 1,008 | 0 | 0 |
| AI-ZYMES | public database | ref 8 (expanded release) | 9 | 1,031 | 6 | 0 |
| DiZyme | public database | ref 4 (2024 release) | 8 | 1,210 | 0 | 0 |
| NanozymeDB | public database | ref 10 | 8 | 596 | 0 | 0 |
| nanozymenet-k | public database | nanozymes.net kinetics subset (ref 11) | 8 | 1,182 | 1,182 | 1,134 |

*a* "Fields populated" counts, per source, how many of the 25 schema fields are non-null in
at least one of its records; fields a source does not carry are left null rather than filled
by inference. The human workbooks carry the widest field set, which is why the schema was
derived from their columns; the four databases carry between 8 and 9 fields, all of them
kinetic or condition fields. *b* The two human workbooks are merged into the single "human"
group, so five provenance groups are built from six source files. *c* The human workbooks
cannot be redistributed and are described here instead of being released. *d* nanozymenet-k
publishes no DOIs at all: its records enter the layer under a stable internal identifier
(`na-<n>`) in place of a DOI, and 1,134 of the 1,182 also carry a unit-uncertainty flag
because its kinetic columns do not declare their units. 13 of the 166 conflict clusters
contain at least one such record; Section 5.5 reports the tier distribution with all 13
removed. *e* Counts are computed directly from `workbench/db_records/`,
`workbench/atlas_records/` and `workbench/atlas_out_multi/atlas_summary.json`
(`provenance`, `lineage`).

## Table S2. Comparison with prior nanozyme ML works

*b* Values are quoted as reported by each cited work; the dataset sizes in the "Data source"
row are those the original authors state. *c* The "This work" column counts 5,027
**integrated** entries, of which 1,008 are newly curated and 4,019 are re-integrated from the
very resources listed in the same row; it is a re-integration plus an audit, not 5,027 newly
curated records, and the two are not commensurable column-for-column. *d* The "Evaluation
split" row for this work refers to the leakage re-evaluation of Section 6.

| Aspect | Wei et al. 2022 | DiZyme (Razlivina 2024) | AI-ZYMES (Xuan et al. 2025) | This work |
|---|---|---|---|---|
| Data source | 920 hand-curated records (5355 screened) [6] | 1210 samples, 390 compositions (400 papers, manual) [3] | 1085 entries, 400 types [8] | 5027 integrated entries (1,008 newly curated + 4,019 re-integrated) · 761 DOIs · 5 provenance groups |
| Condition axis | pH/T as features only | pH/T as features only | pH/T as features only | pH/T first-class; records condition-bound |
| Cross-source audit | none | none | claims standardized curation; no cross-DB audit | 17 same-pH groups ≥10×; 166-cluster atlas |
| Evaluation split | random split | random holdout | not disclosed | DOI-grouped 5-fold (+ random for comparison) |
| Classification | 90.6% (random split) | — | type classifier (AdaBoost) | baseline-level acc under DOI-grouped folds |
| Regression | R² up to 0.80 [6] | Kₘ R² 0.75, Vmax 0.77 [3] | GBR R² ≤ 0.85 (Kₘ/Vmax/kcat) [8] | external Kₘ R² 0.387 → 0.023 after DOI isolation |
| Extraction automation | none (manual) | none (manual; LLM 'looked forward to') | ChatGPT-assisted curation (67.55%) | three-agent LLM pipeline, F1 0.946 (67 gold papers) |
| Reproducibility | not stated | not stated | not stated | deterministic normalization; scripts archived |

*Note on regression R².* AI-ZYMES has two releases with different reported regression
quality, and both appear in this paper. The first release (Sun et al. 2024, ref. [7])
reports gradient-boosting Kₘ R² = 0.6476, quoted in the main text as ≈0.65; the expanded
release (Xuan et al. 2025, ref. [8]) reports GBR R² up to 0.85 on 1,085 entries across
400 catalytic types. The two are not in conflict , they differ in training-set size , and
we cite the lower, earlier figure wherever we discuss the protocol that predates
group-aware splitting. The DiZyme figures (Kₘ R² 0.75, Vmax 0.77) are from the 2024
release (ref. [3]); its 2022 release reports Kₘ R² 0.627 and kcat R² 0.796 (ref. [4]).

> ✅ 2026-09-11 回原文核对（6 篇上传 PDF）：Wei 2022 [4] 920 条 / 90.6% / R² up to 0.80 与原文一致；
> DiZyme 的 1210 samples / 390 compositions / 400 papers 出自 JPCL 2024 [2]（原文 "1210 nanozymes ...
> sourced from 400 articles ... 390 unique nanozymes"），Small 2022 [3] 为初始版（>300 纳米酶 / >100 篇）；
> AI-ZYMES 扩版 1,085 entries / 400 types / GBR R²≤0.85 出自 Xuan 2025 [7]，首篇 GBR Kₘ R²=0.6476
> （正文引作 ≈0.65）出自 Sun 2024 JCIM [5]。
> ⚠️ 2026-09-11 补：本表原挂 [2][5][6]（旧编号），已随正文重编号同步为 [4][2][7]。方括号式引用不受
> `workbench/_renumber_refs.py` 覆盖（该脚本只处理 <sup>），属同类漏网，投稿前需再扫一次。

## Table S3. Same-pH cross-source Kₘ conflicts (17 groups ≥10×)

| Rank | Fold | DOI | Material | Substrate | pH | Sources | Kₘ range (mM) |
|---|---|---|---|---|---|---|---|
| 1 | 1,000,000× | 10.1038/s41467-018-03903-8 | N-PCNSs-5 | H₂O₂ | 7.0 | ai-zymes, nanozymedb, human | 0.000154 – 154 |
| 2 | 1,000,000× | 10.1038/s41467-018-03903-8 | PCNSs | H₂O₂ | 7.0 | ai-zymes, nanozymedb, human | 0.0006789 – 678.9 |
| 3 | 99,985× | 10.1038/s41467-018-03903-8 | N-PCNSs-3 | H₂O₂ | 7.0 | ai-zymes, nanozymedb, human | 0.0006625 – 66.24 |
| 4 | 31,231× | 10.1016/j.bios.2014.08.062 | NiO | H₂O₂ | 3.8 | ai-zymes, dizyme, human | 0.00666 – 208 |
| 5 | 31,045× | 10.1016/j.bios.2014.08.062 | NiO | TMB | 3.8 | ai-zymes, dizyme, human | 0.0067 – 208 |
| 6 | 1,000× | 10.1021/acsami.6b05354 | CuO | H₂O₂ | 4.65 | ai-zymes, dizyme, nanozymedb, human | 0.4 – 400 |
| 7 | 1,000× | 10.1021/acsami.6b05354 | CuO | TMB | 4.65 | ai-zymes, dizyme, nanozymedb, human | 0.025 – 25 |
| 8 | 1,000× | 10.1021/acsami.8b20942 | HccFn(Co₃O₄) | TMB | 4.5 | ai-zymes, nanozymedb, human | 0.84 – 840 |
| 9 | 1,000× | 10.1021/acsami.8b20942 | HccFn(Fe₃O₄) | TMB | 4.5 | ai-zymes, nanozymedb, human | 1.12 – 1120 |
| 10 | 100× | 10.1016/j.bios.2014.08.062 | H2TCPP-NiO | TMB | 3.8 | ai-zymes, nanozymedb, human | 0.391 – 39.1 |
| 11 | 78× | 10.1016/j.apcatb.2020.118725 | Cit-IrNPs | H₂O₂ | 3.86 | ai-zymes, human | 0.27 – 21.09 |
| 12 | 30× | 10.1039/c9cc00199a | Fe SAEs | TMB | 3.8 | ai-zymes, human | 0.13 – 3.92 |
| 13 | 27× | 10.1016/j.colsurfa.2016.07.037 | Fe₂O₃ | H₂O₂ | 3.6 | ai-zymes, human | 11.3 – 305 |
| 14 | 25× | 10.1016/j.snb.2023.134429 | rGO@PDA@CeO₂ | H₂O₂ | 7.4 | ai-zymes, human | 0.26 – 6.39 |
| 15 | 17× | 10.1016/j.snb.2023.134429 | rGO@PDA@CeO₂ | TMB | 7.4 | ai-zymes, human | 0.41 – 6.81 |
| 16 | 11× | 10.1039/c6nr02730j | CeO₂ | TMB | 4.0 | ai-zymes, dizyme, human | 0.14 – 1.5 |
| 17 | 11× | 10.1039/c9nr05346h | CeO₂ | TMB | 4.0 | ai-zymes, nanozymedb, human | 0.14 – 1.5 |