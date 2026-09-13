# -*- coding: utf-8 -*-
"""纳米酶知识图谱层（第二研究内容）。

模块职责：

| 子模块 | 作用 | 是否需 API |
|---|---|---|
| `bench_source` | 人工标注母表 → FlatRecord 兼容产出（provenance=human） | 否 |
| `source_registry` | 五公开库（AI-ZYMES/DiZyme/nanozymes.net/NanozymeDB/ChemX）统一 schema → FlatRecord（provenance=db:*，引用来源） | 否 |
| `lineage` | DOI×源谱系矩阵 + 跨源冲突 + 覆盖盲区 + 防泄漏划分 | 否 |
| `condition_ml` | M1/M2 条件条件化预测（log10 Km，RF，分组 CV）+ M6 多库外部验证 | 否（sklearn 在 conda base） |
| `predict_model` | M8-2b 训练导出（GBR 回归对标 AI-ZYMES + RF 分类头对标 Wei，DOI 分组 OOF 模型卡，树 JSON 导出） | 否（sklearn 在 conda base） |
| `infer` | 消费 model.json 的零依赖推理器（回归外推 + 分类置信度），`.venv` 可跑 | 否 |
| `taxonomy` | 实体归类：确定性别名层 + 可选 LLM 上位类层 | 可选 |
| `hub_summary` | (活性,底物) hub 的知识归纳 | 可选 |
| `conflict` | 同条件跨文献数值冲突检测 | 否 |
| `tools` | `--ask` agent 的工具实现 | 否（检索侧） |
| `ask` | `--ask` 问答 agent 主循环 | 是 |

三条铁律：
1. **事实层与推断层严格分离** —— 任何 LLM 产物都带 `inferred` 标记，且**绝不回写**事实层。
2. **provenance 是一等公民** —— `extraction`（系统抽取）、`human`（人工标注）与 `db:*`（公开库引用来源）永不静默混同。
3. **默认零 API** —— 所有 LLM 能力 opt-in，未开启时优雅返回空而不抛异常。
"""
from __future__ import annotations

__all__ = [
    "bench_source",
    "source_registry",
    "lineage",
    "condition_ml",
    "predict_model",
    "infer",
    "taxonomy",
    "hub_summary",
    "conflict",
    "tools",
    "ask",
]

# provenance 取值（写入 frontmatter 与页面，供 Dataview 过滤）
PROV_EXTRACTION = "extraction"
PROV_HUMAN = "human"
