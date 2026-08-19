"""
FOT-RG3 원본 히스토그램 + GMM PDF + Parameter Space 샘플링 히스토그램
세 분포를 하나의 플랏에 겹쳐서 비교. 각 파라미터(v_ego, v_target, a_target)별 서브플랏.
"""

import os
import numpy as np

_MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture

# ━━ Paths ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORIGINAL_CSV = os.path.join(_MODULE_ROOT, "data", "processed", "ScenarioParameters", "distribution_entries_0_1.csv")
SAMPLED_CSV  = os.path.join(_MODULE_ROOT, "data", "processed", "SPD", "ParamSpace", "LK_CIR_MER_RAB_FOT_param_space.csv")
OUTPUT_FIG   = os.path.join(_MODULE_ROOT, "reports", "figures", "hellinger_overlay.png")

PARAMS = [
    ("v_ego",    "v_ego_kmh",    "v_ego",    "km/h"),
    ("v_target", "v_target_kmh", "v_target",  "km/h"),
    ("a_target", "a_target_ms2", "a_target",  r"m/s$^2$"),
]

N_BINS = 30
GMM_K_RANGE = range(1, 6)


def hellinger_distance(p, q):
    return (1.0 / np.sqrt(2)) * np.sqrt(np.sum((np.sqrt(p) - np.sqrt(q)) ** 2))


def fit_best_gmm(data, k_range):
    best_bic = np.inf
    best_gm = None
    X = data.reshape(-1, 1)
    for k in k_range:
        gm = GaussianMixture(n_components=k, random_state=42, max_iter=2000)
        gm.fit(X)
        bic = gm.bic(X)
        if bic < best_bic:
            best_bic = bic
            best_gm = gm
    return best_gm


def main():
    df_orig = pd.read_csv(ORIGINAL_CSV)
    df_samp = pd.read_csv(SAMPLED_CSV)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    fig.suptitle("FOT-RG3 vs GMM vs Parameter Space", fontsize=14, y=1.02)

    for col_idx, (name, orig_col, samp_col, unit) in enumerate(PARAMS):
        ax = axes[col_idx]

        orig = df_orig[orig_col].dropna().values
        samp = df_samp[samp_col].dropna().values

        lo = min(orig.min(), samp.min())
        hi = max(orig.max(), samp.max())
        margin = (hi - lo) * 0.05
        bins = np.linspace(lo - margin, hi + margin, N_BINS + 1)
        bin_width = bins[1] - bins[0]
        x_smooth = np.linspace(lo - margin, hi + margin, 500)

        hist_orig, _ = np.histogram(orig, bins=bins, density=True)
        hist_samp, _ = np.histogram(samp, bins=bins, density=True)

        # HD
        p = hist_orig * bin_width
        q = hist_samp * bin_width
        if p.sum() > 0:
            p = p / p.sum()
        if q.sum() > 0:
            q = q / q.sum()
        hd = hellinger_distance(p, q)

        # GMM
        if len(orig) >= 2:
            gm = fit_best_gmm(orig, GMM_K_RANGE)
            pdf_vals = np.exp(gm.score_samples(x_smooth.reshape(-1, 1)))
            n_comp = gm.n_components
        else:
            pdf_vals = None
            n_comp = 0

        ax.bar(bins[:-1], hist_orig, width=bin_width, alpha=0.45,
               color="#5B9BD5", align="edge", edgecolor="none",
               label=f"FOT-RG3 (n={len(orig)})")
        ax.bar(bins[:-1], hist_samp, width=bin_width, alpha=0.40,
               color="#ED7D31", align="edge", edgecolor="none",
               label=f"Parameter Space (n={len(samp)})")
        if pdf_vals is not None:
            ax.plot(x_smooth, pdf_vals, "r-", linewidth=2.2,
                    label=f"GMM (K={n_comp})")

        ax.set_xlabel(f"{name} ({unit})", fontsize=12)
        if col_idx == 0:
            ax.set_ylabel("Probability density", fontsize=12)
        ax.set_title(f"{name}  —  HD = {hd:.4f}", fontsize=12)
        ax.legend(fontsize=9, loc="upper right")
        ax.tick_params(labelsize=10)

        print(f"{name:>10}: GMM K={n_comp}, HD={hd:.4f}  (orig={len(orig)}, samp={len(samp)})")

    plt.tight_layout()
    plt.savefig(OUTPUT_FIG, dpi=200, bbox_inches="tight")
    print(f"\nSaved: {OUTPUT_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
