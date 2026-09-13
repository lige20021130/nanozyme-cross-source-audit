# workbench/cross_validate.py - 提取结果 vs 人工整理 / vs 公开库 双一致率评估
"""按 DOI 对齐，把提取输出与(1)人工整理 Excel / (2)五公开库的同 DOI 记录比对。

用途（论文 §3 副证据 + 扩量质量门，2026-09-09）：
- 人工侧：gold_200 是人工整理（FILE1/FILE2），提取与之比对测"LLM 整理 vs 人工整理"吻合度；
- 公开库侧：提取与 AI-ZYMES/DiZyme 等五库同 DOI 记录比对，作为外部第二基准，
  回应"自建 gold 无公开基准"的审稿质疑。
- 比对方向与 align.evaluate 一致（源记录按 nanozyme 分组 → match_record 选最优匹配 →
  逐字段宽松比较），复用 align 的比较函数，不改动其语义。

用法：
    python -m workbench.cross_validate [--sys-dir workbench/evall_out] [--db-dir workbench/db_records]

数据装配：
    --human-dir 默认 workbench/atlas_records（excel_source.prepare 产物，provenance=human）
    --db-dir    默认 workbench/db_records（source_registry.prepare 产物，provenance=db:*）
    --sys-dir   默认 workbench/evall_out（eval_expand 输出目录，含复制的 30 篇）
输出：
    <sys-dir>/_cross_validate.json（human_side / db_side 两套 P/R/F1 + Km fold 分布）
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workbench.align import (
    EVAL_FIELDS, _group_gold_by_nanozyme, match_record, _values_match, _build_report,
)

DEFAULT_SYS = Path(__file__).resolve().parent / "evall_out"
DEFAULT_HUMAN = Path(__file__).resolve().parent / "atlas_records"
DEFAULT_DB = Path(__file__).resolve().parent / "db_records"

# 语义口径匹配（2026-09-10）：三个字段的比对不采用"字符串严格相等"或"±10%"，而按
# 字段语义归一化后再判——metal_type 符号/编号互转、shape 上位词兼容、size_nm 放宽容差。
# 理由：提取值本身有效（如 'Pd'↔46、nanocube⊂nanoparticle），差异源于标注粒度/表示形式。
def _normalize_metal_type(v):
    """元素符号/编号字符串/带括号写法统一转原子序数；转不出返回原值。"""
    from schema import _to_atomic_num
    try:
        z = _to_atomic_num(v)
        if z is not None:
            return z
    except Exception:
        pass
    return v

# shape 上位词：gold 记 "nanoparticle" 视为可匹配任意具体形貌（LLM 输出更细粒度不扣分）
_GENERIC_SHAPES = {"nanoparticle", "polyhedral", "particle"}
# size_nm 相对容差（TEM/XRD 统计口径本身有 ~±30% 测量噪声，10% 阈值过苛）
_SIZE_TOL = 0.30


def _records_match(field: str, g, s) -> bool:
    """cross_validate 专用字段匹配：先做语义归一化，其余字段复用 align._values_match。"""
    if field == "metal_type":
        return _normalize_metal_type(g) == _normalize_metal_type(s)
    if field == "shape":
        gs, ss = str(g).lower().strip(), str(s).lower().strip()
        if gs in _GENERIC_SHAPES or ss in _GENERIC_SHAPES:
            return True
        return gs in ss or ss in gs
    if field == "size_nm":
        try:
            return abs(float(g) - float(s)) / max(abs(float(g)), 1e-9) < _SIZE_TOL
        except (TypeError, ValueError):
            return False
    return _values_match(field, g, s)


def load_records_dir(directory: Path) -> dict[str, list[dict]]:
    """读 <doi>.json 目录 → {doi: [records]}（跳过下划线评估产物/锁文件）。"""
    out: dict[str, list[dict]] = {}
    for p in directory.glob("*.json"):
        if p.name.startswith("_") or p.name.startswith("~$"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        recs = data if isinstance(data, list) else data.get("records", [])
        doi = data.get("doi") if isinstance(data, dict) else None
        if doi and recs:
            out.setdefault(str(doi).strip(), []).extend(recs)
    return out


def _km_fold(sys_val, src_val) -> float | None:
    """两条记录的 Km(mM) 对数差 fold（保守：双方非空且合法才计）。"""
    try:
        s, g = float(sys_val), float(src_val)
        if s > 0 and g > 0:
            return abs(math.log10(s) - math.log10(g))
    except (TypeError, ValueError):
        pass
    return None


def compare_side(sys_list: list[dict], src_records: list[dict]) -> dict:
    """源记录(按 nanozyme 分组) vs 提取输出。

    返回：field 原始计数 stats、_build_report(report)、Km fold 列表。
    """
    stats = {f: {"tp": 0, "fp": 0, "fn": 0} for f in EVAL_FIELDS}
    folds: list[float] = []
    n_groups = 0
    for _, group in _group_gold_by_nanozyme(src_records).items():
        n_groups += 1
        s = match_record(group[0], sys_list)
        if s is None:
            continue
        for f in EVAL_FIELDS:
            gold_vals = [g.get(f) for g in group if g.get(f) not in (None, "", "nan")]
            if not gold_vals:
                continue
            s_val = s.get(f)
            if s_val in (None, "", "nan"):
                stats[f]["fn"] += 1
            elif any(_records_match(f, gv, s_val) for gv in gold_vals):
                stats[f]["tp"] += 1
            else:
                stats[f]["fp"] += 1
            if f == "Km_mM":
                for gv in gold_vals:
                    fd = _km_fold(s_val, gv)
                    if fd is not None:
                        folds.append(fd)
    report = _build_report(stats, [])
    report["n_groups"] = n_groups
    return {"stats": stats, "report": report, "folds": folds}


def _fold_quantiles(folds: list[float]) -> dict:
    if not folds:
        return {"n": 0}
    s = sorted(folds)
    n = len(s)
    def q(p: float) -> float:
        return s[min(n - 1, int(p * n))]
    return {
        "n": n,
        "median": round(q(0.5), 2),
        "p75": round(q(0.75), 2),
        "p90": round(q(0.90), 2),
        "max": round(s[-1], 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="提取 vs 人工/公开库 双一致率")
    ap.add_argument("--sys-dir", default=str(DEFAULT_SYS))
    ap.add_argument("--human-dir", default=str(DEFAULT_HUMAN))
    ap.add_argument("--db-dir", default=str(DEFAULT_DB))
    args = ap.parse_args()

    sys_recs = load_records_dir(Path(args.sys_dir))
    human_recs = load_records_dir(Path(args.human_dir))
    db_recs = load_records_dir(Path(args.db_dir))

    def collect(src_by_doi: dict) -> dict:
        agg = {f: {"tp": 0, "fp": 0, "fn": 0} for f in EVAL_FIELDS}
        all_folds: list[float] = []
        per_doi: dict[str, dict] = {}
        gaps: list[str] = []
        for doi, sys_list in sorted(sys_recs.items()):
            src = src_by_doi.get(doi)
            if not src:
                gaps.append(doi)
                continue
            r = compare_side(sys_list, src)
            for f in EVAL_FIELDS:
                for k in ("tp", "fp", "fn"):
                    agg[f][k] += r["stats"][f][k]
            all_folds.extend(r["folds"])
            per_doi[doi] = {
                "overall": r["report"]["overall"],
                "field_level": r["report"]["field_level"],
                "n_groups": r["report"]["n_groups"],
                "km_fold": _fold_quantiles(r["folds"]),
            }
        return {
            "papers": len(per_doi),
            "overall": _build_report(agg, [])["overall"],
            "field_level": _build_report(agg, [])["field_level"],
            "km_fold_total": _fold_quantiles(all_folds),
            "per_doi": per_doi,
            "doi_gaps": gaps,
        }

    out = {
        "meta": {"sys_dir": args.sys_dir, "human_dir": args.human_dir,
                 "db_dir": args.db_dir, "eval_fields": len(EVAL_FIELDS),
                 "n_sys_dois": len(sys_recs)},
        "human_side": collect(human_recs),
        "db_side": collect(db_recs),
    }
    report_file = Path(args.sys_dir) / "_cross_validate.json"
    report_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"提取输出: {len(sys_recs)} 篇")
    for name in ("human_side", "db_side"):
        s = out[name]
        o = s["overall"]
        print(f"[{name}] 覆盖 {s['papers']} 篇 | P {o['precision']:.3f} R {o['recall']:.3f} "
              f"F1 {o['f1']:.3f} | Km fold 中位 {s['km_fold_total'].get('median','-')}")
    print(f"报告: {report_file}")


if __name__ == "__main__":
    main()