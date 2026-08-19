"""
원본 파라미터 분포 vs GMM 샘플링 parameter space의 Hellinger Distance 비교.
각 파라미터(v_ego, v_target, a_target)별로:
  Row 1: 원본 히스토그램 + GMM PDF 오버레이
  Row 2: GMM PDF만
  Row 3: 원본 vs 샘플링 히스토그램 겹침 + HD 표시
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture

# ━━ Paths ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_CSV = os.path.join(_MODULE_ROOT, "data", "processed", "ScenarioParameters", "distribution_entries_0_1.csv")  # LK 153프레임 — 정본 그림(HD 0.36/0.33/0.14) 조건 (2026-07-25 복원)
SAMPLED_CSV = os.path.join(_MODULE_ROOT, "data", "processed", "SPD", "ParamSpace", "LK_CIR_MER_RAB_FOT_param_space.csv")
OUTPUT_FIG = os.path.join(_MODULE_ROOT, "reports", "figures", "hellinger_comparison.png")

PARAMS = [
    ("v_ego", "v_ego_kmh", "v_ego", "km/h"),
    ("v_target", "v_target_kmh", "v_target", "km/h"),
    ("a_target", "a_target_ms2", "a_target", "m/s²"),
]

N_BINS = 30
GMM_K_RANGE = range(1, 6)


def hellinger_distance(p, q):
    """Discrete Hellinger distance: H(P,Q) = (1/sqrt(2)) * ||sqrt(P) - sqrt(Q)||_2"""
    return (1.0 / np.sqrt(2)) * np.sqrt(np.sum((np.sqrt(p) - np.sqrt(q)) ** 2))


def fit_best_gmm(data, k_range):
    """BIC 기준 최적 K로 1D GMM 피팅."""
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


def gmm_pdf(gm, x):
    """1D GMM의 PDF를 x 점들에서 계산."""
    X = x.reshape(-1, 1)
    log_prob = gm.score_samples(X)
    return np.exp(log_prob)


def main():
    df_orig = pd.read_csv(ORIGINAL_CSV)
    df_samp = pd.read_csv(SAMPLED_CSV)

    fig, axes = plt.subplots(3, 3, figsize=(16, 13))
    fig.suptitle("Parameter Distribution Analysis", fontsize=15, y=0.98)

    for col_idx, (name, orig_col, samp_col, unit) in enumerate(PARAMS):
        if orig_col not in df_orig.columns or samp_col not in df_samp.columns:
            print(f"  SKIP {name}: 컬럼 없음 ({orig_col} / {samp_col}) — drivingAlone 등 2-D 설계 데이터")
            continue
        orig = df_orig[orig_col].dropna().values
        samp = df_samp[samp_col].dropna().values

        lo = min(orig.min(), samp.min())
        hi = max(orig.max(), samp.max())
        margin = (hi - lo) * 0.05
        bins = np.linspace(lo, hi, N_BINS + 1)
        bin_width = bins[1] - bins[0]
        x_smooth = np.linspace(lo - margin, hi + margin, 500)

        # GMM 피팅 (데이터 2개 이상 필요)
        if len(orig) >= 2:
            gm = fit_best_gmm(orig, GMM_K_RANGE)
            pdf_vals = gmm_pdf(gm, x_smooth)
            n_comp = gm.n_components
            print(f"{name:>10}: best GMM K={n_comp}")
        else:
            gm = None
            pdf_vals = None
            n_comp = 0
            print(f"{name:>10}: GMM skipped (n={len(orig)} < 2)")

        # HD 계산
        hist_orig, _ = np.histogram(orig, bins=bins, density=True)
        hist_samp, _ = np.histogram(samp, bins=bins, density=True)
        p = hist_orig * bin_width
        q = hist_samp * bin_width
        p_sum = p.sum()
        q_sum = q.sum()
        if p_sum > 0:
            p = p / p_sum
        if q_sum > 0:
            q = q / q_sum
        hd = hellinger_distance(p, q)
        print(f"{'':>10}  HD = {hd:.4f}  (orig={len(orig)}, samp={len(samp)})")

        # Row 1: 원본 히스토그램 + GMM PDF
        ax1 = axes[0, col_idx]
        ax1.bar(bins[:-1], hist_orig, width=bin_width, alpha=0.5,
                color="C0", align="edge", edgecolor="none", label="FOT-RG3")
        if pdf_vals is not None:
            ax1.plot(x_smooth, pdf_vals, "r-", linewidth=2, label=f"GMM (K={n_comp})")
        ax1.set_title(f"{name} ({unit})")
        ax1.set_ylabel("Probability")
        ax1.legend(fontsize=12)

        # Row 2: GMM PDF만
        ax2 = axes[1, col_idx]
        if pdf_vals is not None:
            ax2.plot(x_smooth, pdf_vals, "r-", linewidth=2, label=f"GMM (K={n_comp})")
            ax2.fill_between(x_smooth, pdf_vals, alpha=0.15, color="r")
        else:
            ax2.text(0.5, 0.5, f"n={len(orig)}, GMM N/A", ha="center", va="center", transform=ax2.transAxes)
        ax2.set_title(f"{name} — GMM only")
        ax2.set_ylabel("Probability")
        ax2.legend(fontsize=12)

        # Row 3: 원본 vs 샘플링 겹침 + HD
        ax3 = axes[2, col_idx]
        ax3.bar(bins[:-1], hist_orig, width=bin_width, alpha=0.5,
                color="C0", align="edge", edgecolor="none", label=f"FOT-RG3 (n={len(orig)})")
        ax3.bar(bins[:-1], hist_samp, width=bin_width, alpha=0.5,
                color="C1", align="edge", edgecolor="none", label=f"Parameter Space (n={len(samp)})")
        ax3.set_title(f"{name} — HD = {hd:.4f}")
        ax3.set_xlabel(f"{name} ({unit})")
        ax3.set_ylabel("Probability")
        ax3.legend(fontsize=12)

    plt.tight_layout()
    plt.savefig(OUTPUT_FIG, dpi=150)
    print(f"\nFigure saved: {OUTPUT_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
