# -*- coding: utf-8 -*-
"""五个公开纳米酶数据库 → FlatRecord 兼容供流（v2 多源汇聚层）。

定位：五库是论文的 **citable data sources**（引用对象），不是自研数据的原料。
本模块只做两件事：
1. 各库列名/单位/酶活/DOI 的确定性归一化 → FlatRecord（与 excel_source.to_flat 同套键）；
2. 无法确判单位的数值标 `_unit.km_uncertain=True`，不猜测换算 —— 偏差是数据生态的特征，
   交由 lineage/audit 层把它变成论文素材。

provenance 取值：human（Excel 精选版）之外，db:ai-zymes / db:dizyme /
db:nanozymenet-k / db:nanozymenet-m / db:nanozymedb（chemx-nanomag 无动力学，不产 Km 记录）。
铁律：只做文件头明确声明的单位换算；零 API、零 GPU、确定性。
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from kg.excel_source import _num, _clean_str, normalize_doi, normalize_activity

DATA_DIR = Path(__file__).resolve().parent.parent / "爬取的纳米酶数据"

SOURCES: list[dict] = [
    {"source_id": "db:ai-zymes", "path": DATA_DIR / "AI-ZYMES" / "AI-ZYMES_full.csv", "kind": "csv"},
    {"source_id": "db:dizyme", "path": DATA_DIR / "DiZyme" / "nanozymes.csv", "kind": "csv"},
    {"source_id": "db:nanozymenet-k", "path": DATA_DIR / "nanozymes.net" / "kinetics.csv", "kind": "csv"},
    {"source_id": "db:nanozymenet-m", "path": DATA_DIR / "nanozymes.net" / "materials.csv", "kind": "csv"},
    {"source_id": "db:nanozymedb", "path": DATA_DIR / "NanozymeDB" / "Nanozymes_full.xlsx", "kind": "xlsx"},
    {"source_id": "db:chemx-nanomag", "path": DATA_DIR / "ChemX_from_ITMO" / "Nanomag.csv", "kind": "csv"},
]


def _pow10(v: Any) -> int:
    n = _num(v)
    return int(n) if n is not None else 0


def _map_row(row: dict, source_id: str) -> dict:
    """各源列名 → 统一中间键（units 为原始单位上下文，供 _unit 语义）。"""
    if source_id == "db:ai-zymes":
        return {
            "nanozyme": row.get("name"), "activity": row.get("mimic_enzyme_activity"),
            "ph": row.get("buffer_ph_value"), "temperature_c": row.get("temperature"),
            "km": row.get("km_per_mm"), "vmax": row.get("vmax_micro_m_per_s"),
            "kcat": row.get("kcat_per_s"), "substrate1": row.get("substrate1"),
            "substrate2": row.get("substrate2"), "doi": row.get("data_reference_doi"),
            "units": {"km": "mM", "vmax": "uM/s", "kcat": "1/s"},
        }
    if source_id == "db:dizyme":
        sub1 = _clean_str(row.get("ReactionType"))
        sub2 = None
        if sub1 and " + " in sub1:
            parts = [s.strip() for s in sub1.split("+")]
            sub1, sub2 = parts[0], parts[1] if len(parts) > 1 else None
        return {
            "nanozyme": row.get("formula"), "activity": row.get("activity"),
            "ph": row.get("ph"), "temperature_c": row.get("temp, °C"),
            "km": row.get("Km, mM"), "vmax": row.get("Vmax, mM/s"),
            "kcat": None, "substrate1": sub1, "substrate2": sub2,
            "doi": row.get("link"),
            "units": {"km": "mM", "vmax": "mM/s", "kcat": None},
        }
    if source_id == "db:nanozymenet-k":
        return {
            "nanozyme": row.get("material"), "activity": row.get("enzyme type"),
            "ph": row.get("pH"), "temperature_c": row.get("T"),
            "km": row.get("km"), "km_exp": row.get("km 10n"),
            "vmax": row.get("vmax"), "vmax_exp": row.get("vmax 10n"),
            "kcat": row.get("kcat"), "kcat_exp": row.get("kcat 10n"),
            "substrate1": row.get("substrate"), "substrate2": None,
            "doi": None, "units": {"km": "mM", "vmax": None, "kcat": None},
        }
    if source_id == "db:nanozymedb":
        return {
            "nanozyme": row.get("Nanozyme Name/ Monomaterial"),
            "activity": row.get("Enzyme Like Activity"),
            "ph": row.get("pH"), "temperature_c": row.get("Temp (℃)"),
            "km": row.get("Kₘ (mM)"), "vmax": row.get("Vmax(nM s⁻¹)"),
            "kcat": row.get("kcat (s⁻¹)"), "substrate1": row.get("Substrate/Activity"),
            "substrate2": None, "doi": row.get("DOI"),
            "units": {"km": "mM", "vmax": "?", "kcat": "1/s"},
        }
    # db:nanozymenet-m（材料元数据）与 db:chemx-nanomag（磁学属性）：无动力学映射
    return {"nanozyme": None}


def to_flat(row: dict, source_id: str) -> dict:
    """一条公开库行 → FlatRecord 兼容 dict（最终键与 excel_source.to_flat 对齐）。"""
    m = _map_row(row, source_id)
    units = m.get("units", {})
    km = _num(m.get("km"))
    km_uncertain = False
    if km is not None and m.get("km_exp") is not None:
        km = km * (10 ** _pow10(m.get("km_exp")))
    elif source_id == "db:nanozymenet-k" and m.get("km_exp") is None:
        km_uncertain = True                  # 缺指数 → 单位不可判
    vmax = _num(m.get("vmax"))
    if vmax is not None and m.get("vmax_exp") is not None:
        vmax = vmax * (10 ** _pow10(m.get("vmax_exp")))
    if vmax is not None and units.get("vmax") == "mM/s":
        vmax = vmax * 1000.0                  # mM/s → µM/s
    if vmax is not None and units.get("vmax") == "?":
        # 单位不明 → 数值不可放到 µM/s 归一标度，保持 None，语义留给审计层
        vmax = None
    kcat = _num(m.get("kcat"))
    if kcat is not None and m.get("kcat_exp") is not None:
        kcat = kcat * (10 ** _pow10(m.get("kcat_exp")))
    rec: dict[str, Any] = {
        "nanozyme": _clean_str(m.get("nanozyme")),
        "mimic_enzyme_activity": normalize_activity(m.get("activity")),
        "buffer_ph_value": _num(m.get("ph")),
        "temperature_c": _num(m.get("temperature_c")),
        "Km_mM": km,
        "Vmax_uM_s_minus1": vmax,
        "Kcat_s_minus1": kcat,
        "kinetic_substrate": _clean_str(m.get("substrate1")),
        "kinetic_method": None,
        "doi": normalize_doi(m.get("doi")),
        "provenance": source_id,
        "_unit": {
            "km": units.get("km"),
            "vmax": units.get("vmax") if vmax is not None else None,
            "kcat": units.get("kcat") if kcat is not None else None,
            "km_uncertain": km_uncertain,
        },
    }
    if m.get("substrate2"):
        rec["_extra"] = {"substrate2": m["substrate2"]}
    return rec


def load(source: dict) -> list[dict]:
    """按 kind 读 csv/xlsx，返回行 dict 列表（行序稳定）。"""
    import pandas as pd
    p = Path(source["path"])
    if not p.exists():
        raise FileNotFoundError(f"数据库文件不存在：{p}")
    kwargs = {}
    if source["kind"] == "xlsx":
        df = pd.read_excel(p)
    else:
        try:
            df = pd.read_csv(p)
        except UnicodeDecodeError:
            df = pd.read_csv(p, encoding="latin-1")
    df.columns = [str(c) for c in df.columns]
    out = []
    for _, row in df.iterrows():
        out.append({c: row[c] for c in df.columns
                    if not (isinstance(row[c], float) and pd.isna(row[c]))})
    return out


def prepare(out_dir: str | Path) -> dict[str, int]:
    """五库 → out_dir/<doi>.json（同 excel_source.prepare 语义）。

    返回 {papers, records, kinetic, by_source:{source_id:n}}；无动力学值的行不产记录。
    DOI 为空的行按 "na-<规律序号>" 写入（write_papers 的 doi_to_filename 对非 DOI
    键同样安全），保持可追溯，不静默丢弃。
    """
    from kg.bench_source import write_papers
    out_dir = Path(out_dir)
    papers: dict[str, list[dict]] = {}
    by_source: dict[str, int] = {}
    for s in SOURCES:
        n = 0
        for row in load(s):
            rec = to_flat(row, s["source_id"])
            if not rec["nanozyme"]:
                continue
            if rec["Km_mM"] is None and rec["Vmax_uM_s_minus1"] is None and rec["Kcat_s_minus1"] is None:
                continue                                   # 无动力学值不出 records
            key = rec["doi"] or f"na-{len(papers) + 1}"
            papers.setdefault(key, []).append(rec)
            n += 1
        by_source[s["source_id"]] = n
    for recs in papers.values():
        recs.sort(key=lambda r: (str(r.get("nanozyme") or ""),
                                 _num(r.get("Km_mM")) if r.get("Km_mM") is not None else -1e9))
    stats = write_papers(papers, out_dir)
    stats["by_source"] = by_source
    return stats