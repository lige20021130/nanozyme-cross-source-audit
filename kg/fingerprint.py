# -*- coding: utf-8 -*-
"""产出 Y：条件指纹（Conditional Fingerprint）驱动材料相似性网络。

把每条材料的动力学表示成「每个 (酶活, 底物) 组件的 log(Km) 随 pH 的形状」，
再对材料两两计算功能相似度，构建"功能置换可能性"网络。
零 API、零 GPU、确定性。
"""
from __future__ import annotations
import math
import statistics
from collections import defaultdict
from pathlib import Path

import networkx as nx

PH_NEAR = 0.5          # 视为同一点云的 pH 容差
KM_EPS = 1e-6


def _log_km(v: float) -> float:
    return math.log10(max(v, KM_EPS))


def _median(vals: list[float]) -> float:
    return float(statistics.median(vals))


def condition_fingerprint(rows: list[dict], mat_key: str) -> dict:
    """某材料的条件指纹：{"act|sub": {"phs": [...], "km_log": [...]}}，按 ph 升序。

    同 pH 的多条记录先对 log(Km) 取中位数再进入指纹（确定性）。
    """
    comps: dict[str, dict[str, list]] = defaultdict(lambda: {"phs": [], "logkms": []})
    for r in rows:
        if r.get("mat_key") != mat_key or r.get("km_mm") is None:
            continue
        act = str(r.get("act") or "")
        sub = str(r.get("sub") or "")
        comps[f"{act}|{sub}"]["phs"].append(float(r["ph"]))
        comps[f"{act}|{sub}"]["logkms"].append(_log_km(float(r["km_mm"])))

    out: dict[str, dict] = {}
    for comp in comps:
        by_ph: dict[float, list] = defaultdict(list)
        for ph, lk in zip(comps[comp]["phs"], comps[comp]["logkms"]):
            by_ph[ph].append(lk)
        phs = sorted(by_ph)
        out[comp] = {"phs": phs, "km_log": [_median(by_ph[p]) for p in phs]}
    return out


def material_similarity(rows: list[dict], ph_tol: float = PH_NEAR) -> nx.Graph:
    """构建材料相似网络：同 (酶活,底物) 组件、且条件邻近的 logKm 差 <= 1.0 → 边。

    边权重 = 1 / (1 + max_logkm_diff)（0..1，越接近 1 越相似）。确定性。
    """
    mat_keys = sorted({r["mat_key"] for r in rows if r.get("mat_key")})
    fps = {mk: condition_fingerprint(rows, mk) for mk in mat_keys}
    g = nx.Graph()
    g.add_nodes_from(mat_keys)
    for i, a in enumerate(mat_keys):
        for b in mat_keys[i + 1:]:
            fa, fb = fps[a], fps[b]
            if not fa or not fb:
                continue
            diffs: list[float] = []
            for comp in fa:
                if comp not in fb:
                    continue
                # 对 A 的每个 pH 点，找 B 中 pH 最接近的点，比较 logKm 差
                for p_a, lk_a in zip(fa[comp]["phs"], fa[comp]["km_log"]):
                    best_diff = None
                    best_lk = None
                    for p_b, lk_b in zip(fb[comp]["phs"], fb[comp]["km_log"]):
                        d_ph = abs(p_a - p_b)
                        if d_ph <= ph_tol and (best_diff is None or d_ph < best_diff):
                            best_diff = d_ph
                            best_lk = abs(lk_a - lk_b)
                    if best_lk is not None:
                        diffs.append(best_lk)
            if not diffs:
                continue
            d = max(diffs)
            if d <= 1.0:                     # 同条件下 logKm 差 <= 1 数量级
                g.add_edge(a, b, weight=round(1.0 / (1.0 + d), 4),
                           max_logkm_diff=round(d, 4),
                           shared_components=len(diffs))
    return g


def write_graphml(g: nx.Graph, path: str | Path) -> None:
    nx.write_graphml(g, str(path))