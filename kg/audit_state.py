# -*- coding: utf-8 -*-
"""产出 Z：跨文献因果复核链（Live Audit Layer）。

把 conflict 检测/conflict_atlas 的冲突簇升级为**可追踪到 DOI 的审计状态**：
每个簇带 tier（1 直入 / 2 复核 / 3 存疑待实验）、review 标记、
争议可能原因标签（单位量级错配/方法差异/条件差异/批间差异）。

状态机（确定性，随文献增长重跑即自动更新）：
    severity == "一致"  → tier=1, review=False
    severity == "可疑"  → tier=2, review=True
    severity == "严重"  → tier=3, review=True
"""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

SEVERITY_TO_TIER = {"一致": 1, "可疑": 2, "严重": 3}
SEVERITY_ORDER = {"严重": 0, "可疑": 1, "一致": 2}


def audit_state(clusters: list[dict]) -> list[dict]:
    """给每个簇附加 tier/review/reason 标签，按严重度排序。"""
    out: list[dict] = []
    for c in clusters:
        sev = str(c.get("severity") or "")
        tier = SEVERITY_TO_TIER.get(sev, 3)
        review = tier >= 2
        fold = c.get("fold")
        tags: list[str] = []
        if isinstance(fold, (int, float)) and fold > 0:
            if any(abs(fold - step) / step <= 0.10 for step in (10, 100, 1000)):
                tags.append("单位量级错配?")
        tags.append("跨文献" if c.get("n_papers", 1) >= 2 else "同文献多测")
        cc = dict(c)
        cc.update({"tier": tier, "review": review,
                   "reason_tags": sorted(set(tags))})
        out.append(cc)
    def _spread(d: dict) -> float:
        v = d.get("spread")
        return float(v) if isinstance(v, (int, float)) else 0.0
    out.sort(key=lambda d: (SEVERITY_ORDER.get(str(d.get("severity")), 9),
                            -_spread(d), str(d.get("material", ""))))
    return out


def write_audit_csv(clusters: list[dict], path: str | Path) -> int:
    """一张人工复核 CSV：一行一簇，末两列人工填。返回行数（0=不写文件）。"""
    if not clusters:
        return 0
    rows: list[dict] = []
    for c in audit_state(clusters):
        items = " | ".join(
            f"{it.get('doi')}={it.get('value')}"
            for it in c.get("items", []) if isinstance(it.get("value"), (int, float)))
        rows.append({
            "材料": c.get("material", ""), "酶活": c.get("activity", ""),
            "底物": c.get("substrate", ""), "pH": c.get("ph"),
            "温度(℃)": c.get("temperature_c"), "指标": c.get("metric", ""),
            "等级": c.get("severity", ""), "tier": c.get("tier", ""),
            "文献数": c.get("n_papers", ""), "倍数": c.get("fold", ""),
            "疑因标签": "/".join(c.get("reason_tags", [])),
            "逐条取值(DOI=值)": items,
            "人工复核结论": "", "复核备注": "",
        })
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)