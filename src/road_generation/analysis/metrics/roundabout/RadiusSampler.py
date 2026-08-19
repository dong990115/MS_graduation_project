import numpy as np
import math
from typing import List, Tuple


class RadiusSampler:
    """Samples radius values along roundabout ring roads.

    For each ring road segment, evaluates geometry at evenly spaced points
    and measures the distance from the roundabout center. For a perfect
    circular ring all radii are equal; Perlin-distorted rings will show
    variation captured by these samples.

    Design decision F1 (CLAUDE_PLAN.md): nSamplesPerRoad=20 (default).
    Design decision F2: caller passes center — no re-fitting here.
    """

    def __init__(self, centerX, centerY, nSamplesPerRoad=20):
        self.cx = centerX
        self.cy = centerY
        self.nSamplesPerRoad = nSamplesPerRoad

    def sampleFromRoads(self, ringRoads) -> Tuple[List[float], List[float]]:
        """Sample radii along an ordered list of ring road segments.

        Args:
            ringRoads: list of ExtendedRoad objects forming the ring
                       (excluding the joint road).

        Returns:
            (cumulative_distances, radii, xs, ys) — parallel lists.
            cumulative_distances[i] = arc-length from start of ring to
            sample i.  radii[i] = distance from center at that sample.
            xs[i], ys[i] = absolute (x, y) position of that sample.
        """
        cumulative_distances = []
        radii = []
        xs = []
        ys = []
        cum_s = 0.0

        for road in ringRoads:
            geom = road.planview._raw_geometries[0]
            x0 = road.planview.x_start
            y0 = road.planview.y_start
            h0 = road.planview.h_start
            length = geom.length

            for j in range(self.nSamplesPerRoad):
                t = j / self.nSamplesPerRoad
                s = t * length
                px, py = self._evalGeometry(geom, x0, y0, h0, s)
                r = math.hypot(px - self.cx, py - self.cy)
                cumulative_distances.append(cum_s + s)
                radii.append(r)
                xs.append(px)
                ys.append(py)

            cum_s += length

        return cumulative_distances, radii, xs, ys

    # ------------------------------------------------------------------
    # Geometry evaluators
    # ------------------------------------------------------------------

    def _evalGeometry(self, geom, x0, y0, h0, s):
        """Dispatch to the right evaluator based on geometry type."""
        typeName = type(geom).__name__
        if typeName == "Arc":
            return self._evalArc(geom, x0, y0, h0, s)
        if typeName == "ParamPoly3":
            return self._evalParamPoly3(geom, x0, y0, h0, s)
        if typeName == "Line":
            return self._evalLine(x0, y0, h0, s)
        raise ValueError(f"Unsupported geometry type: {typeName}")

    @staticmethod
    def _evalArc(geom, x0, y0, h0, s):
        kappa = geom.curvature
        R = 1.0 / abs(kappa)
        if kappa > 0:
            phi0 = h0 - np.pi / 2
        else:
            phi0 = h0 + np.pi / 2
        arc_cx = x0 - np.cos(phi0) * R
        arc_cy = y0 - np.sin(phi0) * R
        theta = s * kappa
        px = arc_cx + np.cos(phi0 + theta) * R
        py = arc_cy + np.sin(phi0 + theta) * R
        return px, py

    @staticmethod
    def _evalParamPoly3(geom, x0, y0, h0, s):
        if geom.prange == "normalized":
            p = s / geom.length if geom.length else 0
        else:
            p = s
        u = geom.au + geom.bu * p + geom.cu * p**2 + geom.du * p**3
        v = geom.av + geom.bv * p + geom.cv * p**2 + geom.dv * p**3
        cos_h = np.cos(h0)
        sin_h = np.sin(h0)
        px = x0 + u * cos_h - v * sin_h
        py = y0 + u * sin_h + v * cos_h
        return px, py

    @staticmethod
    def _evalLine(x0, y0, h0, s):
        return x0 + s * np.cos(h0), y0 + s * np.sin(h0)
