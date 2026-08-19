"""Paper Figure 3-3 — dmTTCP distributions (pool vs EIG-selected) with FP overlays.

Usage:
  python run_analysis2_frame_figs.py

Outputs (thesis Figure 3-3):
  Fig2-mTTCP_frame_RAB   : (a) RAB FP decision frames overlay
  Fig2-mTTCP_frame_allFP : (b) ALL FP(PSM+FOT) decision frames overlay
"""
import csv, os
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 산출물은 저장소 재구성 시 results/ 로 이동했다 (scripts/ -> ../../../.. = 저장소 루트).
# 주의: 입력 중 fp_frame_metrics.csv 는 실차 프레임 지표라 저장소에서 제외되었다.
#       따라서 이 스크립트는 공개 저장소만으로는 실행되지 않는다 (../../../../data/README.md 참조).
A2 = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                  "results", "eig_selection", "analysis2")

POOL_FILL, POOL_EDGE = "#A8CBE3", "#3D7CB0"   # generation pool  = light blue
SEL_FILL, SEL_EDGE = "#F5A25D", "#C55A11"     # EIG-selected     = orange
FP_FILL, FP_EDGE = "#CDEBB5", "#6AA84F"       # FP overlay       = light green
plt.rcParams.update({
    "font.size": 11, "axes.labelsize": 11.5, "legend.fontsize": 9.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.9, "xtick.direction": "out", "ytick.direction": "out",
    "legend.frameon": False, "pdf.fonttype": 42,
})

sfx = ""

rows = list(csv.DictReader(open(os.path.join(A2, "frame_metrics.csv"))))
sel = [r for r in rows if r["selected"] == "1"]
fp = list(csv.DictReader(open(os.path.join(A2, "fp_frame_metrics.csv"))))
print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] pool={len(rows)} sel={len(sel)} FP frames={len(fp)}")


def vals(rs, m):
    return np.array([float(r[m]) for r in rs if r[m] not in ("", "nan")])


VARIANTS = [("RAB", [r for r in fp if r["is_rab"] == "1"], "RAB FP decision frames",
             FP_FILL, FP_EDGE)]
VARIANTS.append(("allFP", fp, "FP decision frames", FP_FILL, FP_EDGE))
METRICS = [("dmttcp", r"$\Delta$mTTCP [s]", "Fig2-mTTCP_frame")]

for vtag, ov_rows, ov_label, ov_fill, ov_edge in VARIANTS:
    for m, xlabel, bs in METRICS:
        fvals = vals(ov_rows, m)
        xmax = 10.0
        if len(fvals) and fvals.max() > xmax:
            xmax = float(np.ceil(fvals.max()) + 1)
        fig, ax = plt.subplots(figsize=(7.2, 4.6))
        # many overlay frames -> filled bars at the very back
        if len(fvals) > 12:
            fc = fvals[fvals <= xmax]
            ax.hist(fc, bins=40, range=(0, xmax),
                    weights=np.full(len(fc), 1.0 / len(fvals)),
                    histtype="bar", facecolor=ov_fill, edgecolor=ov_edge,
                    lw=0.8, zorder=1, label=ov_label)
        # draw order: FP fill (back, z=1) -> selected (z=2) -> pool (front, z=3)
        for name, rs, fill, edge, alpha, z in [
            ("PCG-FOT, EIG-selected", sel, SEL_FILL, SEL_EDGE, 0.65, 2),
            ("PCG-FOT, no selection", rows, POOL_FILL, POOL_EDGE, 0.60, 3),
        ]:
            v = vals(rs, m)
            vc = v[v <= xmax]
            ax.hist(vc, bins=40, range=(0, xmax),
                    weights=np.full(len(vc), 1.0 / len(v)),
                    histtype="bar", facecolor=fill, edgecolor=edge, lw=0.7,
                    alpha=alpha, zorder=z, label=name)
        if 0 < len(fvals) <= 12:
            for i, fv in enumerate(sorted(fvals)):
                ax.axvline(fv, color="#D62728", lw=1.5, ls="--", zorder=4,
                           label=ov_label if i == 0 else None)
        elif len(fvals) == 0:
            ax.text(0.97, 0.55, f"{ov_label}: undefined",
                    ha="right", transform=ax.transAxes, fontsize=8.5, color="#D62728")
        handles, labels = ax.get_legend_handles_labels()
        order = [labels.index(x) for x in
                 ["PCG-FOT, no selection", "PCG-FOT, EIG-selected", ov_label]
                 if x in labels]
        ax.legend([handles[i] for i in order], [labels[i] for i in order],
                  loc="upper right", borderaxespad=0.6)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("probability")
        ax.set_ylim(top=ax.get_ylim()[1] * 1.08)
        fname = f"{bs}_{vtag}{sfx}"
        fig.savefig(os.path.join(A2, fname + ".png"), dpi=200, bbox_inches="tight")
        fig.savefig(os.path.join(A2, fname + ".pdf"), bbox_inches="tight")
        plt.close(fig)
        line = f"  {fname}: overlay n={len(fvals)}"
        if len(fvals):
            band = float(np.percentile(fvals, 50))
            vp, vs = vals(rows, m), vals(sel, m)
            line += (f" | median-band[0,{band:.2f}] pool {(vp<=band).mean()*100:.1f}%"
                     f" vs selected {(vs<=band).mean()*100:.1f}%")
        print(line)
print(f"[{datetime.now():%H:%M:%S}] -> {A2}")
