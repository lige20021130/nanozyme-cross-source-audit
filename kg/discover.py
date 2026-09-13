# -*- coding: utf-8 -*-
"""M7 新知发现：从图谱产出（X 冲突谱 / Y 指纹网络 / Z 审计）挖掘可讲解的领域故事。

三类产出（全部确定性、零 API；跑在 M1-M6 的 records 之上）：
1. **条件响应谱案例**（挑 ≥3 个不同 pH、Km 跨 >5 倍的 (材料,酶活,底物) 组，附 V 形/单调/尖锐最优标记）
2. **跨文献审计裁决案例**（Z 层严重簇 → DOI 级可追踪 + 单位错配嫌疑判定）
3. **跨源单位错配证据**（fold≈10/100/1000 或 >100 的跨源冲突 → "疑似单位标注错配"）
4. **功能置换候选**（Y 网络强相似边，要求共享组件≥3 且剔同族变体；附网络怪异诊断——诚实声明其局限）

输出：discovery_report.json（结构化）+ discovery_report.md（人读版，供论文 §结果）
"""
from __future__ import annotations
import collections
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

GRADIENT_MIN_PH = 3          # 至少 3 个不同 pH
GRADIENT_MIN_FOLD = 5.0      # Km 峰谷比 >= 5
SIM_MIN_WEIGHT = 0.8         # 指纹相似边权重下限
SIM_MIN_SHARED = 3           # 至少共享 3 个条件匹配点（过滤权重饱和 1.0 的平凡匹配）
NOVELTY_MAX_EDGES = 1        # 候选材料在原文献网络中相似边数（阈值判 novelty）


def condition_response_cases(rows: list[dict]) -> list[dict]:
    """按 (材料,酶活,底物) 组扫描 pH 梯度，挑出可讲故事的组。

    rows: flat 条目（含 mat_key/act/sub/ph/km_mm/doi）。
    返回按 fold 降序，每条附 shape（v-shaped / monotone / peak / plateau / noisy）。
    """
    groups: dict[tuple, list[tuple]] = defaultdict(list)
    for r in rows:
        km, ph = r.get("km_mm"), r.get("ph")
        # 剔除 0/非法值（0 是占位/未测信号）
        if km is None or ph is None or float(km) <= 0:
            continue
        groups[(r.get("mat_key"), r.get("act"), r.get("sub"))].append(
            (float(ph), float(km), r.get("doi")))
    out = []
    for (mat, act, sub), pts in groups.items():
        by_ph: dict[float, list[float]] = defaultdict(list)
        for ph, km, _ in pts:
            by_ph[ph].append(km)
        phs = sorted(by_ph)
        if len(phs) < GRADIENT_MIN_PH:
            continue
        meds = [statistics.median(by_ph[p]) for p in phs]
        hi, lo = max(meds), min(meds)
        fold = hi / lo if lo > 0 else 0.0
        if fold < GRADIENT_MIN_FOLD:
            continue
        # shape 判别（在 pH 升序下）
        if meds[0] <= meds[-1] * 1.5 and lo == meds[0]:
            shape = "monotone" if all(meds[i] <= meds[i + 1] * 1.2 for i in range(len(meds) - 1)) else "noisy"
        elif meds[-1] <= meds[0] * 1.5 and lo == meds[-1]:
            shape = "monotone"
        elif meds.index(lo) not in (0, len(meds) - 1):
            shape = "v-shaped"
        else:
            shape = "peak" if meds.index(hi) not in (0, len(meds) - 1) else "noisy"
        out.append({
            "mat_key": mat, "activity": act, "substrate": sub,
            "ph_points": [{"ph": p, "km_median": statistics.median(by_ph[p])} for p in phs],
            "n_points": len(pts),
            "fold": round(fold, 2), "shape": shape,
            "n_papers": len({doi for _, _, doi in pts if doi}),
        })
    out.sort(key=lambda d: -d["fold"])
    return out


def unit_mismatch_evidence(conflicts: list[dict],
                           fold_steps: tuple[float, ...] = (10.0, 100.0, 1000.0),
                           extreme_thresh: float = 100.0) -> list[dict]:
    """从跨源冲突中挑 fold≈10^n（±15%）或 fold>=extreme 的 → "疑似单位错配"证据。

    经验：公开库原始版 Km 与精选版相差 10/100/1000 级、或跨 >100 倍且来源不止一家时，
    几乎都是 m/M 或 µ/10⁻⁶ 等单位标注差异——这是审计层可判、实验无法解释的信号。
    """
    out = []
    for c in conflicts:
        f = float(c.get("fold") or 0)
        flag = None
        for step in fold_steps:
            if abs(f - step) / step <= 0.15:
                flag = f"~{int(step)}×"
                break
        if flag is None and f >= extreme_thresh:
            flag = ">100×"
        if flag:
            c2 = dict(c)
            c2["suspect_unit"] = flag
            out.append(c2)
    out.sort(key=lambda d: -d["fold"])
    return out


def audit_adjudication_cases(audit_csv: str, top_n: int = 8) -> list[dict]:
    """从 Z 审计 CSV 挑"跨文献严重簇"作为可裁决案例（DOI 级可追踪）。"""
    import csv as _csv
    with open(audit_csv, encoding="utf-8-sig") as f:
        rows = list(_csv.DictReader(f))
    cases = []
    for r in rows:
        if r.get("等级") != "严重":
            continue
        try:
            n_papers = int(r.get("文献数") or 0)
            fold = float(r.get("倍数") or 0)
        except ValueError:
            continue
        if n_papers < 1:
            continue
        cases.append({
            "material": r.get("材料", ""), "activity": r.get("酶活", ""),
            "substrate": r.get("底物", ""), "ph": r.get("pH"),
            "temperature_c": r.get("温度(℃)"),
            "metric": r.get("指标", ""), "fold": fold,
            "n_papers": n_papers,
            "tier": r.get("tier"), "reason_tags": r.get("疑因标签", ""),
            "values_doi": r.get("逐条取值(DOI=值)", ""),
        })
    cases.sort(key=lambda d: -d["fold"])
    return cases[:top_n]


def _family(m: str) -> str:
    """材料家族归并：去掉掺杂比例/形貌/批次等变体 token → 同一家族视为同材料的变体。"""
    import re
    s = re.sub(r"\d+(\.\d+)?\s*%", "", m)      # 10%Pr / 5.5%Fe → Pr/Fe
    s = re.sub(r"\b(0\d+)\b", "", s)            # pr01ceo2 → prceo2
    s = re.sub(r"\b(nc|nrs|nus|nps|nws|nds|omc|nfs|ons|nps|mcs|nfs)\b", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9]", "", s.lower())
    return s


def _variant_pair(a: str, b: str) -> bool:
    """子串级变体：短名是长名子串 → 极可能是同一材料的写法变体（10%PrCeO2NC vs Pr01CeO2）。"""
    fa, fb = _family(a), _family(b)
    if fa == fb:
        return True
    if not fa or not fb:
        return False
    shorter, longer = (fa, fb) if len(fa) <= len(fb) else (fb, fa)
    # 短串是长串真子串（长度比 >= 0.6，避免 'ceo2' in 'cofe2o4ceo2' 这类合法多相误杀）
    if shorter in longer and len(shorter) >= 0.6 * len(longer):
        return True
    # 数字骨架比对：剥离全部数字后同骨架 → 不同掺杂量同一材料（lhis100fecof vs lhis75fecof）
    import re as _re
    da, db = _re.sub(r"\d", "", a).lower(), _re.sub(r"\d", "", b).lower()
    if not da or not db:
        return False
    s2, l2 = (da, db) if len(da) <= len(db) else (db, da)
    return s2 == l2 or (s2 in l2 and len(s2) >= 0.6 * len(l2))


def substitution_candidates(graphml: str, rows: list[dict],
                            top_n: int = 15) -> tuple[list[dict], dict]:
    """Y 网络强相似边 → 功能置换候选；返回 (候选, 网络诊断)。

    诊断项报告网络本身的偏向（诚实声明，论文口径）：
    - n_strong_edges / n_nodes：条件脆弱网络的规模；
    - hub_materials：强边度数最高的材料（多为广泛报道/CeO2-Au 类多敏感材料）；
    - variant_note：多数强边是"名称变体/条件稀疏平凡匹配"，非真替代证据。
    """
    import networkx as nx
    g = nx.read_graphml(graphml)
    mats_of_doi: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r.get("mat_key") and r.get("doi"):
            mats_of_doi[r["doi"]].add(r["mat_key"])
    out = []
    seen = set()
    for a, b, data in g.edges(data=True):
        w = float(data.get("weight", 0))
        if w < SIM_MIN_WEIGHT:
            continue
        sc = int(data.get("shared_components", 1))
        if sc < SIM_MIN_SHARED:
            continue                          # 单组件强边是"条件稀疏平凡匹配"，不构成置换信号
        if _family(a) == _family(b) or _variant_pair(a, b):
            continue                           # 同家族/子串变体（Pr 掺杂%等）不是"置换候选"
        # 非同源判定：两材料存在**共同 DOI** → 同源文献，剔除
        a_dois = {doi for doi, mats in mats_of_doi.items() if a in mats}
        b_dois = {doi for doi, mats in mats_of_doi.items() if b in mats}
        if a_dois & b_dois:
            continue
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "a": a, "b": b, "weight": round(w, 3),
            "shared_components": sc,
            "max_logkm_diff": data.get("max_logkm_diff"),
            "n_a_dois": len(a_dois), "n_b_dois": len(b_dois),
        })
    out.sort(key=lambda d: -d["weight"])
    # 网络诊断
    deg = dict(g.degree())
    strong_deg = collections.Counter()
    strong_sc: collections.Counter = collections.Counter()
    for a, b, data in g.edges(data=True):
        if float(data.get("weight", 0)) < SIM_MIN_WEIGHT:
            continue
        strong_deg[a] += 1
        strong_deg[b] += 1
        strong_sc[int(data.get("shared_components", 1))] += 1
    n_strong = sum(strong_sc.values())
    diag = {
        "n_nodes": g.number_of_nodes(),
        "n_edges": g.number_of_edges(),
        "n_strong_edges": n_strong,
        "strong_shared_components": {
            str(k): v for k, v in sorted(strong_sc.items(), reverse=True)},
        "hub_materials": [m for m, _ in strong_deg.most_common(10)],
        "variant_note": ("强边中绝大多数是名称变体（Pr 掺杂%、形貌后缀）或条件稀疏材料的"
                         "平凡匹配（权重饱和 1.0）：全部强边中仅 "
                         f"{sum(v for k, v in strong_sc.items() if k >= SIM_MIN_SHARED)}/"
                         f"{n_strong} 共享 >= {SIM_MIN_SHARED} 个条件点。候选表只从后者产生；"
                         "即使如此，候选仍是'条件指纹相似'的定性分组，需 alias 表 + 逐文献复核后才可作"
                         "置换证据。"),
    }
    return out[:top_n], diag


def build_report(records_dir: str, multi_records_dir: str, atlas_out: str,
                 gold_dirs: list[str] | None = None,
                 top_cases: int = 8) -> dict[str, Any]:
    """一键生成 discovery_report.json + md。gold_dirs: 354 篇 gold 的 records 目录（可选）。"""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from build_wiki import load_papers, collect_entries, flat_values
    from kg import lineage

    def flat_of(d: str) -> list[dict]:
        papers = load_papers(Path(d))
        return [flat_values(e) for e in collect_entries(papers)]

    def raw_rows_of(d: str) -> list[dict]:
        """raw 记录（与 build_kg_atlas/lineage 同口径：kinetic_substrate 未拼接为 'a | b'）。"""
        out = []
        for p in load_papers(Path(d)):
            out.extend(p.get("records", []))
        return out

    # 核心记录：collect_entries(entry) 摊平 + act/sub 显式注入（与 build_kg_atlas 同款）
    papers = load_papers(Path(records_dir))
    entries = collect_entries(papers)
    rows = []
    for e in entries:
        f = flat_values(e)
        f["act"] = e.get("act", "")
        f["sub"] = e.get("sub", "")
        rows.append(f)

    cases = condition_response_cases(rows)[:top_cases]
    # 跨源冲突用 raw 行（flat 行会把 kinetic_substrate 拼成 'a | b'，与 raw 'a' 对不上）
    raw_ex, raw_db = raw_rows_of(records_dir), raw_rows_of(multi_records_dir)
    conflicts = lineage.cross_source_conflicts(raw_ex + raw_db) if raw_db else []
    unit_ev = unit_mismatch_evidence(conflicts)
    audit_cases = audit_adjudication_cases(str(Path(atlas_out) / "audit.csv"))
    cand, cand_diag = substitution_candidates(
        str(Path(atlas_out) / "material_similarity.graphml"), rows)

    # gold 交叉验证：候选对在 gold 中是否已有报道（同 (材料A,B) 出现在同一 DOI）
    gold_hits: list[str] = []
    if gold_dirs:
        pair_in_doc: set[tuple] = set()
        for gd in gold_dirs:
            for p in load_papers(Path(gd)):
                mats = {e.get("mat_key") for e in collect_entries([p]) if e.get("mat_key")}
                for m in mats:
                    for n in mats:
                        if m < n:
                            pair_in_doc.add((m, n))
        for c in cand:
            c["reported_in_gold"] = ((c["a"], c["b"]) in pair_in_doc or
                                     (c["b"], c["a"]) in pair_in_doc)
            if c["reported_in_gold"]:
                gold_hits.append(f"{c['a']}-{c['b']}")

    report = {
        "condition_cases": cases,
        "audit_adjudication_cases": audit_cases,
        "cross_source_conflicts": {"n": len(conflicts), "unit_mismatch_suspects": unit_ev},
        "substitution_candidates": cand,
        "network_diagnosis": cand_diag,
        "gold_reported_pairs": gold_hits,
        "n_gold_dirs": len(gold_dirs or []),
    }
    return report


def report_to_md(report: dict) -> str:
    """结构化的发现报告（人读版，直接进论文讨论草稿）。"""
    md = ["# 新知发现报告（M7）", ""]
    md.append("## 1. 条件响应谱案例（pH 梯度 ≥3 点，Km fold ≥5）")
    md.append("pH 序列为中位数；多文献组为跨文献条件响应簇（n_papers>1），单文献组（n_papers=1）")
    md.append("才是同一体系的真实 pH 曲线。")
    md.append("| 材料 | 酶活 | 底物 | 形状 | fold | 文献数 | pH 序列(Km 中位) |")
    md.append("|---|---|---|---:|---:|---|---|")
    for c in report["condition_cases"]:
        pts = " → ".join(f"{p['ph']}g:{p['km_median']:.2g}" for p in c["ph_points"])
        md.append(f"| {c['mat_key']} | {c['activity']} | {c['substrate']} | "
                  f"{c['shape']} | {c['fold']:.1f}× | {c['n_papers']} | {pts} |")
    md.append("")
    md.append("## 2. 跨文献审计裁决案例（Z 层，DOI 可追踪）")
    md.append("| 材料 | 酶活/底物 | 条件(pH/T) | fold | 文献数 | 取值(DOI=值) |")
    md.append("|---|---|---|---:|---:|---|")
    for c in report["audit_adjudication_cases"][:6]:
        md.append(f"| {c['material']} | {c['activity']}/{c['substrate']} | "
                  f"{c['ph']}/{c['temperature_c']} | {c['fold']:.0f}× | {c['n_papers']} | "
                  f"{c['values_doi'][:80]} |")
    md.append("")
    md.append("## 3. 跨源单位错配 / 谱系差证据")
    md.append(f"跨源冲突 {report['cross_source_conflicts']['n']} 组，其中疑似单位标注错配 "
              f"{len(report['cross_source_conflicts']['unit_mismatch_suspects'])} 组：")
    md.append("")
    md.append("| DOI | 材料 | 底物 | fold | 嫌疑 | 来源 |")
    md.append("|---|---|---:|---|---|---|")
    for u in report["cross_source_conflicts"]["unit_mismatch_suspects"][:10]:
        md.append(f"| {u['doi']} | {u['material']} | {u['substrate']} | "
                  f"{u['fold']:.1f}× | {u.get('suspect_unit','')} | {u['sources']} |")
    md.append("")
    md.append("## 4. 功能置换候选材料（Y 网络强相似边，非同族非同源，共享条件点 ≥3）")
    md.append("| 材料A | 材料B | 相似权重 | 共享条件点 | DOI 数(A,B) | 论文已报 |")
    md.append("|---|---|---:|---:|---:|---|")
    for c in report["substitution_candidates"]:
        md.append(f"| {c['a']} | {c['b']} | {c['weight']} | {c.get('shared_components', '-')} "
                  f"| {c.get('n_a_dois', 0)},{c.get('n_b_dois', 0)} "
                  f"| {c.get('reported_in_gold', '-')} |")
    diag = report.get("network_diagnosis", {})
    if diag:
        md.append("")
        md.append("**网络诊断（诚实声明）**：")
        md.append(f"- 节点 {diag.get('n_nodes')} / 边 {diag.get('n_edges')} / 强边 {diag.get('n_strong_edges')}")
        sc = diag.get("strong_shared_components")
        if sc:
            md.append(f"- 强边按共享组件数分布：{sc}")
        md.append(f"- hub 材料（强边度 Top10）：{', '.join(diag.get('hub_materials', []))}")
        md.append(f"- 局限：{diag.get('variant_note', '')}")
    if report.get("gold_reported_pairs"):
        md.append("")
        md.append(f"gold 库已报道对：{report['gold_reported_pairs']}")
    return "\n".join(md) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="M7 新知发现一键报告")
    ap.add_argument("--records", required=True)
    ap.add_argument("--multi-records", required=True)
    ap.add_argument("--atlas-out", required=True)
    ap.add_argument("--gold", action="append", help="354 篇 gold 的 records 目录（可多传）")
    ap.add_argument("--out", default="workbench/m7_discovery")
    args = ap.parse_args(argv)
    report = build_report(args.records, args.multi_records, args.atlas_out, args.gold)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "discovery_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = report_to_md(report)
    (out / "discovery_report.md").write_text(md, encoding="utf-8")
    print(f"[M7] cases={len(report['condition_cases'])} "
          f"unit_suspects={len(report['cross_source_conflicts']['unit_mismatch_suspects'])} "
          f"candidates={len(report['substitution_candidates'])} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())