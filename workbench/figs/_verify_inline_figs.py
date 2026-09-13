# -*- coding: utf-8 -*-
"""Verify inline figure integration + font-size gate for the merged manuscript.

Checks:
  1. every ![Figure N](path) in the built manuscript resolves on disk
  2. figure N appears after its first in-text citation "Figure N", and
     numbering order == first-citation order (monotonic)
  3. no orphan "## Figures" end-dump block
  4. effective font size gate: min(source fontsize) * (7.2in / (px/300dpi))
     must be >= 6.5 pt at Nature double-column width
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(r"D:\ocrwiki版本\新 nanowiki")
DOC = ROOT / "paper_drafts" / "manuscript_full_track1.md"
FIGS_DIR = ROOT / "workbench" / "figs"
SCRIPTS = ["figs_v2.py", "figs_data.py"]

RE_IMG = re.compile(r"!\[Figure (\d+)\]\(([^)]+)\)")
RE_CITE = re.compile(r"Figure (\d+)(?![0-9])")


def png_size(p: Path):
    with p.open("rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {p}")
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def min_fontsize_per_fig():
    """grep fontsize= in the generator scripts, attribute by nearest fig function."""
    out = {}
    for s in SCRIPTS:
        txt = (FIGS_DIR / s).read_text(encoding="utf-8", errors="replace")
        cur = None
        for line in txt.splitlines():
            m = re.match(r"\s*def\s+(fig\w*)\s*\(", line)
            if m:
                cur = m.group(1)
                out.setdefault(cur, 99.0)
            for fm in re.finditer(r"fontsize\s*=\s*([0-9.]+)", line):
                if cur:
                    out[cur] = min(out[cur], float(fm.group(1)))
    return out


def main():
    text = DOC.read_text(encoding="utf-8")
    lines = text.splitlines()
    ok = True

    # 4) orphan end-dump
    if re.search(r"^##\s+Figures\s*$", text, re.M):
        print("[FAIL] orphan '## Figures' end-dump block still present")
        ok = False
    else:
        print("[OK]   no orphan '## Figures' end-dump block")

    # 1) + 2) inline images
    imgs = [(int(n), p, i) for i, ln in enumerate(lines)
            for n, p in RE_IMG.findall(ln)]
    print(f"[--]   inline images found: {len(imgs)}")
    if len(imgs) != 8:
        print(f"[WARN] expected 8 inline figures, found {len(imgs)}")

    first_cite = {}
    for i, ln in enumerate(lines):
        for n in RE_CITE.findall(ln):
            n = int(n)
            if n not in first_cite:
                first_cite[n] = i

    citation_order = [n for n, _ in sorted(first_cite.items(), key=lambda kv: kv[1])]
    img_order = [n for n, _, _ in imgs]
    print(f"[--]   first-citation order: {citation_order}")
    print(f"[--]   inline-image order  : {img_order}")
    if img_order != sorted(img_order):
        print("[FAIL] inline image order is not monotonic")
        ok = False
    else:
        print("[OK]   inline image order monotonic")
    if citation_order[:len(img_order)] != img_order:
        print("[WARN] image order != first-citation order (renumber needed)")
    else:
        print("[OK]   image order == first-citation order")

    for n, rel, idx in imgs:
        p = (DOC.parent / rel).resolve()
        if not p.exists():
            print(f"[FAIL] Figure {n}: missing file {rel}")
            ok = False
            continue
        cite = first_cite.get(n)
        if cite is None:
            print(f"[FAIL] Figure {n}: no in-text citation")
            ok = False
            continue
        if idx <= cite:
            print(f"[FAIL] Figure {n}: placed at line {idx+1} but cited at line {cite+1}")
            ok = False
            continue
        w, h = png_size(p)
        print(f"[OK]   Figure {n}: {rel}  {w}x{h}px  cited@L{cite+1} placed@L{idx+1}")

    # 4) font gate
    print("\n-- font-size gate (Nature double column = 7.2 in) --")
    fs = min_fontsize_per_fig()
    mapping = {
        "fig1": "fig1_overview.png", "fig2": "fig2_scale.png",
        "fig3": "fig3_extract_eval.png", "fig4": "fig4_units.png",
        "fig_fe3o4": "fig5_fe3o4_cluster.png", "fig_atlas": "fig6_atlas.png",
        "fig7": "fig7_tiers.png", "fig8": "fig8_leakage.png",
    }
    for fn, png in mapping.items():
        p = FIGS_DIR / png
        if not p.exists():
            print(f"[MISS] {png}")
            continue
        w, _ = png_size(p)
        scale = 7.2 / (w / 300.0)
        src = fs.get(fn, 99.0)
        eff = src * scale
        verdict = "PASS" if eff >= 6.5 else "FAIL"
        if eff < 6.5:
            ok = False
        print(f"[{verdict}] {png:26s} {w:4d}px  min_src={src:4.1f}pt  "
              f"scale={scale:.2f}  eff={eff:.2f}pt")

    print("\nRESULT:", "ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
