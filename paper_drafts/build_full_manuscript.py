# -*- coding: utf-8 -*-
"""组装 Track 1 完整论文初稿 manuscript_full_track1.md。

输入：
- manuscript_sections3_6_merged.md（Abstract + §1–§7，含工作笔记）
- references_draft.md（[1]–[14]）
- si_tables_track1.md（SI 表 T1–T3）
输出：
- manuscript_full_track1.md：Title + Abstract + Keywords + §1–§7 正文（剥离工作笔记，
  插入 Table 1/2 表题）+ Figure 1–8 内联到各自首次引用段落之后 + References + 支持信息。
  图片编号按首现顺序（2026-09-11 起 Fig 5 = Fe3O4 簇图，Fig 6 = (pH,T) 图集）。
运行：D:/conda/python.exe paper_drafts/build_full_manuscript.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "manuscript_sections3_6_merged.md"
REFS = HERE / "references_draft.md"
SI = HERE / "si_tables_track1.md"
S6 = HERE / "si_table_s6_unit_recovery.md"
S7 = HERE / "si_table_s7_caliber.md"
S8 = HERE / "si_table_s8_dispersion.md"
OUT = HERE / "manuscript_full_track1.md"

CN = re.compile(r"[\u4e00-\u9fff]")

# 定稿标题（2026-09-11：占位标题行已从正文移除，避免英文工作说明进入投稿稿）
# 2026-09-12 换题（N9）：原标题 "A Condition-Bound Knowledge Base for Nanozyme Kinetics:
# Cross-Source Audit, LLM-Based Extraction, and a Leakage-Aware Re-evaluation" 有两个问题——
# (i) "Knowledge Base" 暗示构建了 KG/查询系统，而正文 §1.3 scope note 明确否认建 KG，
#     标题与正文互相打架；(ii) 三件事并列 + 19 词偏长。新题把主线收成"跨源审计"，
#     "条件绑定"降为修饰语，提取与漏读评估降为其手段。
# 旧题保留于 paper_drafts/_archive/round13_20260912/CHANGES.md 备查。
TITLE = ("# Cross-Source Audit of Condition-Bound Nanozyme Kinetics: "
         "Automated Extraction and a Leakage-Aware Re-evaluation")

SECTION_TITLES = {
    1: "1. Introduction",
    2: "2. A Condition-Bound Flat Schema as the Data Foundation",
    3: "3. LLM-Based Automated Extraction of Condition-Bound Nanozyme Records",
    4: "4. Cross-Source Audit: Reconciling Nanozyme Kinetic Data across Public Databases",
    5: "5. A Condition-Indexed Conflict Atlas with a Live Audit State Machine",
    6: "6. Quantifying Evaluation Leakage in Nanozyme Machine Learning",
    7: "7. Conclusion and Outlook",
}

TABLE_CAPTIONS = {
    "| Text backbone |": ("**Table 1.** Text-backbone comparison under the identical\n"
                         "evaluation protocol (18-field comparable set; vision fixed to\n"
                         "Kimi-K2.6)."),
    "| Data / features |": ("**Table 2.** Catalytic-type classification accuracy under\n"
                           "random and DOI-grouped 5-fold splits (majority-class baseline\n"
                           "shown for reference)."),
}

# 表注（2026-09-11 新增）。两张表此前只有表题、没有表注，而表里的每一列都是
# 一个未定义口径：18 字段是哪 18 个、kinetic bundle 怎么算、majority baseline
# 为什么第三行从 0.695 变成 0.783、两次 flash run 为什么不是同一个。审稿人只要
# 追问其中任意一条，正文里都没有答案。表注把口径就地锁死，并显式解释
# 49.2% / 53.8% / 52.4% 三个 bundle 数字为何并存。
TABLE_NOTES = {
    "| Text backbone |": (
        "*Footnotes.* **a** The 18-field comparable set is the 17-field gold field set "
        "used throughout Section 3 plus `substrate2_concentration_mM`; the full schema "
        "carries 25 fields. **b** F1, precision and recall are the record-level values "
        "reported by each backbone's own evaluation (DeepSeek-V4-Flash run "
        "`20260812_124035`; Qwen3-235B-A22B run `20260810_103914`), on the same 30-paper "
        "fixed set with the same vision backbone (Kimi-K2.6). **c** 'Kinetic bundle' is "
        "the fraction of gold kinetic rows whose Kₘ and Vmax share one condition tuple "
        "(`identity_and_bundle_v1`). It is caliber-dependent, and the values quoted in "
        "this table are on the 18-field caliber: 59/120 = 49.2% (DeepSeek-V4-Flash) and "
        "19/120 = 15.8% (Qwen3-235B-A22B). On the 17-field caliber the same backbone "
        "reaches 53.8% over the same 30 papers (run `20260816_210016`, diagnostics "
        "0.5378) and 52.4% (98/187) over the 67-paper gold set quoted in Section 3.2. "
        "The three values differ only in field caliber and paper set, not in the "
        "underlying match rule. **d** 'Unknown' is the share of candidate rows the schema "
        "could not resolve: 17/121 = 14.1% and 17/92 = 18.5%. **e** A DeepSeek-V4-Pro "
        "variant was evaluated on a five-paper smoke set (F1 0.950, run `20260809_211246`) "
        "and excluded on cost grounds; it is not part of the formal comparison. "
        "**f** The production text backbone is the later 17-field re-run "
        "`20260816_210016`. Because `substrate2_concentration_mM` was dropped from the "
        "schema on 2026-08-16 and is absent from those records, the 18-field comparison "
        "is necessarily reported from the earlier-vintage run."),
    "| Data / features |": (
        "*Footnotes.* **a** 'Core' (n = 1,056) is the atlas subset with a resolvable "
        "catalytic type (POD 734, OXD 223, CAT 61, SOD 38); 'core + databases' "
        "(n = 3,002) adds the public-database rows (POD 2,351, OXD 438, CAT 126, SOD 41, "
        "OTHER 46). **b** The DOI-grouped split uses GroupKFold on the DOI, so no paper "
        "contributes to both training and test folds. **c** The majority-class baseline is "
        "recomputed against each row's own class balance: 734/1,056 = 0.695 for the core "
        "rows, rising to 2,351/3,002 = 0.783 once the database rows are added. The added "
        "rows are more POD-dominated still, so the third row's grouped accuracy (0.783) "
        "merely matches its own baseline and carries no leakage-independent signal. "
        "**d** 'With substrate' adds the substrate identity as a feature "
        "(`norm_substrate`). Source: `workbench/ml_out/_b1_probe_run.txt`."),
}

FIGURES = [
    ("fig1_overview.png",
     "**Figure 1.** Overview of the condition-bound data layer and the three analyses "
     "built on it. Five provenance sources are mapped into a 25-field condition-bound "
     "schema (5,027 entries, 761 DOIs, 388 multi-source), which supports (i) LLM-based "
     "extraction (Section 3), (ii) the cross-source audit and the 166-cluster conflict "
     "atlas (Sections 4–5), and (iii) the leakage re-evaluation (Section 6). The "
     "evidence-grading answering protocol (Section 7) is future work."),
    ("fig2_scale.png",
     "**Figure 2.** Scale of the integrated layer: condition-bound entries per "
     "provenance group (5,027 total). Of the 761 DOIs in the layer, 388 are covered "
     "by more than one source, and that overlap is what makes cross-source auditing "
     "possible (Figure 1)."),
    ("fig3_extract_eval.png",
     "**Figure 3.** Three-agent extraction pipeline and evaluation. (a) A PDF with its "
     "supplementary information is processed by text, image, and metadata agents; a "
     "deterministic integrator merges and post-filters their outputs into condition-bound "
     "25-field FlatRecords. (b) Field-level F1 on the 67 gold-annotated papers for the "
     "production combination (DeepSeek-V4-Flash text, Kimi-K2.6 vision, DeepSeek-V4-Flash "
     "integrator); particle size (0.830) is highlighted in vermillion as the weakest field. "
     "(c) Text-backbone comparison on the 18-field comparable set, 30-paper fixed set "
     "(F1 / precision / recall). All panels use the Okabe–Ito color-blind-safe palette."),
    ("fig4_units.png",
     "**Figure 4.** Systematic unit-scale conflicts across sources. (a) The 17 same-pH "
     "conflict groups ranked by cross-source Kₘ fold (vermillion: ≥100×; dashed and dotted "
     "lines mark the 10× and 100× thresholds). (b) N-PCNSs at pH 7.0 with H₂O₂: a 10⁶-fold "
     "disagreement between sources. (c) CuO at pH 4.65 with H₂O₂: a two-camp ×1000 "
     "pattern in which two sources agree against two others by exactly three orders of "
     "magnitude. In (b) and (c) bars are colored by camp rather than by source "
     "(blue: lower-Kₘ camp; hatched orange: higher-Kₘ camp), so the two camps remain "
     "distinguishable under red–green color deficiency."),
    ("fig5_fe3o4_cluster.png",
     "**Figure 5.** Condition-resolved Kₘ for Fe₃O₄ · peroxidase · H₂O₂ (log scale). Vermillion: "
     "the same-condition cluster at pH 4.0 (five papers, Kₘ 0.076–185 mM, a 2,434-fold "
     "spread). Gray: the same material–activity–substrate system at other pH windows; "
     "pooling all 130 condition-resolved Kₘ measurements from the 34 papers without a "
     "condition axis inflates the apparent spread to 1.05 × 10⁶-fold (0.0028–2,951 mM, "
     "all pH windows)."),
    ("fig6_atlas.png",
     "**Figure 6.** The 166-cluster conflict atlas projected onto the (pH, T) plane. "
     "Color encodes the audit tier in an ordered, color-blind-safe triple (blue: "
     "consistent, 26; orange: suspicious, 43; vermillion: severe, 97); marker shape "
     "encodes the kinetic metric (circle: Kₘ, square: Vmax, triangle: kcat); marker size "
     "grows with the cross-source fold."),
    ("fig7_tiers.png",
     "**Figure 7.** Audit tiers of the 166 conflict clusters. (a) Severity distribution: "
     "26 consistent, 43 suspicious, 97 severe. (b) Clusters by kinetic metric: 91 Kₘ, "
     "64 Vmax, 11 kcat."),
    ("fig8_leakage.png",
     "**Figure 8.** Leakage re-evaluation under DOI-grouped folds. (a) Catalytic-type "
     "accuracy on the core set (n = 1,056): random 5-fold 0.816 vs DOI-grouped 0.672, "
     "against the 0.695 majority-class baseline, which the grouped result does not clear. "
     "Per-class macro-F1 — a separate metric, not plotted on the accuracy axis — falls "
     "from 0.673 to 0.350. (b) Row-level Kₘ regression: external evaluation under the "
     "random protocol 0.387, internal 5-fold with DOI-grouped folds 0.134, external "
     "evaluation after removing training-paper rows 0.023. (c) Material-level Kₘ "
     "regression, each material's rows averaged before evaluation: internal −0.059 and "
     "external −0.043. Both fall below the zero reference line, i.e. cross-material "
     "prediction is worse than predicting the mean. The row-level panel and the "
     "material-level panel share no y-axis, because the material-level values are "
     "negative and would be invisible on an axis that starts at zero."),
]


def strip_worknotes(lines: list[str]) -> list[str]:
    """剥离以 > 开头的连续注释块（状态头/待办/口径注）。"""
    out, in_block = [], False
    for ln in lines:
        if ln.startswith(">"):
            in_block = True
            continue
        if in_block and not ln.startswith(">"):
            in_block = False
        out.append(ln)
    return out


def extract_section(lines: list[str], start_idx: int, end_idx: int) -> list[str]:
    """提取一节正文：去状态块、去「图表与数据对照」及之后内容。"""
    body = lines[start_idx:end_idx]
    # 去「图表与数据对照」小节（每节最后一个 ###，直到节尾）
    for i, ln in enumerate(body):
        if ln.startswith("### 图表与数据对照") or ln.startswith("## 并稿核对表"):
            body = body[:i]
            break
    body = strip_worknotes(body)
    # 去多余空行
    out, blank = [], 0
    for ln in body:
        if ln.strip() == "":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    return out


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    ref_lines = REFS.read_text(encoding="utf-8").splitlines()
    si_lines = SI.read_text(encoding="utf-8").splitlines()

    # ---- 定位各节 ----
    marks = {}
    for i, ln in enumerate(lines):
        m = re.match(r"^## Section (\d) —", ln)
        if m:
            marks[int(m.group(1))] = i
        if ln.startswith("## 并稿核对表"):
            end_all = i
    order = sorted(marks)
    sections = {}
    for k_i, n in enumerate(order):
        s = marks[n]
        e = marks[order[k_i + 1]] if k_i + 1 < len(order) else end_all
        body = extract_section(lines, s, e)
        # 替换节标题（首个 ## 行）
        for j, ln in enumerate(body):
            if ln.startswith("## Section"):
                body[j] = f"## {SECTION_TITLES[n]}"
                break
        sections[n] = body

    # ---- Abstract ----
    abs_start = next(i for i, ln in enumerate(lines) if ln.startswith("## Abstract"))
    abs_body = extract_section(lines, abs_start + 1, marks[1])
    abs_text = "\n".join(abs_body).strip()

    # ---- References：解析 [n] 条目 ----
    refs_out = []
    cur = None
    for ln in ref_lines:
        m = re.match(r"^\*\*\[(\d+)\]", ln)
        if m:
            if cur:
                refs_out.append(cur)
            cur = [f"{m.group(1)}. "]
            continue
        if cur is not None:
            if ln.strip() == "" or ln.startswith(">") or ln.startswith("##"):
                continue
            if CN.search(ln):        # 跳过中文说明行
                continue
            if ln.startswith(("|", "#", "---")):
                if cur:
                    refs_out.append(cur)
                    cur = None
                continue
            cur.append(ln.rstrip())
    if cur:
        refs_out.append(cur)
    ref_items = [" ".join(r).strip() for r in refs_out]

    # ---- SI 附录 ----
    si_body = [ln for ln in si_lines]
    # SI 表内中文工作行剥离：保留表与英文标题
    si_clean = strip_worknotes(si_body)

    # ---- 表题 + 表注插入 ----
    for n in (3, 6):
        body = sections[n]
        for i, ln in enumerate(body):
            key = next((k for k in TABLE_CAPTIONS if ln.startswith(k)), None)
            if key:
                # 表题插在表体之前；表注插在最后一个表体行之后
                j = i
                while j < len(body) and body[j].lstrip().startswith("|"):
                    j += 1
                ins = [TABLE_CAPTIONS[key], ""] + body[i:j]
                if key in TABLE_NOTES:
                    ins += ["", TABLE_NOTES[key]]
                sections[n] = body[:i] + ins + body[j:]
                break

    # ---- 组装 ----
    doc = []
    # 2026-09-11：原标题行/作者占位行是**英文**，绕过 CJK 剥离逻辑，会原样进入投稿稿。
    # 改为脚本注释，不写入 doc。定稿时把 TITLE 常量替换为真实标题，并在 doc 中
    # 追加作者与单位块（AUTHORS_BLOCK），格式按目标期刊模板。
    # TITLE = "..."            # 定稿标题（见 paper_drafts/ 选题记录）
    # AUTHORS_BLOCK = [...]    # 定稿作者/单位/通讯/基金
    doc.append(TITLE)
    doc.append("")
    doc.append("## Abstract")
    doc.append("")
    doc.append(abs_text)
    doc.append("")
    doc.append("**Keywords:** nanozymes; enzyme kinetics; data integration; large "
               "language models; information extraction; data leakage; database "
               "curation")
    doc.append("")
    for n in order:
        doc.extend(sections[n])
        doc.append("")

    # ---- Figures: 内联插入到首次引用段落之后（编号按首现顺序）----
    anchors = []
    for num, (fname, cap) in enumerate(FIGURES, start=1):
        pat = re.compile(rf"Figure {num}(?![0-9])")
        idx = next((i for i, ln in enumerate(doc) if pat.search(ln)), None)
        if idx is None:
            raise SystemExit(f"[figures] Figure {num} has no in-text citation")
        end = idx
        while end + 1 < len(doc) and doc[end + 1].strip() != "":
            end += 1                       # 走到该段落末尾
        anchors.append((end + 1, num, fname, cap))

    for pos, num, fname, cap in sorted(anchors, reverse=True):
        doc[pos:pos] = ["", f"![Figure {num}](../workbench/figs/{fname})", "", cap]

    print("[figures] inline anchors: "
          + ", ".join(f"Fig {n}@{p}" for p, n, _, _ in sorted(anchors, key=lambda x: x[1])))

    # ---- References ----
    doc.append("## References")
    doc.append("")
    for r in ref_items:
        doc.append(r)
        doc.append("")

    # ---- SI ----
    # 2026-09-12 round 14：清单与 SI 正文的编号体系统一为 S1–S9，并把此前"只给路径、
    # 未交付"的 S4（166 簇审计台账）与 S5（57 对普查）实体化为表，另补 S9（图谱稳健性）。
    doc.append("## Supporting Information")
    doc.append("")
    doc.append("The following supporting files accompany this manuscript:")
    doc.append("")
    doc.append("- **Table S1.** The 25-field FlatRecord schema, the per-source field mapping, "
               "and the scale of the five provenance groups, including per-source DOI coverage "
               "and unit-uncertainty counts.")
    doc.append("- **Table S2.** Comparison with prior nanozyme ML works.")
    doc.append("- **Table S3.** Same-pH cross-source Kₘ conflicts, 17 groups ≥10×.")
    doc.append("- **Table S4.** Full audit register of the 166 conflict clusters: material, "
               "activity, substrate, pH, temperature, metric, tier, cross-source fold, suspected "
               "cause, and the per-source values behind every cluster. Records from the one "
               "source that publishes no DOIs are marked.")
    doc.append("- **Table S5.** Cross-source conflict census at the material–substrate "
               "level, without condition control (57 pairs spanning 2.08× to 1.0 × 10⁶×; "
               "39 pairs ≥5×, 28 ≥10×, 14 ≥100×). Section 4.3 "
               "reports the stricter same-pH census instead (17 of 949 same-pH buckets "
               "above 10×; Table S3, Table S6). The two are related by construction and not "
               "in tension: all 17 same-pH groups appear in the 57, and requiring pH "
               "agreement removes the other 40, which are conflicts between sources that "
               "measured under different conditions.")
    doc.append("- **Table S6.** Unit-recovery worksheet: source-publication verification "
               "of the 17 same-pH conflicts — 4 groups confirmed unit conversions, 3 "
               "directionally supported, 1 confirmed *not* a unit artifact (catalyst/"
               "reporter conflation), 9 undecided.")
    doc.append("- **Table S7.** Comparison-rule sensitivity of the 100-paper agreement: "
               "normalised against verbatim comparison, with per-field matched / "
               "false-positive / missed counts.")
    doc.append("- **Table S8.** Per-paper dispersion of the 100-paper agreement: "
               "distribution and deciles of per-paper macro-F1.")
    doc.append("- **Table S9.** Robustness of the conflict-atlas tier distribution: by "
               "kinetic metric, with the no-DOI clusters removed, and on Kₘ alone.")
    doc.append("")
    doc.append("### SI tables (S1–S9)")
    doc.append("")
    doc.extend(si_clean)
    doc.append("")
    for extra in (HERE / "si_table_s4_audit_register.md",
                  HERE / "si_table_s5_census.md"):
        doc.extend(extra.read_text(encoding="utf-8").splitlines())
        doc.append("")
    doc.extend(S6.read_text(encoding="utf-8").splitlines())
    doc.append("")
    doc.extend(S7.read_text(encoding="utf-8").splitlines())
    doc.append("")
    doc.extend(S8.read_text(encoding="utf-8").splitlines())
    doc.append("")
    doc.extend((HERE / "si_table_s9_atlas_robustness.md").read_text(
        encoding="utf-8").splitlines())
    doc.append("")

    # ---- 引用自检（2026-09-11）----
    # 方括号式引用 [n] 不在 workbench/_renumber_refs.py 的覆盖范围内（该脚本只处理
    # <sup>n</sup>），SI 表内引用曾漏改。这里做越界扫描，防止再次错挂。
    n_refs = len(ref_items)
    bad = [(i, int(m.group(1)), ln.strip()[:90])
           for i, ln in enumerate(doc, start=1)
           for m in re.finditer(r"(?<![\w\[])\[(\d{1,2})\]", ln)
           if not 1 <= int(m.group(1)) <= n_refs]
    if bad:
        print(f"[ref-check] WARNING {len(bad)} out-of-range [n]:")
        for i, n, s in bad[:20]:
            print(f"  line {i}: [{n}] {s}")
    else:
        print(f"[ref-check] bracket citations within 1..{n_refs}")

    OUT.write_text("\n".join(doc), encoding="utf-8")
    n_lines = len(doc)
    print(f"saved -> {OUT} ({n_lines} lines, refs={len(ref_items)})")


if __name__ == "__main__":
    main()
