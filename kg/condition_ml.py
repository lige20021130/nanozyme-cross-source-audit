# -*- coding: utf-8 -*-
"""条件条件化预测（M5/M6）：材料×条件 → log10(Km) 的确定性评估管线。

设计（对齐 spec §4 阶段 B，M1 主干 + 条件轴显式化）：
- M1 baseline：RandomForest（对齐 DiZyme 的随机森林做法，R²=0.75 对照线）。
- 条件轴：pH / 温度作为**显式连续特征**进入全局模型（组内点稀疏 → 全局模型撑曲面）。
- 评估：**按 DOI 分组的 K 折**（同文献记录永不跨折），OOF R² / RMSE。
- 消融：`with_conditions=False` 对比材料-only 基线，量化"条件轴"贡献。
- M6 外部验证：`external_split` 把训练 DOI 集合与外部库（DiZyme/nanozymenet/
  NanozymeDB）的**非重叠**行切开，测跨库泛化（见 kg/lineage.holdout_split 的
  家族级防泄漏语义，Plan 2 阶段 B 特有函数在此复用其思想）。

铁律：确定性（固定 random_seed、特征顺序稳定）；不进 .venv（sklearn 在 conda base）；
单元测试用纯构造数据，不依赖真实文件。

待办特性（不在本版）：Vmax 目标（公开库单位异构，需 _unit 语义先行）、
Kcat/Km 效率目标列、SHAP 交互项解释。
"""
from __future__ import annotations
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

# 材料属性近似描述符（周期表常量，零外部包）
ELEM_EN = {"Fe": 1.83, "Co": 1.88, "Ni": 1.91, "Cu": 1.90, "Mn": 1.55, "Pd": 2.20,
           "Pt": 2.28, "Ce": 1.12, "Au": 2.54, "Ag": 1.93, "Zn": 1.65, "Ru": 2.2,
           "Ir": 2.20, "Os": 2.2, "Bi": 2.02, "Mo": 2.16, "W": 2.36, "Ti": 1.54,
           "Zr": 1.33, "Mg": 1.31, "Al": 1.61, "Ca": 1.00, "La": 1.10, "Gd": 1.20,
           "Nd": 1.14, "Er": 1.24, "Yb": 1.1, "N": 3.04, "C": 2.55, "O": 3.44,
           "S": 2.58, "P": 2.19, "B": 2.04, "F": 3.98, "Cl": 3.16, "Si": 1.90,
           "Pr": 1.13, "Sm": 1.17, "Eu": 1.2, "Ho": 1.23, "Tm": 1.25, "Lu": 1.27,
           "Hf": 1.3, "Ta": 1.5, "Re": 1.9, "Se": 2.55, "Te": 2.1, "Cr": 1.66,
           "V": 1.63, "Sc": 1.36, "Y": 1.22, "Nb": 1.6, "Rh": 2.28, "Cd": 1.69,
           "In": 1.78, "Sn": 1.96, "Sb": 2.05, "Ba": 0.89, "Sr": 0.95, "K": 0.82,
           "Na": 0.93, "Li": 0.98, "H": 2.20}
ELEM_MASS = {"Fe": 55.8, "Co": 58.9, "Ni": 58.7, "Cu": 63.5, "Mn": 54.9, "Pd": 106.4,
             "Pt": 195.1, "Ce": 140.1, "Au": 197.0, "Ag": 107.9, "Zn": 65.4, "Ru": 101.1,
             "Ir": 192.2, "Os": 190.2, "Bi": 209.0, "Mo": 95.9, "W": 183.8, "Ti": 47.9,
             "Zr": 91.2, "Mg": 24.3, "Al": 27.0, "Ca": 40.1, "La": 138.9, "Gd": 157.3,
             "Nd": 144.2, "Er": 167.3, "Yb": 173.0, "N": 14.0, "C": 12.0, "O": 16.0,
             "S": 32.1, "P": 31.0, "B": 10.8, "F": 19.0, "Cl": 35.5, "Si": 28.1,
             "Pr": 140.9, "Sm": 150.4, "Eu": 152.0, "Ho": 164.9, "Tm": 168.9, "Lu": 175.0,
             "Hf": 178.5, "Ta": 180.9, "Re": 186.2, "Se": 79.0, "Te": 127.6, "Cr": 52.0,
             "V": 50.9, "Sc": 45.0, "Y": 88.9, "Nb": 92.9, "Rh": 102.9, "Cd": 112.4,
             "In": 114.8, "Sn": 118.7, "Sb": 121.8, "Ba": 137.3, "Sr": 87.6, "K": 39.1,
             "Na": 23.0, "Li": 6.9, "H": 1.0}

# 特征列常量（顺序即特征向量顺序，保持确定性）
CONDITION_FEATURES = ["ph", "temperature_c"]
MATERIAL_FEATURES = ["mat_enc", "size_nm", "metal_en", "metal_mass", "metal_ratio"]
EXPERIMENTAL_FEATURES = ["act", "sub"]


def feature_names(row: dict) -> list[str]:
    """一轮行 → 特征名（其实只依赖 schema 常量；保留参数以便测试对齐）。"""
    _ = row
    return MATERIAL_FEATURES + EXPERIMENTAL_FEATURES + CONDITION_FEATURES


def _fnum(row: dict, key: str) -> float | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _metal_attr(row: dict, attr: dict[str, float]) -> float:
    """按 metal_type（可能含多元素 'Cu-Pd'，取首个）取近似属性；缺省回退统计中值。"""
    mt = str(row.get("metal_type") or "")
    sym = mt.split("-")[0].strip() if mt else ""
    return attr.get(sym, 1.8)


def to_features(row: dict, mat_encoder: dict[str, float], default: float = 1.8,
              with_conditions: bool = True) -> list[float]:
    """一条 FlatRecord 行 → 数值特征向量（确定性）。

    mat_encoder: 材料名 → 平滑目标 log10(Km) 编码（训练折内 fit、test 折 lookup；
    无泄漏见 run_experiment）。离散酶活/底物在 _encode 层 one-hot，这里只放标头布尔。
    """
    return [
        _mat_enc(row, mat_encoder, default),
        _fnum(row, "size_nm") or 0.0,
        _metal_attr(row, ELEM_EN),
        _metal_attr(row, ELEM_MASS),
        _fnum(row, "metal_ratio") or 0.0,
        float(str(row.get("mimic_enzyme_activity") or "").strip().lower() == "peroxidase" or 0),
        float(str(row.get("kinetic_substrate") or "").strip().upper() in ("TMB", "ABTS", "OPD") or 0),
    ] + [float(_fnum(row, "buffer_ph_value") or 0.0) if with_conditions else 0.0,
         float(_fnum(row, "temperature_c") or 0.0) if with_conditions else 0.0]


def _target(row: dict) -> float:
    """目标 = log10(Km/mM)；Km 非正值 → 抛错（上游应过滤）。"""
    km = float(row["Km_mM"])
    return math.log10(km)


def _usable(rows: list[dict], with_conditions: bool) -> list[dict]:
    if with_conditions:
        return [r for r in rows if r.get("buffer_ph_value") is not None
                and r.get("temperature_c") is not None and r.get("Km_mM") is not None
                and float(r["Km_mM"]) > 0]
    return [r for r in rows if r.get("Km_mM") is not None and float(r["Km_mM"]) > 0]


def grouped_kfold(rows: list[dict], n_splits: int = 5, random_seed: int = 0) -> list[tuple[list[dict], list[dict]]]:
    """按 DOI 分组折：同一文献记录永不跨折。确定性（排序后轮转编号 + 固定种子洗牌）。"""
    by_doi: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by_doi.setdefault(str(r.get("doi") or f"na{i}"), []).append(i)
    dois = sorted(by_doi)
    rng = np.random.RandomState(random_seed)
    perm = rng.permutation(len(dois))
    folds: list[list[str]] = [[] for _ in range(n_splits)]
    for pos, doi_idx in enumerate(perm):
        folds[pos % n_splits].append(dois[doi_idx])
    out = []
    for k in range(n_splits):
        test_idx = {i for d in folds[k] for i in by_doi[d]}
        train = [r for j, r in enumerate(rows) if j not in test_idx]
        test = [r for j, r in enumerate(rows) if j in test_idx]
        out.append((train, test))
    return out


def _encode(rows: list[dict], cols: list[str]) -> np.ndarray:
    """对字符串列（act/sub）做确定性 one-hot，返回 [n, k]。"""
    uniq: dict[str, list[str]] = {}
    for r in rows:
        for c in cols:
            s = str(r.get(c) or "na")
            if s not in uniq.get(c, []):
                uniq.setdefault(c, []).append(s)
    for c in cols:
        uniq[c] = sorted(uniq[c])
    mat = []
    for r in rows:
        vec: list[float] = []
        for c in cols:
            s = str(r.get(c) or "na")
            vec += [1.0 if u == s else 0.0 for u in uniq[c]]
        mat.append(vec)
    return np.array(mat, dtype=float)


def target_encode_materials(rows: list[dict], smoothing: float = 5.0) -> dict[str, float]:
    """材料名 → log10(Km) 平滑样本均值（确定性）。

    仅用给定行集统计（训练折内调用，**绝不**混入测试折行 → 无目标泄漏）。
    smoothing：平滑强度（越大越往全局均值收缩，抑制稀有材料过拟合）。
    """
    from collections import defaultdict
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        m = str(r.get("nanozyme") or "na")
        sums[m] += _target(r)
        counts[m] += 1
    global_mean = sum(sums.values()) / max(1, sum(counts.values()))
    enc: dict[str, float] = {}
    for m in counts:
        n = counts[m]
        local = sums[m] / n
        # 平滑：样本少 → 更多收缩向全局均值
        smooth = smoothing / (smoothing + n)
        enc[m] = local * (1 - smooth) + global_mean * smooth
    return enc


def _mat_enc(row: dict, encoder: dict[str, float], default: float) -> float:
    return encoder.get(str(row.get("nanozyme") or "na"), default)


def _build_matrix(rows: list[dict], encoder: dict[str, float], default: float,
                  with_conditions: bool = True) -> np.ndarray:
    """把一行行编码成特征矩阵（material 编码 + 连续描述符 + act/sub one-hot + 条件列）。"""
    enc_rows = [to_features(r, encoder, default, with_conditions) for r in rows]
    return np.hstack([np.array(enc_rows), _encode(rows, EXPERIMENTAL_FEATURES)])


def material_level_eval(rows: list[dict], n_splits: int = 5, random_seed: int = 0,
                        n_estimators: int = 200) -> dict[str, Any]:
    """材料级基线：每一 (doi, 材料) 原子 → 中位 log10(Km)，在原子集上做分组 K 折。

    对齐 DiZyme 的对照口径（每材料一个 Km、R²=0.75）——本工作在此口径上的
    才是与 DiZyme 直接可比的数字；行级条件残差报告另列，避免口径混用。
    """
    from sklearn.ensemble import RandomForestRegressor
    # 按 (doi, 材料) 原子聚组：目标=中位 logKm；条件/材料属性取组内中位数（代表性行）
    atom_map: dict[tuple, list[dict]] = {}
    for r in _usable(rows, True):
        key = (str(r.get("doi") or ""), str(r.get("nanozyme") or ""))
        atom_map.setdefault(key, []).append(r)
    atom_rows: list[dict] = []
    for (doi, nanozyme), items in atom_map.items():
        med = lambda key, default=None: statistics.median(
            [float(it[key]) for it in items if it.get(key) is not None]
        ) if any(it.get(key) is not None for it in items) else default
        tvals = [_target(it) for it in items]           # 在 log 域取中位，避免 10** 溢出
        med_t = statistics.median(tvals)
        atom_rows.append({
            "doi": doi, "nanozyme": nanozyme,
            "Km_mM": 10 ** med_t,
            "buffer_ph_value": med("buffer_ph_value"),
            "temperature_c": med("temperature_c"),
            "mimic_enzyme_activity": items[0].get("mimic_enzyme_activity", "peroxidase"),
            "kinetic_substrate": items[0].get("kinetic_substrate", "TMB"),
            "kinetic_method": None, "metal_type": items[0].get("metal_type"),
            "size_nm": med("size_nm"), "metal_ratio": med("metal_ratio"),
        })
    if len(atom_rows) < n_splits * 2:
        return {"n_atoms": len(atom_rows), "r2": float("nan"), "rmse_log10_km": float("nan")}
    folds = grouped_kfold(atom_rows, n_splits=n_splits, random_seed=random_seed)
    y_all, pred_all = [], []
    for train, test in folds:
        enc = target_encode_materials(train)
        gmean = statistics.mean([_target(r) for r in train])
        Xtr = _build_matrix(train, enc, gmean, True)
        Xte = _build_matrix(test, enc, gmean, True)
        m = RandomForestRegressor(n_estimators=n_estimators, random_state=random_seed,
                                  min_samples_leaf=2, max_features=0.6, n_jobs=1)
        m.fit(Xtr, np.array([_target(r) for r in train]))
        y_all += [_target(r) for r in test]
        pred_all += [float(p) for p in m.predict(Xte)]
    yp, yt = np.array(pred_all), np.array(y_all)
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"n_atoms": len(atom_rows), "r2": r2,
            "rmse_log10_km": float(np.sqrt(ss_res / len(yt)))}


def run_experiment(rows: list[dict], n_splits: int = 5, random_seed: int = 0,
                   with_conditions: bool = True, n_estimators: int = 200) -> dict[str, Any]:
    """分组 K 折 OOF 评估。with_conditions 开关决定是否含 pH/温度两列（消融）。

    材料编码：每折在**训练折内**平滑目标编码（test 折材料未知时回落全局均值），
    杜绝目标泄漏；同一 DOI 从不出现在 train/test 两侧。
    """
    from sklearn.ensemble import RandomForestRegressor
    rows = _usable(rows, with_conditions)
    if len(rows) < n_splits * 2:
        raise ValueError(f"数据不足：usable={len(rows)}、folds={n_splits}")
    folds = grouped_kfold(rows, n_splits=n_splits, random_seed=random_seed)
    y_all: list[float] = []
    pred_all: list[float] = []
    importances: list[float] = []
    for train, test in folds:
        enc = target_encode_materials(train)
        global_mean = statistics.mean([_target(r) for r in train])
        Xtr = _build_matrix(train, enc, global_mean, with_conditions)
        Xte = _build_matrix(test, enc, global_mean, with_conditions)
        ytr = np.array([_target(r) for r in train])
        m = RandomForestRegressor(n_estimators=n_estimators, random_state=random_seed,
                                  min_samples_leaf=2, max_features=0.6, n_jobs=1)
        m.fit(Xtr, ytr)
        importances.append(m.feature_importances_)
        y_all += [_target(r) for r in test]
        pred_all += [float(p) for p in m.predict(Xte)]
    yp = np.array(pred_all)
    yt = np.array(y_all)
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(ss_res / len(yt)))
    return {
        "n_rows": len(rows),
        "n_folds": n_splits,
        "with_conditions": with_conditions,
        "r2_mean": r2,
        "rmse_log10_km": rmse,
        "feature_importance_mean": list(np.mean(np.array(importances), axis=0).tolist()),
        "feature_names": feature_names(rows[0]) + EXPERIMENTAL_FEATURES,
    }


def external_split(train_rows: list[dict], ext_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """M6：训练集与外部库行的**非重叠**分割（按 DOI 去重，跨库一致）。"""
    train_doi = {str(r.get("doi")) for r in train_rows if r.get("doi")}
    ext = [r for r in ext_rows if str(r.get("doi")) not in train_doi]
    return train_rows, ext


def evaluate_external(model_data: dict[str, Any], train_rows: list[dict],
                      ext_rows: list[dict], random_seed: int = 0) -> dict[str, Any]:
    """用 M1 全量重训（条件特征含 pH/温度），对非重叠外部行评 OOF。

    材料编码：训练行 fit、外部行 lookup（未知材料回落全局均值）——外部行之价值
    正在"未见材料"，此处的 R² 是对真泛化的保守估计。**同时报告 family-blocked
    结果（test 材料名不出现于 train），防止同材料跨库泄漏抬高分数。**
    """
    from sklearn.ensemble import RandomForestRegressor
    train = [r for r in _usable(train_rows, True)]
    ext_all = [r for r in ext_rows if r.get("buffer_ph_value") is not None
               and r.get("temperature_c") is not None and r.get("Km_mM") is not None
               and float(r["Km_mM"]) > 0]
    if not train or not ext_all:
        return {"ext_rows": len(ext_all), "r2": float("nan"), "rmse_log10_km": float("nan"),
                "n_train": len(train), "error": "train or ext empty"}
    enc = target_encode_materials(train)
    train_mats = set(enc)
    train_dois = {str(t.get("doi")) for t in train}
    global_mean = statistics.mean([_target(r) for r in train])
    # 三种口径：全外部集（含同 DOI/材料）→ DOI 隔离集（仅 DOI 不在训练）→ 材料家族隔离集（材料从未见）
    full = ext_all
    ext = [r for r in ext_all if str(r.get("doi")) not in train_dois]
    novel = [r for r in ext if str(r.get("nanozyme")) not in train_mats]
    Xtr = _build_matrix(train, enc, global_mean, True)
    ytr = np.array([_target(r) for r in train])
    m = RandomForestRegressor(n_estimators=200, random_state=random_seed,
                              min_samples_leaf=2, max_features=0.6, n_jobs=1)
    m.fit(Xtr, ytr)

    def _score(rows: list[dict]) -> dict:
        if not rows:
            return {"n": 0, "r2": float("nan"), "rmse_log10_km": float("nan")}
        Xte = _build_matrix(rows, enc, global_mean, True)
        yt = np.array([_target(r) for r in rows])
        yp = np.array([float(p) for p in m.predict(Xte)])
        ss_res = float(np.sum((yt - yp) ** 2))
        ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return {"n": len(rows), "r2": r2,
                "rmse_log10_km": float(np.sqrt(ss_res / len(rows)))}

    return {
        "full_ext_all": _score(full),      # 全外部集（含同 DOI/材料重叠）——传统口径
        "ext_rows": len(ext), "r2": _score(ext)["r2"],
        "rmse_log10_km": _score(ext)["rmse_log10_km"],
        "n_train": len(train),
        "novel_material": _score(novel),     # 家族隔离：train 从未见该材料
    }


def run_ablation(rows: list[dict], n_splits: int = 5, random_seed: int = 0) -> dict[str, Any]:
    """条件轴消融：含 vs 不含 pH/温度 两列（M2 显式化绑定）。"""
    with_cond = run_experiment(rows, n_splits=n_splits, random_seed=random_seed,
                               with_conditions=True)
    no_cond = run_experiment(rows, n_splits=n_splits, random_seed=random_seed,
                             with_conditions=False)
    return {"with_conditions": with_cond["r2_mean"],
            "without_conditions": no_cond["r2_mean"],
            "delta_r2": with_cond["r2_mean"] - no_cond["r2_mean"],
            "n_rows": with_cond["n_rows"]}


def main(argv: list[str] | None = None) -> int:
    """CLI：--records <dir> [--multi-records <dir>] --out <dir> [--seed N] [--no-conditions]"""
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from build_wiki import load_papers

    ap = argparse.ArgumentParser(description="M5/M6：条件条件化预测 + 多库外部验证")
    ap.add_argument("--records", required=True)
    ap.add_argument("--multi-records", help="（可选）五库 records 目录，做外部验证")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-conditions", action="store_true")
    args = ap.parse_args(argv)

    def rows_of(d: str):
        return [r for p in load_papers(Path(d)) for r in p.get("records", [])]

    core = rows_of(args.records)
    report = run_experiment(core, n_splits=5, random_seed=args.seed,
                            with_conditions=not args.no_conditions)
    atom = material_level_eval(core, n_splits=5, random_seed=args.seed)
    report["material_level"] = atom
    if not args.no_conditions:
        report["ablation"] = run_ablation(core, n_splits=5, random_seed=args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "m5_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(f"[M5] rows={report['n_rows']} R2={report['r2_mean']:.3f} "
          f"RMSE={report['rmse_log10_km']:.3f} (cond={report['with_conditions']})")
    print(f"[M5] material-level atoms={atom['n_atoms']} R2={atom['r2']:.3f} "
          f"(== DiZyme 0.75 对照口径)")
    if args.multi_records and Path(args.multi_records).exists():
        ext = rows_of(args.multi_records)
        ext_report = evaluate_external(report, core, ext, random_seed=args.seed)
        ext_atom = material_level_eval(ext, n_splits=5, random_seed=args.seed)
        ext_report["material_level"] = ext_atom
        (out / "m6_external.json").write_text(
            json.dumps(ext_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[M6] ext_rows={ext_report['ext_rows']} R2={ext_report['r2']:.3f} "
              f"RMSE={ext_report['rmse_log10_km']:.3f}")
        print(f"[M6] ext material-level atoms={ext_atom['n_atoms']} R2={ext_atom['r2']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())