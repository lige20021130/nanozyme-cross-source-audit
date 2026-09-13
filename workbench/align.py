# workbench/align.py - 数据集对齐与评估（显式列映射，修复 eval 模糊匹配问题）
"""显式 Excel 列 → 29 字段映射，按 DOI 对齐 gold 与系统输出，复用 eval 比较逻辑。

eval.py 的 _map_columns 用归一化模糊匹配，对当前 gold 失效（DOI 列 'data reference doi'、
掺杂列 '-N'、温度 'Temperature/℃'、Vmax 'μM s-1' 等均匹配不上）。本模块用显式映射表对齐。
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logger = logging.getLogger("align")

# 显式列映射：Excel 列名（strip 后）→ FlatRecord 字段
_EXCEL_TO_FIELD: dict[str, str] = {
    "Nanozyme": "nanozyme",
    "Mimic enzyme activity": "mimic_enzyme_activity",
    "-N": "doped_N", "-P": "doped_P", "-S": "doped_S", "-B": "doped_B", "-F": "doped_F",
    "Metal ratio": "metal_ratio", "Metal type": "metal_type", "Metal valence": "metal_valence",
    "shape": "shape", "Size/nm": "size_nm", "Surface modification": "surface_modification",
    "Dispersion medium": "dispersion_medium", "Buffer pH value": "buffer_ph_value",
    "Temperature/℃": "temperature_c", "Substrate1": "substrate1", "Substrate2": "substrate2",
    "Km/mM": "Km_mM", "Vmax/μM s-1": "Vmax_uM_s_minus1",
    "Kcat/s": "Kcat_s_minus1", "Catalytic efficiency /M s-1": "catalytic_efficiency_M_s_minus1",
    "data reference doi": "doi",
}

# 科研对比字段集：17 个（2026-07-20 删除第二金属 3 字段后从 19 减至 17）。
# 与 EM、DVER 共用同一字段集（"17 个关键字段"）。
# 原始 22 字段移除 4 个（2026-07-08）：catalytic_efficiency（gold 无 Kcat 列，公式不统一
# Kcat/Km vs Vmax/Km，218 唯一值系统无法对齐）、submetal_type（gold 标注不一致，B3 主副
# 金属颠倒无法精准修复）、submetal_valence（同 submetal_type，填充率仅 34.7%）。
# 保留 metal_type(填充率100%)/metal_valence(96%)/metal_ratio(82%)。
# 2026-07-20 导师要求删除全部第二金属字段（submetal_ratio/type/valence），因非纳米酶领域常用。
# 详见 PROJECT_RULES.md 第十五章。
EVAL_FIELDS: tuple[str, ...] = (
    "nanozyme", "mimic_enzyme_activity",
    "doped_N", "doped_P", "doped_S", "doped_B", "doped_F",
    "metal_type", "metal_ratio", "metal_valence",
    "shape", "size_nm",
    "dispersion_medium", "buffer_ph_value", "temperature_c",
    "Km_mM", "Vmax_uM_s_minus1",
)

_STATIC_DIAGNOSTIC_FIELDS: tuple[str, ...] = (
    "nanozyme", "mimic_enzyme_activity",
    "doped_N", "doped_P", "doped_S", "doped_B", "doped_F",
    "metal_type", "metal_ratio", "metal_valence",
    "shape", "size_nm",
)
_KINETIC_BUNDLE_FIELDS: tuple[str, ...] = (
    "mimic_enzyme_activity", "buffer_ph_value", "temperature_c",
    "Km_mM", "Vmax_uM_s_minus1",
)
_KINETIC_VALUE_FIELDS: tuple[str, ...] = (
    "Km_mM", "Vmax_uM_s_minus1",
)

# 动力学失败模式诊断字段（2026-07-20 新增，D4-3）
_KINETIC_FAILURE_FIELDS: tuple[str, ...] = (
    "Km_mM", "Vmax_uM_s_minus1",
)

# ===== 比较核心（2026-08-29 T4 自 eval.py 逐字迁入，判定语义不变）=====
_NUMERIC_FIELDS = {
    "metal_ratio", "metal_valence",
    "size_nm", "buffer_ph_value", "temperature_c",
    "Km_mM", "Vmax_uM_s_minus1", "Kcat_s_minus1", "catalytic_efficiency_M_s_minus1",
}
_BINARY_FIELDS = {"doped_N", "doped_P", "doped_S", "doped_B", "doped_F"}


# 弱约束别名映射表：仅覆盖已知常见别名，不在表中的用原值（不引入强约束）
_ACTIVITY_ALIASES = {
    "sod": "superoxide dismutase",
    "pod": "peroxidase",
    "cat": "catalase",
    "gox": "glucose oxidase",
    "lope": "laccase-like",
    "oxd": "oxidase",
}
_MEDIUM_ALIASES = {
    # 醋酸缓冲液等价写法（NaAc=醋酸钠，HAc=醋酸，NaAc-HAc=醋酸缓冲液）
    "naac-hac buffer": "acetate buffer",
    "hac-naac buffer": "acetate buffer",
    "naac-hac": "acetate buffer",
    "hac-naac": "acetate buffer",
    "sodium acetate buffer": "acetate buffer",
    "na acetate buffer": "acetate buffer",
    "sodium acetate": "acetate buffer",
    "naac buffer": "acetate buffer",
    "naac": "acetate buffer",
    "acetate": "acetate buffer",
    "acetate buffer solution": "acetate buffer",
    "acetate buffer": "acetate buffer",
    # Tris 缓冲液等价写法
    "tris-hcl": "tris hcl",
    "tris/hcl buffer": "tris hcl",
    "tris-hcl buffer": "tris hcl",
    "tris hcl": "tris hcl",
    "tris-borate": "tris borate",
    "tris borate": "tris borate",
    # PBS 等价
    "pbs": "phosphate buffer",
    "pbs buffer": "phosphate buffer",
    "phosphate buffer": "phosphate buffer",
    "nah2po4 buffer": "phosphate buffer",
}
_SHAPE_ALIASES = {
    "spherical": "sphere",
    "spheroidal": "sphere",
    "sphere": "sphere",
    "rod": "nanorod",
    "nanorod": "nanorod",
    "wire": "nanowire",
    "nanowire": "nanowire",
    "tube": "nanotube",
    "nanotube": "nanotube",
    "sheet": "nanosheet",
    "nanosheet": "nanosheet",
    "nanoflake": "nanosheet",
    "flake": "nanosheet",
    "flake-like": "nanosheet",
    "plate": "nanoplate",
    "nanoplate": "nanoplate",
    "particle": "nanoparticle",
    "nanoparticle": "nanoparticle",
    # gold 拼写错误容错
    "nanodendrities": "nanodendrite",
    "nanodendrite": "nanodendrite",
    # 形貌别名扩充（2026-08-14 V6 修复：cubic/bean-like/nanostar/nanobar 等未覆盖）
    "cubic": "nanocube",
    "cube-like": "nanocube",
    "cubelike": "nanocube",
    "bean-like": "nanobean",
    "beanlike": "nanobean",
    "nanostar": "nanostar",
    "star": "nanostar",
    "nanobar": "nanobar",
    "bar": "nanobar",
}


def _normalize_alias(field: str, val: str) -> str:
    """弱约束别名归一化：映射表中有则归一化，无则返回原值。"""
    if not val:
        return val
    if field == "mimic_enzyme_activity":
        # 先查缩写映射
        if val in _ACTIVITY_ALIASES:
            return _ACTIVITY_ALIASES[val]
        # 再查 "-like" 后缀归一化（ascorbate oxidase-like → ascorbate oxidase）
        for short, full in _ACTIVITY_ALIASES.items():
            if val.startswith(short) and "like" in val:
                return full
        # 去 "-like" 后缀统一比较
        if val.endswith("-like"):
            return val[:-5].strip()
        return val
    if field == "dispersion_medium":
        return _MEDIUM_ALIASES.get(val, val)
    if field == "shape":
        return _SHAPE_ALIASES.get(val, val)
    return val


def _values_match(field: str, g, s) -> bool:
    if s in (None, "", "nan"):
        # 二进制字段（doped_*）：gold=0 且 sys=null 视为匹配（都是"未掺杂"）
        if field in _BINARY_FIELDS:
            try:
                return int(float(str(g).strip())) == 0
            except (TypeError, ValueError):
                return False
        return False
    if field in _BINARY_FIELDS:
        try:
            return int(float(str(g).strip())) == int(float(str(s).strip()))
        except (TypeError, ValueError):
            return str(g).strip().lower() == str(s).strip().lower()
    if field in _NUMERIC_FIELDS:
        try:
            return abs(float(g) - float(s)) / max(abs(float(g)), 1e-9) < 0.1
        except (TypeError, ValueError):
            return False
    gs, ss = _normalize_alias(field, str(g).lower().strip()), _normalize_alias(field, str(s).lower().strip())
    # nanozyme 字段走 align 的归一化（去后缀+Unicode 破折号归一化+去标点）
    # 修复 P3-2：原字符串路径只 lower+alias，导致 AuNp1 vs AuNP-1 判 mismatch
    # （归一化后本应都等于 aunp1，但原路径不去 -）
    if field == "nanozyme":
        gs, ss = _normalize_nanozyme_name(str(g)), _normalize_nanozyme_name(str(s))
    return gs in ss or ss in gs


def _kinetic_failure_modes(errors: list[dict]) -> dict:
    """聚合动力学字段的失败模式（2026-07-20 新增，D4-3）。

    分类：
    - missing: gold 有值但 system 输出 null（漏提取）
    - unit_error: |deviation| > 100%（单位换算错误，数量级偏差）
    - small_error: 0 < |deviation| <= 100%（数值偏差但同数量级）
    """
    modes: dict[str, dict] = {}
    for f in _KINETIC_FAILURE_FIELDS:
        f_errors = [e for e in errors if e.get("field") == f]
        missing = sum(1 for e in f_errors if e.get("type") == "field_miss")
        unit_err = sum(1 for e in f_errors if e.get("subtype") == "large_error")
        small_err = sum(1 for e in f_errors if e.get("subtype") == "small_error")
        modes[f] = {
            "missing": missing,
            "unit_error": unit_err,
            "small_error": small_err,
            "total": len(f_errors),
        }
    total_missing = sum(m["missing"] for m in modes.values())
    total_unit = sum(m["unit_error"] for m in modes.values())
    total_small = sum(m["small_error"] for m in modes.values())
    return {
        "by_field": modes,
        "summary": {
            "missing": total_missing,
            "unit_error": total_unit,
            "small_error": total_small,
            "total": total_missing + total_unit + total_small,
        },
    }


def _norm(v):
    return None if (isinstance(v, float) and pd.isna(v)) else v


def load_gold(excel_path: str) -> dict[str, list[dict]]:
    """读 gold Excel，按 DOI 索引。每行一条材料记录。

    列映射：显式 `_EXCEL_TO_FIELD` 优先；未命中显式映射的列走规范化回退
    （列名去非字母数字后小写，与 schema.FIELD_NAMES 归一化后匹配）。
    回退不覆盖显式已映射的字段（显式优先级最高）。
    """
    from schema import FIELD_NAMES

    df = pd.read_excel(excel_path)
    col_strip = {str(c).strip(): c for c in df.columns}  # 列名去尾随空格后映射到原列名
    norm_to_field = {
        re.sub(r"[^a-z0-9]", "", f.lower()): f for f in FIELD_NAMES
    }
    records: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        rec: dict = {}
        for col, field in _EXCEL_TO_FIELD.items():
            actual = col_strip.get(col)
            if actual is not None:
                rec[field] = _norm(row[actual])
        # 回退：显式映射未命中的列，按规范化列名匹配字段（不覆盖显式字段）
        for stripped, actual in col_strip.items():
            if stripped in _EXCEL_TO_FIELD:
                continue
            field = norm_to_field.get(re.sub(r"[^a-z0-9]", "", str(actual).lower()))
            if field is not None and field not in rec:
                rec[field] = _norm(row[actual])
        doi = rec.get("doi")
        if doi and str(doi).strip() not in ("", "nan"):
            records.setdefault(str(doi).strip(), []).append(rec)
    return records


def load_system(output_dir: str) -> dict[str, list[dict]]:
    """读 output 目录的 *.json（跳过评估产物与 Office 锁文件），按 DOI 索引。

    跳过：eval_report.json / manifest.json / _eval_*.json（评估缓存，非系统抽取
    结果）/ ~$ 开头的 Office 锁文件。
    """
    out: dict[str, list[dict]] = {}
    for p in Path(output_dir).glob("*.json"):
        if p.name in ("eval_report.json", "manifest.json") or \
           p.name.startswith("~$") or p.name.startswith("_eval"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        doi = data.get("doi")
        if doi:
            out[str(doi).strip()] = data.get("records", [])
    return out


_NANOZYME_SUFFIXES = ("nps", "ncs", "nanoparticles", "nanozyme", "cds", "nanosheets",
                      "nanorods", "nanotubes", "nanoflowers", "particles", "dots")

# Unicode 破折号变体（U+2013 en-dash – / U+2212 minus − 等）统一为 ASCII -
# 修复 P3-1：原字符类 [\s,\-_/@()\.] 只含 ASCII -，导致 Au–APC / Au−APC / Au-APC
# 三种破折号写法被判不同材料（acsami.7b18690 系统 Au–APC 错配到 gold Au−APC）
_NANOZYME_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2212"  # ‐ ‑ ‒ – — −


def _normalize_nanozyme_name(name: str) -> str:
    """归一化纳米酶名：小写、Unicode 破折号归一化、去常见后缀、去标点空格。

    修复（2026-07-17）：
    - P3-1：Unicode 破折号（U+2013 / U+2212 等）统一为 ASCII -，再统一去标点
    - P3-3：后缀剥离后长度 < 3 时回退保留原值，防 AuNPs → au 过短形成单向子串误匹配
    """
    import re
    s = name.lower().strip()
    for dc in _NANOZYME_DASHES:
        s = s.replace(dc, "-")
    # 去常见后缀
    for suffix in _NANOZYME_SUFFIXES:
        if s.endswith(" " + suffix):
            s = s[: -(len(suffix) + 1)]
        elif s.endswith(suffix):
            s = s[: -len(suffix)]
    stripped = re.sub(r"[\s,\-/_/@()\.]", "", s)
    # 剥离后过短则不剥后缀，重做（防 AuNPs→au 太短）
    if len(stripped) < 3:
        s2 = name.lower().strip()
        for dc in _NANOZYME_DASHES:
            s2 = s2.replace(dc, "-")
        return re.sub(r"[\s,\-/_/@()\.]", "", s2)
    return stripped


def match_record(gold_rec: dict, sys_list: list[dict]) -> dict | None:
    """按 nanozyme 名匹配系统记录（放宽版：去后缀+子串+回退字段最优）。

    匹配策略（按优先级）：
    1. 精确匹配（归一化后）— 收集所有候选
    2. 子串包含（归一化后双向）— 精确无候选时收集
    3. 回退：对所有 sys_list 调 _best_match（按字段匹配数选最优，避免回退首条
       导致的跨材料错配，2026-07-15 修复）
    4. 多条候选时按 _best_match 选最优（先 nanozyme 名精确分层，再字段匹配数）
    """
    name = str(gold_rec.get("nanozyme", "")).lower().strip()
    if not name:
        return sys_list[0] if sys_list else None
    norm_name = _normalize_nanozyme_name(name)
    # 1. 精确匹配候选
    candidates = [s for s in sys_list
                  if _normalize_nanozyme_name(str(s.get("nanozyme", ""))) == norm_name]
    # 2. 子串包含候选（精确无候选时）
    if not candidates:
        for s in sys_list:
            sn = _normalize_nanozyme_name(str(s.get("nanozyme", "")))
            if norm_name and sn and (norm_name in sn or sn in norm_name):
                candidates.append(s)
    # 3. 回退：对所有 sys_list 按字段匹配数选最优（不再取首条）
    if not candidates:
        return _best_match(gold_rec, sys_list) if sys_list else None
    if len(candidates) == 1:
        return candidates[0]
    # 4. 多条候选：按 _best_match 选最优
    return _best_match(gold_rec, candidates)


def _best_match(gold_rec: dict, candidates: list[dict]) -> dict:
    """多条同 nanozyme 候选时，先按 nanozyme 名精确度分层，再按字段匹配数选最优。

    修复（2026-07-15）：原版仅按 EVAL_FIELDS 字段匹配数选最优，但当 gold 和 sys
    都有多条不同 nanozyme 名的记录（如 Pd@Pt core-frame vs Pt hollow）时，
    评估器会把 gold Pd@Pt 错配到 sys Pt hollow。现改为先按 nanozyme 名精确匹配
    分层（归一化完全相等优先 > 子串包含 > 字段匹配数），减少跨材料错配。
    """
    gold_name = _normalize_nanozyme_name(str(gold_rec.get("nanozyme", "")))
    # 层 1：归一化 nanozyme 名完全相等
    exact = [s for s in candidates
             if _normalize_nanozyme_name(str(s.get("nanozyme", ""))) == gold_name]
    if len(exact) == 1:
        return exact[0]
    pool = exact if exact else candidates
    # Gold-compatible 主分数有意用评估字段消歧同义或不完整名称候选。
    best, best_score = pool[0], -1
    for s in pool:
        score = sum(1 for f in EVAL_FIELDS
                    if _values_match(f, gold_rec.get(f), s.get(f)))
        if score > best_score:
            best, best_score = s, score
    return best


def _build_report(stats: dict, errors: list[dict]) -> dict:
    def prf(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = round(2 * p * r / (p + r), 4) if (p + r) else 0.0
        acc = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
        return {"p": round(p, 4), "r": round(r, 4), "f1": f1, "accuracy": round(acc, 4)}
    field_level, all_tp, all_fp, all_fn = {}, 0, 0, 0
    for f, st in stats.items():
        all_tp += st["tp"]; all_fp += st["fp"]; all_fn += st["fn"]
        field_level[f] = prf(st["tp"], st["fp"], st["fn"])
    o = prf(all_tp, all_fp, all_fn)
    # macro-F1：对「有 gold 评估」（tp+fp+fn>0）的字段取逐字段 f1 未加权平均。
    # 与 micro overall.f1 口径互补：macro 等权看待稀有字段（如动力学 Km/Vmax）。
    macro_vals = [field_level[f]["f1"] for f, st in stats.items()
                  if (st["tp"] + st["fp"] + st["fn"]) > 0]
    macro_f1 = round(sum(macro_vals) / len(macro_vals), 4) if macro_vals else 0.0
    return {"overall": {"precision": o["p"], "recall": o["r"], "f1": o["f1"],
                        "accuracy": o["accuracy"], "macro_f1": macro_f1},
            "field_level": field_level, "error_cases": errors}


def evaluate(output_dir: str, gold_excel: str, fields: tuple[str, ...] | None = None,
             dois: set[str] | None = None) -> dict:
    """对齐评估：gold 用显式映射加载，字段比较复用 eval 的 _values_match / _build_report。

    变体组评估（2026-07-07）：gold 常把同材料不同条件拆成多条变体记录，系统按"一材料
    一记录"输出 1 条。评估时按 (doi, 归一化 nanozyme 名) 分组，每组逐字段比较：系统值
    若在 gold 组任一变体中匹配则算 tp（只算 1 次）。

    评估增强（2026-07-08）：
    - 零提取率 DOI 列表：sys_list 为空的 DOI
    - strict 对照：gold 组只取第一条做比较（不用 any），看宽松 vs 严格差距
    - EM（Exact Match）：记录级全字段命中的变体组占比
    - 字段分组报告：按 6 组（标识/掺杂/主金属/物理/反应条件/动力学）聚合
    - 错误偏差度：数值字段加 deviation%，subtype 细分
    - 置信区间：overall F1 的 Wilson 95% CI

    Args:
        fields: 评估字段集。None 则用 EVAL_FIELDS（18 个，默认）。
        dois: 仅评估这些 DOI（用于 30 篇固定规模评估）。None 则评估 gold 全量。
    """
    if fields is None:
        fields = EVAL_FIELDS
    sys_by_doi = load_system(output_dir)
    gold_by_doi = load_gold(gold_excel)
    if dois is not None:
        gold_by_doi = {d: v for d, v in gold_by_doi.items() if d in dois}
        sys_by_doi = {d: v for d, v in sys_by_doi.items() if d in dois}
    stats = {f: {"tp": 0, "fp": 0, "fn": 0} for f in fields}
    # strict 对照统计（gold 组只取第一条，不用 any 匹配）
    strict_stats = {f: {"tp": 0, "fp": 0, "fn": 0} for f in fields}
    errors: list[dict] = []
    matched_dois = 0
    zero_extraction_dois: list[str] = []
    total_groups = 0
    em_groups = 0  # 全字段 tp 的变体组数
    for doi, golds in gold_by_doi.items():
        sys_list = sys_by_doi.get(doi, [])
        if sys_list:
            matched_dois += 1
        else:
            zero_extraction_dois.append(doi)
        gold_groups = _group_gold_by_nanozyme(golds)
        for norm_name, group in gold_groups.items():
            total_groups += 1
            s = match_record(group[0], sys_list)
            # 字段级宽松匹配的候选集：所有 nanozyme 匹配的系统记录
            # 修复 P3-4：原 s 固定单条记录，gold group 多变体（SOD/catalase/peroxidase）
            # 时 peroxidase 的动力学数值被丢弃（msec.2018.10.008
            # 系统 peroxidase 记录有 Km/Vmax 但 align 用 SOD 记录匹配判 null）
            sys_matches = [s2 for s2 in sys_list
                           if _material_names_match(group[0].get("nanozyme", ""),
                                                    s2.get("nanozyme", ""))]
            if not sys_matches and s is not None:
                sys_matches = [s]  # nanozyme 名未精确匹配则回退到 match_record 选出的记录
            group_all_tp = True  # EM 判定
            for f in fields:
                gold_vals = []
                for g in group:
                    gv = g.get(f)
                    if isinstance(gv, str) and gv.strip() == "":
                        continue
                    if gv not in (None, "", "nan"):
                        gold_vals.append(gv)
                if not gold_vals:
                    continue
                s_val = s.get(f) if s else None
                # 宽松匹配（any gold 变体 × any 系统同 nanozyme 记录）
                matched = any(
                    _values_match(f, gv, s2.get(f))
                    for s2 in sys_matches
                    for gv in gold_vals
                    if s2.get(f) not in (None, "", "nan")
                )
                # strict 匹配（只取 gold 组第一条）
                strict_matched = s is not None and _values_match(
                    f, group[0].get(f), s_val
                )
                if matched:
                    stats[f]["tp"] += 1
                elif s_val in (None, "", "nan"):
                    stats[f]["fn"] += 1
                    errors.append(_make_error(doi, f, gold_vals[0], s_val, "field_miss"))
                else:
                    stats[f]["fp"] += 1
                    errors.append(_make_error(doi, f, gold_vals[0], s_val, "field_mismatch", _NUMERIC_FIELDS))
                # strict 统计
                if strict_matched:
                    strict_stats[f]["tp"] += 1
                elif s_val in (None, "", "nan"):
                    strict_stats[f]["fn"] += 1
                else:
                    strict_stats[f]["fp"] += 1
                if not matched:
                    group_all_tp = False
            if group_all_tp:
                em_groups += 1
    report = _build_report(stats, errors)
    strict_report = _build_report(strict_stats, [])
    # EM（Exact Match）：全字段命中的变体组占比
    report["overall"]["em"] = round(em_groups / total_groups, 4) if total_groups else 0.0
    # DVER（Document-level Valid Extraction Rate）：每篇错误字段数 ≤1 即有效
    _dver = compute_dver(errors, set(gold_by_doi.keys()))
    report["overall"]["dver"] = _dver["dver"]
    report["dver_detail"] = _dver
    # 置信区间（Wilson 95% CI for F1）
    report["overall"]["f1_ci95"] = _wilson_ci(report["overall"]["f1"], total_groups)
    # strict 对照
    report["strict_mode"] = strict_report["overall"]
    # 零提取率 DOI
    report["zero_extraction_dois"] = zero_extraction_dois
    # 字段分组报告
    report["group_level"] = _group_report(stats)
    report["coverage"] = {"gold_dois": len(gold_by_doi), "system_dois": len(sys_by_doi),
                          "matched_dois": matched_dois}
    report["eval_fields"] = list(fields)
    report["diagnostics"] = _build_diagnostics(gold_by_doi, sys_by_doi, stats)
    report["kinetic_failure_modes"] = _kinetic_failure_modes(errors)
    report["evaluation_protocol"] = {
        "overall": "gold_compatible_v1",
        "diagnostics": "identity_and_bundle_v1",
    }
    return report


_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "标识": ("nanozyme", "mimic_enzyme_activity"),
    "掺杂": ("doped_N", "doped_P", "doped_S", "doped_B", "doped_F"),
    "主金属": ("metal_type", "metal_ratio", "metal_valence"),
    "物理": ("shape", "size_nm"),
    "反应条件": ("dispersion_medium", "buffer_ph_value", "temperature_c"),
    "动力学": ("Km_mM", "Vmax_uM_s_minus1"),
}


def _group_report(stats: dict) -> dict[str, dict]:
    """按字段组聚合 P/R/F1（micro 平均：组内字段 tp/fp/fn 求和再算）。"""
    out: dict[str, dict] = {}
    for group_name, group_fields in _FIELD_GROUPS.items():
        group_stats = {f: stats[f] for f in group_fields if f in stats}
        if not group_stats:
            continue
        r = _build_report(group_stats, [])
        out[group_name] = r["overall"]
    return out


def _wilson_ci(point_est: float, n: int, z: float = 1.96) -> list[float]:
    """Wilson 二项近似 95% CI。n 太小时返回 [0,1]。"""
    if n == 0:
        return [0.0, 1.0]
    p = point_est
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def compute_dver(errors: list[dict], gold_dois: set[str]) -> dict:
    """文献级有效抽取率 DVER（Document-level Valid Extraction Rate）。

    定义：每篇论文（DOI）在评估字段集内，若「原始错误条数 ≤ 1」即视为有效抽取。
    DVER = 有效论文数 / 总论文数。

    原始错误计数口径（与既有基线 DVER=0.6667 一致）：
    - 按 (doi) 统计 field_miss + field_mismatch 的原始错误条数，同一字段在多个
      gold 变体组出错计为多条错误（与「47 处残留错误」叙述口径一致）。
    - total = 参与评估的 gold DOI 总数（含零提取），与 EM 的 total_groups 口径不同。
    - 零提取论文（无任何系统输出）其 gold 字段全部 miss → 错误数高 → 判无效。

    另提供 dver_deduped（按 (doi, field) 去重计数，每篇错误上界 = 评估字段数），
    供口径透明对照，不影响 headline。
    """
    err_count_by_doi = Counter(str(e.get("doi")) for e in errors)
    err_fields_by_doi: dict[str, set] = {}
    for e in errors:
        err_fields_by_doi.setdefault(str(e.get("doi")), set()).add(e.get("field"))
    total = len(gold_dois)
    valid = sum(1 for d in gold_dois if err_count_by_doi.get(str(d), 0) <= 1)
    valid_ded = sum(1 for d in gold_dois if len(err_fields_by_doi.get(str(d), set())) <= 1)
    return {
        "dver": round(valid / total, 4) if total else 0.0,
        "dver_deduped": round(valid_ded / total, 4) if total else 0.0,
        "valid_papers": valid,
        "invalid_papers": total - valid,
        "total_papers": total,
        "raw_error_count": sum(err_count_by_doi.values()),
        "threshold_errors_per_paper": 1,
    }


def _make_error(doi: str, field: str, gold_val, sys_val, err_type: str,
                numeric_fields: set | None = None) -> dict:
    """构造错误案例，数值字段加偏差度和 subtype。"""
    err = {"doi": doi, "field": field, "gold": gold_val, "system": sys_val, "type": err_type}
    if numeric_fields and field in numeric_fields and sys_val not in (None, "", "nan"):
        try:
            g = float(gold_val)
            s = float(sys_val)
            dev = abs(s - g) / max(abs(g), 1e-9) * 100
            err["deviation_pct"] = round(dev, 2)
            err["subtype"] = "small_error" if dev < 30 else "large_error"
        except (TypeError, ValueError):
            err["subtype"] = "wrong_type"
    elif err_type == "field_mismatch":
        err["subtype"] = "value_mismatch"
    else:
        err["subtype"] = "missing"
    return err


def _group_gold_by_nanozyme(golds: list[dict]) -> dict[str, list[dict]]:
    """按归一化 nanozyme 名分组 gold 记录。

    场景：gold 把同材料不同条件拆成多条（如 AuNP-1 在 11 种温度下的动力学）。
    分组后每组只与系统 1 条记录比较，避免重复计算。
    归一化用 _normalize_nanozyme_name（去后缀/标点/空格）。
    """
    groups: dict[str, list[dict]] = {}
    for g in golds:
        name = _normalize_nanozyme_name(str(g.get("nanozyme", "")))
        groups.setdefault(name, []).append(g)
    return groups


# 元素符号表（金属 + 无机非金属），双字符优先匹配；单字符仅保留明确元素，排除
# 易与有机修饰混淆的 A/D/E/G/H/L/M/R/T/U 等。用于同家族判定（如 CuSe vs Cu2-xSedc）。
_NANOZYME_ELEMENTS = (
    "Se", "Cu", "Au", "Ag", "Fe", "Co", "Mn", "Pt", "Pd", "Ce", "Zn", "Ni",
    "Bi", "Sn", "Pb", "Sb", "In", "Ga", "Ge", "Mo", "Ru", "Rh", "Ir", "Os",
    "Re", "Hf", "Nb", "Ta", "Te", "Po", "As", "Cd", "Hg", "Tl", "Be", "Mg",
    "Ca", "Sr", "Ba", "Li", "Na", "Al", "Si", "Sc", "La", "Pr", "Nd", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Ti", "Cr",
    "S", "O", "N", "P", "C", "B", "F", "I", "K", "V", "W", "Y",
)


def _extract_element_set(name: str) -> frozenset[str]:
    """从 nanozyme 名提取元素符号集合（金属+无机非金属）。

    先剥离括号内容（有机修饰如 GSH/BSA）和纳米粒子后缀（NPs/NFs 等），再用贪心
    正则按元素符号表（双字符优先）匹配。用于同家族判定（如 CuSe 与 Cu2-xSedc
    均含 Cu+Se），归一化后不互为子串的化学计量比变体场景。
    """
    import re
    s = str(name)
    s = re.sub(r"\([^)]*\)", "", s)  # 剥离括号内有机修饰
    low = s.lower()
    for suf in _NANOZYME_SUFFIXES:
        if low.endswith(" " + suf):
            s = s[: -(len(suf) + 1)]
            break
        if low.endswith(suf):
            s = s[: -len(suf)]
            break
    pat = re.compile("|".join(_NANOZYME_ELEMENTS))
    elems: set[str] = set()
    pos = 0
    while pos < len(s):
        m = pat.match(s, pos)
        if m:
            elems.add(m.group(0))
            pos = m.end()
        else:
            pos += 1
    return frozenset(elems)


def _material_names_match(gold_name: str, system_name: str) -> bool:
    gold_norm = _normalize_nanozyme_name(str(gold_name))
    system_norm = _normalize_nanozyme_name(str(system_name))
    if gold_norm and system_norm and (
        gold_norm == system_norm or gold_norm in system_norm or system_norm in gold_norm
    ):
        return True
    # P3-5 元素集合同家族判定（保守：集合大小≥2 且完全相等）。
    # 解决化学计量比变体（CuSe vs Cu2-xSedc/Cu3Se2）归一化后不互为子串的错配：
    # 两者元素集合均为 {Cu,Se}。集合大小≥2 限制避免单金属体系（AuNPs vs Au-APC）
    # 误合并——单金属集合大小为 1 不触发本规则，回退到上方子串匹配或 _best_match。
    gold_elems = _extract_element_set(gold_name)
    system_elems = _extract_element_set(system_name)
    return len(gold_elems) >= 2 and gold_elems == system_elems


# EC 大类 → 子类集合（gold 标注习惯有时标大类如 hydrolase，系统标具体子类如
# phosphodiesterase）。用于 _bundle_matches 诊断层宽松匹配，不影响 eval._values_match
# 主 F1 比较（§15.3 合规：仅诊断函数，不改比较逻辑）。
_ACTIVITY_HYPERNYMS: dict[str, set[str]] = {
    "hydrolase": {"phosphodiesterase", "esterase", "protease", "lipase", "nuclease",
                  "glycosidase", "peptidase", "phosphatase", "dnase", "rnase"},
    "oxidoreductase": {"oxidase", "peroxidase", "catalase", "superoxide dismutase",
                       "ferroxidase", "glucose oxidase"},
}


def _activity_match(gold_act, sys_act) -> bool:
    """activity 匹配：精确匹配或 gold 标大类时容忍系统标子类（诊断层宽松）。"""
    if _values_match("mimic_enzyme_activity", gold_act, sys_act):
        return True
    ga = str(gold_act or "").lower().strip()
    sa = str(sys_act or "").lower().strip()
    return ga in _ACTIVITY_HYPERNYMS and sa in _ACTIVITY_HYPERNYMS[ga]


def _bundle_matches(gold: dict, system: dict) -> bool:
    if not _material_names_match(gold.get("nanozyme", ""), system.get("nanozyme", "")):
        return False
    fields = [
        field for field in _KINETIC_BUNDLE_FIELDS
        if gold.get(field) not in (None, "", "nan")
    ]
    for field in fields:
        if field == "mimic_enzyme_activity":
            if not _activity_match(gold.get(field), system.get(field)):
                return False
        elif not _values_match(field, gold.get(field), system.get(field)):
            return False
    return True


def _maximum_bundle_matches(golds: list[dict], systems: list[dict]) -> int:
    edges = {
        gold_index: [
            system_index for system_index, system in enumerate(systems)
            if _bundle_matches(gold, system)
        ]
        for gold_index, gold in enumerate(golds)
    }
    assigned: dict[int, int] = {}

    def assign(gold_index: int, seen: set[int]) -> bool:
        for system_index in edges[gold_index]:
            if system_index in seen:
                continue
            seen.add(system_index)
            if system_index not in assigned or assign(assigned[system_index], seen):
                assigned[system_index] = gold_index
                return True
        return False

    return sum(assign(index, set()) for index in range(len(golds)))


def _build_diagnostics(gold_by_doi: dict, sys_by_doi: dict, stats: dict) -> dict:
    family_total = family_matched = unknown = system_total = 0
    bundle_total = bundle_matched = 0
    for doi, golds in gold_by_doi.items():
        systems = sys_by_doi.get(doi, [])
        groups = _group_gold_by_nanozyme(golds)
        family_total += len(groups)
        family_matched += sum(
            any(_material_names_match(group[0].get("nanozyme", ""), s.get("nanozyme", ""))
                for s in systems)
            for group in groups.values()
        )
        kinetic_golds = [
            gold for gold in golds
            if any(gold.get(field) not in (None, "", "nan") for field in _KINETIC_VALUE_FIELDS)
        ]
        bundle_total += len(kinetic_golds)
        bundle_matched += _maximum_bundle_matches(kinetic_golds, systems)
    for doi, systems in sys_by_doi.items():
        golds = gold_by_doi.get(doi, [])
        system_total += len(systems)
        unknown += sum(
            not any(_material_names_match(g.get("nanozyme", ""), s.get("nanozyme", ""))
                    for g in golds)
            for s in systems
        )
    static_stats = {field: stats[field] for field in _STATIC_DIAGNOSTIC_FIELDS if field in stats}
    static_overall = _build_report(static_stats, [])["overall"] if static_stats else {}
    return {
        "material_family_coverage": _rate("matched", family_matched, family_total),
        "static_field_compatibility": static_overall,
        "kinetic_bundle_match_rate": _rate("matched", bundle_matched, bundle_total),
        "unknown_candidate_rate": _rate("unknown", unknown, system_total),
    }


def _rate(label: str, value: int, total: int) -> dict:
    return {label: value, "total": total, "rate": round(value / total, 4) if total else 0.0}


def main() -> None:
    if len(sys.argv) < 3:
        print("用法: python -m workbench.align <output_dir> <gold_excel> [--all-fields]")
        sys.exit(1)
    fields = None
    if "--all-fields" in sys.argv:
        from schema import FIELD_NAMES
        fields = FIELD_NAMES
    report = evaluate(sys.argv[1], sys.argv[2], fields)
    # 评估报告输出到 评估output/ 目录（避免与 output/ 提取结果混淆）
    eval_out = Path("评估output")
    eval_out.mkdir(parents=True, exist_ok=True)
    out_file = eval_out / "eval_report.json"
    out_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"总体 P/R/F1/Accuracy/EM/DVER: {report['overall']}")
    print(f"DVER 明细: {report['dver_detail']}")
    print(f"strict 模式 P/R/F1: {report['strict_mode']}")
    print(f"覆盖: {report['coverage']}")
    print(f"零提取率 DOI: {len(report['zero_extraction_dois'])} 个")
    print(f"字段分组: {report['group_level']}")
    print(f"错误案例: {len(report['error_cases'])} 条")
    nfields = len(report['eval_fields'])
    field_label = "全部 26" if nfields == 26 else f"科研对比 {nfields}"
    print(f"评估字段数: {nfields}（{field_label}）")
    print(f"报告已写入: {out_file}")


if __name__ == "__main__":
    main()
