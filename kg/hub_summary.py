# -*- coding: utf-8 -*-
"""(活性,底物) hub 的知识归纳（LLM 推断层，opt-in）。

## 定位

hub 页的「Facts」区块是**确定性表格**：每一条测定都绑定 pH/温度/方法，可逐条溯源到 DOI。
本模块在其上追加一个「知识归纳」区块，由 LLM 读表后给出跨记录的规律判断。

## 为什么必须先做统计摘要再交给 LLM

354 篇规模下，最大的 hub 有 **189 篇 / 数百条测定**。把原始表整段塞进 prompt 会：
- 超出上下文或严重稀释注意力；
- 成本随 hub 规模平方级上升；
- 让 LLM 去数数（算中位数/四分位）—— 这正是它最不可靠的地方。

因此本模块先用**确定性统计**算出分布特征（这部分零 API、可复现、可单测），
再把「摘要 + 代表性记录」交给 LLM 做**它真正擅长的**：解释规律、提出假说、标注不确定性。

## 铁律

1. **默认关闭** —— 只有显式 `--hub-summary` 才启用，保证默认编译零 API。
2. **只追加、不改写** —— 归纳块写在 `## 知识归纳（LLM 推断）` 下，绝不触碰 Facts 表格。
3. **显式标注推断** —— 页面顶部与区块内均声明为模型推断，非文献事实。
4. **失败即静默** —— 无 API / 调用异常时返回空串，不抛异常、不污染 vault。
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = """\
你是纳米酶催化动力学专家，擅长从条件绑定的动力学测定数据中归纳规律。

你将看到某个「酶活 × 底物」组合下，从多篇文献结构化提取的测定记录。
每条记录都已绑定 pH、温度与测定方法，因此**跨记录比较时你应当注意条件差异**。

严格要求：
1. 只基于给出的数据推断，不得引入外部知识充当数据结论；
2. 每条归纳必须能被给出的数据支撑或反驳，不得写无法验证的空话；
3. 明确区分「数据直接显示」与「我的推断」；
4. 不要重复罗列表格中已有的数字；
5. 主动指出样本量不足、条件混杂等限制。

输出 markdown，每条归纳用 `### ` 开头，共 3-5 条。不要写开头寒暄与总结段落。
"""

_MAX_ROWS = 25


def flatten(entries: list[dict]) -> list[dict]:
    """把 build_wiki 的 entry 摊平成本模块使用的字段字典。

    复用 `build_wiki.flat_values`，保证 wiki 编译器与 kg 模块口径完全一致。
    **幂等**：已摊平的条目（`rec` 已被解包）不会被二次摊平成空值。
    """
    from build_wiki import flat_values  # 延迟导入，避免循环依赖

    def already_flat(e: dict) -> bool:
        return "rec" not in e and "km_mm" in e

    return [e if already_flat(e) else flat_values(e) for e in entries]


def _cell(v: Any) -> str:
    """表格单元格消毒：换行/竖线会撑破 markdown 表格，必须压平。"""
    s = "—" if v is None else str(v)
    s = s.replace("\r", " ").replace("\n", " ").replace("|", "/")
    return re.sub(r"\s+", " ", s).strip() or "—"


def _nums(vals: list[Any]) -> list[float]:
    out = []
    for v in vals:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == f and f not in (float("inf"), float("-inf")):
            out.append(f)
    return out


def _q(xs: list[float], p: float) -> float | None:
    """四分位（线性插值，与 numpy 默认一致）。"""
    if not xs:
        return None
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    i = (len(s) - 1) * p
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def _orders(xs: list[float]) -> float | None:
    """跨越多少个数量级 = log10(max/min)。仅对**比率标度**的正值有意义。

    注意：pH 是对数标度、温度是区间标度，两者说"跨几个数量级"没有物理意义，
    故这两个维度一律不展示该指标（由 `show_orders` 控制）。
    """
    pos = [x for x in xs if x > 0]
    if len(pos) < 2 or min(pos) <= 0:
        return None
    return round(__import__("math").log10(max(pos) / min(pos)), 2)


def digest(entries: list[dict]) -> dict[str, Any]:
    """确定性统计摘要（零 API，可单测）。

    entries: build_wiki 的 hub entries（会被 `flatten()` 摊平）。
    """
    entries = flatten(entries)

    def col(k: str) -> list[float]:
        return _nums([e.get(k) for e in entries])

    kms, vmaxs, kcats = col("km_mm"), col("vmax_um_s"), col("kcat_s")
    phs, ts = col("ph"), col("temperature_c")

    mats: dict[str, int] = defaultdict(int)
    papers: set[str] = set()
    methods: dict[str, int] = defaultdict(int)
    for e in entries:
        m = str(e.get("material") or "").strip()
        if m:
            mats[m] += 1
        if e.get("doi"):
            papers.add(str(e["doi"]))
        me = str(e.get("method") or "").strip()
        if me:
            methods[me] += 1

    def stat(xs: list[float]) -> dict[str, Any]:
        if not xs:
            return {"n": 0}
        return {
            "n": len(xs),
            "min": round(min(xs), 6), "max": round(max(xs), 6),
            "median": round(statistics.median(xs), 6),
            "q1": round(_q(xs, 0.25) or 0.0, 6),
            "q3": round(_q(xs, 0.75) or 0.0, 6),
            "orders": _orders(xs),
        }

    top_mats = sorted(mats.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
    return {
        "n_measurements": len(entries),
        "n_papers": len(papers),
        "n_materials": len(mats),
        "top_materials": top_mats,
        "top_methods": sorted(methods.items(), key=lambda kv: (-kv[1], kv[0]))[:5],
        "km": stat(kms), "vmax": stat(vmaxs), "kcat": stat(kcats),
        "ph": stat(phs), "temperature": stat(ts),
    }


def _fmt_stat(d: dict[str, Any], unit: str, show_orders: bool = True) -> str:
    if not d.get("n"):
        return f"无数据（{unit}）"
    s = (f"n={d['n']}，中位 {d['median']:g} {unit}，"
         f"四分位 [{d['q1']:g}, {d['q3']:g}]，范围 [{d['min']:g}, {d['max']:g}]")
    if show_orders and d.get("orders"):
        s += f"，跨 {d['orders']:g} 个数量级"
    return s


def build_prompt(activity: str, substrate: str, entries: list[dict]) -> str:
    """组装 prompt：确定性摘要 + 代表性记录。"""
    rows = flatten(entries)
    d = digest(rows)
    lines = [
        f"# 组合：{activity} × {substrate}",
        "",
        "## 规模",
        f"- 测定条数：{d['n_measurements']}｜文献数：{d['n_papers']}｜材料数：{d['n_materials']}",
        "",
        "## 条件分布（确定性统计）",
        f"- pH：{_fmt_stat(d['ph'], '', show_orders=False)}",
        f"- 温度：{_fmt_stat(d['temperature'], '℃', show_orders=False)}",
        f"- 主要测定方法：{('、'.join(f'{m}({c})' for m, c in d['top_methods']) if d['top_methods'] else '未标注')}",
        "",
        "## 动力学参数分布（确定性统计）",
        f"- Km：{_fmt_stat(d['km'], 'mM')}",
        f"- Vmax：{_fmt_stat(d['vmax'], 'uM/s')}",
        f"- Kcat：{_fmt_stat(d['kcat'], '1/s')}",
        "",
        "## 涉及最多的材料",
        "、".join(f"{m}({c} 条)" for m, c in d["top_materials"]) or "—",
        "",
        f"## 代表性记录（最多 {_MAX_ROWS} 行，按材料测定条数降序）",
        "",
        "| 材料 | 方法 | pH | 温度/℃ | Km/mM | Vmax/(uM/s) | Kcat/(1/s) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    order = {m: i for i, (m, _) in enumerate(d["top_materials"])}
    rows = sorted(rows, key=lambda e: (order.get(str(e.get("material") or ""), 999),
                                       str(e.get("material") or "")))
    for e in rows[:_MAX_ROWS]:
        lines.append(
            f"| {_cell(e.get('material'))} | {_cell(e.get('method'))} | {_cell(e.get('ph'))} | "
            f"{_cell(e.get('temperature_c'))} | {_cell(e.get('km_mm'))} | "
            f"{_cell(e.get('vmax_um_s'))} | {_cell(e.get('kcat_s'))} |"
        )
    if len(rows) > _MAX_ROWS:
        lines.append(f"| … | | | | | | |（另有 {len(rows) - _MAX_ROWS} 条未列出）")
    lines += ["", "请给出 3-5 条知识归纳。"]
    return "\n".join(lines)


def summarize_hub(activity: str, substrate: str, entries: list[dict],
                  preferred_provider: str | None = None,
                  temperature: float = 0.2, max_tokens: int = 1200,
                  verbose: bool = False) -> str:
    """对单个 hub 生成归纳文本。无 API 或异常时返回空串（静默降级）。"""
    from kg import llm  # 延迟导入：默认路径不触碰 config/api_client
    if not entries:
        return ""
    text = llm.chat(SYSTEM_PROMPT, build_prompt(activity, substrate, entries),
                    preferred=preferred_provider, temperature=temperature,
                    max_tokens=max_tokens, verbose=verbose)
    return (text or "").strip()


def generate(hubs: dict[tuple[str, str], list[dict]],
             preferred_provider: str | None = None,
             limit: int | None = None, verbose: bool = True) -> dict[tuple[str, str], str]:
    """对全部 hub 生成归纳。无 API 或失败时返回空 dict（不抛异常）。"""
    from kg import llm

    if not llm.available(verbose=verbose):
        return {}
    keys = sorted(hubs.keys(), key=lambda k: (-len(hubs[k]), k))
    if limit:
        keys = keys[:limit]
    out: dict[tuple[str, str], str] = {}
    for i, k in enumerate(keys, 1):
        act, sub = k
        text = summarize_hub(act, sub, hubs[k], preferred_provider)
        if text:
            out[k] = text
        if verbose:
            print(f"  [hub-summary] {i}/{len(keys)} {act}×{sub} "
                  f"({'有' if text else '空'}，{len(hubs[k])} 条)")
    return out


def render_block(text: str) -> str:
    """把归纳文本渲染为 hub 页的「知识归纳」区块。"""
    if not text:
        return ""
    return "\n".join([
        "", "---", "",
        "## 知识归纳（LLM 推断）",
        "",
        "> ⚠️ 本节由大模型基于上方 Facts 表格推断生成，**属推断而非文献事实**。",
        "> 所有数值结论请回到 Facts 表格逐条溯源到 DOI。本节内容**不参与**确定性哈希，",
        "> 也**不回写**任何事实字段。",
        "",
        text,
        "",
    ])


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from build_wiki import load_papers  # noqa: E402

    ap = argparse.ArgumentParser(description="hub 知识归纳（需 API，默认关闭）")
    ap.add_argument("--records", required=True)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--limit", type=int, default=None, help="只处理最大的 N 个 hub")
    ap.add_argument("--dump-prompt", default=None, help="只导出 prompt 到文件，不调用 API")
    args = ap.parse_args()

    from build_wiki import collect_hub_entries  # noqa: E402
    papers = load_papers(Path(args.records))
    hubs = collect_hub_entries(papers)

    if args.dump_prompt:
        key = max(hubs, key=lambda k: len(hubs[k]))
        Path(args.dump_prompt).write_text(
            build_prompt(key[0], key[1], hubs[key]), encoding="utf-8")
        print(f"prompt 已导出（最大 hub {key[0]}×{key[1]}，{len(hubs[key])} 条）→ {args.dump_prompt}")
    else:
        res = generate(hubs, args.provider, limit=args.limit)
        print(f"生成 {len(res)} 个 hub 的归纳")
