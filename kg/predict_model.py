# -*- coding: utf-8 -*-
"""预测模型训练 + 导出（M8-2b）：GBR 回归对标 + 催化类型分类头 → JSON。

设计（对齐 M8-2 文档 §3 B/C/D 与 §3.5 三段式协议 ②）：
- 回归：GradientBoostingRegressor 预测 log10(Km)，对标 AI-ZYMES 的 GBR（Km R²=0.648）；
  特征与 `condition_ml` 同族（材料平滑编码 + 材料属性 + act/sub + 条件轴）。
- 分类：RandomForestClassifier 预测催化类型（POD/OXD/CAT/SOD/OTHER），对标 Wei 2022 分类头；
  特征与 `workbench/ml_out/b1_probe.py` 同族。
- 评估：DOI 分组 5 折 OOF（同文献记录永不跨折）——诚实模型卡随导出写入 meta。
- 导出：sklearn 树结构序列化为 JSON（轻量），供 `.venv` 零依赖推理器 `kg/infer.py` 打分。

铁律（同 condition_ml）：确定性（固定 random_seed）；不进 .venv（sklearn 在 conda base）；
单元测试用纯构造数据，不依赖真实文件。
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

from kg.condition_ml import ELEM_EN, ELEM_MASS, grouped_kfold

# 导出配置：浅树控制 JSON 体积，分类头与 b1 探针同族但限深保体积
GBR_N_ESTIMATORS = 200
GBR_MAX_DEPTH = 3
RF_N_ESTIMATORS = 120
RF_MAX_DEPTH = 6
PREDICTION_INTERVAL = 1.3  # log10(Km) 预测区间半宽（探针实测精度量级）

# 分类底物 one-hot 顺序（与 b1_probe.norm_substrate 对齐）
CLS_SUB_CATS = ["TMB", "ABTS", "H2O2", "OPD", "DA", "AA", "OTHER_SUB", "NO_SUB"]
# 催化类型标签顺序（b1_probe.norm_label 同款）
ACT_CATS = ["POD", "OXD", "CAT", "SOD", "OTHER"]

ELEM_SYMBOLS = set(ELEM_EN)


def _fnum(row: dict, key: str) -> float | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _metal_sym(row: dict) -> str:
    """主金属符号：metal_type 优先，多库缺该字段时从材料名解析首个元素。"""
    mt = str(row.get("metal_type") or "")
    if mt and mt.lower() not in ("nan", "none", "null", "0"):
        return mt.split("-")[0].strip()
    import re
    m = re.match(r"([A-Z][a-z]?)", str(row.get("nanozyme") or ""))
    return m.group(1) if m and m.group(1) in ELEM_SYMBOLS else ""


def _norm_label(v) -> str:
    s = str(v or "").lower()
    if not s or s in ("nan", "none", "null", "unknown"):
        return "OTHER"
    if "superoxide" in s or s == "sod":
        return "SOD"
    if "catalase" in s or s == "cat":
        return "CAT"
    if "peroxidase" in s or s == "pod":
        return "POD"
    if "oxidase" in s or s == "oxd":
        return "OXD"
    return "OTHER"


def _norm_sub(row: dict) -> str:
    for k in ("kinetic_substrate", "substrate1", "substrate2"):
        v = str(row.get(k) or "").lower()
        if not v or v in ("nan", "none", "null"):
            continue
        for token, canon in [("tmb", "TMB"), ("abts", "ABTS"), ("h2o2", "H2O2"),
                             ("opd", "OPD"), ("dopamine", "DA"), ("ascorb", "AA")]:
            if token in v:
                return canon
        return "OTHER_SUB"
    return "NO_SUB"


def _km_targets(rows: list[dict]) -> list[dict]:
    """回归可用行：Km>0 且必有 pH/温度（三段式协议外推需条件）。"""
    return [r for r in rows if _fnum(r, "Km_mM") is not None
            and float(r["Km_mM"]) > 0
            and _fnum(r, "buffer_ph_value") is not None
            and _fnum(r, "temperature_c") is not None]


# ------------------------------------------------------------------ 特征

def build_mat_index(train_rows: list[dict]) -> dict[str, Any]:
    """材料平滑目标编码索引（训练折内 fit，含支撑条数 + 骨架索引）。

    返回：
      encoder: {材料名: {"enc": float, "n": int}}
      fallback: {"enc": 全局均值, "median_size": ..., "median_ratio": ..., "median_valence": ...}
    """
    import re
    from collections import defaultdict
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for r in train_rows:
        m = str(r.get("nanozyme") or "na")
        sums[m] += math.log10(float(r["Km_mM"]))
        counts[m] += 1
    global_mean = sum(sums.values()) / max(1, sum(counts.values()))
    encoder: dict[str, Any] = {}
    skeleton: dict[str, list[str]] = defaultdict(list)
    for m in counts:
        n = counts[m]
        loc = sums[m] / n
        # 平滑：样本少 → 更多收缩向全局均值（同 condition_ml）
        s = 5.0 / (5.0 + n)
        encoder[m] = {"enc": round(loc * (1 - s) + global_mean * s, 6), "n": n}
        sk = re.sub(r"[^a-z0-9]", "", str(m).lower())
        if sk:
            skeleton[sk].append(m)

    def _med(key: str):
        vals = [float(r[key]) for r in train_rows
                if _fnum(r, key) is not None and r.get(key) != 0]
        return statistics.median(vals) if vals else 0.0

    fallback = {"enc": round(global_mean, 6), "median_size": _med("size_nm"),
                "median_ratio": _med("metal_ratio"), "median_valence": _med("metal_valence")}

    sk_map: dict[str, dict[str, Any]] = {}
    for sk, mats in skeleton.items():
        enc = sum(encoder[m]["enc"] * encoder[m]["n"] for m in mats) / sum(
            encoder[m]["n"] for m in mats)
        n = sum(encoder[m]["n"] for m in mats)
        sk_map[sk] = {"enc": round(enc, 6), "n": n, "examples": mats[:5]}
    return {"encoder": encoder, "skeleton": sk_map, "fallback": fallback}


def _onehot(value: str, cats: list[str]) -> list[float]:
    return [1.0 if value == c else 0.0 for c in cats]


def regression_features(row: dict, mat_index: dict[str, Any],
                        act_cats: list[str], sub_cats: list[str]) -> list[float]:
    """回归特征向量（feature_names 顺序固定，.venv 推理器按同序打分）。"""
    entry = mat_index["encoder"].get(str(row.get("nanozyme") or "na"))
    enc = entry["enc"] if isinstance(entry, dict) else mat_index["fallback"]["enc"]
    sub = str(row.get("kinetic_substrate") or row.get("substrate1") or "na")
    base = [
        enc,
        _fnum(row, "size_nm") or mat_index["fallback"]["median_size"],
        ELEM_EN.get(_metal_sym(row), 1.8),
        ELEM_MASS.get(_metal_sym(row), 100.0),
        _fnum(row, "metal_ratio") or mat_index["fallback"]["median_ratio"],
        float(str(row.get("mimic_enzyme_activity") or "").strip().lower() == "peroxidase" or 0),
        float(str(sub).strip().upper() in ("TMB", "ABTS", "OPD") or 0),
        float(_fnum(row, "buffer_ph_value") or 0.0),
        float(_fnum(row, "temperature_c") or 0.0),
    ]
    act = str(row.get("mimic_enzyme_activity") or "na").strip().lower() or "na"
    return base + _onehot(act, act_cats) + _onehot(_norm_sub(row), sub_cats)


REGRESSION_FEATURE_NAMES = ["mat_enc", "size_nm", "metal_en", "metal_mass",
                            "metal_ratio", "is_peroxidase", "is_common_sub",
                            "ph", "temperature_c"]


def classification_features(row: dict, sub_cats: list[str]) -> list[float]:
    """分类特征向量（同 b1_probe.to_xy，with_sub=True 版）。"""
    base = [
        ELEM_EN.get(_metal_sym(row), 1.8),
        ELEM_MASS.get(_metal_sym(row), 100.0),
        _fnum(row, "metal_ratio") or 0.0,
        _fnum(row, "metal_valence") or 0.0,
        _fnum(row, "size_nm") or 0.0,
        _fnum(row, "buffer_ph_value") or 0.0,
        _fnum(row, "temperature_c") or 0.0,
        float(row.get("doped_N") or 0), float(row.get("doped_P") or 0),
        float(row.get("doped_S") or 0), float(row.get("doped_B") or 0),
        float(row.get("doped_F") or 0),
    ]
    return base + _onehot(_norm_sub(row), sub_cats)


CLASSIFICATION_FEATURE_NAMES = ["metal_en", "metal_mass", "metal_ratio",
                                "metal_valence", "size_nm", "ph",
                                "temperature_c", "doped_N", "doped_P",
                                "doped_S", "doped_B", "doped_F"]


# ------------------------------------------------------------------ 树导出

def _tree_json(tree) -> dict:
    t = tree.tree_
    return {
        "left": t.children_left.tolist(),
        "right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": t.threshold.tolist(),
        "value": t.value.reshape(t.value.shape[0], -1).tolist(),  # [n_nodes, n_outputs]
    }


def _export_estimator(model, option: str) -> dict:
    """estimator → JSON（RF/GBR 均可）。树 value 展平：[n_nodes, n_outputs]。"""
    kind = type(model).__name__
    return {
        "type": kind,
        "init": None,                                  # GBR 初始值由 fit_export 显式写入（均值）
        "learning_rate": float(getattr(model, "learning_rate", 1.0)),
        "n_estimators": len(model.estimators_),
        "trees": [_tree_json(e[0] if isinstance(e, (tuple, np.ndarray)) else e)
                  for e in model.estimators_],
    }


def _gb_init_value(y: np.ndarray) -> float:
    """GBR 初始预测值 = 训练目标均值（LeastSquares 损失下即均值）。"""
    return float(np.mean(y))


# ------------------------------------------------------------------ 评估（DOI 分组 OOF，诚实模型卡）

def _cv_regression(rows: list[dict], mat_index: dict[str, Any],
                   act_cats: list[str], sub_cats: list[str],
                   n_splits: int = 5, random_seed: int = 0) -> dict[str, Any]:
    """GBR 同配置 DOI 分组 OOF：R² / RMSE(log10 Km)。"""
    y_all, p_all = [], []
    for train, test in grouped_kfold(rows, n_splits, random_seed):
        idx = build_mat_index(train)
        Xtr = np.array([regression_features(r, idx, act_cats, sub_cats) for r in train])
        ytr = np.array([math.log10(float(r["Km_mM"])) for r in train], dtype=float)
        m = GradientBoostingRegressor(n_estimators=GBR_N_ESTIMATORS, max_depth=GBR_MAX_DEPTH,
                                      learning_rate=0.05, random_state=random_seed)
        m.fit(Xtr, ytr)
        Xte = np.array([regression_features(r, idx, act_cats, sub_cats) for r in test])
        y_all += [math.log10(float(r["Km_mM"])) for r in test]
        p_all += [float(p) for p in m.predict(Xte)]
    yp, yt = np.array(p_all), np.array(y_all)
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"n_rows": len(rows), "r2": r2,
            "rmse_log10_km": float(np.sqrt(ss_res / len(yt)))}


def _cv_classification(rows: list[dict], n_splits: int = 5,
                       random_seed: int = 0) -> dict[str, Any]:
    """RF 分类头 DOI 分组 OOF：acc / macro-F1 / 多数类基线（整数标签，同导出口径）。"""
    y_all, p_all = [], []
    for train, test in grouped_kfold(rows, n_splits, random_seed):
        Xtr = np.array([classification_features(r, CLS_SUB_CATS) for r in train])
        Xte = np.array([classification_features(r, CLS_SUB_CATS) for r in test])
        ytr = [ACT_CATS.index(_norm_label(r.get("mimic_enzyme_activity"))) for r in train]
        clf = RandomForestClassifier(n_estimators=RF_N_ESTIMATORS, max_depth=RF_MAX_DEPTH,
                                     random_state=random_seed, n_jobs=1)
        clf.fit(Xtr, ytr)
        y_all += [ACT_CATS.index(_norm_label(r.get("mimic_enzyme_activity"))) for r in test]
        p_all += list(clf.predict(Xte))
    acc = accuracy_score(y_all, p_all)
    mf1 = f1_score(y_all, p_all, average="macro", labels=[0, 1, 2, 3, 4],
                   zero_division=0)
    maj = max(Counter(y_all).values()) / len(y_all)
    return {"n_rows": len(rows), "acc": acc, "macro_f1": mf1, "majority_baseline": maj}


# ------------------------------------------------------------------ 训练 + 导出

def fit_export(rows: list[dict], out_path: str | Path,
               n_splits: int = 5, random_seed: int = 0,
               run_cv: bool = True) -> dict[str, Any]:
    """全量训练（回归 GBR + 分类 RF）并导出 JSON。返回模型 dict 摘要。

    评估口径与导出模型同配置（浅树），诚实模型卡随导出写入 meta。
    """
    reg_rows = _km_targets(rows)
    cls_rows = [r for r in rows if _metal_sym(r)]  # 分类需金属符号
    mat_index = build_mat_index(reg_rows)
    # act/sub 类别顺序在全量集上确定（sorted unique，确定性）
    act_cats = sorted({str(r.get("mimic_enzyme_activity") or "").strip().lower()
                       for r in reg_rows} - {""}) or ["na"]
    sub_cats = sorted({_norm_sub(r) for r in reg_rows}) or ["NO_SUB"]

    X = np.array([regression_features(r, mat_index, act_cats, sub_cats) for r in reg_rows])
    y = np.array([math.log10(float(r["Km_mM"])) for r in reg_rows], dtype=float)
    gbr = GradientBoostingRegressor(n_estimators=GBR_N_ESTIMATORS, max_depth=GBR_MAX_DEPTH,
                                    learning_rate=0.05, random_state=random_seed)
    gbr.fit(X, y)
    reg_export = _export_estimator(gbr, "回归")
    reg_export["init"] = _gb_init_value(y)

    Xc = np.array([classification_features(r, CLS_SUB_CATS) for r in cls_rows])
    # 训练用整数标签（对应 cls_act_cats 下标）→ sklearn classes_ 升序即索引序，
    # 导出 class_indices 供 infer 重映射，规避字符串 classes_ 排序与固定序不符
    yc = [_norm_label(r.get("mimic_enzyme_activity")) for r in cls_rows]
    yc_idx = [ACT_CATS.index(lab) for lab in yc]
    rf = RandomForestClassifier(n_estimators=RF_N_ESTIMATORS, max_depth=RF_MAX_DEPTH,
                                random_state=random_seed, n_jobs=1)
    rf.fit(Xc, yc_idx)
    cls_export = _export_estimator(rf, "分类")
    cls_export["class_indices"] = rf.classes_.tolist()

    meta: dict[str, Any] = {
        "data": {"total_rows": len(rows), "reg_rows": len(reg_rows),
                 "cls_rows": len(cls_rows), "n_materials": len(mat_index["encoder"])},
        "regression": {"model": "GradientBoostingRegressor",
                       "n_estimators": GBR_N_ESTIMATORS, "max_depth": GBR_MAX_DEPTH,
                       "evaluation": f"DOI-grouped {n_splits}-fold OOF"},
        "classification": {"model": "RandomForestClassifier",
                           "n_estimators": RF_N_ESTIMATORS, "max_depth": RF_MAX_DEPTH,
                           "evaluation": f"DOI-grouped {n_splits}-fold OOF"},
        "prediction_interval": PREDICTION_INTERVAL,
        "feature_names": {"regression": REGRESSION_FEATURE_NAMES
                          + [f"act_{c}" for c in act_cats] + [f"sub_{c}" for c in sub_cats],
                          "classification": CLASSIFICATION_FEATURE_NAMES
                          + [f"sub_{c}" for c in CLS_SUB_CATS]},
    }
    if run_cv:
        meta["regression"].update(_cv_regression(reg_rows, mat_index, act_cats, sub_cats,
                                                 n_splits, random_seed))
        meta["classification"].update(_cv_classification(cls_rows, n_splits, random_seed))

    model = {
        "model": "nanozyme-predict",
        "version": 1,
        "meta": meta,
        "act_cats": act_cats,
        "sub_cats": sub_cats,
        "cls_sub_cats": CLS_SUB_CATS,
        "cls_act_cats": ACT_CATS,
        "mat_index": mat_index,
        "regression": reg_export,
        "classification": cls_export,
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return model


def main(argv: list[str] | None = None) -> int:
    """CLI：--records <dir> [--multi-records <dir>] --out <path> [--seed N] [--no-cv]"""
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from build_wiki import load_papers

    ap = argparse.ArgumentParser(description="M8-2b：训练 + 导出预测模型（GBR 回归 + RF 分类头）")
    ap.add_argument("--records", required=True)
    ap.add_argument("--multi-records", help="（可选）五库 records 目录，DOI 去重后并入训练")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-cv", action="store_true")
    args = ap.parse_args(argv)

    def rows_of(d: str) -> list[dict]:
        return [r for p in load_papers(Path(d)) for r in p.get("records", [])]

    rows = rows_of(args.records)
    origin = ["atlas_records"]
    if args.multi_records and Path(args.multi_records).exists():
        core_dois = {str(p.get("doi") or "") for p in load_papers(Path(args.records))}
        rows += [r for r in rows_of(args.multi_records)
                 if str(r.get("doi") or "") not in core_dois]
        origin.append("multi_records(dedup)")
    model = fit_export(rows, args.out, run_cv=not args.no_cv)
    meta = model["meta"]
    print(f"[M8-2b] rows={meta['data']['total_rows']} reg={meta['data']['reg_rows']} "
          f"materials={meta['data']['n_materials']} sources={origin}")
    print(f"[M8-2b] GBR  OOF R2={meta['regression']['r2']:.3f} "
          f"RMSE={meta['regression']['rmse_log10_km']:.3f} (DOI-grouped)")
    print(f"[M8-2b] RF   OOF acc={meta['classification']['acc']:.3f} "
          f"macro-F1={meta['classification']['macro_f1']:.3f} (DOI-grouped)")
    print(f"[M8-2b] 已导出：{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())