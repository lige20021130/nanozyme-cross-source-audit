# -*- coding: utf-8 -*-
"""人工标注母表 → FlatRecord 兼容产出（provenance = human）。

数据源：E 盘 `人工收集的文献归类/人工智能纳米酶/整理后的对照集/nanozyme_benchmark_clean.json`
（1043 条记录 / 354 个唯一 DOI，源自人工母表 `数据整理-SLP-20240108.xlsx` 的 1085 行）。

设计要点：
1. **零 API、纯确定性** —— 本模块不做任何 LLM 调用，只做字段映射与类型归一。
2. **provenance 显式标记** —— 产出的每篇 paper 与每条 record 都带 `provenance: "human"`，
   与系统抽取产出（`extraction`）在 wiki 中永不静默混同。
3. **零侵入** —— 不改 `schema.py`、不改抽取系统；仅产出 `build_wiki.py` 可消费的同构文件。
4. **多出的字段单独存放** —— 人工表独有的 `synthesis_path`（合成路径）等不在 FlatRecord 25
   字段内的信息，统一放在 `_extra` 里，避免污染事实层的字段契约。

已知限制（诚实声明）：
- 人工表的 `substrate1/substrate2` **不区分 Km 究竟针对哪个底物**（仅是一对底物，顺序任意）。
  本模块保守地令 `kinetic_substrate = substrate1`。用 27 篇重叠文献校准，系统抽取的
  `kinetic_substrate` 有 90.4%（103/114）落在人工 substrate1/2 之内，故该近似可接受，
  但 hub 归属在少数文献上可能与真实 Km 归属有偏差。
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

# 人工标注集默认路径（U 盘挂载后可用）
BENCH_DEFAULT = Path(
    "E:/人工收集的文献归类/人工智能纳米酶/整理后的对照集/nanozyme_benchmark_clean.json"
)

# 仅人工表出现、align 的 _ACTIVITY_ALIASES 未覆盖的酶活别名
_BENCH_ACTIVITY_ALIASES = {
    "apx": "ascorbate peroxidase",
    "ascorbate peroxidase": "ascorbate peroxidase",
    "gpx": "glutathione peroxidase",
    "haloperoxidase": "haloperoxidase",
    "nadh oxidase": "nadh oxidase",
    "nox": "nadh oxidase",
    "glucose oxidase": "glucose oxidase",
    "nitric oxide synthase": "nitric oxide synthase",
    "nos": "nitric oxide synthase",
}

# 人工表用原子序数编码元素（metal1_type = 23.0 表示 V）
_ELEMENTS = {
    1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F", 11: "Na", 12: "Mg",
    13: "Al", 14: "Si", 15: "P", 16: "S", 17: "Cl", 19: "K", 20: "Ca",
    22: "Ti", 23: "V", 24: "Cr", 25: "Mn", 26: "Fe", 27: "Co", 28: "Ni",
    29: "Cu", 30: "Zn", 31: "Ga", 32: "Ge", 33: "As", 34: "Se", 35: "Br",
    38: "Sr", 39: "Y", 40: "Zr", 41: "Nb", 42: "Mo", 44: "Ru", 45: "Rh",
    46: "Pd", 47: "Ag", 48: "Cd", 49: "In", 50: "Sn", 51: "Sb", 52: "Te",
    53: "I", 55: "Cs", 56: "Ba", 57: "La", 58: "Ce", 59: "Pr", 60: "Nd",
    62: "Sm", 63: "Eu", 64: "Gd", 65: "Tb", 66: "Dy", 67: "Ho", 68: "Er",
    69: "Tm", 70: "Yb", 71: "Lu", 72: "Hf", 73: "Ta", 74: "W", 75: "Re",
    76: "Os", 77: "Ir", 78: "Pt", 79: "Au", 80: "Hg", 81: "Tl", 82: "Pb",
    83: "Bi", 90: "Th", 92: "U",
}

# 人工表字段 → FlatRecord 字段
_FIELD_MAP = {
    "nanozyme": "nanozyme",
    "enzyme_activity_raw": "mimic_enzyme_activity",
    "shape_raw": "shape",
    "size_nm": "size_nm",
    "surface_modification": "surface_modification",
    "dispersion_medium": "dispersion_medium",
    "buffer_ph": "buffer_ph_value",
    "temperature_c": "temperature_c",
    "substrate1": "substrate1",
    "substrate2": "substrate2",
    "km_mM": "Km_mM",
    "vmax_uM_s": "Vmax_uM_s_minus1",
    "kcat_s": "Kcat_s_minus1",
    "kcat_over_km": "catalytic_efficiency_M_s_minus1",
}

# 人工表独有、FlatRecord 无对应字段 → 收入 _extra
_EXTRA_FIELDS = (
    "synthesis_path",          # 合成路径（抽取系统目前不抽，人工表有）
    "buffer_ph_label",         # acidic / neutral / alkaline
    "substrate2_conc_mM",
    "ic50_sod_uM",
    "metal1_ratio", "metal1_type", "metal1_valence",
    "metal2_ratio", "metal2_type", "metal2_valence",
    "metal3_ratio", "metal3_type", "metal3_valence",
    "metal4_ratio", "metal4_type", "metal4_valence",
    "paper_index", "source", "pdf_path",
)

_KINETIC_FIELDS = ("Km_mM", "Vmax_uM_s_minus1", "Kcat_s_minus1",
                   "catalytic_efficiency_M_s_minus1")


def _num(v: Any) -> float | None:
    """把人工表的脏值（' '、None、'1'、'2500'）转成 float，失败返回 None。"""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    # NaN / inf 一律视为缺失
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _clean_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def normalize_doi(doi: Any) -> str:
    """DOI 归一：去前缀、去协议、小写、去尾点。"""
    if not doi:
        return ""
    s = str(doi).strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:\s*", "", s, flags=re.I)
    return s.strip().rstrip(".").lower()


def doi_to_filename(doi: str) -> str:
    """DOI → 文件名（与抽取系统一致的 `10.1002_xxx` 形式）。"""
    return re.sub(r"[^\w.\-]", "_", doi)


def normalize_activity(v: Any) -> str | None:
    """人工表酶活归一：先查 bench 专属别名，再去 `-like` 后缀，最后小写。"""
    s = _clean_str(v)
    if not s:
        return None
    s = s.strip()
    low = s.lower()
    if low in _BENCH_ACTIVITY_ALIASES:
        return _BENCH_ACTIVITY_ALIASES[low]
    # "peroxidase-like" → "peroxidase"
    if low.endswith("-like"):
        low = low[:-5].strip()
    if low in _BENCH_ACTIVITY_ALIASES:
        return _BENCH_ACTIVITY_ALIASES[low]
    if low.endswith(" like"):
        low = low[:-5].strip()
    # 首字母大写差异由下游 _norm_activity 统一，这里只做小写收敛
    return low or None


def element_of(v: Any) -> str | None:
    """原子序数 → 元素符号。人工表用数字编码元素。"""
    f = _num(v)
    if f is None:
        return None
    return _ELEMENTS.get(int(f))


def to_flat(raw: dict) -> dict:
    """一条人工表记录 → 一条 FlatRecord 兼容记录。"""
    rec: dict[str, Any] = {dst: None for dst in _FIELD_MAP.values()}
    rec.update({f: None for f in _KINETIC_FIELDS})
    rec["kinetic_substrate"] = None
    rec["kinetic_method"] = None
    rec["doped_N"] = rec["doped_P"] = rec["doped_S"] = rec["doped_B"] = rec["doped_F"] = None
    rec["metal_ratio"] = rec["metal_type"] = rec["metal_valence"] = None
    rec["doi"] = normalize_doi(raw.get("doi"))

    for src, dst in _FIELD_MAP.items():
        v = raw.get(src)
        if dst in _KINETIC_FIELDS or dst in ("size_nm", "buffer_ph_value", "temperature_c"):
            rec[dst] = _num(v)
        else:
            rec[dst] = _clean_str(v)

    rec["mimic_enzyme_activity"] = normalize_activity(raw.get("enzyme_activity_raw"))

    # kinetic_substrate：人工表不区分 Km 归属，保守取 substrate1
    rec["kinetic_substrate"] = rec.get("substrate1")

    # 元素编码 → 符号，作为 metal_type 的可读形式
    sym = element_of(raw.get("metal1_type"))
    if sym:
        rec["metal_type"] = sym
    rec["metal_ratio"] = _num(raw.get("metal1_ratio"))
    rec["metal_valence"] = _num(raw.get("metal1_valence"))

    # 人工表独有的合成路径等 → _extra
    extra: dict[str, Any] = {}
    for k in _EXTRA_FIELDS:
        v = raw.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            extra[k] = s
    # metal1_type 原始原子序数也保留，便于回溯
    if raw.get("metal1_type") is not None:
        extra["metal1_type_z"] = raw.get("metal1_type")
    if extra:
        rec["_extra"] = extra

    rec["provenance"] = "human"
    return rec


def has_kinetic(rec: dict) -> bool:
    """是否有动力学数值（与 build_wiki.iter_kinetic_records 判据一致）。"""
    return rec.get("Km_mM") is not None or rec.get("Vmax_uM_s_minus1") is not None


def load_bench(path: str | Path = BENCH_DEFAULT) -> list[dict]:
    """读人工标注集，返回原始记录列表（按 doi + 材料名排序，保证确定性）。"""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"人工标注集格式异常，期望 list，实际 {type(data).__name__}")
    return data


def group_by_doi(records: list[dict]) -> dict[str, list[dict]]:
    """按 DOI 聚合成 paper 结构（与抽取系统 output/<doi>.json 同构）。"""
    papers: dict[str, list[dict]] = defaultdict(list)
    for raw in records:
        doi = normalize_doi(raw.get("doi"))
        if not doi:
            continue
        papers[doi].append(to_flat(raw))
    for doi in papers:
        papers[doi].sort(key=lambda r: (
            str(r.get("nanozyme") or ""),
            str(r.get("mimic_enzyme_activity") or ""),
            str(r.get("kinetic_substrate") or ""),
            r.get("buffer_ph_value") if r.get("buffer_ph_value") is not None else -1e9,
            r.get("temperature_c") if r.get("temperature_c") is not None else -1e9,
            r.get("Km_mM") if r.get("Km_mM") is not None else -1e9,
        ))
    return dict(papers)


def to_paper(doi: str, recs: list[dict]) -> dict:
    """组装成 build_wiki.load_papers 可消费的 paper 结构。"""
    return {
        "doi": doi,
        "source_pdf": "",
        "records": recs,
        "provenance": "human",
        "_meta": {
            "source": "人工标注母表 (nanozyme_benchmark_clean.json)",
            "provenance": "human",
            "n_records": len(recs),
            "n_kinetic": sum(1 for r in recs if has_kinetic(r)),
        },
    }


def write_papers(papers: dict[str, list[dict]], out_dir: str | Path) -> dict[str, int]:
    """把 paper 结构写成 out_dir/<doi>.json。返回统计。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_papers = n_recs = n_kin = 0
    for doi in sorted(papers):
        recs = papers[doi]
        paper = to_paper(doi, recs)
        fp = out / f"{doi_to_filename(doi)}.json"
        fp.write_text(json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8")
        n_papers += 1
        n_recs += len(recs)
        n_kin += sum(1 for r in recs if has_kinetic(r))
    return {"papers": n_papers, "records": n_recs, "kinetic": n_kin}


def prepare(path: str | Path = BENCH_DEFAULT,
            out_dir: str | Path = "workbench/bench_records") -> dict[str, int]:
    """一步到位：读人工集 → 映射 → 写出 records 目录。"""
    raw = load_bench(path)
    papers = group_by_doi(raw)
    stats = write_papers(papers, out_dir)
    stats["source"] = str(path)
    stats["out_dir"] = str(out_dir)
    return stats


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="人工标注母表 → wiki records")
    ap.add_argument("--bench", default=str(BENCH_DEFAULT), help="人工标注集 JSON 路径")
    ap.add_argument("--out", default="workbench/bench_records", help="输出 records 目录")
    args = ap.parse_args()

    if not Path(args.bench).exists():
        print(f"错误：人工标注集不存在 {args.bench}（U 盘是否已挂载？）")
        sys.exit(1)
    st = prepare(args.bench, args.out)
    print(f"人工集 → records 完成：{st['papers']} 篇 / {st['records']} 条记录 "
          f"/ {st['kinetic']} 条含动力学")
    print(f"输出目录：{st['out_dir']}")
