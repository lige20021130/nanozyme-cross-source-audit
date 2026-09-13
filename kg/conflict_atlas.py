# -*- coding: utf-8 -*-
"""产出 X：条件证据冲突谱（Condition-Resolved Conflict Atlas）。

把同一 (材料, 酶活, 底物) 的动力学数值投影到 (pH, 温度) 平面，按条件距离聚类，
输出每个材料的"条件-响应点云"，供渲染与冲突审计复用。
零 API、零 GPU、确定性（相同输入 → 相同输出）。
"""
from __future__ import annotations
import pathlib
import statistics
from collections import defaultdict
from typing import Any

PH_TOL = 0.2
T_TOL = 2.0
# 温度兜底约定：聚类时缺失温度按 25.0℃ 参与坐标计算（`or 25.0`），
# 但输出 ph_points[].temperature_c 保留原始 None，便于审计还原真相。
T_FALLBACK = 25.0


def _cluster_conditions(pts: list[tuple[float, float]]) -> list[list[int]]:
    """贪心聚类 (ph, T)：与 conflict._cluster 同逻辑（复用判据，保持口径一致）。"""
    idx = sorted(range(len(pts)), key=lambda i: (pts[i][0], pts[i][1]))
    clusters: list[list[int]] = []
    for i in idx:
        ph, t = pts[i]
        placed = False
        for c in clusters:
            phs = [pts[j][0] for j in c]
            ts = [pts[j][1] for j in c]
            if (abs(ph - statistics.median(phs)) <= PH_TOL
                    and abs(t - statistics.median(ts)) <= T_TOL):
                c.append(i)
                placed = True
                break
        if not placed:
            clusters.append([i])
    return clusters


def conflict_by_condition(entries: list[dict], metric: str = "km_mm") -> list[dict]:
    """按 (材料, 酶活, 底物) 分组 → 条件聚类 → 输出点云簇。

    entry 即 build_wiki.collect_entries 产物（含 act/sub 键）。
    返回：[{"material","activity","substrate","metric","n_points",
            "ph_points":[{ph,temperature_c,value,doi,slug,provenance}，按 ph 升序]}，...]，
    按 (mat_key, activity, substrate) 排序。缺失温度聚类按 25.0、输出保留 None。
    """
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for e in entries:
        v = e.get(metric)
        if v is None or e.get("ph") is None:
            continue
        groups[(e.get("mat_key") or "", str(e.get("act") or ""),
                str(e.get("sub") or ""))].append(e)

    out: list[dict] = []
    for (mat, act, sub), items in sorted(groups.items()):
        pts = [(float(e["ph"]), float(e["temperature_c"] or T_FALLBACK)) for e in items]
        clusters = _cluster_conditions(pts)
        for c in clusters:
            if len(c) < 2:      # 单点不成谱（保留单点由 fingerprint 承担）
                continue
            sub_items = [items[i] for i in c]
            points = sorted(
                [{"ph": float(e["ph"]),
                  "temperature_c": float(e["temperature_c"]) if e.get("temperature_c") is not None else None,
                  "value": e.get(metric),
                  "doi": e.get("doi", ""), "slug": e.get("slug", ""),
                  "provenance": e.get("provenance", "")}
                 for e in sub_items],
                key=lambda p: (p["ph"], p["doi"]))
            out.append({
                "material": sub_items[0].get("material", mat),
                "mat_key": mat, "activity": act, "substrate": sub,
                "metric": metric, "n_points": len(points),
                "ph_points": points,
                "n_papers": len({p["doi"] for p in points if p["doi"]}),
            })
    out.sort(key=lambda d: (d["mat_key"], d["activity"], d["substrate"]))
    return out


# ---------------------------------------------------------------- 渲染

def render_atlas(cluster: dict, out_png: str | pathlib.Path,
                 title: str | None = None) -> bool:
    """把单个条件簇的 Km 点云渲染成 (pH vs Km, log 轴) 散点图 PNG。

    用 log10(Km) 纵轴（Km 跨数量级是常态）。点标注 DOI 后缀，便于溯源。
    确定性：相同输入产出相同字节（固定 dpi、无随机）。
    """
    import matplotlib
    matplotlib.use("Agg")                      # 零交互后端，服务器/CI 安全
    import matplotlib.pyplot as plt
    plt.rcParams["axes.unicode_minus"] = False  # 轴负号用 ASCII
    # log 轴指数负号仍走 mathtext，触发字体字形缺失警告（纯噪声）：
    # matplotlib 经 logging 写出，定向降到 ERROR 级别抑制
    import logging
    logging.getLogger("matplotlib").setLevel(logging.ERROR)

    points = cluster.get("ph_points", [])
    if not points:
        return False
    pts = [(p["ph"], p.get("value")) for p in points if p.get("value") is not None]
    if not pts:
        return False
    phs = [a for a, _ in pts]
    vals = [b for _, b in pts]
    labels = [p["doi"].split("/")[-1][:10] for p in points if p.get("value") is not None]

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    ax.scatter(phs, vals, s=60, color="#1f77b4", zorder=3)
    for x, y, lab in zip(phs, vals, labels):
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_yscale("log")
    ax.set_xlabel("pH")
    ax.set_ylabel(f"{cluster.get('metric', 'km_mm')} (log)")
    ax.set_title(title or f"{cluster['material']}｜{cluster['activity']} × {cluster['substrate']}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return True


def render_all(clusters: list[dict], out_dir: str | pathlib.Path,
               limit: int = 12) -> list[str]:
    """批量渲染前 limit 个簇（按 n_points 降序），返回已写 PNG 相对路径列表。

    文件名追加簇序号（cl#），避免同一 (材料,酶活,底物) 存在多个条件分离簇时
    同名覆盖导致静默丢图（如 ceriumoxide--oxidase--TMB 的 pH5/pH7 两簇）。
    """
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    made: list[str] = []
    for cl in sorted(clusters, key=lambda d: -d["n_points"])[:limit]:
        base = f"{cl['mat_key']}--{cl['activity']}--{cl['substrate']}--{cl['metric']}"
        fn = f"{base}--c{len(made) + 1:02d}.png"
        if render_atlas(cl, out / fn,
                        title=f"{cl['material']}｜{cl['activity']} × {cl['substrate']}"):
            made.append(fn)
    return made