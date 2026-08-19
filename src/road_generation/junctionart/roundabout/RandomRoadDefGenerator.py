"""
RandomRoadDefGenerator
----------------------
Reproduces the random incident-road definition generation process described in
Section IV (Fig. 10) of:

    Ikram, Z., Muktadir, G. M., & Whitehead, J. (2023).
    Procedural Generation of Complex Roundabouts for Autonomous Vehicle Testing.
    IEEE Intelligent Vehicles Symposium (IV).

Paper specifies only (verbatim):
    "First we generate 20 n-way random roundabouts. The method requires us to
    first select a random circle with a radius of 35 to 45 meters and then
    randomly pick n points. Then we randomize their heading, and pass them
    into our generator (Fig. 10)."

The paper does NOT specify:
  - How to distribute the n points (uniform angle? jittered around uniform?
    free random on/near the circle?)
  - The amplitude of the heading randomization

This implementation uses an evenly-spaced angle layout with bounded jitter on
both position and heading. Defaults are chosen so that the generated incident
arrangements remain valid for ClassicGenerator while still exhibiting the
asymmetry shown in Fig. 10. Adjust at construction time if you want a
different operating regime.

Output format matches the ipConfig dict consumed by
``ClassicGenerator.generateWithIncidentPointConfiguration``:
    [{"x": float, "y": float, "heading": float}, ...]   # heading in radians
"""

import math
from typing import Dict, List, Tuple

import numpy as np


class RandomRoadDefGenerator:
    """Generate random ipConfig lists for Mode E (ClassicGenerator) evaluation.

    Parameters
    ----------
    radiusRange : tuple(float, float)
        Closed interval [r_min, r_max] (meters) from which the circle radius
        is sampled uniformly. Paper value: (35, 45).
    headingJitterDeg : float
        Half-width (degrees) of the uniform jitter added to each incident
        heading. The base heading points radially outward from the circle
        center; jitter is added on top.
    positionJitterDeg : float
        Half-width (degrees) of the uniform jitter added to each incident
        point's azimuth around the circle. Base azimuths are evenly spaced.
    seed : int or None
        Seed for the internal numpy RandomState. Two generators with the same
        seed produce the same sequence of ipConfigs.
    """

    def __init__(
        self,
        radiusRange: Tuple[float, float] = (35.0, 45.0),
        headingJitterDeg: float = 30.0,
        positionJitterDeg: float = 15.0,
        seed: int = 42,
    ) -> None:
        if radiusRange[0] <= 0 or radiusRange[1] < radiusRange[0]:
            raise ValueError(f"Invalid radiusRange: {radiusRange}")
        if headingJitterDeg < 0 or positionJitterDeg < 0:
            raise ValueError("Jitter values must be non-negative")

        self.radiusRange = radiusRange
        self.headingJitterRad = math.radians(headingJitterDeg)
        self.positionJitterRad = math.radians(positionJitterDeg)
        self._rng = np.random.RandomState(seed)
        self._lastCircle: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def generate(self, nIncident: int) -> List[Dict[str, float]]:
        """Generate one random ipConfig with ``nIncident`` incident points.

        Parameters
        ----------
        nIncident : int
            Number of incident roads. Must be >= 2. ClassicGenerator handles
            2..N, paper Fig.12 reports 3, 4, 5.

        Returns
        -------
        list of dict
            Each dict has keys ``"x"``, ``"y"``, ``"heading"`` (radians).
            The roundabout center is the origin (0, 0).
        """
        if nIncident < 2:
            raise ValueError(f"nIncident must be >= 2, got {nIncident}")

        radius = float(self._rng.uniform(self.radiusRange[0], self.radiusRange[1]))
        self._lastCircle = (0.0, 0.0, radius)

        baseAzimuths = np.linspace(0.0, 2.0 * math.pi, nIncident, endpoint=False)
        azimuthJitter = self._rng.uniform(
            -self.positionJitterRad, self.positionJitterRad, size=nIncident
        )
        azimuths = baseAzimuths + azimuthJitter

        headingJitter = self._rng.uniform(
            -self.headingJitterRad, self.headingJitterRad, size=nIncident
        )

        ipConfig: List[Dict[str, float]] = []
        for theta, h_jit in zip(azimuths, headingJitter):
            # Place point exactly on the circle to satisfy Phase 1 "no incident
            # points strictly inside the circle"; small radial jitter is left
            # to Phase 1's r = 0.4 * min_dist scaling.
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            # Base heading points radially outward (incident road departs from
            # the roundabout). Jitter is added on top.
            heading = theta + h_jit
            ipConfig.append({"x": float(x), "y": float(y), "heading": float(heading)})

        return ipConfig

    def lastCircle(self) -> Tuple[float, float, float]:
        """Return (cx, cy, radius) used by the most recent ``generate`` call.

        Useful for ERA validation: compare the fitted center/radius produced
        by ClassicGenerator with the ground-truth circle that originated the
        ipConfig.
        """
        return self._lastCircle
