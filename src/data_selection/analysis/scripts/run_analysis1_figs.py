"""Analysis 1 outputs — NORMALIZED shape metrics (decision 2026-07-13).

Input : output/analysis1/shape_stats.csv, shape_pool.npz
        (raw r_k, dr_k per network from run_analysis1_batch.py; ring
         centerline sampled at ds = 0.5 m, masked gaps excluded)
Metric: per network with mean radius r_bar = mean(r_k),
          x~_k  = (r_k - r_bar) / r_bar     normalized radial deviation
          dr~_k = (r_k - r_{k-1}) / r_bar   normalized radius change
        0 = perfectly circular at that sample; +-0.05 = 5 % of the mean
        radius outward/inward. Size (r_bar) is removed by construction.
Output: Fig1a (x~ density), Fig1b (dr~ density),
        Fig1c (x~, dr~) 2D — spec adoption criteria evaluated and printed,
        Table1_shape_diversity.csv
"""
import os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- publication style ---------------------------------------------------
# blue-orange pair: hues stay separable under red-green CVD, and the two
# fills differ in lightness so they also separate in grayscale print
PCG_FILL, PCG_EDGE = "#A8CBE3", "#3D7CB0"   # light blue
FP_FILL, FP_EDGE = "#F5A25D", "#C55A11"     # orange
plt.rcParams.update({
    "font.size": 11, "axes.labelsize": 11.5, "legend.fontsize": 9.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.9, "xtick.direction": "out", "ytick.direction": "out",
    "legend.frameon": False, "pdf.fonttype": 42,
})

# 산출물은 저장소 재구성 시 results/ 로 이동했다 (scripts/ -> ../../../.. = 저장소 루트).
A1 = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                  "results", "eig_selection", "analysis1")

rows = list(csv.DictReader(open(os.path.join(A1, "shape_stats.csv"))))
pool = np.load(os.path.join(A1, "shape_pool.npz"))


def normalized(group):
    """pooled x~ and dr~ over all networks of a group + per-network dict."""
    xs, ds, per = [], [], {}
    for r in rows:
        if r["group"] != group or r["ok"] != "1":
            continue
        rbar = float(r["r_bar"])
        x = (pool["r_" + r["name"]] - rbar) / rbar
        d = pool["dr_" + r["name"]] / rbar
        xs.append(x)
        ds.append(d)
        per[r["name"]] = (x, d)
    return np.concatenate(xs), np.concatenate(ds), per


x_pcg, d_pcg, per_pcg = normalized("PCG")
x_fp, d_fp, per_fp = normalized("Real")
print(f"PCG: x~ n={len(x_pcg)}, dr~ n={len(d_pcg)} | FP: x~ n={len(x_fp)}, dr~ n={len(d_fp)}")


def dist_fig(v_pcg, v_fp, xlabel, fname, nbins=70):
    # symmetric range about 0 (the perfect-circle reference)
    m = 1.04 * max(abs(min(v_pcg.min(), v_fp.min())),
                   abs(max(v_pcg.max(), v_fp.max())))
    bins = np.linspace(-m, m, nbins)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    # probability normalization: bar height = fraction of the set's samples
    # in that bin (heights of each set sum to 1; 0.3 reads as 30 %)
    ax.hist(v_pcg, bins=bins, weights=np.full(len(v_pcg), 1.0 / len(v_pcg)),
            histtype="bar", facecolor=PCG_FILL, edgecolor=PCG_EDGE, lw=0.7,
            alpha=0.75, label="PCG roundabout")
    ax.hist(v_fp, bins=bins, weights=np.full(len(v_fp), 1.0 / len(v_fp)),
            histtype="bar", facecolor=FP_FILL, edgecolor=FP_EDGE, lw=0.7,
            alpha=0.65, label="FP roundabout")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("probability")
    ax.set_xlim(-m, m)
    ax.set_ylim(top=ax.get_ylim()[1] * 1.08)   # headroom so bars never touch it
    ax.legend(loc="upper right", borderaxespad=0.6)
    fig.savefig(os.path.join(A1, fname + ".png"), dpi=200, bbox_inches="tight")
    fig.savefig(os.path.join(A1, fname + ".pdf"), bbox_inches="tight")
    plt.close(fig)


dist_fig(x_pcg, x_fp, "normalized radial deviation", "Fig1a_radius_dist")
dist_fig(d_pcg, d_fp, "normalized radius change", "Fig1b_radius_change_dist")

# ---------------- Fig 1c: 2D + adoption criteria -------------------------
def paired(per):
    out = []
    for x, d in per.values():
        n = min(len(x), len(d))
        out.append(np.column_stack([x[:n], d[:n]]))
    return np.vstack(out)


xy_pcg = paired(per_pcg)
xy_fp = paired(per_fp)
fig, ax = plt.subplots(figsize=(6.6, 5.2))
ax.scatter(xy_pcg[:, 0], xy_pcg[:, 1], s=8, color=PCG_FILL, alpha=0.35,
           edgecolors="none", label="PCG roundabout")
ax.scatter(xy_fp[:, 0], xy_fp[:, 1], s=8, color=FP_FILL, edgecolors="none",
           label="FP roundabout")
ax.set_xlabel("normalized radial deviation")
ax.set_ylabel("normalized radius change")
ax.set_ylim(top=ax.get_ylim()[1] * 1.15)   # headroom for the fixed legend
ax.legend(loc="upper right", borderaxespad=0.6)
fig.savefig(os.path.join(A1, "Fig1c_2d_shape.png"), dpi=200, bbox_inches="tight")
fig.savefig(os.path.join(A1, "Fig1c_2d_shape.pdf"), bbox_inches="tight")
plt.close(fig)

H, xe, ye = np.histogram2d(xy_pcg[:, 0], xy_pcg[:, 1], bins=60)
ix = np.clip(np.searchsorted(xe, xy_fp[:, 0]) - 1, 0, H.shape[0] - 1)
iy = np.clip(np.searchsorted(ye, xy_fp[:, 1]) - 1, 0, H.shape[1] - 1)
frac_inside = float((H[ix, iy] > 0).mean())
corr = float(np.corrcoef(xy_pcg[:, 0], xy_pcg[:, 1])[0, 1])
print(f"[Fig1c criteria] FP inside PCG cloud: {frac_inside*100:.1f}% | "
      f"PCG x~-dr~ corr: {corr:+.3f}")

# ---------------- Table 1 ----------------
def qband(fp_vals, pcg_vals):
    pos = np.searchsorted(np.sort(pcg_vals), fp_vals) / len(pcg_vals) * 100
    return f"[p{pos.min():.1f}, p{pos.max():.1f}]"


def srow(label, n_net, xv, dv, extra_x="", extra_d=""):
    iqr = lambda v: f"[{np.percentile(v,25):.4f}, {np.percentile(v,75):.4f}]"
    return [label, n_net,
            f"[{xv.min():.4f}, {xv.max():.4f}]", iqr(xv), f"{xv.std():.4f}", extra_x,
            f"[{dv.min():.5f}, {dv.max():.5f}]", iqr(dv), f"{dv.std():.5f}", extra_d,
            len(xv), len(dv)]


tab = [srow("PCG (n=1,000)", 1000, x_pcg, d_pcg)]
tab.append(srow("FP roundabouts (n=2)", 2, x_fp, d_fp,
                qband(x_fp, x_pcg), qband(d_fp, d_pcg)))
for name, (x, d) in per_fp.items():
    tab.append(srow(f"  FP {name.split('_')[-1]}", 1, x, d,
                    qband(x, x_pcg), qband(d, d_pcg)))
hdr = ["set", "n_networks", "x_range", "x_IQR", "x_SD", "x_FP_in_PCG_CDF",
       "dr_range", "dr_IQR", "dr_SD", "dr_FP_in_PCG_CDF", "N_x", "N_dr"]
with open(os.path.join(A1, "Table1_shape_diversity.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(hdr)
    w.writerows(tab)
print("Table 1:")
for row in [hdr] + tab:
    print("  " + " | ".join(str(c) for c in row))
print("->", A1)
