# -*- coding: utf-8 -*-
"""P0-1：为 17 组同 pH 冲突定位源 PDF，并抽取 Km 相关上下文供人工回原文核对。

步骤：
1. 递归扫描源 PDF 语料（E:\\人工收集的文献归类\\人工智能纳米酶\\论文-数据库），建索引。
2. 按 DOI 尾段在文件名中模糊匹配（PDF 文件名常含期刊缩写编号）。
3. 对命中的 PDF 用 pdfplumber 抽取全文，正则定位 Km / Michaelis / mM 上下文。
4. 输出 workbench/p0_unit_recovery_ctx.json（每例的候选上下文片段），供人工判定。

运行：D:/conda/python.exe workbench/p0_unit_recovery.py [--scan]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("E:/人工收集的文献归类/人工智能纳米酶/论文-数据库")
INDEX = ROOT / "workbench" / "p0_pdf_index.json"
OUT = ROOT / "workbench" / "p0_unit_recovery_ctx.json"

# 17 组冲突（来自 SI Table S3）
GROUPS = [
    ("10.1038/s41467-018-03903-8", "N-PCNSs-5", "H2O2", 7.0, "0.000154 vs 154", 1_000_000),
    ("10.1038/s41467-018-03903-8", "PCNSs", "H2O2", 7.0, "0.0006789 vs 678.9", 1_000_000),
    ("10.1038/s41467-018-03903-8", "N-PCNSs-3", "H2O2", 7.0, "0.0006625 vs 66.24", 99_985),
    ("10.1016/j.bios.2014.08.062", "NiO", "H2O2", 3.8, "0.00666 vs 208", 31_231),
    ("10.1016/j.bios.2014.08.062", "NiO", "TMB", 3.8, "0.0067 vs 208", 31_045),
    ("10.1021/acsami.6b05354", "CuO", "H2O2", 4.65, "0.4 vs 400", 1_000),
    ("10.1021/acsami.6b05354", "CuO", "TMB", 4.65, "0.025 vs 25", 1_000),
    ("10.1021/acsami.8b20942", "HccFn(Co3O4)", "TMB", 4.5, "0.84 vs 840", 1_000),
    ("10.1021/acsami.8b20942", "HccFn(Fe3O4)", "TMB", 4.5, "1.12 vs 1120", 1_000),
    ("10.1016/j.bios.2014.08.062", "H2TCPP-NiO", "TMB", 3.8, "0.391 vs 39.1", 100),
    ("10.1016/j.apcatb.2020.118725", "Cit-IrNPs", "H2O2", 3.86, "0.27 vs 21.09", 78),
    ("10.1039/c9cc00199a", "Fe SAEs", "TMB", 3.8, "0.13 vs 3.92", 30),
    ("10.1016/j.colsurfa.2016.07.037", "Fe2O3", "H2O2", 3.6, "11.3 vs 305", 27),
    ("10.1016/j.snb.2023.134429", "rGO@PDA@CeO2", "H2O2", 7.4, "0.26 vs 6.39", 25),
    ("10.1016/j.snb.2023.134429", "rGO@PDA@CeO2", "TMB", 7.4, "0.41 vs 6.81", 17),
    ("10.1039/c6nr02730j", "CeO2", "TMB", 4.0, "0.14 vs 1.5", 11),
    ("10.1039/c9nr05346h", "CeO2", "TMB", 4.0, "0.14 vs 1.5", 11),
]

KM_PAT = re.compile(
    r"(K_?m|K_?M|Michaelis)[\s\S]{0,400}?", re.IGNORECASE)


def build_index() -> dict:
    pdfs = [p for p in CORPUS.rglob("*.pdf")] if CORPUS.exists() else []
    idx = {str(p): p.name for p in pdfs}
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[index] {len(pdfs)} PDFs -> {INDEX}")
    return idx


def match_pdf(doi: str, idx: dict) -> list[str]:
    """DOI -> 候选 PDF 路径（按尾段与去标点后子串匹配）。"""
    tail = doi.split("/")[-1]
    key = tail.replace(".", "")
    cands = []
    for path, name in idx.items():
        nk = name.replace(".", "").replace("_", "").replace("-", "").replace(" ", "")
        if key in nk or key.replace("/", "") in nk:
            cands.append(path)
    # 退一步：用最后一段（如 6b05354 / 8b20942 / C9CC00199A）
    if not cands:
        last = re.split(r"[.\-]", tail)[-1]
        if len(last) >= 5:
            for path, name in idx.items():
                if last.lower() in name.lower():
                    cands.append(path)
    return sorted(cands)[:3]


def extract_ctx(pdf_path: str, max_pages: int = 60) -> list[str]:
    """抽取含 Km / Michaelis 的上下文片段。"""
    try:
        import pdfplumber
    except ImportError:
        return ["[pdfplumber 未安装]"]
    ctx = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            try:
                txt = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                continue
            for m in re.finditer(r"(?i)K_?[mM]\b|Michaelis", txt):
                s = max(0, m.start() - 160)
                e = min(len(txt), m.end() + 220)
                frag = " ".join(txt[s:e].split())
                if any(u in frag for u in ("mM", "µM", "uM", "M", "mM-1")):
                    ctx.append(f"[p{i+1}] {frag}")
            if len(ctx) >= 25:
                break
    # 去重
    seen, out = set(), []
    for c in ctx:
        k = c[:80]
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out[:12]


def main() -> None:
    if "--scan" in sys.argv or not INDEX.exists():
        idx = build_index()
    else:
        idx = json.loads(INDEX.read_text(encoding="utf-8"))
        print(f"[index] loaded {len(idx)} PDFs")

    # 只处理唯一 DOI
    dois = sorted({g[0] for g in GROUPS})
    res = {}
    for doi in dois:
        cands = match_pdf(doi, idx)
        entry = {"doi": doi, "candidates": cands, "contexts": []}
        if cands:
            entry["contexts"] = extract_ctx(cands[0])
        res[doi] = entry
        n = len(entry["contexts"])
        print(f"{doi:44s} pdf={'YES' if cands else 'no '}  ctx={n}")

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
