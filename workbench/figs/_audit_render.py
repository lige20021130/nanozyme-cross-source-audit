# -*- coding: utf-8 -*-
"""Read-only pixel audit of the 8 manuscript PNGs. No figures are modified.

Computes per figure: canvas size, content bbox + margins, border-clip ring,
whitespace waste, red/green (colorblind) risk, and min effective font pt.
"""
import os
import re
import numpy as np
from PIL import Image

FIG_DIR = r"D:/ocrwiki版本/新 nanowiki/workbench/figs"

# function name -> (source .py, output png) as actually generated
FUNC_MAP = [
    ("figs_v2.py",   "fig1",      "fig1_overview.png"),
    ("figs_data.py", "fig2",      "fig2_scale.png"),
    ("figs_v2.py",   "fig3",      "fig3_extract_eval.png"),
    ("figs_v2.py",   "fig4",      "fig4_units.png"),
    ("figs_v2.py",   "fig_fe3o4", "fig5_fe3o4_cluster.png"),
    ("figs_v2.py",   "fig_atlas", "fig6_atlas.png"),
    ("figs_data.py", "fig7",      "fig7_tiers.png"),
    ("figs_v2.py",   "fig8",      "fig8_leakage.png"),
]


def parse_func_fontsizes(path):
    """Return {func_name: [fontsize/fn numeric literals, fs numeric defaults]}."""
    txt = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^def\s+(\w+)\s*\(", txt, re.M):
        name = m.group(1)
        start = m.end()
        nm = re.search(r"\ndef\s+\w+\s*\(", txt[start:])
        end = start + nm.start() if nm else len(txt)
        body = txt[start:end]
        # literal fontsize=NN  (exclude title_fontsize)
        fs = [float(x) for x in re.findall(r"(?<!\w)fontsize\s*=\s*([\d.]+)", body)]
        # box() helper default fs=NN and fs=NN call args
        fsv = [float(x) for x in re.findall(r"(?<!\w)fs\s*=\s*([\d.]+)", body)]
        out[name] = sorted(fs + fsv)
    return out


def analyze(png_path):
    img = Image.open(png_path).convert("RGB")
    arr = np.asarray(img).astype(np.int16)
    H, W = arr.shape[:2]
    ink = (arr < 250).any(axis=2)              # any channel < 250 => ink
    ys, xs = np.where(ink)
    res = {"W": W, "H": H, "aspect": W / H, "n_ink": int(ink.sum())}
    if xs.size == 0:
        return res
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    res.update({
        "bbox": (x0, y0, x1, y1),
        "left": x0, "right": W - 1 - x1,
        "top": y0, "bottom": H - 1 - y1,
    })
    res["left_pct"]   = 100.0 * x0 / W
    res["right_pct"]  = 100.0 * (W - 1 - x1) / W
    res["top_pct"]    = 100.0 * y0 / H
    res["bottom_pct"] = 100.0 * (H - 1 - y1) / H

    # 2-px border ring
    ring = np.zeros_like(ink)
    ring[:2, :] = True
    ring[-2:, :] = True
    ring[:, :2] = True
    ring[:, -2:] = True
    top_c    = int((ink[:2, :]).sum())
    bottom_c = int((ink[-2:, :]).sum())
    left_c   = int((ink[:, :2]).sum())
    right_c  = int((ink[:, -2:]).sum())
    res["border"] = {"top": top_c, "bottom": bottom_c, "left": left_c, "right": right_c}

    # red / green colorblind risk  (quantize 4-bit per channel)
    q = (arr >> 4) << 4
    R, G, B = q[:, :, 0], q[:, :, 1], q[:, :, 2]
    red_mask = (R > 150) & (G < 90) & (B < 90)
    grn_mask = (G > 130) & (R < 110) & (B < 110)
    res["red_px"] = int(red_mask.sum())
    res["grn_px"] = int(grn_mask.sum())
    return res


def main():
    v2 = parse_func_fontsizes(os.path.join(FIG_DIR, "figs_v2.py"))
    d  = parse_func_fontsizes(os.path.join(FIG_DIR, "figs_data.py"))
    fontmap = {}
    for src, fn, png in FUNC_MAP:
        fmap = v2 if src == "figs_v2.py" else d
        fontmap[png] = fmap.get(fn, [])

    rows = []
    print("=" * 78)
    for src, fn, png in FUNC_MAP:
        p = os.path.join(FIG_DIR, png)
        r = analyze(p)
        fs = fontmap[png]
        min_fs = min(fs) if fs else float("nan")
        px_w = r["W"]
        # effective pt: source fontsize scaled to Nature 7.2in printed width
        eff = min_fs * (7.2 / (px_w / 300.0)) if px_w else float("nan")

        margins = {
            "L": (r.get("left_pct", 0.0), "width"),
            "R": (r.get("right_pct", 0.0), "width"),
            "T": (r.get("top_pct", 0.0), "height"),
            "B": (r.get("bottom_pct", 0.0), "height"),
        }
        worst_side = max(margins, key=lambda k: margins[k][0])
        worst_pct = margins[worst_side][0]

        bd = r.get("border", {})
        clip_flag = any(bd.get(e, 0) > 20 for e in ("top", "bottom", "left", "right"))
        clip_total = sum(bd.values())

        ws_flag = worst_pct > 22.0
        rg_both = (r.get("red_px", 0) > 0) and (r.get("grn_px", 0) > 0)

        defects = []
        if clip_flag:
            defects.append("border-clip>20px(" + ",".join(
                f"{e}={bd[e]}" for e in ("top", "bottom", "left", "right") if bd[e] > 20) + ")")
        if ws_flag:
            defects.append(f"whitespace {worst_side}={worst_pct:.1f}%>22%")
        if rg_both:
            defects.append(f"red&green present (R={r['red_px']},G={r['grn_px']}px)")
        if eff < 6.5:
            defects.append(f"eff pt {eff:.2f}<6.5")

        verdict = "PASS" if not defects else "; ".join(defects)

        print(f"\n### {png}  (src={src}:{fn})")
        print(f"  canvas={r['W']}x{r['H']}px  aspect={r['aspect']:.3f}  ink={r['n_ink']}px")
        if "bbox" in r:
            print(f"  bbox=({r['bbox']})  margins px L={r['left']} R={r['right']} "
                  f"T={r['top']} B={r['bottom']}")
            print(f"  margins % L={r['left_pct']:.1f} R={r['right_pct']:.1f} "
                  f"T={r['top_pct']:.1f} B={r['bottom_pct']:.1f}  worst={worst_side}={worst_pct:.1f}%")
        print(f"  border ring px: {bd}  total={clip_total}  flag={clip_flag}")
        print(f"  red_px={r.get('red_px',0)}  grn_px={r.get('grn_px',0)}  both={rg_both}")
        print(f"  fontsize literals={fs}  min_fs={min_fs}  eff_pt={eff:.2f}")
        print(f"  VERDICT: {verdict}")
        rows.append((png, f"{r['W']}x{r['H']}", f"{worst_side}={worst_pct:.1f}%",
                     "YES" if clip_flag else "no", "YES" if rg_both else "no",
                     f"{eff:.2f}", verdict))

    print("\n" + "=" * 78)
    print("VERDICT TABLE")
    print(f"{'figure':22} {'size':11} {'worst_margin':13} {'clip':5} {'R&G':4} {'eff_pt':7} result")
    for row in rows:
        print(f"{row[0]:22} {row[1]:11} {row[2]:13} {row[3]:5} {row[4]:4} {row[5]:7} {row[6]}")


if __name__ == "__main__":
    main()
