import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from typing import List, Dict, Optional, Tuple

plt.rcParams.update({'font.size': 10})


class RoundaboutPlots:
    """ERA (Expressive Range Analysis) plots for roundabout generation.

    Reproduces the visualizations described in the paper Section IV
    (Figures 11-15).  All plot methods accept an optional *outputPath*;
    when given, the figure is saved as PNG instead of shown interactively.
    """

    # ------------------------------------------------------------------ #
    # Fig.11 — Superimposed ring shapes (bird's-eye view)
    # ------------------------------------------------------------------ #
    @staticmethod
    def plotSuperimposed(
        profiles: Dict[str, Tuple[List[float], List[float]]],
        outputPath: Optional[str] = None,
    ):
        """Overlay multiple ring shapes as a bird's-eye (x, y) plot.

        Args:
            profiles: {label: (xs_normalized, ys_normalized)}.
                      Coordinates should be centered at origin and
                      normalized by mean radius (unit circle = 1.0).
            outputPath: if given, save PNG here.
        """
        fig, ax = plt.subplots(figsize=(6, 6))
        for label, (xs, ys) in profiles.items():
            xs_closed = list(xs) + [xs[0]]
            ys_closed = list(ys) + [ys[0]]
            ax.plot(xs_closed, ys_closed, alpha=0.3, linewidth=0.8)
        ax.set_aspect('equal')
        ax.set_xlabel("x (normalized)")
        ax.set_ylabel("y (normalized)")
        ax.set_title("Superimposed ring shapes")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        _save_or_show(fig, outputPath)

    # ------------------------------------------------------------------ #
    # Fig.12 — Radii distribution grouped by n-way
    # ------------------------------------------------------------------ #
    @staticmethod
    def plotRadiiDistribution(
        radii_by_nway: Dict[int, List[float]],
        outputPath: Optional[str] = None,
    ):
        """Histogram + KDE of radius values, one curve per n-way count."""
        import seaborn as sns
        fig, ax = plt.subplots(figsize=(8, 4))
        for n, radii in sorted(radii_by_nway.items()):
            sns.kdeplot(radii, ax=ax, label=f"{n}-way", fill=True, alpha=0.3)
        ax.set_xlabel("Radius (m)")
        ax.set_ylabel("Density")
        ax.set_title("Radii distribution by number of legs")
        ax.legend()
        fig.tight_layout()
        _save_or_show(fig, outputPath)

    # ------------------------------------------------------------------ #
    # Fig.13 — dRadius/dDistance distribution grouped by n-way
    # ------------------------------------------------------------------ #
    @staticmethod
    def plotDRadiiDistribution(
        dradii_by_nway: Dict[int, List[float]],
        outputPath: Optional[str] = None,
    ):
        """Histogram + KDE of dRadius/dDistance values."""
        import seaborn as sns
        fig, ax = plt.subplots(figsize=(8, 4))
        for n, dradii in sorted(dradii_by_nway.items()):
            sns.kdeplot(dradii, ax=ax, label=f"{n}-way", fill=True, alpha=0.3)
        ax.set_xlabel("dRadius / dDistance")
        ax.set_ylabel("Density")
        ax.set_title("Rate-of-change of radius distribution")
        ax.legend()
        fig.tight_layout()
        _save_or_show(fig, outputPath)

    # ------------------------------------------------------------------ #
    # Fig.14 — Same input 30 repetitions (only meaningful with Perlin)
    # ------------------------------------------------------------------ #
    @staticmethod
    def plotRepeatability(
        ring_profiles: List[Tuple[List[float], List[float]]],
        outputPath: Optional[str] = None,
    ):
        """Overlay ring shapes from repeated trials of the same input.

        Args:
            ring_profiles: list of (xs_norm, ys_norm) tuples, one per trial.
        """
        fig, ax = plt.subplots(figsize=(6, 6))
        for xs, ys in ring_profiles:
            xs_closed = list(xs) + [xs[0]]
            ys_closed = list(ys) + [ys[0]]
            ax.plot(xs_closed, ys_closed, alpha=0.3, linewidth=0.8)
        ax.set_aspect('equal')
        ax.set_xlabel("x (normalized)")
        ax.set_ylabel("y (normalized)")
        ax.set_title(f"Repeatability ({len(ring_profiles)} trials, same input)")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        _save_or_show(fig, outputPath)

    # ------------------------------------------------------------------ #
    # Fig.15 — Bivariate KDE  (radii × dRadii) — pixel heatmap
    # ------------------------------------------------------------------ #
    @staticmethod
    def plotBivariateKDE(
        radii: List[float],
        dradii: List[float],
        outputPath: Optional[str] = None,
        bins: int = 64,
        sigma: float = 1.5,
    ):
        """2-D density heatmap of (radius, dRadius/dDistance).

        Uses histogram2d + Gaussian smoothing for pixel-style output
        matching the paper's Fig.15.
        """
        fig, ax = plt.subplots(figsize=(6, 5))
        H, xedges, yedges = np.histogram2d(radii, dradii, bins=bins)
        H = gaussian_filter(H.astype(float), sigma=sigma)
        ax.imshow(
            H.T, origin='lower', aspect='auto',
            extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
            cmap='hot', interpolation='bilinear',
        )
        ax.set_xlabel("Radius (m)")
        ax.set_ylabel("dRadius / dDistance")
        ax.set_title("Bivariate density (radii × dRadii)")
        fig.tight_layout()
        _save_or_show(fig, outputPath)


# ------------------------------------------------------------------ #
# Helper
# ------------------------------------------------------------------ #
def _save_or_show(fig, path: Optional[str]):
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=150)
        plt.close(fig)
    else:
        plt.show()
