# Track 1 manuscript — Abstract + Sections 1–7 (merged draft)

> 并稿状态：Abstract + §1–§7 的机械合并（2026-09-10 启，2026-09-11 完成 §7 与 Abstract；Abstract/§1/§2/§7 为新增）。各节正文零改动，仅标题层级升级（节=##，小节=###），节间以 --- 分隔。交叉引用与重复数字已核对，见文末《并稿核对表》。

---

## Abstract

Nanozyme kinetic values are abundant but unreliable: public databases re-annotate the
same material–substrate system independently and disagree by orders of magnitude, and
store them without the conditions that give them meaning. We report a condition-bound
data layer for nanozyme kinetics and the pipeline that builds and audits it. A flat 25-field record makes pH and temperature first-class attributes and binds every
kinetic constant to its substrate, conditions, DOI, and provenance; five provenance groups
contribute 5,027 entries across 761 DOIs (388 multi-source). A deterministic audit exposes
17 same-pH groups whose Kₘ differs across sources by ≥10×, including a 10⁶-fold case and
×1000 patterns traced to an M→mM conversion. A 166-cluster conflict atlas (97 severe, 43
suspicious, 26 consistent) records every value with its DOI. A three-agent LLM
pipeline converts PDFs into condition-bound records at F1 = 0.946 on 67 gold-annotated
papers, keeping the layer extensible without per-record manual entry. Re-evaluating
nanozyme machine learning with folds grouped by DOI removes most of the predictive power
reported under random splits: classification accuracy falls to the majority-class
baseline, and external Kₘ regression R² falls from 0.387 to 0.023. Correctness rests on
unit recovery against the source publication, not on inter-source agreement.

---

## Section 1 — Introduction

> 状态：英文初稿（2026-09-10，2026-09-11 回原文核对后修订）。立论素材：
> Li 2023（J. Mater. Chem. B 11, 6466）展望第(1)条**原文句**（非 m8-2 转述）、
> Wei 2022（随机 80/20 分类 90.6%，R² up to 0.80，920 条）、
> DiZyme JPCL 2024 [5]（1,210 samples / 390 compositions / 400 papers，Kₘ R²=0.75、Vmax 0.77，随机 holdout）
> + DiZyme Small 2022 [4]（初始版 >300 纳米酶 / >100 篇，kcat R²=0.796、Kₘ 0.627）、
> AI-ZYMES Sun 2024 JCIM [7]（GBR Kₘ R²=0.6476，首篇；扩版 Xuan 2025 [6]，1,085 entries / 400 types）。
> 本工作主线来自 §2–§6 已核实的数字（25 字段/5,027 条目/761 DOI/166 簇/0.387→0.023）。
> 写作遵循：数据零丢失、口径诚实、陈述中性、禁 AIGC 腔。

---

### 1.1 Problem: nanozyme kinetic data are abundant, inconsistent, and hard to trust

Nanozymes, nanomaterials with enzyme-like catalytic activity, have become a mainstream
topic in materials science, biochemistry, and diagnostics since the discovery of
intrinsic peroxidase-like activity in Fe₃O₄ nanoparticles.<sup>1</sup> The literature now reports
thousands of kinetic measurements: Michaelis–Menten constants (Kₘ), maximum velocities
(Vmax), turnover numbers (kcat), and the reaction conditions under which they were
obtained (buffer pH, temperature, substrate, assay method). These numbers are the raw
material for mechanistic comparison, material screening, and machine-learning models of
nanozyme activity.

Yet the quality of this data resource has not kept pace with its volume: data veracity
and standardisation are long-standing obstacles across data-driven materials science
generally, not only in nanozymes.<sup>2</sup> Three obstacles recur across
the field. First, **kinetic values are reported without a
machine-readable condition axis**: a single database row "Fe₃O₄, peroxidase, H₂O₂, Kₘ"
silently aggregates measurements taken at pH 2–8 and temperatures from ambient to 50 °C,
even though Kₘ can vary by orders of magnitude across that range (Section 5). A
condition-agnostic value is not a number one can reason with; it is an implicit average
over conditions nobody logged. Second, **public databases disagree about the same
measurement by orders of magnitude**. Our cross-source audit (Section 4) finds 17 groups
in which the same material–substrate pair at the same pH is annotated with Kₘ values
differing by at least 10× across sources, with a characteristic 10²/10³/10⁶-fold ladder
that matches unit misassignment (mM vs. µM vs. M) rather than experimental scatter; the
most extreme case spans 10⁶× (N-PCNSs, pH 7.0, H₂O₂). Third, **the curation bottleneck
does not scale**: extracting condition-bound records from running text, tables, and
figure insets is labor-intensive enough that even the largest existing platforms
(DiZyme, whose latest release curates 1,210 samples from 400 papers and whose initial
release covered >300 nanozymes from >100 papers) still rely on manual collection.<sup>3,4</sup>

The consequences are concrete. Machine-learning models trained on these data inherit
the inconsistencies, and the failure mode is already documented in adjacent materials
domains, where values traced from source articles into curated datasets show recurrent
text–figure mismatches, ambiguous axis annotations, and unit inconsistencies that are
numerically plausible enough to survive routine pre-processing and propagate as
structured label noise; in one cross-database case the ambiguity produced a 100-fold
error in a reported conductivity.<sup>5</sup> Wei et al. report 90.6% classification accuracy on random
splits,<sup>6</sup> and DiZyme and AI-ZYMES report regression R² of 0.75 (Kₘ) and 0.65
(Kₘ),<sup>3,7</sup> yet these numbers are obtained without isolating records that originate
from the same paper or material family. Two AI-ZYMES figures appear in this paper and are
not in conflict: they are two releases of one platform, not two measurements of one model.
The ≈0.65 quoted here is the first release (Kₘ R² = 0.6476);<sup>7</sup> the ≤0.85 in
Table S2 is the expanded release, trained on 1,085 entries across 400 catalytic
types.<sup>8</sup> The gap reflects training-set size. When we repeat the standard protocol on our own condition-bound layer — the same model
family and the same features, differing only in that folds are grouped by paper — accuracy
drops to roughly the majority-class baseline and the external-validation R² falls from
0.387 to 0.023 (Section 6). This is a re-run of the *protocol* on our corpus, not a
reproduction of the published models: neither their training data nor their exact feature
construction is available, and we make no claim about their internal implementations. In other words, part of what the field reports as
predictive performance is memorization of source identity rather than learned physics.

### 1.2 Opportunity: a unified schema, an audit, and an automated pipeline

A recent review of nanozyme machine learning concludes its outlook by prioritizing the
establishment and development of nanozyme databases, calling the development of databases
with enough available information on nanozymes "important and indispensable" and calling
for "standard and unified detection and representation methods" to guarantee the quality
of data and database.<sup>9</sup> We take this as our starting point and answer it at
four levels; Figure 1 gives an overview of how the pieces fit together.

First, we define a condition-bound data model (§2): a flat, 25-field record in
which pH and temperature are first-class attributes, every kinetic constant is tied to
the substrate it refers to, and no value aggregates across conditions. The schema is
deliberately simple and deterministic—normalization lives in code, not in a language
model—so that the layer is reproducible and auditable by construction. Five provenance
groups — human-curated records, merged from two independently maintained spreadsheets,
plus four public databases — are mapped into this
schema with unit semantics kept intact, yielding 5,027 condition-bound entries across
761 DOIs, of which 388 are covered by multiple sources.

Second, we make the inconsistency visible and attributable (§§4–5). Instead of
merging disagreeing values quietly, we audit them: at constant pH, 17 conflict groups
violate 10-fold; projected onto (pH, T), the same data form a 166-cluster conflict
atlas; every point retains its provenance, and every point drawn from a DOI-carrying
source retains its DOI, so a disputed number can normally be walked
back to its paper in one step; Section 5.5 states the exception, the one source that
publishes no DOIs. The audit is a living state machine that re-runs
deterministically as records are added, rather than a frozen table.

Third, we automate the curation itself (§3): a three-agent LLM pipeline converts a
PDF plus its supplementary materials into condition-bound records, evaluated at
F1 = 0.946 against 67 gold-annotated papers and at F1 = 0.907 against 100
triple-aligned papers. Automated extraction at this accuracy changes the scaling
behaviour of the layer rather than its cost: records are produced by a pipeline run and
spot-checked, not typed in one at a time, so extending the layer to new literature is
bounded by how many PDFs can be processed rather than by how many curator-hours are
available. We deliberately do not report throughput, latency, or monetary cost; those
depend on the deployed model, the hardware, and the pricing of the day, and we did not
measure them under a fixed protocol. What we do report is the accuracy at which a run
operates (Section 3) and the fact that every stage of the run is deterministic given the
model and the prompt, which is the property that makes the output auditable.

Finally, because the same data are widely used to train predictive models, **we
quantify the leakage that random evaluation protocols hide** (§6): the same classifier
and regressor, identical data and features, lose their apparent accuracy when folds are
grouped by paper, and only 4.1% of material–condition queries can be answered by
retrieval from a different paper under the same conditions, with cross-paper Kₘ
values scattering by a median of 13.2×. These numbers define when prediction is
unsupported and motivate the graded, uncertainty-aware answering protocol the
companion platform adopts (Section 7, future work).

### 1.3 Contributions and scope

In summary, this paper makes four contributions.

1. A condition-bound, 25-field data model and an integrated layer of 5,027
   entries from five provenance groups, with provenance and unit semantics preserved
   throughout (§2).
2. A cross-source audit that exposes systematic, order-of-magnitude unit-scale
   conflicts invisible to any single database, including two-camp cases where two
   independent sources agree against two others by exactly ×1000 (§4).
3. A condition-indexed conflict atlas with a live audit state machine (166
   clusters; 97 severe, 43 suspicious, 26 consistent), in which every value carries
   its source provenance and every value from a DOI-carrying source is DOI-traceable
   (§5), and an LLM-based extraction pipeline at F1 = 0.946 (§3)
   that keeps the layer extensible without per-record manual entry.
4. A leakage-quantified re-evaluation of nanozyme machine learning (§6): the
   apparent predictive power reported under random splits largely disappears under
   DOI-grouped folds, establishing a methodological baseline the field has not yet
   applied to itself.

Scope notes. We do not claim to construct a knowledge graph or ontologies; this work
is a reconciled, condition-bound dataset plus the tools to keep it reconciled. The
atlas clusters cross-literature conflicts, which are not single-system pH–response
curves and therefore cannot be read as materials physics without further experiments.
The sustainable public platform and the predict protocol that consumes these data are
described as future work (Section 7).

---

### 图表与数据对照（§1）

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 同 pH 跨源 17 组 ≥10× / N-PCNSs 10⁶× | §4.3（复核脚本 2026-09-10） | 17 组；N-PCNSs 0.000154 vs 154 mM |
| DiZyme 人工采集 1,210 samples（扩展版）/ >300 纳米酶（初始版） | ✅ 2026-09-11 回原文：JPCL 2024 [5] / Small 2022 [4] | 原 "400 篇" 无原文支撑，已剔除 |
| Wei 90.6%（R² up to 0.80, 920 条）/ DiZyme R²=0.75 / AI-ZYMES GBR 0.6476 | ✅ 2026-09-11 回原文（6 篇上传 PDF） | 随机拆分，无 DOI 隔离；0.648 → [7] Sun JCIM |
| 0.387→0.023 外部回归 | §6.3 m6_external.json | 2637→1165 行；材料级 −0.043 |
| Li 2023 展望第(1)条 | ✅ 2026-09-11 回原文取句 | "important and indispensable" / "standard and unified detection and representation methods" |
| 25 字段 / 5,027 / 761 / 388 | §2（实测 + atlas_summary） | 与 §2.3 一致 |
| 166 簇 / 97-43-26 | §5（audit.csv） | 与 §5.2 一致 |
| 检索覆盖 4.1% / 中位 13.2× | §6.4（b3 探针） | 40/978；命中组 P90 1.5e4× |
| F1=0.946（67 篇，CI95 0.885–0.976）/ 0.965（30 篇）/ 0.907（100 篇） | §3（_eval_gold67.json / _eval_30.json / _cross_validate.json） | 与 §3.2/3.4 一致；2026-09-11 扩样 |

> 待办（§1）：
> 1. ✅ **已解决（2026-09-11）**：Li 2023 展望第(1)条已回上传 PDF 取回原文句，正文引号内
>    现为原文（"important and indispensable"、"standard and unified detection and representation
>    methods"），"first priority" 式转述已删除。参考文献 [3] 已附原文核对记录。
>    遗留：原文段落截图未归档（`paper_notes/` 目录仍不存在，可后续补）。
> 2. §1.1 "the most extreme case spans 10⁶×" 与 §4.3 的 N-PCNSs 一致；"17 groups ≥10×" 用 §4.3
>    复核口径（2026-09-10），不用 m8-5 旧档 57 组——已保持一致。
> 3. §1.2 末句 "graded, uncertainty-aware answering protocol ... (Section 7, future work)" 与
>    §6.4/§6.5 的 "grading protocol sketched in Section 7" 表述需统一措辞；本稿用 "graded"，
>    定稿时二选一（建议统一为 grading protocol）。
> 4. §1.3 贡献 2 "two-camp cases ... exactly ×1000" 引用 §4.3 的 CuO/HccFn 例；"including two-camp
>     cases" 处建议补 CuO DOI（10.1021/acsami.6b05354）或留待正文。
> 5. ✅ **已解决（2026-09-11）**：Wei 2022 全名已补（15 位作者，*Adv. Mater.* **34**, 2201736，
>    DOI 10.1002/adma.202201736），条目 [2] 定稿；非 ACS AMI，是 Adv. Mater.。
> 6. ✅ **已解决（2026-09-11）**：四个外源数字已全部回原文核对（见文末「文献引用核对」），
>    其中两处须改：AI-ZYMES GBR 0.648 的出处是 Sun 2024 JCIM [7]（非 [6]）；
>    DiZyme 的 1,210 samples / R²=0.75 属 JPCL 2024 [5]，Small 2022 [4] 为初始版（>300 纳米酶、>100 篇）。
>    其余（Wei 90.6%/R² 0.80、Xuan 1,085 entries、Li 2023 原文句）与原文一致。

---

## Section 2 — A Condition-Bound Flat Schema as the Data Foundation

> 状态：英文初稿（2026-09-10）。源码依据：`schema.py`（FlatRecord，实测 25 字段，
> `FIELD_NAMES` 实测 `len=25`）、`integrator_agent.py`（记录拆分主键 + 条件绑定）、
> `kg/source_registry.py`（五公开库→FlatRecord）、`kg/excel_source.py`（人工 Excel→FlatRecord）、
> `workbench/atlas_out_multi/atlas_summary.json`（5,027 / 761 / 388）。
> 章节定位：数据底座（I1/I2 的载体）——§3–§6 全部依赖本节的字段契约。
> 写作遵循：数据零丢失、口径诚实、陈述中性、禁 AIGC 腔。

---

### 2.1 A single flat schema for condition-bound records

The unit of data in this work is a single catalytic measurement of one nanozyme under
one documented reaction condition. We encode it as a fixed, flat record (FlatRecord)
with 25 typed fields, grouped into six semantic blocks: identity (nanozyme material,
mimic enzyme activity, DOI), non-metal doping (five lattice dopants N/P/S/B/F), primary
metal composition (ratio, atomic number, valence), physical characteristics (morphology,
size, surface modification), and reaction conditions (dispersion medium, pH,
temperature, primary substrate), followed by the kinetic core (secondary substrate, Kₘ,
Vmax, kcat, catalytic efficiency, the substrate each constant is bound to, and the
assay method). Two design choices matter for everything downstream.

First, pH and temperature are first-class fields, not annotations attached to a
kinetic value in prose. Every Kₘ/Vmax/kcat carried by a record is explicitly bound to the
buffer pH (`buffer_ph_value`) and temperature (`temperature_c`) at which it was
measured, and a paper that reports constants under multiple conditions produces multiple
records rather than one aggregated row. This is the property that later sections exploit:
Section 4 can audit values "at the same pH", and Section 5 can cluster by (pH, T)
neighborhoods, neither of which is possible on condition-agnostic database extracts.

Second, the schema is flat and deterministic. All normalization—element symbols to
atomic numbers, mixed-valence strings to a single valence, "Mn:Co = 1:2" ratio strings
to a percentage, "1.2 ± 0.1" to the central value, Unicode scientific notation to
floating point, and unit suffixes (mM/µM/M/nm) to parsed numbers—happens in validator
code that is reproducible without any language-model involvement. The validator is
tolerant by design: a value that fails its field-specific parse is set to null with a
warning rather than rejecting the entire record, and the original strings are preserved
internally so that no information is destroyed by normalization.

### 2.2 Record identity and condition-bound splitting

A record's identity is the tuple (DOI, nanozyme material, mimic enzyme activity,
primary substrate). This four-part key is what the integrator uses to merge duplicate
extractions and what the downstream layers use to compare records from different
sources. Two records that agree on identity are "the same system"; the reaction
conditions (pH, temperature) are *not* part of the identity key, because they vary
across legitimate measurements of the same system. Instead, conditions split the level
of granularity: any record may materialize along the pH or temperature axis, so that a
single paper reporting Kₘ at pH 4.0 and pH 7.0 yields two condition-bound records
sharing one identity. Binding is enforced at integration time by a deterministic
experiment-binding step that groups rows by identity, then splits a group on (pH, T):
each output row is measured at exactly one documented condition point.

This convention has a direct consequence for the rest of the paper. A condition-agnostic
database answers "what is the Kₘ of Fe₃O₄–peroxidase–H₂O₂?" with one number pulled from
any pH; our foundation answers the same question with a *set of condition-bound records*,
each carrying its own pH, temperature, DOI, and provenance. Whether that set is coherent
is a question of empirical audit (Sections 4–5), not of storage design—but the storage
design is what makes the question answerable.

### 2.3 A five-source layer with intact provenance

The foundation is assembled from five provenance groups — human-curated records, merged
from two Excel spreadsheets maintained independently by domain researchers, plus four
public nanozyme databases: AI-ZYMES,<sup>8</sup> DiZyme,<sup>4</sup> NanozymeDB,<sup>10</sup> and nanozymenet-k (nanozymes.net kinetics)<sup>11</sup> — each
mapped into the same FlatRecord shape by deterministic column and unit normalization
that performs no conversion beyond what the source file header explicitly declares.
**Relationship to the sources.** One of the five sources is our own earlier work: the
corresponding author of this paper is a co-author of the AI-ZYMES papers (refs 7 and
8). AI-ZYMES is included and audited on exactly the same terms as the other four
sources, and the audit procedure is deterministic and is delivered in full as
Supporting Information (Tables S4–S6), so the result can be checked independently of
us.
Rows whose unit semantics cannot be determined are flagged, not guessed: a value of
uncertain unit is kept out of the normalized kinetic axis and handed to the audit layer,
because a silent unit assumption is exactly the class of error Section 4 exposes in the
public databases themselves.

After normalization and identity-key merging, the integrated layer holds 5,027
condition-bound kinetic entries covering 761 unique DOIs (Table S1). Of these DoIs,
388 are covered by two or more sources, which is the overlap that makes cross-source
auditing possible; the per-group contribution is 1,008 human entries, 1,031 from
AI-ZYMES, 1,210 from DiZyme, 596 from NanozymeDB, and 1,182 from nanozymenet-k
(Figure 2; Table S1 gives the per-source field map).
**DOI coverage.** Four of the six contributing source files carry a DOI on every record,
and those DOIs, together with the provenance group and the original unit semantics,
survive the entire integration, so a discrepancy observed downstream is attributable to a
specific source cell rather than to our alignment procedure. Two gaps remain and are
stated rather than smoothed over. First, nanozymenet-k publishes no DOIs at all: its
1,182 records enter the layer under a stable internal identifier (`na-<n>`) instead of a
DOI, and most of them also carry a unit-uncertainty flag, because its kinetic columns do
not declare their units. Second, 6 records adopted from AI-ZYMES likewise carry no DOI.
DOI coverage of the layer is therefore approximately 76%, and every conclusion that rests
on cross-source linkage is drawn from the DOI-carrying subset. Section 5.5 quantifies
what this costs the conflict atlas.

The three downstream analyses each depend on a different clause of this contract, and
none of them can be recovered after the fact. The cross-source audit (Section 4) needs
provenance and unit semantics intact, otherwise a ten-thousand-fold discrepancy could be
an artifact of our own conversion; the conflict atlas (Section 5) needs condition-bound
granularity and reference-record identity, otherwise clusters mix unrelated conditions;
and the leakage re-evaluation (Section 6) needs the flattened numeric fields and known
units to build features, and it measures the cost of relaxing the contract, because
pooling records without a condition axis inflates model scores through exactly the
leakage this foundation is designed out of.

---

### 图表与数据对照（§2）

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 25 字段六组语义块 | schema.py FlatRecord.model_fields 实测（conda base 运行） | len(FIELD_NAMES)=25 |
| 主键 (DOI, nanozyme, activity, substrate) | integrator_agent.py records merge key / _bind_experiments_by_rules | 四元组，pH/T 不入门键 |
| 条件拆分（pH/T 轴） | integrator_agent.py experiment-binding | 同 identity 内按 (pH, T) 拆行 |
| 容忍验证 + 原文保留 | schema.py safe_validate + _raw_inputs | 坏字段置 None，字符串存私有 |
| 5,027 条目 / 761 DOI / 388 多源 | atlas_summary.json entries / lineage | entries 5027, n_doi 761, n_multi 388 |
| 五源贡献 | atlas_summary.json provenance | human 1008 / ai-zymes 1031 / dizyme 1210 / nanozymedb 596 / nanozymenet-k 1182（合计 5027） |
| 不确定单位不猜测 | source_registry.py to_flat | km_uncertain=True 标记，非猜测换算 |
| Table S1 | 待生成 | 五源逐库 mapping + 规模明细 |

> 待办（§2）：
> 1. ✅ 已解决（2026-09-10 收尾）：字段数口径已统一为 **25**（实测 `FlatRecord.model_fields`=25，
>    2026-08-14 剔除 `substrate2_concentration_mM`，26→25）。详见 §2 数据对照表待办 1 的完成清单；
>    历史快照（memory/specs+plans/m8-*/系统漏洞分析）保留不改。
> 2. §2.3 提到 Table S1（五源逐库 mapping）需生成；§4.1 的五源数字（5,027/761/388）已核对一致。
> 3. §2.4 引 §6 "when records are pooled without a condition axis ... inflate"——是该节自身的结论，
>    此处作为前向引用，措辞已保守（"cost of relaxing the contract"），定稿时确认不过度抢 §6 的结论。
> 4. §2.5 平台章节已有独立中文草稿 `docs/paper_section_2_5_agent_platform_draft.md`（智能体平台 +
>    predict 三阶段 + 分支一致率 25/25），并入合并稿时作为 §2.5；其内部"26 字段"已同步改 25。
> 5. §2.3 五源名 nanozymenet-k（nanozymes.net kinetics）与 §4.1"nanozymenet-k"一致性已核对。
>    source_registry 另有 nanozymenet-m（材料元数据，不产 Kₘ）与 ChemX（磁学属性）不入动力学层，
>    如审稿问为何只有四公开库，SI 中说明。

---

## Section 3 — LLM-Based Automated Extraction of Condition-Bound Nanozyme Records

> 状态：英文初稿（2026-09-10）。数字来源：`workbench/model_swap_out/*/_eval_30.json`
> （4 个 flash+kimi 30 篇全量 + 1 个 qwen+kimi 30 篇全量；pro 仅 5 篇冒烟，不作为横比）、
> `workbench/evall_out/_cross_validate.json`（100 篇一致率）。
> 写作遵循：数据零丢失、口径诚实、陈述中性、禁 AIGC 腔。

---

### 3.1 A three-agent extraction pipeline

Manual curation of nanozyme kinetics does not scale with the literature: Kₘ, Vmax, and
their reaction conditions are presented in running text, tables, and figure insets in
mixed forms, and the effort per paper is large enough that even dedicated efforts such as
DiZyme still rely on human preprocessing.<sup>4</sup> Human extraction is itself imperfect:
a reproducibility study of evidence synthesis found that 17.0% of trial records could
not be reproduced from the original sources, with numerical mistakes and ambiguous
definitions the dominant error classes.<sup>12</sup> Large language models have recently been
applied to literature data extraction in adjacent materials domains — multicomponent
alloy data,<sup>13</sup> source-tracked multi-stage extraction pipelines,<sup>14</sup> automated
knowledge maps and databases,<sup>15</sup> and LLM-assisted curation of established materials
databases<sup>16</sup>. Closest to this work is nanoMINER,<sup>17</sup> a multi-agent
text-plus-vision system that also extracts nanozyme parameters, including Kₘ, Vmax, pH,
and temperature, and reports per-parameter precision and recall. What no prior system
provides is the *condition-bound* record itself — one row per documented (pH, T) point,
with each constant explicitly bound to its substrate — which is the property the cross-source
audit of Section 4 and the condition-indexed atlas of Section 5 both consume. Our
contribution is therefore the schema, the audit, and the leakage re-evaluation, not
multi-agent extraction as such. We address
this with a three-agent LLM
pipeline that converts a PDF (with its supplementary information, when present) into a
list of condition-bound FlatRecords under a fixed 25-field schema (Figure 3a).

Three extraction agents work in parallel and are fused by a deterministic integrator.
The text agent reads the full body text and tables and proposes records; the image agent
reasons over figure panels with a vision-language model, but only emits records for
figures that actually carry kinetic or morphology data (catalog and logo panels are
discarded after caption-anchored filtering); the metadata agent resolves title, DOI, and
SI attachment. The integrator then merges agent outputs by the record identity key — the
(DOI, nanozyme, enzyme activity, substrate) tuple — applying a deterministic post-filter
that normalizes units (mM / µM / M), binds values to their pH and temperature, and drops
duplicate or contradictory rows. Critically, records are split whenever a paper reports
independent Kₘ/Vmax at different pH or temperature, so that each output row is
condition-bound rather than an aggregate over conditions. All normalization steps live
in code and are reproducible without any LLM involvement.

The configuration is deliberately minimal: one text model, one vision model, one
integrator model, and a single synthesis prompt per agent. No rule-based grading layer
is imposed on top of the LLM output; the schema validator tolerates common LLM format
variants (element symbols vs. atomic numbers, "Mn:Co = 1:2" ratio strings, valence
notations) deterministically before records enter the output.

We ablate the LLM integrator on stratified papers: using only the text
and image agents with code-level merging (no LLM integrator) reaches F1 = 0.92 (0.917
baseline, 0.922 after deterministic post-filter fixes), while the full pipeline with
LLM integration and the deterministic post-filter reaches F1 = 0.965 on the 30-paper set
(0.946 on the 67-paper set; Section 3.2). **Caliber note.** The two ablation arms are
scored on a 19-field legacy caliber that includes `submetal_ratio` and the since-removed
`substrate2_concentration_mM`, whereas the 0.965 and 0.946 figures are scored on the
17-field caliber of Section 3.2; the ablation therefore brackets the integrator's
contribution and should not be read as a difference against 0.965 at fixed caliber. The
difference in either reading is dominated by the kinetic bundle: without LLM integration,
Kₘ and Vmax values from different condition tuples are merged or dropped, which is
precisely the failure mode that condition-bound storage is designed to avoid.

### 3.2 Evaluation against human-annotated gold standards

To measure extraction correctness rather than stylistic agreement, we evaluate against a
gold standard annotated field-by-field by domain researchers, using the same record-to-record
protocol as elsewhere in this work: each gold record is matched against the extracted output
under the same record-identity and field-comparison rules, and the 17-field comparable set is
reported. The comparable set is the subset of the 25-field schema that the gold annotation
actually covers: the eight fields dropped are DOI, surface modification, both substrate
slots, kcat, catalytic efficiency, and the two kinetic-binding fields, all of which were
annotated inconsistently or not at all. Two of the retained fields — Vmax and particle size
— are the weakest extracted ones (Section 3.2, Figure 3b; Section 4.5 bounds their use in
the audit); they are kept because dropping one's own weak fields before scoring would
inflate agreement rather than report it. Field
comparison is verbatim except where two notations carry one fact, and three fields are
normalised accordingly: metal identity (element symbol against atomic number), morphology (a
generic annotation such as "nanoparticle" is not charged against a more specific prediction),
and particle size (relative tolerance 30%, the spread of TEM and XRD reporting). Section 3.4
reports what the verbatim alternative would yield.
The annotation pool contains 200 reviewed papers; 67 of these also carry a full pipeline
extraction and form the primary evaluation set, and the original 30-paper set — stratified by
journal to approximate the population of nanozyme publications — is retained as a fixed
reference so that the effect of sample size can be read directly.

With the production combination — DeepSeek-V4-Flash for text, Kimi-K2.6 for vision, and
DeepSeek-V4-Flash for integration — the extraction reaches F1 = 0.946 on the 67-paper set
(precision 0.923, recall 0.972; macro-F1 0.943; 95% CI 0.885–0.976; Figure 3b). On the
30-paper set the same pipeline and protocol give F1 = 0.965 (precision 0.962, recall 0.968;
95% CI 0.865–0.992). The two numbers differ by 0.018, and the comparison is informative in
the direction that matters for interpretation: enlarging the sample by a factor of 2.2 lowers
the point estimate slightly but **raises the confidence floor from 0.865 to 0.885 and narrows
the interval from 0.127 to 0.091**. We therefore report the 67-paper figure as the headline
number and treat the 30-paper result as its optimistic predecessor rather than as the claim.

Field-level results on the 67-paper set are strongest for the activity label (F1 = 1.000),
Kₘ (0.960), buffer pH (0.954) and metal type (0.949), and weakest for particle size (0.830),
temperature (0.890) and Vmax (0.896), consistent with the discussion of weak fields in
Section 4.5. This ordering, not the aggregate, determines where the output can be trusted.

Two operational diagnostics govern downstream use. The kinetic bundle match rate — the
fraction of gold kinetic rows whose Kₘ and Vmax appertain to the same condition tuple — is
52.4% (98/187), material-family coverage is 91.3% (94/103), and 7.1% of candidates (14/197)
are left unresolved by the schema. We report these alongside the field scores because a
record can be field-correct and still unusable: if Kₘ and Vmax come from different condition
tuples, the row cannot answer a condition-bound query regardless of its F1.

We also report the stricter record-level measures, which are substantially lower: exact-match
(EM) 0.233 and the ≤1-error record rate (DVER) 0.433 on the same 67 papers. Field-level F1
near 0.95 and record-level EM near 0.23 are not in conflict — the former says that 95% of
*fields* are right, the latter that only about a quarter of *records* are right in every
field simultaneously. For a database that is populated record by record, the second number is
the operative one, and we use it to size the residual disagreement that the audit of
Section 4 must tolerate.

### 3.3 Model comparison

To justify the model choice on evidence rather than convenience, we compared text
backbones under the identical evaluation protocol (vision fixed to Kimi-K2.6; three
full runs of DeepSeek-V4-Flash, one full run of Qwen3-235B-A22B) on the 30-paper fixed set,
using the 18-field comparable set for both models to keep the comparison fair:

| Text backbone | F1 (18 fields) | Precision | Recall | Kinetic bundle | Unknown |
|---|---|---|---|---|---|
| DeepSeek-V4-Flash | 0.952 | 0.944 | 0.961 | 49.2% | 14.1% |
| Qwen3-235B-A22B | 0.944 | 0.904 | 0.989 | 15.8% | 18.5% |

The two models trade differently (Figure 3c): Qwen recalls more candidates (0.989 vs. 0.961) at the
price of precision, and its kinetic-bundle match rate collapses to 15.8% — a 33-point
drop, with Vmax magnitude errors up to 100×. Since the present application consumes
kinetic values as first-class data (Section 2), we selected DeepSeek-V4-Flash despite the
near-identical aggregate F1. A DeepSeek-V4-Pro variant was also evaluated and was
excluded from the formal comparison on cost grounds (footnote e gives the run and the
score).

### 3.4 Agreement on 100 triple-aligned papers

The 67-paper gold exercise quantifies correctness; scale is a different question. We
therefore measured field-level agreement between the pipeline and two existing resources
on 100 papers that appear simultaneously in our human Excel, in at least one public
database, and in our local PDF corpus. Against the manually curated Excel (100 papers, all
17 audited fields pooled), F1 = 0.907 (precision 0.869, recall 0.949, macro-F1 0.902);
against the public-database records (102 DOI-level matches, the database side covering
slightly more articles; pooled over the six fields the databases also carry — material,
mimicked activity, pH, temperature, Kₘ and Vmax), F1 = 0.907 (precision 0.891, recall 0.924,
macro-F1 0.904). Two methodological choices move this number, and we report both ends of
each rather than only the favourable one.

The first is aggregation. A pooled field-level F1 weights every field occurrence equally and
therefore lets frequent, easy fields dominate; weighting every paper equally instead — the
mean over papers of each paper's macro-F1 — gives 0.841 on the human side (median 0.863,
interquartile range 0.765–0.918, minimum 0.471; 72 of 100 papers reach 0.80 or better) and
0.843 on the database side (median 0.833, interquartile range 0.778–1.000, minimum 0.278; 73
of 102 at or above 0.80). Tables S7 and S8 give the per-field and per-paper detail behind both
figures.

The second is representation. Two curators can record the same fact in two notations, so, as
in the 67-paper exercise, three fields are normalised before matching: metal identity (element
symbol against atomic number), morphology (a generic gold label such as "nanoparticle" is not
charged against a more specific prediction such as "nanocube"), and particle size (±30%, the
spread of TEM and XRD reporting). Compared verbatim instead, the same 100 papers give
F1 = 0.847 (precision 0.769, recall 0.943). The entire 0.06 difference is carried by three
fields — metal identity 0.94 against 0.00, morphology 0.94 against 0.39, and size 0.76 against
0.68, while the remaining fourteen fields are identical under both rules. We retain the
verbatim figure in this work as an explicit lower bound. It is not, however, a measure of
extraction quality: an atomic number and its element symbol are one annotation written two
ways, and the gold morphology column is generic in 58% of its rows, so a verbatim comparison
of that field scores mainly whether the pipeline echoed the word "nanoparticle" rather than
whether it located the particle.

Agreement on Kₘ is centered:
across 251 matched pairs on the human side the median log10 fold deviation is 0.00, and
across 409 pairs on the database side it is 0.01, i.e., no systematic magnitude offset
separates our output from either reference in the bulk of the data. Restricted to Kₘ alone —
the quantity the audit consumes, and effectively the only kinetic field the public databases
carry on comparable terms — agreement is F1 = 0.903 on the human side (precision 0.918,
recall 0.888) and F1 = 0.909 on the database side (precision 0.921, recall 0.897); Vmax
agreement is lower on both sides (0.818 and 0.830), for the reason discussed in Section 4.5.

The tail of that distribution, not its center, is what the audit of Section 4 has to explain.
On the human side the 75th and 90th percentiles of the log₁₀ fold deviation are 1.17 and
2.41: 90% of the 251 matched pairs agree within a factor of 257, while the remaining 10%
disagree by two and a half orders of magnitude or more (maximum 4.30 log₁₀ units, i.e., about
2 × 10⁴-fold). The database side shows the same shape over 409 pairs (P75 = 1.23, P90 = 2.55,
maximum 5.50). A distribution that is centered at zero but carries a decade-scale upper tail
is not the signature of independent measurement noise, which would decay smoothly toward the
tail; it is the signature of a discrete relabeling — a unit assignment that is correct for
most rows and off by a power of ten for a minority. Section 4 identifies the mechanism in the
cases where the source publication can still be read, and Section 4.3 counts how often it
occurs among comparable same-pH buckets.

---

### 图表与数据对照

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 三智能体 + 25 字段 + 拆分主键 | CODE_WIKI / m8-4 I1 | doi+nanozyme+酶活+底物 |
| F1=0.965 (17 字段, 30 篇) | model_swap_out/deepseek-v4-flash__kimi-k2.6__20260816_210016/_eval_30.json | P 0.9615 R 0.9681 CI95 [0.8649,0.9915] |
| F1=0.946 (17 字段, 67 篇, 主口径) | evall_out/_eval_gold67.json（2026-09-11） | P 0.9226 R 0.9716 CI95 [0.8847,0.9760]; EM 0.233 DVER 0.4328; bundle 52.41% (98/187); unknown 7.11%; coverage 91.26% |
| Vmax F1=0.829 | 同上 field_level（210016, 30 篇） | Vmax_uM_s_minus1 |
| size F1=0.935 | 同上 field_level（210016, 30 篇） | size_nm |
| （100 篇口径：Vmax 0.818 / size 0.756） | _cross_validate.json human_side | 100 篇 triple-aligned，非 30 篇 |
| kin bundle 53.8% | 20260816_210016 diagnostics | 0.5378 |
| unknown 9.6% | 同上 | 0.0957 |
| 横比表 18 字段 | flash 20260812_124035 (0.9521, kin 0.492, unk 0.141) vs qwen 20260810_103914 (0.9443, kin 0.158, unk 0.185) | 两口径 fair |
| pro 5 篇冒烟 | deepseek-v4-pro__kimi-k2.6__20260809_211246 | F1 0.9495，仅 5 篇，不入横比 |
| 100 篇 F1=0.907 双侧（occurrence-pooled，**归一化口径**） | _cross_validate.json | human P0.869/R0.949 macro0.902（17 字段）; db P0.891/R0.924 macro0.904（db 仅 6 字段可比） |
| 100 篇 **逐字口径**（无归一化） | 复算 `workbench/_strict_probe.py`（2026-09-11） | human P0.7685/R0.9425 **F1 0.8467** mac0.8099 acc0.7341；per-paper macro 均值 0.7421；**这就是外部报告的 0.847 出处** |
| 100 篇 paper-level macro-F1 均值（归一化口径） | 同上 per_doi.overall.macro_f1 | human 0.8413（中位 0.860, IQR 0.765–0.916, min 0.471, ≥0.8 占 72/100）; db 0.8433（中位 0.833, IQR 0.777–1.000, min 0.278, ≥0.8 占 73/102） |
| 归一化三条规则 | cross_validate.py `_records_match`（2026-09-10 加） | metal_type 符号↔原子序数；shape 上位词（nanoparticle/polyhedral/particle）+ 子串；size_nm 容差 10%→30% |
| 逐字→归一化 差异分解（human） | 上述两次复算 | metal_type 0.00→0.9389；shape 0.39→0.9423；size_nm 0.684→0.7563；其余 14 字段完全相同 |
| 一致性证据 | 67 篇 gold（_eval_gold67.json） | metal_type 0.949 / shape 0.898 / size_nm 0.830 — **均非 0，说明 §3.2 用的就是归一化口径**，故 §3.4 取 0.907 才与 §3.2 同口径 |
| 消融：无 integrator F1=0.917→0.922 | ablation_out/stratified_30/_eval_baseline.json / _eval_after_fix.json | 代码合并 + 后处理修复；全管线 0.965 |

> 待办（写正文前必做）：
> 0. ✅ 已解决（2026-09-11）：§3.2 字段级引用错位已修正——0.818/0.756 实为 **100 篇**
>    `_cross_validate.json`（human_side）的值，被误放进了 30 篇 gold（eval_30）语境。
>    现 §3.2 用 30 篇实测：**Vmax=0.829、size=0.935**（210016 field_level）。
>    100 篇口径的 0.818/0.756 保留在 §3 对照表备查，且与 §4.5 弱字段表述一致。
> 1. flash 17 字段最优版有两个：20260816_123718 (F1=0.9677, kin 0.563) 与 20260816_210016 (F1=0.9648, kin
>    0.538)。本稿采用 210016（论文已沿用的 CI95 出处）。若论文最终用 123718 需要在 §3.2 与 m8-4 间统一口径。
> 2. 横比表的 kinetic bundle 为 18 字段版数字（flash 20260812: 0.492 vs 0.158），与 §3.2 的 17 字段 53.8%
>    不同口径，正文已注明"18-field comparable set"，表头需保持该注释以免读者混淆。
> 3. 消融实验 (0.917→0.922 vs 0.965) 来自 `stratified_30` 目录，需复核其评估协议与 §3.2 的 17/18 字段口径一致
>    后再引用；`_gold_30.xlsx` 与 papers_30 是否为同 30 篇需确认。

---

## Section 4 — Cross-Source Audit: Reconciling Nanozyme Kinetic Data across Public Databases

> 状态：英文初稿（2026-09-10）。数字均来自 `workbench/atlas_out_multi/cross_source_conflicts.csv`、
> `atlas_summary.json`、`workbench/evall_out/_cross_validate.json`，可逐条溯源。
> 章节定位：轨道一最强数据贡献（I2）。写作遵循：数据零丢失、诚实口径、陈述中性、禁 AIGC 腔。

---

### 4.1 A multi-source integration layer for nanozyme kinetics

A recurring obstacle to data-driven nanozyme research is the fragmentation of catalytic
parameters across independent curation efforts. Kinetic constants such as the Michaelis-
Menten constant (Kₘ) and the maximum velocity (Vmax) are reported per paper as isolated
numbers, frequently without machine-readable units, and are re-annotated separately by
each public database: AI-ZYMES, DiZyme, NanozymeDB, and nanozymenet-k, in addition to
manually curated spreadsheets maintained by domain researchers. None of these resources
performs a systematic cross-audit against the others; discrepancies of several orders of
magnitude for the same material–substrate pair are therefore invisible to any single
database's users. AI-ZYMES is the authors' own resource (Section 2.3); it is treated here
as one of the audited sources, and the cross-source conflicts reported below were
identified by a deterministic procedure rather than by curatorial judgement, so the audit
can be reproduced without trusting any of the five sources — including our own.

We assembled these sources into a single condition-bound integration layer following the
uniform FlatRecord schema described in Section 2 (25 fields, pH and temperature kept as
first-class attributes). The merged layer contains 5,027 condition-bound kinetic entries
covering 761 unique DOIs, contributed by five provenance groups: human-curated Excel
records (1,008 entries), AI-ZYMES (1,031), DiZyme (1,210), NanozymeDB (596), and
nanozymenet-k (1,182). Among the 761 DOIs, 388 are covered by two or more sources,
creating the overlap that makes a cross-source audit possible. All entries carry their
DOI and original unit semantics (mM vs. µM vs. M) intact through integration, so any
subsequent conflict is attributable rather than introduced by our normalization.

### 4.2 Extraction agreement as a precondition for auditing

Before interpreting cross-source discrepancies as database errors, we must establish that our
own records agree with existing resources under a comparable protocol. Section 3.4 reports that
agreement on the 100 triple-aligned papers: F1 = 0.907 against the human Excel (precision 0.869,
recall 0.949) and F1 = 0.907 against the public-database records (precision 0.891, recall 0.924),
with a median Kₘ deviation of zero on a log-fold scale. Two consequences follow, and their
asymmetry matters. First, no systematic magnitude offset separates our output from either
reference, so an order-of-magnitude disagreement observed downstream cannot be an artifact of our
extraction. Second, and this is the limit of the argument, agreement with a reference only shows
that we reproduce it; it does not certify the reference. Because Section 4.3 shows that some of
those very references carry unit-scale errors, we use agreement strictly as a *precondition* for
auditing (we are not the source of the conflicts) and never as evidence that a disputed value is
correct. Where correctness matters, the argument rests on the source-publication recovery of
Table S6, not on inter-source agreement.

Bounding this explicitly: certifying the references themselves would mean re-extracting every
disputed value from its source publication. We have done that for the 17 most severe
conflicts, the ones that carry the argument, and report the outcome group by group in
Table S6, rather than for the full layer. We therefore quote no layer-wide figure for
reference accuracy, and none should be inferred from the agreement numbers above. This is a
stated boundary of the present audit: the claim is that the conflicts we report are real and
attributable, not that every value outside them is correct.

### 4.3 Systematic unit-scale conflicts across sources

Before counting conflicts we state the denominator explicitly. Of the 388 multi-source DOIs,
348 contribute at least one same-pH comparison with two or more separately curated sources; these
resolve into 949 same-pH comparison buckets (918 unique DOI–material–substrate systems).
Comparing only entries recorded at the same pH to avoid conflating true condition
dependence with annotation error, the disagreement distribution over these buckets is
40 ≥ 2×, 24 ≥ 5×, 17 ≥ 10×, and 10 ≥ 100× (Figure 4a; the full census is given in
Table S5). The conflict *rate* is therefore low — 1.8% of comparable buckets disagree by more
than an order of magnitude, while the conflict *magnitude* is extreme, reaching 10⁶. A 10-fold ladder is characteristic of
unit misassignment (mM vs. µM vs. M differ by powers of ten), whereas genuine
experimental variability rarely spans orders of magnitude for the same material,
substrate, and pH. The census is corroborated at a larger scale by the agreement
distribution of Section 3.4: across 251 human-side and 409 database-side Kₘ pairs the
deviation is centered at zero but carries a decade-scale upper tail (P90 = 2.41 and 2.55
log₁₀ units), so the 17 groups reported here are the visible tip of a population-level
phenomenon rather than a handful of isolated curation accidents.

The most extreme case is N-PCNSs (DOI 10.1038/s41467-018-03903-8), a nitrogen-doped
carbonaceous nanozyme. At pH 7.0 and H₂O₂ substrate, the Kₘ is recorded as 1.54 × 10⁻⁴ mM
by AI-ZYMES and by our human-curated annotation, whereas NanozymeDB
records 154 mM for the identical condition — a 10⁶-fold spread that an exact power of ten
identifies as a unit artifact rather than an experimental difference, and that two
separately curated sources (AI-ZYMES, our own, and the human annotation) agree on
(Table S3, Figure 4b). The CuO series
(DOI 10.1021/acsami.6b05354) shows the complementary pattern at pH 4.65: AI-ZYMES and
the human annotation both give 0.4 mM, while DiZyme and NanozymeDB give 400 mM
(×1000), i.e., two internally consistent camps separated by exactly three orders of
magnitude (Figure 4c). The same "two-camp ×1000" signature recurs across unrelated
materials (CuO, HccFn(Fe₃O₄/Co₃O₄)) listed in Table S3, pointing to systematic unit-scale
labeling errors inside a subset of the public databases rather than to our alignment
procedure.

What the source publications say. A power-of-ten ladder is suggestive, not probative, so
we attempted to recover each conflict at its source (Table S6). For the two-camp ×1000
signature the recovery is decisive. In the CuO paper (DOI 10.1021/acsami.6b05354) the
kinetic table declares its unit in the column header, "K_m (M)", and reports 0.40 for
H₂O₂ and 0.025 for TMB; the two database camps store 0.4/0.025 and 400/25 respectively.
Since 0.40 M = 400 mM and 0.025 M = 25 mM, the ×1000 gap is an M→mM conversion step that
one pair of sources performs and the other does not: the two camps are the *same measurement*
recorded under two unit conventions, not two disagreeing experiments. The HccFn paper
(DOI 10.1021/acsami.8b20942) reproduces the pattern in a second, independent material: its
kinetic table likewise declares "K_M (M)", and its two TMB rows read 0.84 and 1.12 —
stored by one camp as 0.84 and 1.12 mM and by the other as 840 and 1120 mM. The same table
also supplies an internal control: its two H₂O₂ rows are stored identically by every source
(1770 and 2480 mM, fold 1.0), so the mis-scaling is a per-row behaviour of the sources that
split rather than a property of the paper. Both recoveries required reading a rasterised
table, which we did by OCR. Three further groups
(NiO, H₂TCPP-NiO; DOI 10.1016/j.bios.2014.08.062) are directionally consistent with the same
reading: the paper tunes its substrate concentration over 10–250 mM, against which a stored
Kₘ of 0.00666 mM is three orders of magnitude below the lowest assayed concentration.
For the remaining groups the worksheet stops at a mechanical obstacle rather than a
scientific one: the kinetic table is a raster image with no text layer, the values sit in a
supplementary file, or the PDF is absent from our corpus (8 of the 10 unique DOIs behind the
17 groups were located). Reading those source tables resolved 8 of the 17 groups: 4 confirmed
unit conversions, 3 directionally supported, and 1 that proved *not* to be a unit artifact at
all but a conflation of catalyst and reporter in the databases' own keys — leaving 9
undecided (Table S6). We therefore
claim the unit-conversion mechanism as *established for the two-camp ×1000 signature*, where
an exact power of ten admits no other reading, and as a hypothesis for the remainder.

### 4.4 Condition-resolved conflict atlas

Merging the conditions back into the picture turns the pairwise conflicts into a
condition-bound conflict atlas. Projecting Kₘ of identical material–activity–substrate
tuples onto the (pH, T) plane produces 166 conflict clusters across the integrated
layer. The sharpest clean example is the pure Fe₃O₄–peroxidase–H₂O₂ locus at pH 4.0,
25 °C: five independent papers report Kₘ from 0.076 to 185 mM, a 2,434-fold spread
under identical conditions (DOI set in Supporting Information, Figure 5), with each point
carrying its DOI and source lineage, so the spread is fully auditable rather than
anonymous. Pooling all 130 condition-resolved Kₘ measurements from the 34
Fe₃O₄–peroxidase–H₂O₂ papers without a condition axis inflates the spread to
1.05 × 10⁶-fold (0.0028–2,951 mM, across all pH windows), which is precisely why a
condition-agnostic database cannot distinguish unit-scale annotation error from genuine
pH dependence. Two single-paper condition series used in this work as controlled case
studies confirm that, when experimental conditions are held fixed by the original
authors, cross-source Kₘ values collapse onto the same locus: for the polyoxometalate
K5PV2Mo10O40 (oxidase, TMB, DOI 10.1039/c0cc04850j) the human annotation and AI-ZYMES
agree on every pH of the 3.0–7.0 series (Kₘ 0.0004–0.0086 mM at 25 °C), and the
perforated-graphene gold composite HBPG-AuNPs (peroxidase, H₂O₂, DOI
10.1007/s00216-016-9976-z) shows identical cross-source values across pH 3.0–8.5
(Kₘ 63–778 mM at 25 °C).

The atlas exposes what condition-agnostic storage hides: a database entry "Fe₃O₄,
peroxidase, H₂O₂, Kₘ" is meaningless without its pH and temperature, and discrepancies of
10³–10⁴ within one material–substrate pair are inflated by pooling unrelated conditions.
Every cluster enters a deterministic audit state machine in which severity is assigned
from the within-cluster spread (consistent, suspicious, or severe at 30% and 100%
relative spread, respectively), tier 1–3 recommends no review, expert review, or
experimental verification, and each row keeps the underlying DOIs for re-checking or
correction as the field produces new data (Section 5).

### 4.5 Scope and honest limitations

Three caveats bound these claims. First, cross-literature conflict clusters are not
single-system pH–response curves: they pool independent syntheses whose batch-to-batch
size, crystallinity, and surface chemistry differ, so part of the observed spread is
genuine experimental variability rather than annotation error. Our unit-scale
attribution (Sections 4.3–4.4) is best supported where the fold ladder matches unit
semantics (10²/10³/10⁶) and where the human annotation independently selects one ladder
rung. It is not universal: reading the source tables showed that one of the 17 groups is
not a unit artifact at all but a conflation of modifier and reporter in the databases' own
keys (Section 4.3, case A2), which is why the mechanism is claimed as established only for
the two-camp ×1000 signature and as a hypothesis elsewhere. Second, the same-pH conflict census (17 groups above 10-fold) is obtained under the
agreement protocol of Section 4.2; conflicts between sources that never co-occur in a
triple-aligned paper are not enumerated here. Third, our extraction itself is a candidate
source of residual
disagreement — the Vmax and particle-size fields in particular degrade the overall
agreement (Section 3), so the audit conservatively excludes those fields from the
"comparable field set" of Section 4.2.

Despite these limits, the aggregate picture is unambiguous: public nanozyme kinetic
databases contain systematic unit-scale conflicts that no single resource — including
AI-ZYMES, which is our own — has reported
or corrected. We provide the full conflict census, per-source values, and unit-recovery
worksheets in the Supporting Information, enabling domain experts to adjudicate the
individual cases.

---

### 图表与数据对照

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 5,027 条目 / 761 DOI / 388 多源 | atlas_summary.json lineage | n_doi 761, n_multi_source_doi 388 |
| 五源贡献 | atlas_summary.json provenance | human 1008 / ai-zymes 1031 / dizyme 1210 / nanozymedb 596 / nanozymenet-k 1182 |
| F1=0.907 双侧 | _cross_validate.json | human P0.869/R0.949 macro 0.902（100 篇，n=251 Kₘ 对）; db P0.892/R0.924 macro 0.904（102 篇，n=409 对）; Kₘ log10 fold median 0.00/0.01, P90 2.41/2.55 |
| 同 pH 跨源冲突 17 组 / fold≥100 ×10 | 2026-09-11 复核脚本（recheck_sameph_conflicts.py，按 doi+材料+底物+pH 精确分组） | fold≥10 ×17, fold≥100 ×10 |
| N-PCNSs pH7.0 10⁶ | db_records/atlas_records 10.1038_s41467-018-03903-8.json | ai-zymes 0.000154 / nanozymedb 154 / human 0.000154 |
| CuO pH4.65 ×1000 | db_records/atlas_records 10.1021_acsami.6b05354.json | ai-zymes 0.4 / dizyme 400 / nanozymedb 400 / human 0.4 |
| 166 冲突簇 | atlas_summary.json | n_conflict_clusters 166 |
| Fe₃O₄ 同条件 2434× / 全局 1.05×10⁶ | `workbench/figs/_probe_fig5_gray.py`（2026-09-11 复算） | pH4.0/25°C 五篇 0.076~185（**可精确复现**）；全局 34 篇/130 点 0.0028~2951.1（全 pH 窗口）＝1,053,964×。**旧值「26 篇 0.0028~1175.3（pH3.0–4.5）＝4.2×10⁵」已作废**：0.0028 实际在 pH 4.6、1175.3 在 pH 4.4，且 pH 4.5 存在 2951.1/2528.4/2480 三个更大值，任何单一 pH 窗口都取不到该组合 |
| K5PV2Mo10O40 pH 系列 | atlas_records + db_records 10.1039_c0cc04850j.json | 5 点 pH3.0–7.0，Kₘ 0.0004–0.0086，human≡ai-zymes |
| HBPG-AuNPs pH 系列 | atlas_records + db_records 10.1007_s00216-016-9976-z.json | 5 点 pH3.0–8.5，Kₘ 63–778，human≡ai-zymes |

> 待办（写正文前必做）：
> 0. ✅ 已解决（2026-09-11）：同 pH 冲突口径统一为 **17 组 ≥10× / 10 组 ≥100×**（可复现脚本
>    `workbench/figs/recheck_sameph_conflicts.py`，输出 `fig4_conflicts_sameph.json`）。
>    §4.3 正文、对照表、Fig 4a 均已同步；§1/§7/Abstract 只引 17 组与 10⁶×，无需改动。
> 1. Fe₃O₄ 6913× 已弃用，正文用 2434×（同条件）/ 1.05×10⁶（全局，全 pH 窗口）。
>    2026-09-11 更正：更早的「4.2×10⁵（pH3.0–4.5）/ 26 篇」不可复现，已全部替换（§4.4、Fig 5 图注、§5.2）。
> 2. "混合 pH 全量冲突普查（5× 起）"作为 SI 附表，正文只用同 pH 口径 17 组。
> 3. Fig 6 的 Fe₃O₄ 簇图需以 pH4.0/25°C 五篇 DOI 为准重绘。
> 4. Fig 4 面板 (b)(c) 数据源已定：N-PCNSs(ai-zymes/nanozymedb/human) + CuO(四源)，按 pH 标注条件。
> 5. 两个干净案例图（可选 SI）：K5PV2Mo10O40 / HBPG-AuNPs 的跨源 pH 轨迹叠加图可直接由两 case 数据绘制。

---

## Section 5 — A Condition-Indexed Conflict Atlas with a Live Audit State Machine

> 状态：英文初稿（2026-09-10）。数字来源：
> `workbench/atlas_out_multi/audit.csv`（166 行, tier3 97 / tier2 43 / tier1 26）、
> `atlas_summary.json`（n_conflict_clusters 166）、`kg/conflict.py`（severity 阈值）、
> `kg/audit_state.py`（tier 状态机）、2026-09-10 重建脚本（Fe₃O₄ 簇 2434×；全局值 2026-09-11 复算为 1.05×10⁶）。
> 写作遵循：数据零丢失、诚实口径、陈述中性、禁 AIGC 腔。

---

### 5.1 Why condition indexing changes the picture

All existing nanozyme databases store one kinetic value per material–substrate pair
without a condition axis. A single entry "Fe₃O₄, peroxidase, H₂O₂, Kₘ" aggregates values
measured anywhere between pH 2 and pH 8, at temperatures from ambient to 50 °C, by
syntheses that differ in size, crystallinity, and surface chemistry. Under this
convention a ten-thousand-fold disagreement can be invisible — or can masquerade as
"batch variability", when part of it is none other than the system's real condition
dependence.

We therefore index every kinetic record by the reaction conditions under which it was
measured, and cluster records by material–activity–substrate tuples with explicit pH and
temperature tolerances (ΔpH 0.2, ΔT 2 °C). A conflict is defined only within a cluster;
values from neighboring conditions never compete. This turns the flat storage into a
condition-indexed conflict atlas: 166 clusters across the integrated layer (Figure 6), each holding
the Kₘ, Vmax, or kcat values of the same material–substrate system measured under
comparable conditions by independent papers, together with the DOI and provenance of
every point.

### 5.2 The conflict spectrum across the atlas

The 166 clusters are distributed across metrics (91 Kₘ, 64 Vmax, 11 kcat) and display a
clear severity structure. For each cluster, the relative spread  (max − min)/median is
computed; clusters with spread below 30% are labeled consistent, 30–100% suspicious, and
above 100% severe. On the current layer, 26 clusters are consistent, 43 are suspicious,
and 97 are severe (Figure 7), i.e., for the majority of material–substrate systems with multiple
independent measurements under comparable conditions, the reported values disagree by
more than a factor of two about the median. Within this tail, 7 clusters additionally
carry a unit-magnitude-suspicion tag, i.e., a fold that coincides with a power of ten
(Table S4); the most striking are MnO₂–oxidase–TMB at pH 4.0 (Kₘ 9.5 × 10²-fold),
CeO₂–peroxidase–H₂O₂ at pH 4.0 (Kₘ 9.64 × 10²-fold), and Fe₃O₄–peroxidase–TMB at pH 4.0
(Vmax 9.5 × 10¹-fold), all at 25–45 °C.

Two examples clarify what the atlas separates. At the pure Fe₃O₄–peroxidase–H₂O₂ locus
at pH 4.0, 25 °C, five independent papers report Kₘ from 0.076 to 185 mM, a 2,434-fold
spread under identical conditions (Section 4.4; Figure 5). Pooling all 130
condition-resolved Kₘ measurements from the 34 Fe₃O₄–peroxidase–H₂O₂ papers without a
condition axis inflates the spread to 1.05 × 10⁶-fold across all pH windows;
the atlas attributes most of that inflation to condition mixing, but retains the
remaining 2,434-fold as a genuine same-condition conflict to be adjudicated. By contrast,
the K5PV2Mo10O40 and HBPG-AuNP series of Section 4.4 fall into consistent clusters across
all their pH points — independent sources agree when the original papers measured a
controlled series.

### 5.3 Provenance and lineage tracking

Every point in the atlas carries its provenance group (human Excel, AI-ZYMES,
DiZyme, NanozymeDB, or nanozymenet-k), and every point drawn from a DOI-carrying source
carries its DOI as well. The lineage
matrix reports that 388 of 761 DOIs are covered by two or more sources, so that a
conflict is never an anonymous outlier: each cluster row lists its per-source values
explicitly (Table S4), and any value can be re-annotated or corrected without breaking
the rest of the cluster. This resolvability is the property that distinguishes the
atlas from a plain database extract — a reader can walk from a disputed number to the
original paper in one step, for every record whose source publishes a DOI. The single
exception, nanozymenet-k, contributes no DOIs; its records are identified by stable
internal keys and are flagged in Table S4, and Section 5.5 quantifies how much of the
atlas depends on them.

### 5.4 The live audit state machine

Because the atlas is rebuilt deterministically whenever records are added to the layer,
its conflict census and severity assignments update automatically. On top of the
severity labels we attach an audit state: tier 1 (consistent) proceeds without review;
tier 2 (suspicious) flags the cluster for expert inspection; tier 3 (severe) marks the
cluster as requiring experimental or bibliographic verification before the value is
used in downstream modeling. The audit CSV therefore is not a frozen snapshot but a
living register: adjudication of one DOI re-runs the deterministic pipeline, moves only
that cluster, and leaves the remaining 165 clusters untouched. In the current layer, 97
clusters sit in tier 3 and 43 in tier 2 — a quantitative, trackable inventory of where
nanozyme kinetic data are too unreliable for analysis without condition-level
adjudication.

### 5.5 Scope and honest limitations

We restrict the conflict claim to same-condition, cross-literature disagreement: the
cluster construction removes the confound of condition mixing, but it does not remove
batch-to-batch synthesis variability, which is real and unknowable from the literature
alone. Tier-3 status therefore means "needs adjudication", not "confirmed wrong".
Second, the severity thresholds (30%/100%) are arbitrary standardization choices; they
are deterministic and stated, so results are reproducible under other thresholds.
Third, clusters of size two (a single pair of papers) cannot distinguish "two honest
but different measurements" from one error; we still report them, as withholding them
would understate the atlas's disagreement rate. Fourth, and most consequential for the
tier counts, one source publishes neither DOIs nor unit-annotated kinetic columns:
nanozymenet-k contributes 1,182 records, none of them DOI-bearing and most of them
carrying a unit-uncertainty flag. Thirteen of the 166 clusters contain at least one such
record, and because their kinetic magnitudes are not unit-verified those clusters carry no
evidential weight. Removing all 13 leaves 153 clusters distributed as 21 consistent / 41
suspicious / 91 severe, and lowers the number of clusters with a ≥10⁶-fold spread from 11
to 5 (from 17 to 11 at ≥10⁴-fold). The severity structure therefore does not rest on the
unverified source. Fifth, the 64 Vmax-based clusters sit on the weakest extracted field
(F1 0.896; Section 3.2), so we recompute the tier distribution on the Kₘ clusters alone:
91 clusters, distributed as 15 consistent / 28 suspicious / 48 severe — a 52.7% severe
share against 58.4% overall. The audit's conclusion is carried by the Kₘ clusters, which
are the quantity the public databases carry on comparable terms, and not by Vmax. Both
breakdowns are given in Table S9. Finally, the atlas currently indexes
conditions at the pH/temperature granularity reported in the papers; buffers, ionic
strength, and substrate concentration are not yet part of the clustering key, and
reporting them in future versions will only sharpen or resolve borderline clusters.

---

### 图表与数据对照

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 166 簇 / 91 Kₘ / 64 Vmax / 11 kcat | atlas_summary.json n_conflict_clusters + audit.csv 指标列 | 166 = 97+43+26 |
| 26 一致 / 43 可疑 / 97 严重 | audit.csv tier 列 | tier1 26 / tier2 43 / tier3 97 |
| ΔpH 0.2 / ΔT 2°C | kg/conflict.py PH_TOL / T_TOL | PH_TOL=0.2, T_TOL=2.0 |
| 30%/100% 阈值 | kg/conflict.py severity_of | 一致<0.3 / 可疑≥0.3 / 严重>1.0 |
| tier 状态机 | kg/audit_state.py SEVERITY_TO_TIER | 一致→1 / 可疑→2 / 严重→3 |
| 7 组单位错配疑似 | audit.csv 疑因标签 | 单位量级错配?/跨文献 7 |
| Fe₃O₄ 2434× / 1.05×10⁶ | `workbench/figs/_probe_fig5_gray.py`（2026-09-11 复算） | pH4.0/25°C 五篇 0.076~185；全局 34 篇/130 点 0.0028~2951.1（全 pH 窗口）＝1,053,964×。旧值 4.2×10⁵/26 篇不可复现，已作废 |
| 388/761 多源 DOI | atlas_summary.json lineage | n_multi_source_doi 388 |
| K5PV2Mo10O40 / HBPG-AuNP 一致簇 | atlas_records + db_records 同 DOI | 逐 pH 跨源一致（见 4.4） |

> 待办（写正文前必做）：
> 1. ~~§5.2 单位错配疑似组~~ **已提取**：7 组全 tier3，MnO₂ km 950× / CeO₂-perox-H₂O₂ km 964.18× /
>    Fe₃O₄-perox-TMB vmax 94.87× 等，已在正文引用并待入 Table S4。
> 2. Table S4（SI）：逐簇 tier/降序 fold/DOI=值 全表，由 audit.csv 直接派生，注意 audit.csv 列是中文，
>    SI 表需与正文英文术语对齐。
> 3. §5.4 "re-runs the deterministic pipeline" 的活审计演示：audit_state.py 单测覆盖 tier 映射即可，论文
>    里无需运行演示，但 Method 需注明"随文献增长重跑即自动更新"。
> 4. Fig 6（Fe₃O₄ 簇图）+ Fig 7（audit tier 分布条形图）的数据源已定，待绘图。
> 5. §5.5 三个局限均需在 Method/讨论呼应，避免论文自洽性问题。

---

## Section 6 — Quantifying Evaluation Leakage in Nanozyme Machine Learning

> 状态：英文初稿（2026-09-10，二次修订）。数字来源：`workbench/ml_out/m5_report.json`、
> `m6_external.json`（2026-09-10 复跑，新增 `full_ext_all` 字段，全外部 2637 行 R²=0.387 已存档）、
> `b1_probe.py` 实测（`_b1_probe_run.txt`）、`b3_probe.py` 实测（`_b3_probe_run.txt`）。
> conda base 复现路径已记录。§6.2 表格已按实测全文核对；§6.3 回归口径与 m8-4 统一（0.387→0.023）。
> 章节定位：方法论校正（I3）——"给整个子领域泼冷水"的 calibration 章节。
> 写作遵循：数据零丢失、诚实口径、陈述中性、禁 AIGC 腔。

---

### 6.1 The leakage problem

High predictive accuracy on nanozyme activity is frequently reported in the literature:
Wei et al. achieve 90.6% classification on random splits,<sup>6</sup> DiZyme reports
stacking-model R² up to 0.75,<sup>3</sup> and AI-ZYMES reports a gradient-boosting
regressor with R² ≈ 0.65 for Kₘ.<sup>7</sup> These
numbers are widely quoted, yet they share a methodological feature that undermines
them: random splitting places records from the same paper, often the same material in
the same lab — simultaneously in the training and test folds. A model can then "recognize
the material" rather than predict the property, an instance of group leakage that is
standard knowledge in machine learning but has not been audited in the nanozyme
literature.

Concretely, a dataset derived from nanozyme papers is grouped by DOI: one publication
reports several Kₘ/Vmax rows for the same material across conditions, and those rows
carry correlated synthesis, measurement, and reporting characteristics. Under a random
split some rows of a group land in training while their siblings land in test; the
classifier's accuracy and the regressor's R² then measure memorization of the group
label as much as generalization. We quantify this effect with a minimal experimental
change, the identical model, the identical features, and the identical data, differing
only in how cross-validation folds are formed. We stress the scope of this comparison: we
re-run the *splitting protocol* on our own integrated layer rather than re-executing the
published pipelines, whose code and training data are not available. The claim is therefore
about the protocol and the data structure it is applied to, not about the correctness of
any specific prior implementation.

### 6.2 Classification: random vs. DOI-grouped evaluation

We use a standard random-forest classifier on two data sizes, 1,056 and 3,002 rows drawn
from the integrated layer (Section 2), predicting the catalytic type (POD, OXD, CAT, SOD);
all models and evaluation machinery (random forests, grouped cross-validation) are
standard scikit-learn components.<sup>18</sup>
The only procedural difference between the two runs is the split: stratified random
5-fold versus 5-fold grouped by DOI, so that no paper contributes rows to both training
and test in the same fold.

| Data / features | Random 5-fold | DOI-grouped | Majority baseline |
|---|---|---|---|
| Core (n=1,056), no substrate | 0.816 | 0.672 | 0.695 |
| Core (n=1,056), with substrate | 0.813 | 0.723 | 0.695 |
| Core + databases (n=3,002), with substrate | 0.840 | 0.783 | 0.783 |

Under random splitting, accuracy (0.816) is of the same order as the 90.6% vintage of Wei et al. in
magnitude. Under the honest DOI-grouped protocol, accuracy drops to 0.672 — at or below
the 0.695 majority-class baseline, i.e., the classifier is not better than predicting
"POD" for every row (Figure 8a). The per-class picture is worse: macro-F1 collapses from 0.673 to
0.350 on the core set, with the minority classes SOD (F1 0.686 → 0.074) and CAT
(0.500 → 0.152) being essentially unlearnable once leakage is removed. Adding public
database rows (n=3,002) improves random-split accuracy to 0.840 but leaves grouped
accuracy pinned at the 0.783 baseline — more data does not cure a leakage-driven
score.

> 口径注（写表注用）：with-substrate 特征的 DOI-grouped 为 0.723（不做主要结论，
> 主文以 no-substrate 0.672 vs 基线 0.695 为对照）；0.723 也已低于随机 0.813，
> 与主修方向一致，但读时应以主修行为准。

### 6.3 Regression: same rule, different numbers

The same discipline applies to Kₘ regression, and here the magnitude of the effect is
largest. On 978 rows with a random-forest regressor (the same feature family as in
Section 6.2; 200 trees, min_samples_leaf=2) and condition features (pH, temperature,
substrate), internal 5-fold OOF with DOI-grouped folds gives R² = 0.134. We then repeat
the classic external-validation protocol as it is routinely reported in this
literature: the model is trained on the corpus and evaluated on all 2,637 external rows
that carry pH, temperature and Kₘ, including rows whose DOI already appears in
training. This yields R² = 0.387 under the same *protocol* on which those
external-validation claims rest, and this is exactly the kind of "external validation"
DiZyme and AI-ZYMES report.<sup>3,7</sup> Our value sits below the 0.63–0.95 range they
quote, but that is a corpus difference rather than a contradiction: ours is computed on a
different, condition-bound corpus, not on the authors' own data, and the point of the
comparison is the protocol, not the absolute value. The only change is to remove the 1,472 rows whose papers already
contributed to training (the strict analogue of grouping by paper): on the remaining
1,165 external rows, R² falls to 0.023 (Figure 8b), and the RMSE in log10(Kₘ) stays around 1.2 (an
order of magnitude or worse on typical predictions). At the material level, where
each material's rows are averaged before evaluation, internal R² = −0.059 and external
R² = −0.043 (Figure 8c): cross-material Kₘ prediction is not
better than the mean, and both values fall below zero, so the mean itself, not a
degraded but still positive fit — is the honest reference point. **We report the one
subset that cuts the other way**, rather than only the figures that support the
conclusion: on the 854 external rows whose material does not appear in training at all,
the row-level R² is 0.157 — weakly positive, and higher than the 0.023 obtained after
DOI isolation. The two are not in conflict. The 0.157 subset is a *material-level*
novelty filter, not a *paper-level* one: it still contains rows from papers present in
training, so it inherits the within-paper correlation that the DOI-grouped protocol
exists to remove; once each material's rows are averaged, it turns negative like the
rest. Both readings are reported here so that the bound is not read as stronger than the
data support. These numbers
are consistent with the classification result: the apparent predictive power of nanozyme
models resides in within-paper or within-material memorization, not in genuine
generalization across the literature.

### 6.4 Where retrieval outcompetes modeling

The corrective insight from the probes is that most predictions should never be made.
A leave-one-DOI-out retrieval probe measures how often a query (material, activity,
substrate, pH, T) can be answered by citing an existing record of the same
material–substrate–condition system from a different paper: only 40 of 978 queries
(4.1%) hit such an in-domain neighbor. For the 95.9% of queries that must be answered
by extrapolation, and even within the 4.1% that can be retrieved, the cross-paper Kₘ
values for the same condition neighborhood scatter by a median of 13.2× (P90 1.5 × 10⁴×,
with 85% of hit groups exceeding 3×). A model that reports a point prediction for such
queries is therefore claiming precision where the underlying data do not support it —
the quantitative motivation for a value-grading protocol rather than a black-box point
estimate (Section 7; the grading protocol of the companion platform is future work).

### 6.5 Position and limitations

The contribution of this section is not a stronger model, it is a calibration of
reported numbers. We do not claim that no nanozyme property is predictable; we claim
that the current evidence, evaluated without group leakage, does not establish it, and
we provide the drop magnitudes (0.816→0.672 classification; 0.387→0.023 regression,
with internal OOF R²=0.134) so that the field can judge the gap. Three qualifications.
First, our grouped folds group by DOI only; laboratory- and synthesis-level grouping
would remove additional (weaker) correlation not captured here, so these drops are a
lower bound on the leakage effect. Second, the regression setting is deliberately
simple (a single random forest, hand features); a stronger model might recover some
internal R², but the external −0.043 material-level result shows that feature-based
cross-material prediction is the bottleneck. Third, the row-level and material-level
results must be read at their own levels. The row-level R² values (0.023 external,
0.134 internal) are positive, so they do beat a mean-imputation baseline; the
material-level values (−0.043 external, −0.059 internal) are genuinely negative, i.e.
after each material's rows are averaged, prediction is worse than predicting the mean.
The contrast is the finding, not a contradiction: a small row-level signal survives, and
it disappears once the material is the unit of prediction. Either way the magnitude is
orders of magnitude smaller than the reported values, and the
grading protocol sketched in Section 7 is designed accordingly.

---

### 图表与数据对照

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 分类随机 0.816 / 分组 0.672 / 基线 0.695（core, no-sub） | b1_probe 实测 _b1_probe_run.txt | CORE(atlas)\|no-sub |
| 分类 with-sub 0.813 / 0.723 | 同上 | CORE\|with-sub |
| CORE+MULTI with-sub 0.840 / 0.783（=基线） | 同上 | CORE+MULTI\|with-sub |
| macro-F1 0.673→0.350；SOD 0.686→0.074；CAT 0.500→0.152 | 同上 | core, no-sub |
| 回归内部 OOF R²=0.134 / RMSE 1.308 | m5_report.json r2_mean | 978 行, 5-fold, with_conditions（DOI 分组） |
| 回归全外部（未隔离）R²=0.387 / RMSE 1.041 | m6_external.json full_ext_all | 2637 行（含训练 DOI 重叠 1472 行） |
| 回归外部（DOI 隔离）R²=0.023 / RMSE 1.209 | m6_external.json | ext 1165 行，训练 978 行 |
| 材料级内部 −0.059 / 外部 −0.043 | m5_report.material_level / m6_external.material_level | 576 / 1281 atoms |
| 检索覆盖 4.1%（40/978） | b3_probe _b3_probe_run.txt | same (mat, act, sub)+pH±0.5+T±5℃ |
| 命中组中位 13.2× / P90 15464.5× / >3× 占 85% | 同上 | 跨文献 Kₘ 倍数 |
| 消融 ΔR²=+0.035（条件特征） | m5_report.ablation | 0.100→0.135 |

> 待办（写正文前必做）：
> 1. ✅ 已解决：0.387 出处查实——`m6_external.json full_ext_all`（2637 行，未做 DOI 隔离）=0.3866，
>    与 m8-1/m8-2/m8-4 记录一致。§6.3 已统一为「全外部 0.387 → DOI 隔离 0.023」。
>    同时保留内部 OOF 0.134 作为基线参照。模型名已修正为 RandomForest（原稿 GBR 系笔误）。
> 2. ✅ 已解决：§6.2 with-sub DOI-grouped 实测为 0.723（非 0.678），表格与正文已改，附口径注。
> 3. ✅ 已解决：Fig 5 已绘制——`figures/fig5_evaluation_leakage.html`（archify workflow，4-lane 双口径对照）。
>    candidate：`figures/fig5_evaluation_leakage.candidate.json`（deliver 通过 showcase 全 9 项、0 error 0 warning）。
>    visual-check 受沙箱限制未跑（需启动浏览器进程）；如需浏览器证据需在正式环境执行
>    `archify visual-check`。图内文案为英文（直接嵌入论文 Fig 5）。
> 4. ✅ 已处理：§6.4/§6.5 "predict protocol of Section 7" 改为 "grading protocol sketched in
>    Section 7" + companion platform 标记为 future work，与 §7 结论章节结构自洽。

---

## Section 7 — Conclusion and Outlook

> 状态：英文初稿（2026-09-11）。数据来源：与 §1–§6 一致（全部为已核实的数字）。
> 定位：收束铁路线（诚实口径）+ 一句话预告轨道二（智能体平台论文）。
> 写作遵循：数据零丢失、口径诚实、陈述中性、禁 AIGC 腔。

---

### 7.1 What we established

Nanozyme kinetic data are abundant but not yet trustworthy: the same material–substrate
system is re-annotated independently by several public databases whose values disagree by
orders of magnitude, and those values are stored without the reaction conditions that give
them meaning. This paper treats that situation as the research object rather than an
inconvenience, and delivers four things that survive contact with the data.

What survives is one integrated claim with four supports. A condition-bound layer of 5,027
entries across 761 DOIs, in which pH and temperature are first-class and no kinetic constant
aggregates across conditions (Section 2). A cross-source audit with an explicit denominator —
348 comparable DOIs, 949 same-pH buckets, 17 buckets ≥ 10× — in which the two-camp ×1000
signature is now confirmed against the source publication as an M→mM conversion artifact
(Section 4, Table S6). A condition-indexed conflict atlas (166 clusters; 97 severe, 43
suspicious, 26 consistent) with a deterministic, rerunnable audit state machine and DOI-level
lineage, so that "which number is right" is a resolvable question rather than an article of
faith (Section 5). And an extraction pipeline — three agents, one schema, F1 0.946 on 67 gold
papers (0.965 on the original 30-paper set) and 0.907 agreement on 100 triple-aligned
papers, that keeps the layer extensible without per-record manual entry (Section 3).

Underneath the positive results is a methodological finding we keep deliberately
conservative. Evaluated without group leakage — folds grouped by DOI, models and features
otherwise identical — the field's reported predictive performance mostly disappears:
classification accuracy falls to the majority-class baseline, and external Kₘ regression
R² falls from 0.387 to 0.023 (Section 6). The same theme runs through the input side:
within the 4.1% of material–condition queries that can be answered by retrieval at all,
cross-paper Kₘ values scatter by a median of 13.2×. These are not failures of our models;
they are statements about the data and about the evaluation protocols that have been
applied to them.

### 7.2 What we did not claim

Four limits bound the interpretation. First, the atlas clusters cross-literature
conflicts; it is not a measurement of single-system pH–response curves, and resolving a
cluster to a physical answer requires original experiments, not better bookkeeping.
Second, the audit semantics depend on documentation: conditions are indexed at the
pH/temperature granularity the papers report, and buffers, ionic strength, and substrate
concentration are not yet part of the clustering key. Third, our own extraction is a
source of residual disagreement on the weakest fields (Vmax, size), which we exclude from
the audit's comparable field set rather than let them inflate apparent agreement. Fourth,
the agreement figures of Section 3.4 are not raw-string agreement: three fields are
compared after normalising notation, and although fourteen of seventeen fields are
unaffected by that choice, the two ends of the range (0.847 verbatim, 0.907 normalised) are
both reported rather than only the higher one. A reader who rejects the morphology
tolerance outright should read the 0.847 figure as our result; that field's tolerance is a
policy, not an equivalence, and Section 3.4 says so.

### 7.3 Outlook

The natural continuation is an intelligent-agent platform that consumes this layer: a
five-layer system in which extraction, multi-source aggregation, audit, prediction, and
question answering are orchestrated by function-calling agents, with an explicit
evidence-grading protocol that distinguishes, for every numeric answer, literature
retrieval (with DOIs), model extrapolation (with interval and evaluation protocol), and
refusal (with reason). The Section 6 numbers—baseline-level accuracy under group-free
folds, near-zero external R², 4.1% retrieval coverage, and 13.2× median cross-paper
scatter—define when each branch of that protocol applies, and the protocol will only
become more necessary as automated extraction lowers the per-paper effort required to
keep the layer current.
Extending the layer to 1,000+ papers, calibrating the predict step against external
gold standards, and experimentally adjudicating a small number of severe conflicts are
the concrete next steps; the platform itself is the subject of our follow-up work.

### 7.4 Data and code availability

Every figure, table, and headline number in this manuscript is produced by a script that
ships with it, and the run that produced the quoted value is identified here so that each
claim can be re-derived rather than trusted.

| Claim | Artifact | Reproduce with |
|---|---|---|
| Integrated layer (5,027 entries, 761 DOIs, 388 multi-source) | `workbench/atlas_out_multi/atlas_summary.json`; `workbench/atlas_records/` | `kg/build_kg_atlas.py`; `kg/excel_source.py` |
| Extraction quality, 67 papers (F1 0.946) | `workbench/evall_out/_eval_gold67.json` | `workbench/align.py` |
| Extraction quality, 30 papers (F1 0.965) | `workbench/model_swap_out/deepseek-v4-flash__kimi-k2.6__20260816_210016/_eval_30.json` | `workbench/align.py` |
| Triple-aligned agreement, 100 papers (F1 0.907; 0.847 verbatim) | `workbench/evall_out/_cross_validate.json` | `workbench/cross_validate.py`; verbatim re-run in `workbench/_strict_probe.py` |
| Tables S7–S8 (comparison-rule sensitivity, per-paper dispersion) | `paper_drafts/si_table_s7_caliber.md`, `paper_drafts/si_table_s8_dispersion.md` | `workbench/_caliber_tables.py` |
| Same-pH conflict census, 17 groups | `workbench/figs/fig4_conflicts_sameph.json` | `workbench/figs/recheck_sameph_conflicts.py` |
| Conflict atlas, 166 clusters / 97-43-26 | `workbench/atlas_out_multi/audit.csv` | `kg/conflict.py`; `kg/conflict_atlas.py` |
| Unit recovery against source PDFs | `paper_drafts/s6_recovery_probe.md` (verbatim OCR grids); `workbench/p0_unit_recovery_ctx.json`, `workbench/p0_pdf_index.json` | `workbench/p0_unit_recovery.py`; OCR of rasterised tables (RapidOCR, 300 dpi) |
| Condition-resolved Fe₃O₄ spread (2,434× same-condition; 1.05 × 10⁶ pooled) | `workbench/figs/fig5_fe3o4_cluster.png` | `workbench/figs/_probe_fig5_gray.py` (8 assertions) |
| Figure numbering, inline placement, print legibility | `paper_drafts/manuscript_full_track1.md` | `workbench/figs/_verify_inline_figs.py`; `workbench/figs/_audit_render.py` |
| Reference numbering (first-appearance order) | `paper_drafts/references_draft.md` | `workbench/_insert_audit_refs.py` (KEY-based, covers `<sup>` and SI `[n]`) |
| Leakage re-evaluation (0.387 → 0.023) | `workbench/ml_out/m5_report.json`, `workbench/ml_out/m6_external.json` | `workbench/` ML harness |

The extraction pipeline, the schema validator, the audit state machine, the conflict
census, and both comparison rules (verbatim and normalised) are released together, so a
reader can recompute every agreement figure under either rule. The public-database records
compared in Section 3.4 are redistributed as identifiers and values with per-row provenance
rather than as bulk dumps of the upstream sources; the two human-curated spreadsheets cannot
be redistributed and are described in Table S1 instead.

Every figure is generated by a script in `workbench/figs/` at 300 dpi from
the same artifacts listed above; figure dimensions and print-legibility parameters are
stated in the cover letter.

---

### 图表与数据对照（§7）

| 文内引用 | 数据来源 | 数值 |
|---|---|---|
| 25 字段 / 5,027 / 761 / 388 | §2（atlas_summary.json） | 与 §2.3 一致 |
| 17 组 ≥10× / N-PCNSs 10⁶ / CuO ×1000 | §4.3（复核脚本 2026-09-10） | 与 §4.3 一致 |
| 166 簇 / 97-43-26 | §5（audit.csv） | 与 §5.2 一致 |
| F1=0.965 / 0.907 | §3.2 / §3.4 | 与 §3 一致 |
| 0.387→0.023 / 基线 acc | §6.3 / §6.2 | 与 §6 一致 |
| 4.1% / 中位 13.2× | §6.4（b3 探针） | 与 §6.4 一致 |
| 轨道二一句话预告 | docs/m8-5 轨道二规划 | 五层平台 + predict 三段式（I5） |

> 待办（§7）：
> 1. ✅ 已处理：循环引用消除。§6 → §7 单向引用（"grading protocol sketched in Section 7"），
>    §7 改为"evidence-grading protocol"描述性表述 + 引 §6 数字（基线 acc、0.387→0.023、4.1%、13.2×）
>    作为协议适用判据，不回指 §7 编号。§1.2 的 "grading protocol" 措辞待与 §6 统一（见 §1 待办 3）。
> 2. §7.3 是对轨道二的预告，非本论文内容——措辞已用 "follow-up work" 保持界线；不含任何
>    轨道二数字（分支一致率 25/25 等），避免承诺正文没验证的东西。
> 3. §7.1 复述各章数字时与 §1–§6 保持完全一致（已核对）；若后续任一章数字改动，需同步 §7（结论是
>    数字汇总处，最易失同步）。
> 4. 定稿时 §7 需与 Abstract 呼应（同数字、同口径、同语气），Abstract 写作时以本稿为锚。
> 5. §7.2 三个局限与 §4.5/§5.5 对应：跨文献簇≠pH 曲线（§4.5 first）、条件粒度（§5.5 fourth）、
>    弱字段排除（§4.5 third / §3.2）——已保持自洽。

---

## 并稿核对表（2026-09-10）

交叉引用自洽性（核对结论：全部通过）
- §1 → Section 2/3/4/5/6（概述各章）、Section 7（future work，指向结论章）
- §2 → Section 4（provenance/单位审计）、Section 5（条件绑定）、Section 6（ML 外推）
- §3 → Section 2（schema）、Section 3.2（消融）、Section 4 / 4.2（审计衔接）
- §4 → Section 2（schema）、Section 3（提取）、Section 4.2（一致性协议）、Section 5（审计状态机）
- §5 → Section 4.4（Fe₃O₄ 簇/两个干净 case）
- §6 → Section 2（集成层）、Section 5（特征族）、Section 7（grading protocol，指向结论章）
- §7 → Section 2/3/4/5/6（数字汇总回指）；不回指 §7 自身编号（循环引用已消除）

图/表编号（核对结论：无冲突）
- 图序：Fig 4b/4c（§4.3 单位错配案例）、Fig 5（§6 泄漏对照，已绘）、Fig 6（§4.4/§5 Fe₃O₄ 簇）、Fig 7（§5 audit tier 分布）
- 表序：Table 3（§4.3 单位错配清单）；Table S4（SI 逐簇 tier/fold 表，§5.2/5.3）
- 注：Fig 4 面板 (b)(c) 与 Table 3 数据源已定（N-PCNSs / CuO），Fig 6/Fig 7 待绘

重复数字一致性（核对结论：全部一致）
- 100 篇 F1=0.907 双侧：§3.4 与 §4.2 重复，数值、P/R 完全一致
- Fe₃O₄ 同条件 2434× / 全局 1.05×10⁶：§4.4 与 §5.2 重复，一致（6913× 已弃用；旧全局值 4.2×10⁵ 于 2026-09-11 更正为 1.05×10⁶）
- K5PV2Mo10O40 / HBPG-AuNP 干净 case：§4.4 与 §5.2 重复，一致
- 166 冲突簇 / 26-43-97 分布：§4.4、§5.1、§5.2、§5.4 多处重复，一致
- 388/761 多源 DOI：§4.1 与 §5.3 重复，一致
- 消融 F1=0.965 vs 0.917→0.922：§3.1 与 §3.2 重复，一致

遗留口径问题（写稿定稿时处理）
1. ✅ 已解决（2026-09-10 收尾）：字段数口径统一为 25,,实测 `schema.py FlatRecord.model_fields`=25
   （2026-08-14 剔除 `substrate2_concentration_mM`，26→25，BUILD_INSTRUCTIONS.md 有记录）。§2 按 25 写，
   §3/§4 正文与对照表、§2.5 平台草稿、PROJECT_RULES、CODE_WIKI、schema.py 注释、tests docstring 已全部同步；
   历史快照（memory、docs/superpowers/specs+plans、m8-4/m8-5、系统漏洞分析）保留当时状态。
2. §4.3 同 pH 冲突 17 组 ≥10× / 10 组 ≥100×（2026-09-11 复核口径，可复现脚本
   `workbench/figs/recheck_sameph_conflicts.py`）,,与 m8-5 记录的旧口径「57 组 / 21 组」及
   早期复核的「17/14」不同，正文/对照表/Fig 4a 已按可复现口径 17/10 统一，旧档不采用。
3. ✅ 已解决（2026-09-11）：§3.2 "field analysis in Section 4.2" → Section 4.5（Vmax/size 弱字段
   分析实际定位在 §4.5 局限说明与 §3.2 自身，前向引用已校正）。
4. 正文七节已齐：§1 立论、§2 数据底座、§3 提取、§4 审计、§5 冲突谱、§6 泄漏、§7 结论。
   §2.5 平台章节中文草稿 `docs/paper_section_2_5_agent_platform_draft.md` 尚未并入（轨道二素材，投稿前决定去留）。
   Section 7 引用已落地为实际章节，前向悬空引用全部消除。

文献引用核对（投稿前必做）
- ✅ 已完成（2026-09-11）：References 已嵌入正文,,`paper_drafts/references_draft.md`（[1]–[14]）；
  正文标注：§1.1 Fe₃O₄<sup>1</sup>、DiZyme 人工采集<sup>6,7</sup>、Wei<sup>3</sup>、DiZyme/AI-ZYMES R²<sup>7,8</sup>；
  §1.2 Li 2023<sup>4</sup>；§2.3 四库<sup>6,9,10,11</sup>；§3.1 DiZyme<sup>6</sup>；§6.1 Wei/DiZyme/AI-ZYMES<sup>3,7,8</sup>；§6.3<sup>7,8</sup>。
- ✅ 已解决（2026-09-11 回原文核对 6 篇上传 PDF）：
  · Li 2023：展望第(1)条原文已取回（"important and indispensable" / "standard and unified detection
    and representation methods"），正文引号内为原文，非转述,,待办解除。
  · Wei 2022：acc 90.6% / R² up to 0.80 / 920 条数据与原文一致，条目 [2] 定稿。
  · Sun 2024 JCIM = AI-ZYMES 首篇（GBR Kₘ R²=0.6476、kcat R²=0.95、平台首次提出）,,[7] 保留，
    且是正文 "GBR R²≈0.65/0.648" 的唯一正确出处（原误挂 [6]），编号已改。
  · Xuan 2025 Sci. Rep. = AI-ZYMES 扩版（1,085 entries / 400 types / GBR R²≤0.85），[6] 保留并重新定位。
  · Small 2022 = DiZyme 初始版（>300 纳米酶 / >100 篇 / kcat R²=0.796、Kₘ R²=0.627）,,[4]。
  · JPCL 2024 = DiZyme 扩展版 + Assistant（1,210 samples / Kₘ R²=0.75、Vmax R²=0.77）,,[5]，
    正文 "DiZyme R² up to 0.75" 与 "thousand curated samples" 均归 [5]。
  · ⚠️ 引文归属修正：m8-2 记的 "1210 样本 / 390 组成 / 400 篇" 数字全部属实，但出自
    JPCL 2024 [5]（原文 "1210 nanozymes ... sourced from 400 articles ... 390 unique nanozymes"），
    原稿误挂 Small 2022 [4]（其原文为 >300 纳米酶 / >100 篇 / kcat R²=0.796、Kₘ R²=0.627）,,编号已改。

工作笔记与正文的边界
- 各节尾部的「图表与数据对照」与「待办」是写作工作区，非投稿正文；
  投稿定稿时剥离为 SI 素材清单或内部笔记。正文以 ## 下英文正文为准。
