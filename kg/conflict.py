# -*- coding: utf-8 -*-
"""同条件跨文献数值冲突检测（旗舰服务，零 API、确定性）。

## 为什么这是旗舰服务

纳米酶的 Km / Vmax **脱离测定条件就不可比**。现有公开资源（AI-ZYMES、DiZyme 等）
全是扁平表，把 Km 当材料标量存，天然无法回答：

> 「同一材料、同一活性、同一底物、在**相近的 pH 与温度**下，不同文献报的 Km 差多少？」

本模块正是回答这个问题。它要求同时满足「同材料 + 同活性 + 同底物 + pH 相近 + 温度相近」
且来自 **≥2 篇不同文献**，然后比较其动力学数值。

## 规模史（诚实记录）

- **30 篇抽取产出**：满足条件的簇 **0 个**（98 条测定摊在 68 个组上，根本不存在
  两篇文献测同一材料同一条件）→ 该服务在原设计中被迫降级。
- **354 篇人工标注集（999 条测定）**：Km 簇 **10**（严重 6）｜Vmax 簇 **10**
  （严重 4、一致 3）｜Kcat 簇 **2**（严重 2）→ 服务复活。

这正好说明「条件绑定」这一设计不是空谈：只有当规模上去、且每条记录都带着 pH/温度时，
这个查询才存在。

## ⚠️ 解读红线

**本模块只负责"带完整溯源地暴露分歧"，不判定分歧原因。** Km 前十大簇的倍数
（276.78 / 73.72 / 36.71 / … / 1.41）多数**不落在 10 的整数次幂附近**，因此
「疑似单位量级错配」只是复核表里的一列**提示**（±10% 容差命中 ×10/×100/×1000），
禁止当作结论引用 —— 详见 `suspect_magnitude` 的注释。

## 判据

| 指标 | 定义 |
|---|---|
| 相对极差 | `(max - min) / median`，只看**正值** |
| 严重冲突 | 相对极差 > 100%（即最大值超过最小值的 2 倍） |
| 可疑冲突 | 30% ~ 100% |
| 一致 | < 30% |

容差沿用 KG 设计：pH ±0.2、温度 ±2℃。
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

# 容差（与 docs/plans/2026-08-30-nanozyme-kg-design.md 决策 2 一致）
PH_TOL = 0.2
T_TOL = 2.0

SEVERITY_ORDER = {"严重": 0, "可疑": 1, "一致": 2}


def _cluster(values: list[tuple[float, float]], ph_tol: float, t_tol: float
             ) -> list[list[int]]:
    """对 (ph, T) 做贪心聚类，返回若干下标簇。

    贪心而非层次聚类：条件维度样本量小（通常 <20），贪心结果稳定且可复现。
    """
    idx = sorted(range(len(values)), key=lambda i: (values[i][0], values[i][1]))
    clusters: list[list[int]] = []
    for i in idx:
        ph, t = values[i]
        placed = False
        for c in clusters:
            phs = [values[j][0] for j in c]
            ts = [values[j][1] for j in c]
            if (abs(ph - statistics.median(phs)) <= ph_tol
                    and abs(t - statistics.median(ts)) <= t_tol):
                c.append(i)
                placed = True
                break
        if not placed:
            clusters.append([i])
    return clusters


def severity_of(spread: float) -> str:
    if spread > 1.0:
        return "严重"
    if spread >= 0.3:
        return "可疑"
    return "一致"


def find_conflicts(entries: list[dict], metric: str = "km_mm",
                   ph_tol: float = PH_TOL, t_tol: float = T_TOL,
                   min_papers: int = 2) -> list[dict]:
    """检测同条件跨文献冲突。

    entries: build_wiki 的 entry 列表（内部会 `flat_values` 摊平）。
    返回按严重程度排序的冲突簇列表。
    """
    from build_wiki import flat_values  # 延迟导入，避免循环依赖

    rows = [flat_values(e) for e in entries]

    # 先按 (材料, 活性, 底物) 粗分组；活性/底物从 entry 上取（flat_values 不含）
    groups: dict[tuple[str, str, str], list[tuple[dict, dict]]] = defaultdict(list)
    for e, r in zip(entries, rows):
        if r.get(metric) is None or r["ph"] is None or r["temperature_c"] is None:
            continue
        groups[(r["mat_key"], str(e.get("act") or ""), str(e.get("sub") or ""))].append((e, r))

    out: list[dict] = []
    for (mat, act, sub), items in groups.items():
        pts = [(r["ph"], r["temperature_c"]) for _, r in items]
        for c in _cluster(pts, ph_tol, t_tol):
            sub_items = [items[i] for i in c]
            dois = {r["doi"] for _, r in sub_items if r["doi"]}
            if len(dois) < min_papers:
                continue
            vals = [r[metric] for _, r in sub_items if r[metric] is not None]
            vals = [v for v in vals if v > 0]
            if len(vals) < 2:
                continue
            med = statistics.median(vals)
            spread = (max(vals) - min(vals)) / med if med else 0.0
            out.append({
                "material": mat,
                "material_display": sub_items[0][1].get("material") or mat,
                "activity": act, "substrate": sub,
                "ph": round(statistics.median([r["ph"] for _, r in sub_items]), 2),
                "temperature_c": round(
                    statistics.median([r["temperature_c"] for _, r in sub_items]), 1),
                "metric": metric,
                "n_values": len(vals), "n_papers": len(dois),
                "min": min(vals), "max": max(vals), "median": round(med, 6),
                "spread": round(spread, 4),
                "fold": round(max(vals) / min(vals), 2) if min(vals) > 0 else None,
                "severity": severity_of(spread),
                "items": [{"doi": r["doi"], "value": r[metric], "slug": r["slug"],
                           "ph": r["ph"], "temperature_c": r["temperature_c"]}
                          for _, r in sub_items],
            })
    out.sort(key=lambda d: (SEVERITY_ORDER[d["severity"]], -d["spread"],
                            d["material"], d["activity"]))
    return out


def summarize(conflicts: list[dict]) -> dict[str, int]:
    """按严重程度计数。"""
    c: dict[str, int] = defaultdict(int)
    for x in conflicts:
        c[x["severity"]] += 1
    return {"total": len(conflicts), "严重": c["严重"], "可疑": c["可疑"], "一致": c["一致"]}


# 三个动力学指标：键 → (展示单位, 页名后缀)。顺序即编译顺序。
METRICS = ("km_mm", "vmax_um_s", "kcat_s")
METRIC_UNITS = {"km_mm": "Km (mM)", "vmax_um_s": "Vmax (uM/s)", "kcat_s": "Kcat (1/s)"}
METRIC_SLUG = {"km_mm": "km", "vmax_um_s": "vmax", "kcat_s": "kcat"}


def render_page(conflicts: list[dict], metric: str = "km_mm") -> str:
    """渲染单指标冲突检测页（vault 的 `lint/conflicts_<slug>.md`）。"""
    unit = METRIC_UNITS.get(metric, metric)
    s = summarize(conflicts)
    lines = [
        "---",
        "type: lint",
        "tags:",
        "  - lint",
        "  - conflict",
        f"metric: {metric}",
        f"n_clusters: {s['total']}",
        f"n_severe: {s['严重']}",
        "---",
        "",
        "# 同条件跨文献冲突检测",
        "",
        f"> 指标：**{unit}**｜容差：pH ±{PH_TOL}、温度 ±{T_TOL}℃",
        "> 判定「同条件」需同时满足：同材料 + 同酶活 + 同底物 + pH 相近 + 温度相近，且来自 **≥2 篇文献**。",
        "",
        f"- 同条件跨文献簇：**{s['total']}**",
        f"- 严重冲突（相对极差 >100%）：**{s['严重']}**",
        f"- 可疑冲突（30%~100%）：**{s['可疑']}**",
        f"- 基本一致（<30%）：**{s['一致']}**",
        "",
        "## 判据",
        "",
        "| 等级 | 相对极差 (max-min)/median |",
        "| --- | --- |",
        "| 严重 | > 100%（最大值超过最小值的 2 倍） |",
        "| 可疑 | 30% ~ 100% |",
        "| 一致 | < 30% |",
        "",
        "## 冲突明细",
        "",
    ]
    if not conflicts:
        lines += ["> 当前规模下未检出同条件跨文献簇。", ""]
        return "\n".join(lines)

    lines += [
        "| 等级 | 材料 | 酶活 | 底物 | pH | 温度(℃) | 篇 | 值域 | 倍数 | 相对极差 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for x in conflicts:
        rng = f"{x['min']:g} – {x['max']:g}"
        lines.append(
            f"| **{x['severity']}** | {x['material_display']} | {x['activity']} | "
            f"{x['substrate']} | {x['ph']:g} | {x['temperature_c']:g} | {x['n_papers']} | "
            f"{rng} | {x['fold']:g}× | {x['spread'] * 100:.0f}% |"
        )
    lines += ["", "## 逐条溯源", ""]
    for x in conflicts:
        lines.append(
            f"### {x['material_display']}｜{x['activity']} × {x['substrate']}"
            f"｜pH {x['ph']:g}｜{x['temperature_c']:g}℃｜{x['severity']}"
        )
        lines.append("")
        lines.append("| 文献 (DOI) | pH | 温度(℃) | 值 | 测定页 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for it in x["items"]:
            val = f"{it['value']:g}" if isinstance(it["value"], (int, float)) else "—"
            lines.append(
                f"| `{it['doi']}` | {it['ph']:g} | {it['temperature_c']:g} | {val} | "
                f"[[{it['slug']}]] |"
            )
        lines.append("")
    lines += [
        "---",
        "",
        "## 如何解读",
        "",
        "同条件跨文献的数值分歧可能来自（本系统**不做自动判定**，只负责暴露）：",
        "",
        "1. **真实的条件差异**：缓冲液种类、离子强度、底物浓度、酶量等未在本图谱中建模；",
        "2. **单位/量级误用**：文献原表的 mM 与 μM 混用、比活力与表观速率常数混淆；",
        "3. **数据处理差异**：Michaelis-Menten 拟合 vs Lineweaver-Burk 线性化；",
        "4. **材料本身的批间差异**：合成路线不同导致真实活性不同。",
        "",
        "本页所有数值均可逐条回溯到 DOI 与测定页，供人工复核。",
        "",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------ 人工复核导出

# 倍数落在 10^n 的 ±10% 内 → 提示疑似单位量级错配。
# ⚠️ 只是**提示**，不是判定：实测 10 个 Km 簇里仅 2 个落在 ×10 附近，
# 多数分歧并非整数量级差。禁止把本列当结论使用。
_MAG_STEPS = (10, 100, 1000)
_MAG_TOL = 0.10


def suspect_magnitude(fold: float | None) -> str:
    """倍数是否接近 10/100/1000 → 返回提示串（如 `×10?`），否则空串。"""
    if not fold or fold <= 0:
        return ""
    for s in _MAG_STEPS:
        if abs(fold - s) / s <= _MAG_TOL:
            return f"×{s}?"
    return ""


def review_rows(conflicts: list[dict]) -> list[dict]:
    """摊平成人工复核表的一行一簇（含逐条 DOI=值，末两列留给人工填）。"""
    rows: list[dict] = []
    for x in conflicts:
        vals = " | ".join(
            f"{it['doi']}={it['value']:g}"
            for it in x["items"] if isinstance(it.get("value"), (int, float))
        )
        rows.append({
            "指标": METRIC_UNITS.get(x["metric"], x["metric"]),
            "等级": x["severity"],
            "材料": x["material_display"],
            "酶活": x["activity"],
            "底物": x["substrate"],
            "pH": x["ph"],
            "温度(℃)": x["temperature_c"],
            "文献数": x["n_papers"],
            "数值数": x["n_values"],
            "最小": x["min"],
            "最大": x["max"],
            "中位数": x["median"],
            "倍数": x["fold"],
            "相对极差": f"{x['spread'] * 100:.0f}%",
            "疑似量级错配": suspect_magnitude(x["fold"]),
            "逐条取值(DOI=值)": vals,
            "人工复核结论": "",
            "复核备注": "",
        })
    return rows


def write_review_csv(groups: dict[str, list[dict]], path: str | Path) -> int:
    """把三指标的冲突簇写成一张人工复核表。返回行数（0 表示无簇，不写文件）。"""
    import csv

    rows: list[dict] = []
    for m in METRICS:
        rows.extend(review_rows(groups.get(m) or []))
    if not rows:
        return 0
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8-sig") as f:   # BOM：Excel 直接打开不乱码
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from build_wiki import load_papers, collect_entries  # noqa: E402

    ap = argparse.ArgumentParser(description="同条件跨文献冲突检测（零 API）")
    ap.add_argument("--records", required=True)
    ap.add_argument("--metric", default="km_mm",
                    choices=("km_mm", "vmax_um_s", "kcat_s"))
    ap.add_argument("--ph-tol", type=float, default=PH_TOL)
    ap.add_argument("--t-tol", type=float, default=T_TOL)
    args = ap.parse_args()

    papers = load_papers(Path(args.records))
    cs = find_conflicts(collect_entries(papers), metric=args.metric,
                        ph_tol=args.ph_tol, t_tol=args.t_tol)
    st = summarize(cs)
    print(f"冲突簇 {st['total']}：严重 {st['严重']} / 可疑 {st['可疑']} / 一致 {st['一致']}")
    for x in cs[:15]:
        print(f"  [{x['severity']}] {x['material_display'][:26]:<26} "
              f"{x['activity'][:12]:<12} × {x['substrate'][:8]:<8} "
              f"pH{x['ph']:<5} T{x['temperature_c']:<5} "
              f"{x['min']:g}→{x['max']:g} ({x['fold']:g}×)")
