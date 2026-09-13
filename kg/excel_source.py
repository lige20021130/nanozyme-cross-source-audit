# -*- coding: utf-8 -*-
"""两份人工标注 Excel → FlatRecord 兼容产出（provenance=human，零 API）。

与 kg/bench_source.py 的定位差异：
- bench_source 消费的输入是已清洗的 nanozyme_benchmark_clean.json（JSON）。
- 本模块直接消费**原始 Excel**（董瑞 FILE1、SLP FILE2），负责列名映射、
  单位归一、酶活/元素别名解析，是"Excel → 图谱"的入口。
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

# 双 Excel 的 sheet 与列名（以实际文件核对为准，这里列出已实测的）
# source_id 供 prepare 识别：FILE1 无 "Mimic enzyme activity" 列（全文件为 POD 活性），
# 需回填 peroxidase；FILE2 自带酶活列，不做回填。
FILE1 = {"path": r"C:\Users\lcl\Desktop\代码仓库\处理的数据\原始数据（纳米酶的POD活性-20240927 - 发给董瑞(1).xlsx", "sheet": "Sheet7", "source_id": "file1"}
FILE2 = {"path": r"E:\人工收集的文献归类\人工智能纳米酶\数据汇总-SLP-20231010 - 整理后的.xlsx", "sheet": "Sheet1", "source_id": "file2"}

# 元素 Symbol（同 bench_source._ELEMENTS，集中一份）
_ELEMENTS = {
    1:"H",5:"B",6:"C",7:"N",8:"O",9:"F",11:"Na",12:"Mg",13:"Al",14:"Si",15:"P",
    16:"S",17:"Cl",19:"K",20:"Ca",22:"Ti",23:"V",24:"Cr",25:"Mn",26:"Fe",27:"Co",
    28:"Ni",29:"Cu",30:"Zn",31:"Ga",32:"Ge",33:"As",34:"Se",35:"Br",38:"Sr",39:"Y",
    40:"Zr",41:"Nb",42:"Mo",44:"Ru",45:"Rh",46:"Pd",47:"Ag",48:"Cd",49:"In",50:"Sn",
    51:"Sb",52:"Te",53:"I",55:"Cs",56:"Ba",57:"La",58:"Ce",59:"Pr",60:"Nd",62:"Sm",
    63:"Eu",64:"Gd",65:"Tb",66:"Dy",67:"Ho",68:"Er",69:"Tm",70:"Yb",71:"Lu",72:"Hf",
    73:"Ta",74:"W",75:"Re",76:"Os",77:"Ir",78:"Pt",79:"Au",80:"Hg",81:"Tl",82:"Pb",
    83:"Bi",90:"Th",92:"U",
}
_ACTIVITY_ALIASES = {
    "peroxidase": "peroxidase", "pod": "peroxidase", "peroxidase-like": "peroxidase",
    "oxidase": "oxidase", "oxd": "oxidase", "oxidase-like": "oxidase",
    "catalase": "catalase", "cat": "catalase", "catalase-like": "catalase",
    "superoxide dismutase": "superoxide dismutase", "sod": "superoxide dismutase",
    "glutathione peroxidase": "glutathione peroxidase", "gpx": "glutathione peroxidase",
}

def _num(v: Any) -> float | None:
    if v is None: return None
    s = str(v).strip().replace(",", "")
    if not s: return None
    try: f = float(s)
    except ValueError: return None
    if f != f or f in (float("inf"), float("-inf")): return None
    return f

def _clean_str(v: Any) -> str | None:
    if v is None: return None
    s = str(v).strip()
    return s or None

def _pick(row: dict, *keys: str) -> Any:
    """按顺序取第一个存在且非 None 的键值；全缺返回 None。区分「键缺失」与「值为 0/False」。"""
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None

def element_of(v: Any) -> str | None:
    f = _num(v)
    if f is None: return None
    return _ELEMENTS.get(int(f))

def normalize_activity(v: Any) -> str | None:
    if v is None: return None
    s = str(v).strip().lower()
    if s in _ACTIVITY_ALIASES: return _ACTIVITY_ALIASES[s]
    for k in ("-like", " like"):
        if s.endswith(k):
            s = s[: -len(k)].strip()
            break
    return _ACTIVITY_ALIASES.get(s, s or None)

def normalize_doi(v: Any) -> str:
    if not v: return ""
    s = str(v).strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:\s*", "", s, flags=re.I)
    return s.strip().rstrip(".").lower()

def to_flat(row: dict, ph_col: str = "Buffer pH value", t_col: str = "Temperature/℃",
            sub1: str = "Substrate1 ", sub2: str = "Substrate2 ",
            km_col: str = "Km/mM", vmax_col: str = "Vmax/μM s-1",
            source: str | None = None) -> dict:
    """一条 Excel 行 → FlatRecord 兼容 dict。行内键名以实际列名为准（保守取 get）。

    source == "file1" 时，若行内无酶活列（POD 数据集），回填 "peroxidase"；
    显式给出的酶活值保持不变，不做回填覆盖。
    """
    rec: dict[str, Any] = {
        "nanozyme": _clean_str(_pick(row, "Name", "name")),
        "mimic_enzyme_activity": normalize_activity(_pick(row, "Mimic enzyme activity", "mimic_enzyme_activity")),
        "shape": _clean_str(_pick(row, "shape", "Shape")),
        "size_nm": _num(_pick(row, "Size/nm", "size_nm")),
        "dispersion_medium": _clean_str(_pick(row, "Dispersion medium", "dispersion_medium")),
        "surface_modification": _clean_str(_pick(row, "Surface modification", "surface_modification")),
        "buffer_ph_value": _num(_pick(row, ph_col, "Buffer pH")),
        "temperature_c": _num(_pick(row, t_col, "temperature_c")),
        "substrate1": _clean_str(_pick(row, sub1, "substrate1")),
        "substrate2": _clean_str(_pick(row, sub2, "substrate2")),
        "Km_mM": _num(_pick(row, km_col, "km_mM")),
        "Vmax_uM_s_minus1": _num(_pick(row, vmax_col, "vmax_uM_s")),
        "Kcat_s_minus1": _num(_pick(row, "Kcat/s-1 ", "Kcat/s-1", "kcat_s")),
        "catalytic_efficiency_M_s_minus1": _num(_pick(row, "k cat /Km\n(Catalytic efficiency )/M-1 s-1")),
        "doi": normalize_doi(_pick(row, "data reference doi", "doi")),
        "metal_type": element_of(_pick(row, "Metal type", "metal_type")),
        "metal_ratio": _num(_pick(row, "Metal ratio", "metal_ratio")),
        "metal_valence": _num(_pick(row, "Metal valence", "metal_valence")),
        "doped_N": _num(_pick(row, "N")),
        "doped_P": _num(_pick(row, "P")),
        "doped_S": _num(_pick(row, "S")),
        "doped_B": _num(_pick(row, "B")),
        "doped_F": _num(_pick(row, "F")),
        "kinetic_substrate": _clean_str(_pick(row, "Substrate1 ", "substrate1")),
        "kinetic_method": None,
        "provenance": "human",
    }
    extra = {}
    for k in ("Substrate2 concentration(mM)", "IC50(SOD)/μM", "合成路径", "论文索引",
              "Buffer pH ", "metal1_type", "metal1_ratio", "metal1_valence"):
        if k in row and row[k] is not None and str(row[k]).strip():
            extra[k] = row[k]
    if extra:
        rec["_extra"] = extra
    # FILE1 为 POD 数据集、无酶活列：回填默认酶活（不清空显式值）
    if source == "file1" and not rec["mimic_enzyme_activity"]:
        rec["mimic_enzyme_activity"] = "peroxidase"
    return rec

def load_excel(path: str | Path, sheet: str | None = None) -> list[dict]:
    """读 Excel，按行返回 dict 列表（行序稳定）。"""
    import pandas as pd
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Excel 不存在：{p}")
    sheets = None if sheet else 0
    df = pd.read_excel(p, sheet_name=sheets)
    if isinstance(df, dict):
        if sheet:
            df = df[sheet]
        else:
            df = next(iter(df.values()))
    # 列名规整：去掉列名首尾空格（实测部分列名带尾空格），其余不动
    df.columns = [str(c) for c in df.columns]
    out: list[dict] = []
    for _, row in df.iterrows():
        out.append({c: row[c] for c in df.columns
                    if not (isinstance(row[c], float) and pd.isna(row[c]))})
    return out

def prepare(files: list[dict], out_dir: str | Path) -> dict[str, int]:
    """多 Excel → out_dir/<doi>.json。返回统计（papers/records/kinetic/dups）。

    注意：这里不能复用 bench_source.group_by_doi —— 它会按 bench 的原始字段名
    再次执行 to_flat（期望 km_mM / enzyme_activity_raw），而本模块 to_flat 产出的
    已是最终 FlatRecord（Km_mM），二次映射会把 Km/酶活全部清成 None。故此处按
    DOI 本地聚合，仅复用不重新映射的 write_papers。
    """
    from kg.bench_source import write_papers
    raw_records: list[dict] = []
    for f in files:
        for row in load_excel(f["path"], f.get("sheet")):
            rec = to_flat(row, source=f.get("source_id"))
            if rec["nanozyme"]:
                raw_records.append(rec)
    # 完全重复去重（同 doi+材料+酶活+底物+Km）
    seen: set[tuple] = set()
    dedup: list[dict] = []
    for r in raw_records:
        key = (r.get("doi"), r.get("nanozyme"), r.get("mimic_enzyme_activity"),
               r.get("kinetic_substrate"), r.get("Km_mM"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    # 按 DOI 本地聚合（records 已是最终 FlatRecord，仅按 key 排序保证确定性）
    def _sort_key(r: dict):
        return (
            str(r.get("nanozyme") or ""),
            str(r.get("mimic_enzyme_activity") or ""),
            str(r.get("kinetic_substrate") or ""),
            r.get("buffer_ph_value") if r.get("buffer_ph_value") is not None else -1e9,
            r.get("temperature_c") if r.get("temperature_c") is not None else -1e9,
            r.get("Km_mM") if r.get("Km_mM") is not None else -1e9,
        )
    papers: dict[str, list[dict]] = {}
    for r in dedup:
        if not r.get("doi"):
            continue
        papers.setdefault(r["doi"], []).append(r)
    for recs in papers.values():
        recs.sort(key=_sort_key)
    stats = write_papers(papers, out_dir)
    stats["dedup_dropped"] = len(raw_records) - len(dedup)
    return stats