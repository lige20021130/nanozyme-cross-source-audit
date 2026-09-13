# -*- coding: utf-8 -*-
"""`--ask` 问答 agent 的工具集（检索侧零 API，全部确定性）。

## 定位

这是「基于大模型推理、消费结构化抽取产出的纳米酶知识库」的**工具层**。
大模型不直接读 PDF、也不凭记忆作答 —— 它只能通过这七个工具访问数据，
因此每一句回答都能落到具体的测定记录与 DOI 上。

## 七个工具

| 工具 | 作用 | 为什么必须有 |
|---|---|---|
| `query_structured` | 按材料/酶活/底物/pH/温度区间过滤测定 | **核心**。没有它，LLM 只能靠全文检索猜数字 |
| `search_notes` | vault 全文检索 | 找页面、找上下文 |
| `read_note` | 读单个页面 | 展开细节 |
| `graph_neighbors` | 查某个节点的邻居 | 回答「和 X 相关的有哪些」 |
| `plot_gradient` | 出条件梯度曲线 | 回答「Km 随温度怎么变」 |
| `predict` | 未知组合的 Km 预测（三段式证据分级输出） | **M8-2b**：检索优先命中→文献实测+冲突范围；未命中→模型外推+区间+支撑；支撑不足→拒给点值只给量级 |
| `write_analysis_page` | 把结论写回 vault | **再吸收**：让 agent 的产物进入 wiki |

## 安全边界

- 所有检索工具**只读**。
- `write_analysis_page` 只能写入 vault 的 `analysis/` 目录，且页面强制带
  `inferred` 标记 —— agent 的结论**绝不混入事实层**。
- 路径穿越（`../`）一律拒绝。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# 允许 agent 写入的目录（相对 vault 根）
WRITE_ROOT = "analysis"

# predict 工具外推段的最小训练支撑条数（< 此值拒给点值，仅给量级区间）
MIN_PREDICT_SUPPORT = 3


def _skeleton(name: str) -> str:
    """材料名数字字母骨架（小写，去非字母数字）：Fe3O4 与 Fe3O4 同骨架。"""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())

# JSON Schema（供 LLM function-calling；同时用于本地校验）
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "query_structured",
        "description": (
            "按条件检索条件绑定的动力学测定记录。这是回答任何数值问题的首选工具。"
            "返回每条记录的材料、酶活、底物、pH、温度、Km、Vmax、Kcat、DOI 与页面链接。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "材料名（子串匹配，如 Fe3O4、AuNP）"},
                "activity": {"type": "string", "description": "酶活类型，如 peroxidase、oxidase、catalase"},
                "substrate": {"type": "string", "description": "底物，如 TMB、H2O2、ABTS"},
                "ph_min": {"type": "number", "description": "pH 下界"},
                "ph_max": {"type": "number", "description": "pH 上界"},
                "t_min": {"type": "number", "description": "温度下界（℃）"},
                "t_max": {"type": "number", "description": "温度上界（℃）"},
                "metric": {"type": "string", "enum": ["km_mm", "vmax_um_s", "kcat_s"],
                           "description": "要求该指标非空的记录"},
                "limit": {"type": "integer", "description": "最多返回条数，默认 20"},
            },
        },
    },
    {
        "name": "search_notes",
        "description": "在 vault 的 markdown 页面中做全文检索，返回命中的文件路径与上下文片段。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索词"},
                "limit": {"type": "integer", "description": "最多返回条数，默认 10"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_note",
        "description": "读取 vault 中某个页面的完整内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对 vault 根的路径，如 measurements/xxx.md"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "graph_neighbors",
        "description": "列出某个页面的出链（wikilink）与入链，用于回答「X 与什么相关」。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对 vault 根的页面路径"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "plot_gradient",
        "description": (
            "对某个 (材料, 酶活, 底物) 组合，若存在仅温度或仅 pH 变化的条件梯度序列，"
            "绘制响应曲线并返回图片路径与变化倍数。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "材料名（子串匹配）"},
                "activity": {"type": "string", "description": "酶活类型"},
                "substrate": {"type": "string", "description": "底物"},
            },
        },
    },
    {
        "name": "predict",
        "description": (
            "预测给定 (材料, 酶活, 底物, pH, 温度) 组合的 Km（Michaelis 常数）。"
            "三段式证据分级输出：① 图谱存在同组合跨文献记录 → 返回文献实测值与冲突范围；"
            "② 未命中 → 模型外推（log10 Km 点值 + 预测区间 + 训练支撑条数）；"
            "③ 训练支撑不足或冲突严重 → 拒给点值，仅给量级区间。"
            "在正文无法回答「某新材料在特定条件的 Km 大概是多少」时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "材料名（如 Fe3O4、CeO2 NPs）"},
                "activity": {"type": "string", "description": "酶活类型，如 peroxidase、oxidase"},
                "substrate": {"type": "string", "description": "底物，如 TMB、H2O2"},
                "ph": {"type": "number", "description": "查询 pH（必备条件）"},
                "temperature_c": {"type": "number", "description": "查询温度（℃，必备条件）"},
                "size_nm": {"type": "number", "description": "粒径（可选，缺省用训练中位）"},
            },
            "required": ["material", "ph", "temperature_c"],
        },
    },
    {
        "name": "write_analysis_page",
        "description": (
            "把分析结论写入 vault 的 analysis/ 目录（再吸收）。"
            "页面会自动带上推断标记，不会污染事实层。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "页面标题"},
                "content": {"type": "string", "description": "正文 markdown"},
            },
            "required": ["title", "content"],
        },
    },
]

TOOL_NAMES = [t["name"] for t in TOOL_SCHEMAS]


# ------------------------------------------------------------------ 索引

class WikiIndex:
    """vault + records 的只读索引，供工具查询。构造一次，多次查询。"""

    def __init__(self, records_dir: str | Path, vault_dir: str | Path,
                 model_path: str | Path | None = None):
        from build_wiki import load_papers, collect_entries, flat_values  # 延迟导入

        self.records_dir = Path(records_dir)
        self.vault_dir = Path(vault_dir)
        self.papers = load_papers(self.records_dir)
        self.entries = collect_entries(self.papers)
        self.rows = [flat_values(e) for e in self.entries]
        self.hubs: dict[tuple[str, str], list[dict]] = {}
        for e, r in zip(self.entries, self.rows):
            self.hubs.setdefault((str(e.get("act") or ""), str(e.get("sub") or "")), []).append(r)
        # M8-2b：predict 工具的模型（kg/predict_model.py 导出 JSON，惰性加载）
        self.model_path = Path(model_path) if model_path else None
        self._model: dict | None = None
        self._model_error: str | None = None

    # ---------------------------------------------------------------- 工具

    def query_structured(self, material: str | None = None, activity: str | None = None,
                         substrate: str | None = None, ph_min: float | None = None,
                         ph_max: float | None = None, t_min: float | None = None,
                         t_max: float | None = None, metric: str | None = None,
                         limit: int = 20) -> dict:
        out: list[dict] = []

        def ok_sub(v: str | None, pat: str | None) -> bool:
            return not pat or pat.lower() in str(v or "").lower()

        for e, r in zip(self.entries, self.rows):
            if not ok_sub(r["material"], material):
                continue
            if not ok_sub(str(e.get("act") or ""), activity):
                continue
            if not ok_sub(str(e.get("sub") or ""), substrate):
                continue
            if metric and r.get(metric) is None:
                continue
            if ph_min is not None and (r["ph"] is None or r["ph"] < ph_min):
                continue
            if ph_max is not None and (r["ph"] is None or r["ph"] > ph_max):
                continue
            if t_min is not None and (r["temperature_c"] is None or r["temperature_c"] < t_min):
                continue
            if t_max is not None and (r["temperature_c"] is None or r["temperature_c"] > t_max):
                continue
            out.append({
                "material": r["material"], "activity": e.get("act"), "substrate": e.get("sub"),
                "method": r["method"], "ph": r["ph"], "temperature_c": r["temperature_c"],
                "km_mm": r["km_mm"], "vmax_um_s": r["vmax_um_s"], "kcat_s": r["kcat_s"],
                "doi": r["doi"], "page": f"measurements/{r['slug']}.md",
                "provenance": r["provenance"],
            })
        # 稳定排序：材料 → pH → 温度
        out.sort(key=lambda d: (str(d["material"]), d["ph"] if d["ph"] is not None else -1e9,
                                d["temperature_c"] if d["temperature_c"] is not None else -1e9))
        total = len(out)
        return {"total": total, "returned": min(total, limit or 20),
                "rows": out[:limit or 20]}

    def search_notes(self, query: str, limit: int = 10) -> dict:
        pat = re.compile(re.escape(query), re.I)
        hits: list[dict] = []
        for p in sorted(self.vault_dir.rglob("*.md")):
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            m = pat.search(text)
            if not m:
                continue
            s = max(0, m.start() - 60)
            hits.append({
                "path": str(p.relative_to(self.vault_dir)).replace("\\", "/"),
                "context": re.sub(r"\s+", " ", text[s:m.end() + 60]).strip(),
            })
            if len(hits) >= (limit or 10):
                break
        return {"total": len(hits), "hits": hits}

    def read_note(self, path: str) -> dict:
        p = self._safe(path)
        if p is None or not p.is_file():
            return {"error": f"页面不存在或路径非法：{path}"}
        return {"path": path, "content": p.read_text(encoding="utf-8")}

    def graph_neighbors(self, path: str) -> dict:
        p = self._safe(path)
        if p is None or not p.is_file():
            return {"error": f"页面不存在或路径非法：{path}"}
        text = p.read_text(encoding="utf-8")
        stem = p.stem
        out_links = sorted({m.group(1).split("|")[0].split("#")[0]
                            for m in re.finditer(r"\[\[([^\]]+)\]\]", text)})
        back_links: list[str] = []
        for q in sorted(self.vault_dir.rglob("*.md")):
            if q.resolve() == p.resolve():
                continue
            try:
                t = q.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for m in re.finditer(r"\[\[([^\]]+)\]\]", t):
                if m.group(1).split("|")[0].split("#")[0].strip() == stem:
                    back_links.append(str(q.relative_to(self.vault_dir)).replace("\\", "/"))
                    break
        return {"path": path, "out_links": out_links,
                "back_links": sorted(set(back_links))}

    def plot_gradient(self, material: str, activity: str | None = None,
                      substrate: str | None = None) -> dict:
        import wiki_gradient

        pat = re.compile(re.escape(material), re.I)
        matched = [(e, r) for e, r in zip(self.entries, self.rows)
                   if pat.search(str(r["material"]))]
        if activity:
            matched = [(e, r) for e, r in matched
                       if activity.lower() in str(e.get("act") or "").lower()]
        if substrate:
            matched = [(e, r) for e, r in matched
                       if substrate.lower() in str(e.get("sub") or "").lower()]
        if not matched:
            return {"error": f"未找到材料匹配 `{material}` 的测定记录"}
        groups: dict[tuple[str, str, str], list[dict]] = {}
        for e, r in matched:
            groups.setdefault((r["mat_key"], str(e.get("act") or ""), str(e.get("sub") or "")),
                              []).append(e)
        # 必须落在 analysis/ 下：gradients/ 属确定性生成目录，写进去会被下次重编译
        # 判为陈旧文件删掉（破坏 removed_stale=0 的幂等性），也会让推断产物混进事实层。
        outdir = self.vault_dir / WRITE_ROOT / "gradients"
        outdir.mkdir(parents=True, exist_ok=True)
        made: list[dict] = []
        for (mk, act, sub), items in sorted(groups.items()):
            for g in wiki_gradient.detect_gradients(items):
                png = outdir / f"ask__{g['slug']}.png"
                if not wiki_gradient.plot_gradient(g, png):
                    continue
                made.append({
                    "material": g["mat_display"], "activity": g["act"],
                    "substrate": g["sub"], "varying": g["varying"],
                    "fixed": f"{g['fixed_name']} = {g['fixed_val']}",
                    "n_points": g["n_points"], "fold_change": g["fold_change"],
                    "png": str(png.relative_to(self.vault_dir)).replace("\\", "/"),
                })
        if not made:
            return {"error": (f"材料 `{material}` 下未检出条件梯度序列"
                              "（需要同一文献+材料+酶活+底物下仅温度或仅 pH 变化且 ≥3 个点）")}
        return {"total": len(made), "gradients": made}

    def write_analysis_page(self, title: str, content: str) -> dict:
        safe = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", str(title).strip())[:80] or "untitled"
        target = (self.vault_dir / WRITE_ROOT / f"{safe}.md").resolve()
        root = (self.vault_dir / WRITE_ROOT).resolve()
        if not str(target).startswith(str(root)):
            return {"error": "写入路径越界，已拒绝"}
        target.parent.mkdir(parents=True, exist_ok=True)
        page = "\n".join([
            "---",
            "type: analysis",
            "tags:",
            "  - analysis",
            "inferred: true",
            f"title: {title}",
            "---",
            "",
            f"# {title}",
            "",
            "> ⚠️ 本页由问答 agent 生成，属**推断产物**，不是事实层数据。",
            "> 所有数值结论请回到 `measurements/` 下的测定页逐条溯源到 DOI。",
            "",
            content,
            "",
        ])
        target.write_text(page, encoding="utf-8")
        return {"written": str(target.relative_to(self.vault_dir)).replace("\\", "/")}

    # ---------------------------------------------------------------- M8-2b：predict

    def predict(self, material: str, activity: str | None = None,
                substrate: str | None = None, ph: float | None = None,
                temperature_c: float | None = None,
                size_nm: float | None = None) -> dict:
        """三段式证据分级输出（M8-2 §3.5 协议）。

        ① 检索优先：材料子串匹配 + 条件邻域（pH±0.5 / T±5℃）跨文献记录 → 实测值+冲突范围；
        ② 未命中 → 模型外推（log10 Km 点值 + 区间 + 训练支撑）；③ 支撑不足 → 拒给点值。
        模型惰性加载；未配置模型文件时仅检索段可用（不抛异常）。
        """
        from kg import infer

        if ph is None or temperature_c is None:
            return {"stage": "bad_request",
                    "error": "predict 需要 ph 与 temperature_c（条件外推不可缺条件）"}
        ph, t = float(ph), float(temperature_c)
        query = {"material": str(material or ""), "activity": activity,
                 "substrate": substrate, "ph": ph, "temperature_c": t}

        # ---- ① 检索优先（strict=同一材料骨架，related=修饰/复合等近缘）
        # 宽松子串初筛用于找近缘候选；「同组合」判定只用骨架相等的 strict 记录，
        # 避免将 CeO2/rGO、BSA-CeO2 等复合体系误当同一材料的跨文献冲突。
        pat = re.compile(re.escape(str(material or "")), re.I)
        sk = _skeleton(material)
        cand: list[dict] = []
        for e, r in zip(self.entries, self.rows):
            if r["km_mm"] is None or r["ph"] is None or r["temperature_c"] is None:
                continue
            if not pat.search(str(r["material"] or "")):
                continue
            if activity and activity.lower() not in str(e.get("act") or "").lower():
                continue
            if substrate and substrate.lower() not in str(e.get("sub") or "").lower():
                continue
            if abs(r["ph"] - ph) <= 0.5 and abs(r["temperature_c"] - t) <= 5.0:
                cand.append({
                    "material": r["material"], "activity": e.get("act"),
                    "substrate": e.get("sub"), "ph": r["ph"],
                    "temperature_c": r["temperature_c"], "km_mm": r["km_mm"],
                    "doi": r["doi"], "provenance": r["provenance"],
                    "match": "exact" if _skeleton(r["material"]) == sk else "related",
                })
        strict = [c for c in cand if c["match"] == "exact"]
        if len({c["doi"] for c in strict}) >= 2:
            kms = [c["km_mm"] for c in strict if c["km_mm"] > 0]
            fold = max(kms) / min(kms) if len(kms) >= 2 and min(kms) > 0 else None
            note = (f"该组合跨文献 Km 差异 {fold:.1f}×，tier-2 冲突，见冲突谱"
                    if fold and fold > 3 else "组内跨文献离散度较小，可直接引用")
            return {"stage": "retrieval", "query": query, "n_records": len(strict),
                    "n_papers": len({c["doi"] for c in strict}),
                    "records": strict, "fold_max_min": round(fold, 1) if fold else None,
                    "conflict_note": note,
                    "related_records": [c for c in cand if c["match"] == "related"],
                    "advice": "优先引用文献实测值（含条件与 DOI），而非模型外推。"}

        # ---- ②/③ 模型外推
        outfit = {"stage": "extrapolation", "query": query}
        model = self._load_model()
        if model is None:
            outfit.update({"stage": "no_model", "nearby_records": len(cand),
                           "error": self._model_error or "未配置模型文件（model_path）"})
            return outfit
        pred = infer.predict_logkm(model, str(material or ""), activity, substrate, ph, t,
                                   size_nm)
        act = infer.predict_act(model, str(material or ""), substrate, ph, t)
        meta = model["meta"]
        outfit["model_card"] = {
            "model": meta["regression"]["model"],
            "n_estimators": meta["regression"]["n_estimators"],
            "max_depth": meta["regression"]["max_depth"],
            "r2_oof": round(meta["regression"]["r2"], 3),
            "rmse_log10_km": round(meta["regression"]["rmse_log10_km"], 3),
            "evaluation": meta["regression"]["evaluation"],
            "n_train_rows": meta["data"]["reg_rows"],
            "classifier_acc": round(meta["classification"]["acc"], 3),
        }
        outfit["predicted_activity"] = act
        if pred["support"] >= MIN_PREDICT_SUPPORT:
            outfit.update({
                "predicted_log10_km": pred["predicted_log10_km"],
                "predicted_km_mM": pred["predicted_km_mM"],
                "km_range_mM": pred["km_range_mM"],
                "interval_log10": pred["interval_log10"],
                "training_support": pred["support"],
                "material_status": pred["material_status"],
                "advice": "模型外推仅供族内条件外推参考（DOI 分组 OOF R² 见模型卡）；"
                          "跨材料泛化≈0，不可作为绝对真值。",
            })
        else:
            outfit.update({
                "stage": "refusal",
                "reason": f"训练支撑不足（{pred['support']} 条 < {MIN_PREDICT_SUPPORT}）或冲突严重",
                "magnitude_range_mM": pred["km_range_mM"],
                "training_support": pred["support"],
                "material_status": pred["material_status"],
                "advice": "仅给量级参考；建议补充该材料动力学数据（按需检索→提取→回填）后重查。",
            })
        return outfit

    def _load_model(self) -> dict | None:
        """惰性加载推理模型；失败记录错误、返回 None（不抛异常，agent 可继续）。"""
        if self._model is not None or self._model_error is not None:
            return self._model
        if self.model_path is None:
            self._model_error = "未配置模型路径（model_path=None），predict 仅检索段可用"
            return None
        from kg import infer
        try:
            self._model = infer.load(self.model_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._model_error = f"模型加载失败：{exc}"
        return self._model

    # ---------------------------------------------------------------- 内部

    def _safe(self, path: str) -> Path | None:
        """路径消毒：拒绝 `../` 穿越与绝对路径。"""
        if not path:
            return None
        rel = str(path).replace("\\", "/").lstrip("/")
        if ".." in rel.split("/"):
            return None
        p = (self.vault_dir / rel).resolve()
        if not str(p).startswith(str(self.vault_dir.resolve())):
            return None
        return p


def dispatch(index: WikiIndex, name: str, args: dict) -> dict:
    """按工具名分派。未知工具返回结构化错误（不抛异常）。"""
    fn = getattr(index, name, None)
    if fn is None or name not in TOOL_NAMES:
        return {"error": f"未知工具：{name}", "available": TOOL_NAMES}
    try:
        # 过滤掉工具 schema 之外的键，防 LLM 传野参数
        sig = fn.__code__.co_varnames[: fn.__code__.co_argcount]
        clean = {k: v for k, v in (args or {}).items() if k in sig}
        return fn(**clean)
    except TypeError as exc:
        return {"error": f"参数错误：{exc}"}
    except Exception as exc:  # 工具内部异常不得炸掉整个 agent
        return {"error": f"工具执行失败：{exc}"}


def tool_prompt() -> str:
    """给 LLM 的工具说明（紧凑版，省 token）。"""
    return json.dumps(TOOL_SCHEMAS, ensure_ascii=False, indent=None)
