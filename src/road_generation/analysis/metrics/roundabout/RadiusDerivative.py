import numpy as np
from typing import List, Tuple


class RadiusDerivative:
    """Computes dRadius/dDistance along a roundabout ring.

    Uses central finite differences on interior points and forward/backward
    differences at boundaries.  Matches the paper's Fig.13 metric
    ("rate of change of radius with respect to distance along the ring").
    """

    @staticmethod
    def compute(distances: List[float], radii: List[float]) -> Tuple[List[float], List[float]]:
        """Compute dRadius/dDistance.

        Args:
            distances: cumulative arc-length values (monotonically increasing).
            radii: radius values at each distance.

        Returns:
            (mid_distances, dradii) — parallel lists.
            mid_distances are the evaluation points;
            dradii are the derivative estimates.
        """
        d = np.asarray(distances, dtype=float)
        r = np.asarray(radii, dtype=float)
        n = len(d)
        if n < 2:
            return [], []

        mid = np.empty(n)
        dr = np.empty(n)

        dr[0] = (r[1] - r[0]) / (d[1] - d[0]) if d[1] != d[0] else 0.0
        mid[0] = d[0]

        for i in range(1, n - 1):
            ds = d[i + 1] - d[i - 1]
            dr[i] = (r[i + 1] - r[i - 1]) / ds if ds != 0 else 0.0
            mid[i] = d[i]

        dr[-1] = (r[-1] - r[-2]) / (d[-1] - d[-2]) if d[-1] != d[-2] else 0.0
        mid[-1] = d[-1]

        return mid.tolist(), dr.tolist()
