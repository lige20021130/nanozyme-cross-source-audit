# -*- coding: utf-8 -*-
"""零依赖纯 Python 推理器：消费 `kg/predict_model.py` 导出的 JSON 模型。

- 决策树遍历：`feature[node] == -2` 为叶子；否则 `x[i] <= threshold` 走 left。
- 回归（GradientBoosting）得分 = init + lr × Σ 树输出；RandomForest = Σ/ n。
- 分类（RandomForest）得分 = 各树叶子类别计数 softmax 后取平均 → argmax。
- 材料身份：精确匹配 → 数字字母骨架匹配（向量化聚合编码）→ novel（回落全局均值）。

铁律：零第三方依赖（不用 numpy/sklearn，纯 list/float 计算）；确定性；
`.venv` 与 conda base 均可运行（ask/tools 侧用）。
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

_CACHE: dict[Path, dict[str, Any]] = {}


def load(model_path: str | Path) -> dict[str, Any]:
    path = Path(model_path)
    if path not in _CACHE:
        _CACHE[path] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE[path]


# ------------------------------------------------------------------ 工具

def _norm_sub(v: str) -> str:
    s = str(v or "").lower()
    if not s or s in ("nan", "none", "null"):
        return "NO_SUB"
    for token, canon in [("tmb", "TMB"), ("abts", "ABTS"), ("h2o2", "H2O2"),
                         ("opd", "OPD"), ("dopamine", "DA"), ("ascorb", "AA")]:
        if token in s:
            return canon
    return "OTHER_SUB"


def _metal_sym(material: str) -> str:
    m = re.match(r"([A-Z][a-z]?)", str(material or ""))
    return m.group(1) if m else ""


ELEM_EN = {"Fe": 1.83, "Co": 1.88, "Ni": 1.91, "Cu": 1.90, "Mn": 1.55,
           "Pd": 2.20, "Pt": 2.28, "Ce": 1.12, "Au": 2.54, "Ag": 1.93,
           "Zn": 1.65, "Ru": 2.2, "Ir": 2.20, "Os": 2.2, "Bi": 2.02,
           "Mo": 2.16, "W": 2.36, "Ti": 1.54, "Zr": 1.33, "Mg": 1.31,
           "Al": 1.61, "Ca": 1.00}
ELEM_MASS = {"Fe": 55.8, "Co": 58.9, "Ni": 58.7, "Cu": 63.5, "Mn": 54.9,
             "Pd": 106.4, "Pt": 195.1, "Ce": 140.1, "Au": 197.0, "Ag": 107.9,
             "Zn": 65.4, "Ru": 101.1, "Ir": 192.2, "Os": 190.2, "Bi": 209.0,
             "Mo": 95.9, "W": 183.8, "Ti": 47.9, "Zr": 91.2, "Mg": 24.3,
             "Al": 27.0, "Ca": 40.1}


def _onehot(value: str, cats: list[str]) -> list[float]:
    return [1.0 if value == c else 0.0 for c in cats]


def _material_entry(model: dict[str, Any], material: str) -> dict | None:
    """精确 → 骨架匹配（出口：encoder 条目或 None）。"""
    index = model["mat_index"]
    enc = index["encoder"]
    if material in enc:
        return enc[material]
    m = enc.get(str(material or ""))
    if m:
        return m
    sk = re.sub(r"[^a-z0-9]", "", str(material or "").lower())
    return index["skeleton"].get(sk) if sk else None


def _reg_features(model: dict[str, Any], material: str, act: str | None,
                  sub: str | None, ph: float, t: float,
                  size: float | None = None) -> list[float]:
    index = model["mat_index"]
    entry = _material_entry(model, material)
    enc = (entry or index["fallback"])["enc"]
    fb = index["fallback"]
    a = str(act or "").strip().lower() or "na"
    s = str(sub or "")
    base = [
        enc,
        size if size is not None else fb["median_size"],
        ELEM_EN.get(_metal_sym(material), 1.8),
        ELEM_MASS.get(_metal_sym(material), 100.0),
        fb["median_ratio"],
        float(a == "peroxidase"),
        float(s.strip().upper() in ("TMB", "ABTS", "OPD")),
        float(ph), float(t),
    ]
    return base + _onehot(a, model["act_cats"]) + _onehot(_norm_sub(s), model["sub_cats"])


def _cls_features(model: dict[str, Any], material: str, sub: str | None,
                  ph: float, t: float) -> list[float]:
    fb = model["mat_index"]["fallback"]
    sym = _metal_sym(material)
    return [
        ELEM_EN.get(sym, 1.8), ELEM_MASS.get(sym, 100.0),
        fb["median_ratio"], fb["median_valence"], fb["median_size"],
        float(ph), float(t), 0.0, 0.0, 0.0, 0.0, 0.0,
    ] + _onehot(_norm_sub(str(sub or "")), model["cls_sub_cats"])


# ------------------------------------------------------------------ 打分

def _tree_leaf(tree: dict, x: list[float]) -> int:
    node = 0
    feature, threshold, left, right = (tree["feature"], tree["threshold"],
                                       tree["left"], tree["right"])
    while feature[node] != -2:
        node = left[node] if x[feature[node]] <= threshold[node] else right[node]
    return node


def _tree_value(tree: dict, x: list[float]) -> list[float]:
    return tree["value"][_tree_leaf(tree, x)]


def predict_logkm(model: dict[str, Any], material: str, activity: str | None = None,
                  substrate: str | None = None, ph: float = 0.0, t: float = 0.0,
                  size: float | None = None) -> dict[str, Any]:
    """回归外推：log10(Km) 点值 + 预测区间 + 训练支撑条数（三段式协议 ② 的模型段）。

    `support` = 该材料在训练集出现的记录条数（0 = novel）；`seen`：
    exact / skeleton / novel 三态，供 tools.predict 决定 ②/③。
    """
    x = _reg_features(model, material, activity, substrate, ph, t, size)
    reg = model["regression"]
    init = reg.get("init", 0.0)
    lr = reg.get("learning_rate", 1.0)
    if reg["type"] == "RandomForestRegressor":
        score = statistics.mean(_tree_value(t, x)[0] for t in reg["trees"]) + init
    else:  # GradientBoostingRegressor
        score = init + lr * sum(_tree_value(t, x)[0] for t in reg["trees"])
    entry = _material_entry(model, material)
    interval = model["meta"]["prediction_interval"]
    status = "exact" if entry and material in model["mat_index"]["encoder"] \
        else "skeleton" if entry else "novel"
    return {
        "predicted_log10_km": round(score, 4),
        "predicted_km_mM": round(10 ** score, 5),
        "interval_log10": round(interval, 2),
        "km_range_mM": [round(10 ** (score - interval), 5),
                        round(10 ** (score + interval), 5)],
        "support": int(entry["n"]) if entry else 0,
        "material_status": status,
        "interval": interval,
    }


def predict_act(model: dict[str, Any], material: str, substrate: str | None = None,
                ph: float = 0.0, t: float = 0.0) -> dict[str, Any]:
    """分类头：催化类型 + 置信度。

    叶子类别分布 = 各类样本计数 / 该叶子样本总数（与 sklearn RF 的
    predict_proba 同构，比 softmax 更贴近原模型语义）。
    """
    x = _cls_features(model, material, substrate, ph, t)
    cats = model["cls_act_cats"]
    # 导出时 class_indices 是 sklearn classes_（数据中出现的类别索引）；缺失则默认全序
    cls_idx = model["classification"].get("class_indices") or list(range(len(cats)))
    probs = [0.0] * len(cats)
    n_trees = len(model["classification"]["trees"])
    for tree in model["classification"]["trees"]:
        cls_counts = _tree_value(tree, x)      # 长度 = len(cls_idx)
        total = sum(cls_counts) or 1.0
        for j, ci in enumerate(cls_idx):
            probs[ci] += cls_counts[j] / total / n_trees
    best = max(range(len(probs)), key=lambda i: probs[i])
    return {"activity": cats[best],
            "confidence": round(probs[best], 3),
            "probs": {c: round(p, 3) for c, p in zip(cats, probs)}}