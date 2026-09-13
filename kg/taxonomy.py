# -*- coding: utf-8 -*-
"""实体归类（taxonomy）：把分散的实体名收敛到「类别 + 族」两层。

## 为什么需要这一层

人工标注集有 **547 个不同的材料名 / 354 篇**，归一化后仍有 **513 个**。其中大量是
同一材料的不同变体写名（`AuNP-2` / `AuNP-3` / `AuNP-4`），或同一类材料的自由文本
（`Fe3O4` / `Fe2O3` / `Co3O4` 都属金属氧化物）。不归类的话图谱上层是一盘散沙，
「同类材料对比」这类查询根本无法表达。

## 两层设计

| 层 | 是否需 API | 做什么 | 依据 |
|---|---|---|---|
| **L0 确定性层** | 否（默认开） | 变体合并（`-N` 后缀）、酶活别名、底物受控词表 | 规则确定，可审计 |
| **L1 LLM 层** | 是（`--taxonomy` 开） | 上位类别（金属氧化物/贵金属/…）+ 同族合并建议 | 需要领域语义判断 |

**L1 的产物全部标记为 `inferred`，只写入上层「类别」页，绝不回写事实层的材料名。**

## 变体合并的安全规则（L0）

只在**剥离后缀后得到的基名本身也是集合中的真实材料名**时才合并：
- `AuNP-2` → 剥离得 `aunp`，集合中存在 `AuNP` → 合并 ✅
- `Fe3O4` → 剥离得 `fe3o`，集合中不存在 → **不合并** ✅（避免把化学式拆坏）

这条规则保证「宁可不合并，也不错合并」。
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg.bench_source import has_kinetic  # noqa: E402

# taxonomy 缓存（入库，可复现；LLM 层产物不入库）
TAXONOMY_PATH = Path(__file__).resolve().parent / "taxonomy.json"

# L1 允许输出的上位类别（固定集合，防 LLM 自由发挥导致不可控）
CATEGORIES = (
    "金属氧化物", "贵金属", "碳基材料", "单原子催化剂", "金属有机框架",
    "硫化物", "复合异质结构", "合金", "量子点", "其他",
)

# 变体后缀：归一化后分隔符已被剥离，故直接匹配尾随数字
#   AuNP-2 → aunp2 → base=aunp（集合中须真实存在 aunp 才合并）
#   Fe3O4  → fe3o4 → base=fe3o（集合中不存在 → 不合并）
#   Au0.25Pt0.75 → au025pt075 → base=au025pt（基名含数字 → 拒绝，配比编码不是变体）
_VARIANT_RE = re.compile(r"^(?P<base>.+?)(?P<idx>\d+)$")

# 基名中不得含数字：配比编码（au025pt）与化学式（fe3o4）一律排除在合并之外
_BASE_HAS_DIGIT = re.compile(r"\d")

_DEFAULT_TAXONOMY: dict[str, Any] = {
    "version": 1,
    "categories": list(CATEGORIES),
    "materials": {},   # norm_name -> {raw, count, category, family, layer}
    "activities": {},  # norm_activity -> {raw, count, category}
    "substrates": {},  # norm_substrate -> {raw, count, category}
    "llm_applied": False,
    "llm_provider": None,
}


# ------------------------------------------------------------------ L0 确定性层

def collect_entities(papers: list[dict]) -> dict[str, dict[str, dict]]:
    """从 papers 中收集材料 / 酶活 / 底物的原始取值与出现次数。"""
    mats: dict[str, dict] = {}
    acts: dict[str, dict] = {}
    subs: dict[str, dict] = {}

    def bump(table: dict[str, dict], key: str, raw: str) -> None:
        if not key:
            return
        e = table.setdefault(key, {"count": 0, "raws": set(), "dois": set()})
        e["count"] += 1
        if raw:
            e["raws"].add(raw)
        e["dois"].add(doi)

    for paper in papers:
        doi = paper.get("doi", "")
        for rec in paper.get("records", []):
            if not has_kinetic(rec):
                continue
            raw_mat = str(rec.get("nanozyme") or "").strip()
            bump(mats, _norm_name(raw_mat), raw_mat)
            raw_act = str(rec.get("mimic_enzyme_activity") or "").strip()
            bump(acts, _norm_act(raw_act), raw_act)
            raw_sub = str(rec.get("kinetic_substrate") or rec.get("substrate1") or "").strip()
            bump(subs, _norm_sub(raw_sub), raw_sub)
    return {"materials": mats, "activities": acts, "substrates": subs}


def _norm_name(s: str) -> str:
    """材料名归一化键：小写 + 去非字母数字。"""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _norm_act(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).lower().strip())


def _norm_sub(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def merge_variants(keys: set[str]) -> dict[str, str]:
    """L0 变体合并：返回 {原 key -> family key}。

    仅当剥离数字后缀后的基名本身也在集合中时才合并（安全规则，见模块 docstring）。
    """
    out: dict[str, str] = {}
    for k in sorted(keys):
        m = _VARIANT_RE.match(k)
        if not m:
            out[k] = k
            continue
        base = m.group("base")
        # 三条同时满足才合并（宁可不合并，也不错合并）：
        #   1) 基名长度 >= 3          —— 防 "au" 之类过短基名造成单向子串误匹配
        #   2) 基名本身在集合中       —— 必须是真实存在的材料名
        #   3) 基名不含数字           —— 排除配比编码（au025pt）与化学式（fe3o4）
        if (len(base) >= 3 and base in keys
                and not _BASE_HAS_DIGIT.search(base)):
            out[k] = base
        else:
            out[k] = k
    return out


def build_deterministic(papers: list[dict]) -> dict[str, Any]:
    """L0：只做确定性归类，零 API。"""
    ents = collect_entities(papers)
    tax: dict[str, Any] = json.loads(json.dumps(_DEFAULT_TAXONOMY))

    fam = merge_variants(set(ents["materials"].keys()))
    for key, e in sorted(ents["materials"].items()):
        tax["materials"][key] = {
            "raws": sorted(e["raws"])[:8],
            "count": e["count"],
            "n_papers": len(e["dois"]),
            "category": None,        # L0 不指定上位类（留给 L1）
            "family": fam.get(key, key),
            "layer": "L0",
        }
    for key, e in sorted(ents["activities"].items()):
        tax["activities"][key] = {
            "raws": sorted(e["raws"])[:8],
            "count": e["count"], "n_papers": len(e["dois"]),
            "category": None, "layer": "L0",
        }
    for key, e in sorted(ents["substrates"].items()):
        tax["substrates"][key] = {
            "raws": sorted(e["raws"])[:8],
            "count": e["count"], "n_papers": len(e["dois"]),
            "category": None, "layer": "L0",
        }
    return tax


# ------------------------------------------------------------------ L1 LLM 层

SYSTEM_PROMPT = """\
你是纳米酶材料分类专家。给定一批纳米酶材料的名称，完成两件事：

1) 为每个名称指定一个上位类别 category，必须严格从下列固定集合中选一个：
   金属氧化物、贵金属、碳基材料、单原子催化剂、金属有机框架、硫化物、复合异质结构、合金、量子点、其他

2) 把指向「同一种材料的不同变体」的名称合并为一个族 family，用最短最通用的写法作为 family 名。
   - 例：AuNP-2 / AuNP-3 → family 写 "AuNP"
   - 例：Fe3O4 与 Fe2O3 是不同材料，禁止合并
   - 只合并你确信是同一材料变体的；不确定就让它们各自成族（family 填原名）

输出格式（**逐行，不要 JSON、不要代码块、不要任何解释**）：
名称|类别|族名

每个输入名称输出一行，顺序与输入一致。示例：
AuNP-2|贵金属|AuNP
Fe3O4|金属氧化物|Fe3O4

用逐行格式而非 JSON 的理由：输出更省 token，且万一被截断，已输出的每一行仍可解析
（JSON 一旦不完整则整批作废）。
"""

# 每批材料数：推理型模型思考过程会吃 token，批次过大会触发截断。
# 逐行格式下 25 个/批 约需 1.5k 输出 token，留足余量。
BATCH = 25


def _build_batch_prompt(names: list[str]) -> str:
    """组装 user 消息（system 由 `kg.llm.chat` 单独传入，此处不再重复）。"""
    listed = "\n".join(names)
    return (f"待分类的材料名称（共 {len(names)} 个，每行一个）：\n{listed}\n\n"
            "请按 `名称|类别|族名` 逐行输出：")


# 容忍模型输出代码块包裹、序号前缀、多余空格
_LINE_RE = re.compile(r"^\s*(?:\d+[.、)]\s*)?(?P<name>.+?)\s*\|\s*"
                      r"(?P<cat>[^|]+?)\s*\|\s*(?P<fam>.+?)\s*$")


def parse_lines(text: str, valid: set[str]) -> dict[str, tuple[str, str]]:
    """解析逐行 `名称|类别|族名`，返回 {名称: (类别, 族名)}。

    逐行解析的好处：即使响应被 max_tokens 截断，已完成的行依然可用。
    """
    out: dict[str, tuple[str, str]] = {}
    truncated = "响应被截断" in (text or "")
    hits: list[tuple[str, tuple[str, str]]] = []
    for raw in (text or "").splitlines():
        line = raw.strip().strip("`")
        if not line or line.startswith(("名称", "#", "{", "}")):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        name = m.group("name").strip().strip("`")
        cat = m.group("cat").strip()
        fam = m.group("fam").strip()
        if not name:
            continue
        # 类别必须落在受控集合内，否则该行只取族名
        cat = cat if cat in valid else None
        hits.append((name, (cat, fam)))
    # 响应被 max_tokens 截断时，最后一行很可能是半截的（族名被砍），丢弃它
    if truncated and hits:
        hits = hits[:-1]
    for name, val in hits:
        out[name] = val
    return out


def apply_llm_taxonomy(tax: dict[str, Any], preferred_provider: str | None = None,
                       batch: int = BATCH, limit: int | None = None,
                       verbose: bool = True) -> dict[str, Any]:
    """L1：对材料名做上位类归类与同族合并。失败则原样返回（优雅降级）。

    limit 用于限制处理多少个材料（调试/控成本）。
    """
    from kg import llm  # 延迟导入：默认路径不触碰 config/api_client

    if not llm.available(verbose=verbose):
        return tax

    names = sorted(tax["materials"].keys())
    if limit:
        names = names[:limit]
    # 只处理尚未归类的
    todo = [n for n in names if not tax["materials"][n].get("category")]
    if not todo:
        return tax

    ok = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        raw_names = [tax["materials"][n]["raws"][0] if tax["materials"][n]["raws"] else n
                     for n in chunk]
        try:
            text = llm.chat(SYSTEM_PROMPT, _build_batch_prompt(raw_names),
                            preferred=preferred_provider,
                            temperature=0.1, max_tokens=6000, verbose=verbose)
        except Exception as e:  # 单点失败不中断整轮
            if verbose:
                print(f"  [taxonomy] 批次 {i // batch + 1} 调用失败：{e}")
            continue
        if not text:
            continue
        parsed = parse_lines(text, set(CATEGORIES))
        # 模型可能改写名称，先按原名匹配，再退化到归一化名匹配
        norm_parsed = {_norm_name(k): v for k, v in parsed.items()}
        for n, rn in zip(chunk, raw_names):
            hit = parsed.get(rn) or parsed.get(n) or norm_parsed.get(n)
            if not hit:
                continue
            cat, fam = hit
            if cat:
                tax["materials"][n]["category"] = cat
            if fam:
                tax["materials"][n]["family"] = _norm_name(fam) or tax["materials"][n]["family"]
            tax["materials"][n]["layer"] = "L1"
            ok += 1
        if verbose:
            print(f"  [taxonomy] 批次 {i // batch + 1}/{(len(todo) + batch - 1) // batch} "
                  f"完成（本批解析 {len(parsed)} 行）")
    tax["llm_applied"] = ok > 0
    tax["llm_provider"] = preferred_provider if ok else None
    if verbose:
        print(f"  [taxonomy] L1 归类完成：{ok}/{len(todo)} 个材料")
    return tax


# ------------------------------------------------------------------ 读写与渲染

def load_taxonomy(path: str | Path = TAXONOMY_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return json.loads(json.dumps(_DEFAULT_TAXONOMY))
    return json.loads(p.read_text(encoding="utf-8"))


def save_taxonomy(tax: dict[str, Any], path: str | Path = TAXONOMY_PATH) -> None:
    Path(path).write_text(json.dumps(tax, ensure_ascii=False, indent=2), encoding="utf-8")


def build(papers: list[dict], use_llm: bool = False,
          provider: str | None = None, limit: int | None = None,
          verbose: bool = True) -> dict[str, Any]:
    """完整归类流程：L0 确定性 → （可选）L1 LLM。"""
    tax = build_deterministic(papers)
    if verbose:
        fam = family_groups(tax)
        n_var = sum(len(v) for v in fam.values() if len(v) > 1)
        print(f"  [taxonomy] L0 完成：{len(tax['materials'])} 材料 / "
              f"{len(tax['activities'])} 酶活 / {len(tax['substrates'])} 底物"
              f"｜变体合并归拢 {n_var} 个材料到 {sum(1 for v in fam.values() if len(v) > 1)} 个族")
    if use_llm:
        tax = apply_llm_taxonomy(tax, provider, limit=limit, verbose=verbose)
    return tax


def category_groups(tax: dict[str, Any]) -> dict[str, list[tuple[str, dict]]]:
    """按 category 分组材料，返回 {category: [(norm_key, info), ...]}（按篇数降序）。"""
    g: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for k, v in tax["materials"].items():
        g[v.get("category") or "未归类"].append((k, v))
    for cat in g:
        g[cat].sort(key=lambda kv: (-kv[1]["n_papers"], -kv[1]["count"], kv[0]))
    return dict(g)


def family_groups(tax: dict[str, Any]) -> dict[str, list[str]]:
    """按 family 分组材料 norm_key。"""
    g: dict[str, list[str]] = defaultdict(list)
    for k, v in tax["materials"].items():
        g[v.get("family") or k].append(k)
    return {k: sorted(v) for k, v in g.items()}


def render_category_page(cat: str, members: list[tuple[str, dict]]) -> str:
    """渲染一个「类别」页（图谱上层节点）。"""
    total_papers = len({k for k, _ in members})
    lines = [
        "---",
        "type: category",
        "tags:",
        "  - category",
        f"category: {cat}",
        f"n_materials: {len(members)}",
        "---",
        "",
        f"# 类别：{cat}",
        "",
        f"- 材料数：**{len(members)}**",
        "",
        "## Facts（确定性统计）",
        "",
        "| 材料 | 原始写法 | 测定条数 | 文献数 | 族 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for k, v in members:
        raws = "、".join(f"`{r}`" for r in v["raws"][:2]) or "—"
        lines.append(f"| {k} | {raws} | {v['count']} | {v['n_papers']} | {v.get('family') or '—'} |")
    lines += ["", "## Inferred（LLM 推断）", "",
              "> 本页的 `category` 归属由 LLM 归类产生，属**推断**而非事实；",
              "> 材料名、条数、文献数仍为确定性统计。推断结果**不回写**事实层。", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="实体归类 taxonomy")
    ap.add_argument("--records", required=True, help="records 目录")
    ap.add_argument("--llm", action="store_true", help="启用 L1 LLM 归类（需 API）")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=str(TAXONOMY_PATH))
    args = ap.parse_args()

    from build_wiki import load_papers  # noqa: E402

    papers = load_papers(Path(args.records))
    tax = build(papers, use_llm=args.llm, provider=args.provider, limit=args.limit)
    save_taxonomy(tax, args.out)
    print(f"\ntaxonomy 已写出：{args.out}")
    for cat, mem in sorted(category_groups(tax).items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(mem)} 个材料")
