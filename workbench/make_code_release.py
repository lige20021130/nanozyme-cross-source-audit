# -*- coding: utf-8 -*-
"""打包一份可直接推送的代码/数据发布包（2026-09-12 round 14）。

背景：核查过作者的 GitHub 账号 lige20021130 —— `nanowiki` 仓库为空，其余为本机练习
仓库，**当前不存在承载本工作的公开仓库**。投稿包 Data Availability 因此如实写
"on reasonable request"。本脚本把"复现本工作所需的最小集合"整理成一个独立目录，
清掉 .venv / PDF 语料 / 开题材料等体积大户，使作者可以两步发布：

    cd code_release
    git init && git add -A && git commit -m "Code and derived data for the nanozyme audit paper"
    git remote add origin <你的仓库地址> && git push -u origin main

输出：`code_release/`（含 README.md / LICENSE / .gitignore）
运行：D:/conda/python.exe workbench/make_code_release.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "code_release"

# ---- 需要随包发布的文件/目录（相对 ROOT） ----
DIRS = [
    "kg",                       # 冲突图谱 / 审计状态机 / 源注册
    "workbench/figs",           # 8 张图的生成脚本 + 门控脚本
]
FILES = [
    "schema.py",
    "paper_drafts/build_full_manuscript.py",
    "paper_drafts/build_submission.py",
    "paper_drafts/manuscript_sections3_6_merged.md",
    "paper_drafts/references_draft.md",
    "paper_drafts/si_tables_track1.md",
    "paper_drafts/si_table_s4_audit_register.md",
    "paper_drafts/si_table_s5_census.md",
    "paper_drafts/si_table_s6_unit_recovery.md",
    "paper_drafts/si_table_s7_caliber.md",
    "paper_drafts/si_table_s8_dispersion.md",
    "paper_drafts/si_table_s9_atlas_robustness.md",
    "paper_drafts/EVIDENCE_TRAIL.md",
]

# ---- 顶层分析脚本（workbench/*.py，不含大目录） ----
WORKBENCH_PY = [
    "workbench/align.py",          # 唯一权威评估口径
    "workbench/cross_validate.py",  # 100 篇三方一致
    "workbench/_strict_probe.py",   # 逐字 vs 归一化
    "workbench/_caliber_tables.py",  # Table S7/S8
    "workbench/p0_unit_recovery.py",  # Table S6
    "workbench/_insert_audit_refs.py",  # KEY 基引用重编号
    "workbench/make_code_release.py",
]

# ---- 复现数字所需的小体量派生产物 ----
ARTIFACTS = [
    "workbench/atlas_out_multi/atlas_summary.json",
    "workbench/atlas_out_multi/audit.csv",
    "workbench/atlas_out_multi/cross_source_conflicts.csv",
    "workbench/atlas_out_multi/lineage_matrix.json",
    "workbench/figs/fig4_conflicts_sameph.json",
    "workbench/evall_out/_eval_gold67.json",
    "workbench/evall_out/_eval_30.json",
    "workbench/evall_out/_cross_validate.json",
    "workbench/ml_out/_b1_probe_run.txt",
    "workbench/ml_out/_b3_probe_run.txt",
    "workbench/ml_out/m5_report.json",
    "workbench/ml_out/m6_external.json",
    "workbench/ablation_out/stratified_30/_eval_baseline.json",
    "workbench/ablation_out/stratified_30/_eval_after_fix.json",
    "workbench/model_swap_out/_summary.json",
    "workbench/model_swap_out/deepseek-v4-flash__kimi-k2.6__20260812_124035/_eval_30.json",
    "workbench/model_swap_out/deepseek-v4-flash__kimi-k2.6__20260816_210016/_eval_30.json",
    "workbench/model_swap_out/qwen3-235b-modelscope__kimi-k2.6__20260810_103914/_eval_30.json",
]

GITIGNORE = """__pycache__/
*.pyc
.venv/
venv/
*.pdf
*.tif
*.tiff
.DS_Store
Thumbs.db
submission_JCIM/
"""

README = """# Cross-Source Audit of Condition-Bound Nanozyme Kinetics — code and derived data

Reproducibility package for the manuscript *Cross-Source Audit of Condition-Bound
Nanozyme Kinetics: Automated Extraction and a Leakage-Aware Re-evaluation*.

## What this package supports

| Claim in the paper | Artifact | Entry point |
|---|---|---|
| Integrated layer: 5,027 entries, 761 DOIs, 388 multi-source | `workbench/atlas_out_multi/atlas_summary.json` | `kg/build_kg_atlas.py`, `kg/excel_source.py` |
| Same-pH conflict census: 949 buckets, 40 / 24 / 17 / 10 at 2x / 5x / 10x / 100x | `workbench/figs/fig4_conflicts_sameph.json` | `workbench/figs/recheck_sameph_conflicts.py` |
| 166-cluster conflict atlas: 97 severe / 43 suspicious / 26 consistent | `workbench/atlas_out_multi/audit.csv` | `kg/conflict.py`, `kg/conflict_atlas.py` |
| Table S4 / S5 / S9 (audit register, census, robustness) | `paper_drafts/si_table_s4_audit_register.md` and siblings | `workbench/figs/gen_si_extra_tables.py` |
| Extraction quality: F1 0.946 (67 papers), 0.965 (30 papers) | `workbench/evall_out/_eval_gold67.json` | `workbench/align.py` |
| Triple-aligned agreement: 0.907 normalised, 0.847 verbatim | `workbench/evall_out/_cross_validate.json` | `workbench/cross_validate.py`, `workbench/_strict_probe.py` |
| Leakage re-evaluation: 0.816 -> 0.672 classification; 0.387 -> 0.023 regression | `workbench/ml_out/_b1_probe_run.txt`, `m5_report.json`, `m6_external.json` | `workbench/ml_out/b1_probe.py`, `b3_probe.py` |
| Tables S7 / S8 (comparison-rule sensitivity, per-paper dispersion) | `paper_drafts/si_table_s7_caliber.md`, `si_table_s8_dispersion.md` | `workbench/_caliber_tables.py` |
| Table S6 (unit recovery against the source publications) | `paper_drafts/si_table_s6_unit_recovery.md` | `workbench/p0_unit_recovery.py` |
| Manuscript, Supporting Information, submission build | `paper_drafts/manuscript_sections3_6_merged.md` | `paper_drafts/build_full_manuscript.py` then `build_submission.py` |

`paper_drafts/EVIDENCE_TRAIL.md` maps every headline number in the manuscript to the
artifact that produces it and to the command that recomputes it.

## Not included

* **Full-text PDFs.** The nanozyme literature corpus is not redistributable here.
* **Third-party database dumps.** The records compared in Section 3.4 are carried as
  identifiers and per-row values with provenance (see `audit.csv`) rather than as bulk
  copies of the upstream resources.
* **The two human-curated spreadsheets.** They cannot be redistributed and are described
  in Table S1 of the Supporting Information.
* **LLM API keys and model weights.** The extraction backends are commercial APIs; the
  pipeline calls them, it does not ship them.

## Environment

Python 3.8+ with `numpy`, `pandas`, `matplotlib`, `scikit-learn`, `python-docx`, `Pillow`.
Figures are regenerated by `workbench/figs/figs_v2.py` and `workbench/figs/figs_data.py`
at 300 dpi. The two gates used throughout are
`workbench/figs/_verify_inline_figs.py` (figure numbering, inline placement,
double-column font size) and `workbench/figs/_audit_render.py` (clipping, margins,
effective point size).

## Known limitation

One source (nanozymenet-k) publishes no DOIs; its records enter the layer under stable
internal identifiers (`na-<n>`) and most of them carry a unit-uncertainty flag. DOI
coverage of the layer is therefore about 76%, and 13 of the 166 clusters contain at least
one such record. Section 5.5 of the manuscript quantifies the effect and Table S9 reports
the tier distribution with all 13 removed.

## License

Apache License 2.0 (see `LICENSE`).
"""

LICENSE_HEAD = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright 2026 Chengle Li, Liping Sun

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   The full license text is at http://www.apache.org/licenses/LICENSE-2.0
"""


# 2026-09-12：**版权与授权排除**。workbench/figs 下混有已发表论文的全文纯文本
# （取自出版社 PDF），kg/paper_drafts 下可能有原始 xlsx 人工表——两类都不得随公开
# 仓库分发。注意：workbench/ml_out/_b*_probe_run.txt 是**我们自己的**探针日志，
# 是 Table 2 数字的源头，必须保留。
PAPER_FULLTEXT = {"_jpcl.txt", "_small.txt", "_sun_jcim.txt", "_wei.txt", "_xuan.txt"}
SKIP_SUFFIX = {".pyc", ".pdf", ".html", ".htm", ".xlsx", ".xls"}


def is_excluded(p: Path) -> bool:
    return (p.name in PAPER_FULLTEXT
            or p.suffix.lower() in SKIP_SUFFIX
            or "__pycache__" in p.parts)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    missing, copied = [], 0

    for rel in FILES + WORKBENCH_PY + ARTIFACTS:
        src = ROOT / rel
        if not src.exists():
            missing.append(rel)
            continue
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    for rel in DIRS:
        src = ROOT / rel
        if not src.exists():
            missing.append(rel + "/")
            continue
        for p in src.rglob("*"):
            if not p.is_file():
                continue
            if is_excluded(p):
                continue
            dst = OUT / p.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            copied += 1

    (OUT / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (OUT / "README.md").write_text(README, encoding="utf-8")
    (OUT / "LICENSE").write_text(LICENSE_HEAD, encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    n = sum(1 for f in OUT.rglob("*") if f.is_file())
    print(f"[release] {n} files, {total / 1e6:.2f} MB -> {OUT}")
    print(f"[release] directories: {', '.join(sorted(p.name for p in OUT.iterdir() if p.is_dir()))}")

    leaked = [p.relative_to(OUT) for p in OUT.rglob("*") if p.is_file() and is_excluded(p)]
    if leaked:
        print(f"[release] ERROR {len(leaked)} redistributable-risk file(s) in package:")
        for p in leaked[:10]:
            print("   !", p)
    else:
        print("[release] copyright check: no paper full texts / spreadsheets included")

    if missing:
        print(f"[release] WARNING {len(missing)} expected path(s) absent:")
        for m in missing:
            print("   -", m)


if __name__ == "__main__":
    main()
