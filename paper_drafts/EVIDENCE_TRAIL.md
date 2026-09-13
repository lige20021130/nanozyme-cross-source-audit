# Evidence trail — Track 1 manuscript

> 用途：把稿件的每一个头条数字钉回源文件，并给出**能当场复算的验证命令**。
> 审稿人问"这个数哪来的"时，按本表一行即可回答；本表也是每轮改稿的回归清单。
> 维护：2026-09-12（round 13）。改动任何源文件后，重跑本表最后一列的命令。

---

## 0. 构建链与门控

| 环节 | 命令 |
|---|---|
| 唯一构建入口 | `D:/conda/python.exe paper_drafts/build_full_manuscript.py` → `paper_drafts/manuscript_full_track1.md` |
| 图内联 / 图号顺序 / 双栏字号 | `D:/conda/python.exe workbench/figs/_verify_inline_figs.py` |
| 渲染级：裁切 / 留白 / 红绿同现 / 有效字号 | `D:/conda/python.exe workbench/figs/_audit_render.py` |
| Fig 5 图注 8 条断言 | `D:/conda/python.exe workbench/figs/_probe_fig5_gray.py` |
| 引用重编号（KEY 基，覆盖 `<sup>` 与 SI `[n]`） | `D:/conda/python.exe workbench/_insert_audit_refs.py --apply` |
| 重生成图 1/3/4/6/8 | `D:/conda/python.exe workbench/figs/figs_v2.py` |
| 重生成图 2/7 | `D:/conda/python.exe workbench/figs/figs_data.py` |

构建脚本自带的自检：`[ref-check] bracket citations within 1..N`（方括号引用越界即报）。

---

## 1. 数据集规模（§1.2、§2.3、Fig 1/2）

| 稿件表述 | 源文件 | 复算 |
|---|---|---|
| 25 fields | `schema.py` → `FIELD_NAMES`（实测 25） | `python -c "from schema import FIELD_NAMES; print(len(FIELD_NAMES))"` |
| 5,027 entries | `workbench/atlas_out_multi/atlas_summary.json` → `entries` | `python -c "import json,pathlib;print(json.loads(pathlib.Path('workbench/atlas_out_multi/atlas_summary.json').read_text(encoding='utf-8'))['entries'])"` |
| 761 DOIs / 388 multi-source | 同上 → `lineage.n_doi`, `lineage.n_multi_source_doi` | 同上，取 `['lineage']` |
| 五源 1008/1031/1210/596/1182 | 同上 → `provenance` | 合计 = 5,027（可验） |

## 2. 冲突图谱（§4、§5、Fig 4/6/7）

| 稿件表述 | 源文件 | 复算 |
|---|---|---|
| 949 同 pH 桶 → 17 组 ≥10× | `workbench/figs/fig4_conflicts_sameph.json`（17 条） | `figs_v2.py` 运行时打印 `[fig4] conflicts=17 over10=17 over100=10` |
| 166 簇（97 severe / 43 suspicious / 26 consistent） | `workbench/atlas_out_multi/audit.csv` | `figs_v2.py` 打印 `[fig6] clusters=166 tiers={1:26, 2:43, 3:97}`；`n_conflict_clusters` 亦在 `atlas_summary.json` |
| 91 Kₘ / 64 Vmax / 11 kcat | 同上 audit.csv 指标列 | 同上 |
| Fe₃O₄ 同条件 **2,434×**；全局 **1.05×10⁶** | `workbench/atlas_records/` + `atlas_out_multi/` | `D:/conda/python.exe workbench/figs/_probe_fig5_gray.py`（8 条断言全 OK） |

## 3. 单位复原（§4.3、Table S6）

| 稿件表述 | 源文件 | 复算 |
|---|---|---|
| 17 组 = 确证 4 / 分组假阳性 1 / 方向性 3 / 值不可恢复 2 / 源不可达 7 | `paper_drafts/si_table_s6_unit_recovery.md`；脚本 `workbench/p0_unit_recovery.py`；探针 `paper_drafts/s6_recovery_probe.md` | `D:/conda/python.exe workbench/p0_unit_recovery.py` |
| 4+1+3+2+7 = 17（口径自洽） | 同上 | 手算 |

## 4. 抽取评估（§3.2–§3.4、Fig 3、Table 1、Table S7/S8）

| 稿件表述 | 源文件 | 复算 |
|---|---|---|
| F1 **0.946**（67 gold，主口径） | `workbench/evall_out/_eval_gold67.json` → `overall.F1` | 直接读 JSON |
| F1 0.965（30 篇） | `workbench/model_swap_out/*/_eval_30.json` | 直接读 |
| 100 篇一致性 0.907；逐字 0.847 | `workbench/_strict_probe.py`（2026-09-11 复算） | `D:/conda/python.exe workbench/_strict_probe.py` |
| kinetic bundle 49.2% / 53.8% / 52.4% 三口径 | `diagnostics.kinetic_bundle_match_rate`（三份 JSON） | 口径对照见 `build_full_manuscript.py` 的 `TABLE_NOTES` 注 c |
| Table S7 比较规则敏感性 / Table S8 逐篇离散 | `workbench/_caliber_tables.py` | 重跑该脚本 |

## 5. 漏读评估（§6、Fig 8、Table 2）

| 稿件表述 | 源文件 | 复算 |
|---|---|---|
| 分类 0.816 → 0.672，基线 0.695；macro-F1 0.673 → 0.350 | `workbench/ml_out/_b1_probe_run.txt`（`[CORE(atlas)|…]`） | 直接读该文件 |
| Core+DB 0.840 → 0.783，基线 0.783 | 同上（`[CORE+MULTI|…]`，n=3,002） | 同上 |
| 回归 0.387 / 0.134 / 0.023 | 同上 | 同上 |
| 材料级 −0.059 / −0.043 | 同上（`material-level` 段） | 同上 |
| 检索命中 40/978 = 4.1%；跨文献 Kₘ 中位 13.2×、P90 1.5×10⁴× | `workbench/ml_out/_b3_probe_run.txt` 第 6、8 行 | 直接读 |

## 6. 引用（References）

| 项 | 说明 |
|---|---|
| 17 条，按正文首现顺序 | 由 `workbench/_insert_audit_refs.py` 机械赋号；实测 `first-citation order = [1..17]` PASS |
| 首现顺序自检 | `python -c` 扫 `manuscript_full_track1.md` 正文段 `<sup>`，比对 1..17（本轮已跑，PASS） |
| 三条新增文献的外部凭证 | [2] Himanen 2019 — PubMed 31728276；[5] Wang 2026 — arXiv:2609.01621 页面；[12] Xu 2022 — PubMed 35537752 |

## 7. 未决 / 待补（诚实占位，不得猜测填充）

| 项 | 状态 |
|---|---|
| **N11 参考源错误率** | **数据尚未采集（2026-09-12：协议由双人改为单人两阶段）**。工具在 `workbench/n11_doubleblind/`：`draw_sample.py`（seed 20260912，抽样框 **293 条 / 97 DOI** → 抽 **25 条 / 25 个不同 DOI**）产出 `01_from_source.csv`（阶段 1 盲读）+ `02_reference_SEALED.csv`（阶段 2 封存参考值）；填完跑 `score_single_rater.py` 出 SI Table S9。采集前稿件中**不得**出现任何该数字的估计。⚠️ 单人设计，**非双盲**，无 Cohen's κ，稿件须称"与参考值不一致的比例"并同时报 Wilson 区间。若日后有第二人，用 `99_optional_second_rater.csv` + `score_doubleblind.py` 补算 κ。 |
| 吞吐 / token / 成本 | `workbench/` 全库无任何相关记录 → §1.2、§1.3 已弱化表述，不报数字 |
| [11] nanozymes.net 链接存活 | 沙箱不可达，投稿前需人工复查 |
| [5][14][15] 预印本 | 按目标期刊政策决定是否保留 arXiv 格式 |

---

## 8. 版本区分（改动留痕）

| 版本 | 快照位置 |
|---|---|
| round 13 改动**前**（2026-09-12） | `paper_drafts/_archive/round13_20260912/PRE_*` |
| round 13 改动清单与理由 | `paper_drafts/_archive/round13_20260912/CHANGES.md` |
| round 12 及更早 | 见 `.workbuddy/memory/2026-09-11.md` 起各日日志 |

---

## 9. round 14 新增 / 变更（2026-09-12，审稿响应）

> 触发：以 JCIM 审稿人立场做全文逐节核验（报告 `审稿报告_JCIM_20260912.md`）。
> 40 余个数字复算全部一致，无编造；改动集中在**披露、口径、SI 交付完整性**。

| 改动 | 源文件 | 复算 / 核对命令 |
|---|---|---|
| 通讯作者信息补齐（ORCID 0009-0009-9766-9467；sunliping@ahtcm.edu.cn；单位统一为 "School of Medical Informatics Engineering … 230012"） | `paper_drafts/paper_meta.py` | 来源：其 ACS Appl. Nano Mater. 2025, 8, 8918–8926 作者信息栏 |
| 基金号（2024AH051025 / DT2400000498 / gcyj202409）**待本人确认** | `paper_drafts/paper_meta.py` | 来源：安徽中医药大学医药信息工程学院 + 研究生院导师简介页；JCIM 2024 funding statement |
| JCIM 主编 = Prof. Kenneth M. Merz Jr. | `paper_drafts/paper_meta.py` | ASC/JCIM 编辑页 |
| 自审关系披露（AI-ZYMES = refs 7/8 = 通讯作者共同署名） | `manuscript_sections3_6_merged.md` §2.3/§4.1/§4.5；`paper_meta.py` COI；cover letter | CrossRef 核实 ref [7] 摘要含 "AI-ZYMES"、一作 Liping Sun |
| "five provenance groups（2 表 + 4 库）" 口径冲突修正 | §1.2、§2.3 | `atlas_summary.json.provenance` 只有 5 键 |
| **DOI 覆盖披露**：nanozymenet-k 无 DOI（1,182 条，内部键 `na-<n>`），另 6 条 AI-ZYMES 无 DOI；覆盖率约 76% | §2.3、§1.2、§1.3、§5.3 | `workbench/db_records/`+`atlas_records/` JSON 扫描；`kg/source_registry.py:157` 定义 `na-<n>` |
| **图谱稳健性**：13/166 簇含非 DOI 记录（6 个 tier-3，6/11 个 ≥10⁶× 簇）；剔除后 153 簇 = 21/41/91，≥10⁶× 由 11→5 | §5.5、**Table S9** | `workbench/figs/gen_si_extra_tables.py` |
| **Kₘ-only 敏感性**：91 簇 = 15/28/48（严重 52.7% vs 全局 58.4%） | §5.5、**Table S9** | 同上 |
| 补报 `novel_material` R²=0.157（n=854）以免选择性报告 | §6.3 | `workbench/ml_out/m6_external.json → novel_material` |
| §3.1 消融口径披露（19 字段 vs 17 字段，不可直接与 0.965 相减） | §3.1 | `ablation_out/stratified_30/_eval_*.json → eval_fields`（19）vs `evall_out/_eval_gold67.json`（17） |
| **新增文献 [17] nanoMINER**（npj Comput. Mater. 2025, 11, 194）；sklearn 顺延 [18] | `references_draft.md`、§3.1、§6.2 | CrossRef 10.1038/s41524-025-01674-7 |
| 修正：precision 0.892→0.891；"random 80/20"→"random"；§6.2 行数 978–3,002→1,056 与 3,002；§6.3 交叉引用 §5→§6.2；"genomic-basis GBR"→gradient-boosting；§6.5 正负 R² 措辞；§7.4 排版元信息移入 cover letter | 各节 | 见审稿报告 §4 |
| **SI 补交付 Table S4（166 行）/ S5（57 行）/ S9**；SI 编号统一 S1–S9 | `paper_drafts/si_table_s4_audit_register.md` 等；`build_full_manuscript.py` | `D:/conda/python.exe workbench/figs/gen_si_extra_tables.py` |
| Table S1 增补 per-source 映射面板（字段填充数 23/9/8/8/8、DOI 缺失数、单位不确定数） | `si_tables_track1.md` | 由 `db_records/`+`atlas_records/` 实测 |
| Table S2 加限定：5,027 中 4,019 系从被比库重新整合 | `si_tables_track1.md` | 1008+1031+1210+596+1182 |

**投稿前仍待人工处理**
1. 关闭 `submission_JCIM/SI.docx` 后跑一次 `D:/conda/python.exe paper_drafts/build_submission.py`（当前被编辑器占用，已改名为 `SI_REBUILT.docx` 暂放同目录）。
2. 基金号适用性由通讯作者确认（`paper_meta.py` FUNDING 上方的注释）。
3. 建议审稿人 2 位（Kelong Fan / Lingyan Feng）与回避名单（AI-ZYMES 共同作者）需本人确认无合作关系。
4. 代码仓库地址：目前如实写 "on reasonable request"；若能先推 GitHub/Zenodo 更好。
5. Wei 2022 的 "random 80/20" 与 "920 records / 5355 screened" 已从正文改为可证表述；Table S2 中 920/5355 仍按原文所报保留，建议投稿前回原文复核。
