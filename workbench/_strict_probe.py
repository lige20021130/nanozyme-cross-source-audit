# workbench/_strict_probe.py
"""一次性诊断：用 align 的严格 _values_match 复算 cross_validate 的 pooled F1，
   用于判定外部报告的 human_side F1=0.847 是否来自"未做语义归一化"的旧口径。
   仅诊断，不产出论文数据。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench import cross_validate as cv
from workbench.align import EVAL_FIELDS, _build_report, _values_match


def collect(src_by_doi, matcher):
    agg = {f: {"tp": 0, "fp": 0, "fn": 0} for f in EVAL_FIELDS}
    per = {}
    for doi, sys_list in sorted(cv.load_records_dir(cv.DEFAULT_SYS).items()):
        src = src_by_doi.get(doi)
        if not src:
            continue
        cv._records_match = matcher
        r = cv.compare_side(sys_list, src)
        for f in EVAL_FIELDS:
            for k in ("tp", "fp", "fn"):
                agg[f][k] += r["stats"][f][k]
        rep = r["report"]["overall"]
        per[doi] = rep
    return {"overall": _build_report(agg, [])["overall"],
            "field_level": _build_report(agg, [])["field_level"],
            "per_paper_macro": per}


def main():
    sysd = cv.DEFAULT_SYS
    human = cv.load_records_dir(cv.DEFAULT_HUMAN)
    db = cv.load_records_dir(cv.DEFAULT_DB)

    print("=== A) 语义归一化口径（cross_validate.py 现行 _records_match）===")
    for name, src in (("human", human), ("db", db)):
        o = collect(src, cv._records_match)["overall"]
        print(f"  {name:5s} P {o['precision']:.4f} R {o['recall']:.4f} "
              f"F1 {o['f1']:.4f} acc {o['accuracy']:.4f} macro {o['macro_f1']:.4f}")

    print("=== B) 严格口径（align._values_match，无 metal_type/shape/size 归一化）===")
    for name, src in (("human", human), ("db", db)):
        res = collect(src, _values_match)
        o = res["overall"]
        print(f"  {name:5s} P {o['precision']:.4f} R {o['recall']:.4f} "
              f"F1 {o['f1']:.4f} acc {o['accuracy']:.4f} macro {o['macro_f1']:.4f}")
        weak = {f: round(v['f1'], 3) for f, v in res["field_level"].items()}
        print("        field F1:", weak)
        mf = res["per_paper_macro"]
        if mf:
            vals = sorted(v["macro_f1"] for v in mf.values())
            n = len(vals)
            print(f"        per-paper macro mean {sum(vals)/n:.4f} median {vals[n//2]:.4f}")


if __name__ == "__main__":
    main()
