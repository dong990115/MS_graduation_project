"""
Mode E evaluation pipeline — ERA (Expressive Range Analysis) for roundabouts.

Usage:
    python run_modeE_eval.py --mode baseline
    python run_modeE_eval.py --mode baseline --nways 3 4 5 --trials 20

Modes:
    baseline      — perfect circular ring, naive closest segment selection
    centerOffset  — (Task 2) ring + centerOffset segment selection
    distorted     — (Task 3) Perlin-distorted ring
    full          — centerOffset + Perlin distortion

Output:
    output/eval/{mode}/era_radii_{n}way.png       (Fig.12)
    output/eval/{mode}/era_dradii_{n}way.png      (Fig.13)
    output/eval/{mode}/era_superimposed_{n}way.png (Fig.11)
    output/eval/{mode}/era_bivariate_{n}way.png    (Fig.15)
"""

import argparse
import math
import os
import sys
import traceback

from junctionart.roundabout.RandomRoadDefGenerator import RandomRoadDefGenerator
from junctionart.roundabout.ClassicGenerator import ClassicGenerator
from junctionart.extensions.CountryCodes import CountryCodes
from analysis.metrics.roundabout.RadiusSampler import RadiusSampler
from analysis.metrics.roundabout.RadiusDerivative import RadiusDerivative
from analysis.metrics.roundabout.RoundaboutPlots import RoundaboutPlots


N_RING_SEGMENTS = 10


def generate_roundabout(ipConfig, mode="baseline", noiseSeed=0):
    useCenterOffset = mode in ("centerOffset", "full")
    distorted = mode in ("distorted", "full")
    gen = ClassicGenerator(country=CountryCodes.US)
    odr = gen.generateWithIncidentPointConfiguration(
        ipConfig=ipConfig, odrId=0, nCircularLanes=1,
        useCenterOffset=useCenterOffset,
        distorted=distorted,
        noiseSeed=noiseSeed,
    )
    return odr, gen


def run_trials(nway, nTrials, mode, seed_base=0):
    """Generate *nTrials* roundabouts and collect ERA samples.

    Returns:
        all_radii       — flat list of all radius samples
        all_dradii      — flat list of all dRadius/dDistance samples
        profiles        — {trial_label: (xs_norm, ys_norm)} for superimposed plot
    """
    all_radii = []
    all_dradii = []
    profiles = {}

    for trial in range(nTrials):
        seed = seed_base + trial
        rng = RandomRoadDefGenerator(seed=seed)
        ipConfig = rng.generate(nway)

        try:
            odr, gen = generate_roundabout(ipConfig, mode, noiseSeed=seed)
        except Exception:
            print(f"  [WARN] trial {trial} (seed={seed}) failed, skipping:")
            traceback.print_exc()
            continue

        sampler = RadiusSampler(gen.center.x, gen.center.y, nSamplesPerRoad=20)
        ring_roads = list(odr.roads.values())[:N_RING_SEGMENTS]
        dists, radii, xs, ys = sampler.sampleFromRoads(ring_roads)
        _, dradii = RadiusDerivative.compute(dists, radii)

        all_radii.extend(radii)
        all_dradii.extend(dradii)

        mean_r = sum(radii) / len(radii) if radii else 1.0
        xs_norm = [(x - gen.center.x) / mean_r for x in xs]
        ys_norm = [(y - gen.center.y) / mean_r for y in ys]
        profiles[f"trial-{trial}"] = (xs_norm, ys_norm)

    return all_radii, all_dradii, profiles


def main():
    parser = argparse.ArgumentParser(description="Mode E ERA evaluation")
    parser.add_argument("--mode", default="baseline",
                        choices=["baseline", "centerOffset", "distorted", "full"])
    parser.add_argument("--nways", type=int, nargs="+", default=[3, 4, 5])
    parser.add_argument("--trials", type=int, default=20)
    args = parser.parse_args()

    outdir = os.path.join("output", "eval", args.mode)
    os.makedirs(outdir, exist_ok=True)

    if args.mode in ("distorted", "full"):
        print(f"[INFO] Perlin distortion enabled (amplitude=0.25, frequency=2.0)")

    radii_by_nway = {}
    dradii_by_nway = {}

    for nway in args.nways:
        print(f"=== {nway}-way, mode={args.mode}, trials={args.trials} ===")
        all_radii, all_dradii, profiles = run_trials(
            nway, args.trials, args.mode, seed_base=nway * 1000,
        )
        radii_by_nway[nway] = all_radii
        dradii_by_nway[nway] = all_dradii

        if profiles:
            RoundaboutPlots.plotSuperimposed(
                profiles,
                os.path.join(outdir, f"era_superimposed_{nway}way.png"),
            )
            print(f"  saved era_superimposed_{nway}way.png")

        if all_radii and all_dradii:
            RoundaboutPlots.plotBivariateKDE(
                all_radii, all_dradii,
                os.path.join(outdir, f"era_bivariate_{nway}way.png"),
            )
            print(f"  saved era_bivariate_{nway}way.png")

    RoundaboutPlots.plotRadiiDistribution(
        radii_by_nway,
        os.path.join(outdir, "era_radii_all.png"),
    )
    print(f"saved era_radii_all.png")

    RoundaboutPlots.plotDRadiiDistribution(
        dradii_by_nway,
        os.path.join(outdir, "era_dradii_all.png"),
    )
    print(f"saved era_dradii_all.png")

    print(f"\nDone. Output in {outdir}/")


if __name__ == "__main__":
    main()
