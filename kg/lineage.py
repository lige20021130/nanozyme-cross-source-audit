# -*- coding: utf-8 -*-
"""DOI×源谱系矩阵 + 跨源冲突 + 覆盖盲区 + 防泄漏划分（v2 多源汇聚层）。

三个科学问题（spec §3.2，五库 = 引用来源）：
1. 谱系差：同一 DOI 在【数据库原始版】与【人工精选版 Excel】间 Km 差异（fold 分布）。
2. 库间一致率：同一 DOI+材料+底物+pH 下，跨源 Km fold 分布。
3. 覆盖盲区：仅一侧出现的材料/酶活组合。

零 API、零 GPU、确定性（同输入 → 同输出）。输入为 FlatRecord 兼容 dict（含 provenance）。
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path

FOLD_THRESH = 2.0


def _row_key(r: dict) -> tuple:
    return (str(r.get("doi") or ""), str(r.get("nanozyme") or ""),
            str(r.get("kinetic_substrate") or ""))


def cross_source_conflicts(rows: list[dict], fold_thresh: float = FOLD_THRESH) -> list[dict]:
    """同 DOI+材料+底物、且 pH 明确的跨源 Km 比对，fold >= 阈值 → 冲突一行。

    pH 缺失的记录不可比，整组跳过（公开库 pH 覆盖低的真实特征，如实呈现）；
    温度列不进分组键（公开库温度覆盖更低，结论在论文里陈述该近似）。
    km_uncertain 的记录参与比对但标 "unit_uncertain": True（引用方自行解释）。
    返回按 fold 降序。
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("Km_mM") is None or r.get("buffer_ph_value") is None:
            continue
        groups[_row_key(r)].append(r)
    out: list[dict] = []
    for key, items in groups.items():
        if len({it.get("provenance") for it in items}) < 2:
            continue                       # 单一来源不构成跨源
        # 同来源代表值（同来源取中位数，确定性）
        by_src: dict[str, list[float]] = defaultdict(list)
        for it in items:
            by_src[str(it.get("provenance"))].append(float(it["Km_mM"]))
        combined = sorted(v for vs in by_src.values() for v in vs)
        if len(combined) < 2:
            continue
        lo, hi = combined[0], combined[-1]
        if hi <= 0 or lo <= 0:
            continue
        fold = hi / lo
        if fold >= fold_thresh:
            out.append({
                "doi": key[0], "material": key[1], "substrate": key[2],
                # sources 存排序列表（CSV 可序列化；测试比对时用 set() 包裹）
                "sources": sorted(by_src),
                "min_km": lo, "max_km": hi, "fold": round(fold, 4),
                "n_sources": len(by_src),
                "unit_uncertain": any(
                    (it.get("_unit") or {}).get("km_uncertain") for it in items),
            })
    out.sort(key=lambda d: -d["fold"])
    return out


def lineage_matrix(excel_records: list[dict], db_records: list[dict]) -> dict:
    """DOI × 源 稀疏矩阵 + 统计（谱系差/一致率/盲区 的原始材料）。"""
    by_doi: dict[str, set[str]] = defaultdict(set)
    for r in excel_records:
        d = r.get("doi")
        if d:
            by_doi[d].add("excel")
    for r in db_records:
        d = r.get("doi")
        if d:
            by_doi[d].add(str(r.get("provenance")))
    return {
        "n_doi": len(by_doi),
        "excel_only_doi": sorted(d for d, s in by_doi.items() if s == {"excel"}),
        "multi_source_doi": sorted(d for d, s in by_doi.items() if len(s) >= 2),
        "doi_by_source": {s: sorted(d for d, ss in by_doi.items() if s in ss)
                          for s in sorted({v for ss in by_doi.values() for v in ss})},
    }


def coverage_gaps(excel_records: list[dict], db_records: list[dict]) -> dict:
    """仅精选版有 / 仅公开库有的材料、酶活组合。"""
    def set_of(rows, key):
        return {str(r.get(key) or "").strip() for r in rows if r.get(key)}
    em, dm = set_of(excel_records, "nanozyme"), set_of(db_records, "nanozyme")
    ea, da = set_of(excel_records, "mimic_enzyme_activity"), set_of(db_records, "mimic_enzyme_activity")
    return {
        "materials_excel_only": sorted(em - dm),
        "materials_db_only": sorted(dm - em),
        "activities_excel_only": sorted(ea - da),
        "activities_db_only": sorted(da - ea),
    }


def holdout_split(rows: list[dict], test_dois: set[str]) -> tuple[list[dict], list[dict]]:
    """按 DOI 划分训练/测试；同 DOI 全进同侧，同材料家族同 origin 族亦同侧。

    防泄漏规则：
    - DOI 在 test_dois → test，其余 → train（主判据）；
    - 若某"材料家族"（nanozyme 相同的同一来源族：provenance 的 origin 即
      "human"/"db"）的任一 DOI 在 test，该家族全部行进 test —— 防止同文献
      多 DOI 或公开库重复抓取同材料时造成的双向泄漏。
    返回 (train, test)，顺序稳定。
    """
    def fam_key(r: dict) -> str:
        origin = str(r.get("provenance") or "").split(":")[0]
        return f"{str(r.get('nanozyme') or '')}::{origin}"
    fam: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        fam[fam_key(r)].append(r)
    fam_test = {fk for fk, rs in fam.items()
                if any(r.get("doi") in test_dois for r in rs)}
    test_rows, train_rows = [], []
    for r in rows:
        if r.get("doi") in test_dois or fam_key(r) in fam_test:
            test_rows.append(r)
        else:
            train_rows.append(r)
    return train_rows, test_rows


def write_stats(out_dir: str | Path, excel_records: list[dict],
                db_records: list[dict], conflicts: list[dict]) -> dict:
    """写 lineage_matrix.json / cross_source_conflicts.csv / coverage_gaps.json。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    matrix = lineage_matrix(excel_records, db_records)
    gaps = coverage_gaps(excel_records, db_records)
    (out / "lineage_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "coverage_gaps.json").write_text(
        json.dumps(gaps, ensure_ascii=False, indent=2), encoding="utf-8")
    p = out / "cross_source_conflicts.csv"
    if conflicts:
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(conflicts[0].keys()))
            w.writeheader()
            w.writerows(conflicts)
    return {
        "n_doi": matrix["n_doi"],
        "n_multi_source_doi": len(matrix["multi_source_doi"]),
        "n_cross_source_conflicts": len(conflicts),
        "n_materials_excel_only": len(gaps["materials_excel_only"]),
        "n_materials_db_only": len(gaps["materials_db_only"]),
    }