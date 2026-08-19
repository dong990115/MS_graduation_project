"""Mode E: 절차적 생성 단계별 시각화

논문 Figure처럼 각 단계 후 중간 결과를 이미지로 저장.

Stage 1: 원형 링 (perfect circle)
Stage 2: Perlin distortion 적용 (불규칙 형상)
Stage 3: 접근로(approach road) 추가
Stage 4: 정션 연결 + 최종 완성

Usage:
    python run_modeE_stages.py --seed 0
    python run_modeE_stages.py --seed 0 --nway 4 --output-dir output/stages
"""

import argparse
import os
import math
import numpy as np
import matplotlib.pyplot as plt
import pyodrx

from junctionart.extensions.CountryCodes import CountryCodes
from junctionart.roundabout.ClassicGenerator import ClassicGenerator
from junctionart.roundabout.RandomRoadDefGenerator import RandomRoadDefGenerator
from junctionart.junctions.LaneSides import LaneSides
from junctionart import extensions
from junctionart.junctions.RoadLinker import RoadLinker
from junctionart.junctions.ODRHelper import ODRHelper


def _eval_geom(geom, x0, y0, h0, s):
    """RadiusSampler와 동일한 geometry 평가."""
    typeName = type(geom).__name__
    if typeName == "Arc":
        kappa = geom.curvature
        R = 1.0 / abs(kappa)
        phi0 = h0 - np.pi / 2 if kappa > 0 else h0 + np.pi / 2
        arc_cx = x0 - np.cos(phi0) * R
        arc_cy = y0 - np.sin(phi0) * R
        theta = s * kappa
        return arc_cx + np.cos(phi0 + theta) * R, arc_cy + np.sin(phi0 + theta) * R
    if typeName == "ParamPoly3":
        p = s / geom.length if getattr(geom, 'prange', 'normalized') == 'normalized' and geom.length else s
        u = geom.au + geom.bu * p + geom.cu * p**2 + geom.du * p**3
        v = geom.av + geom.bv * p + geom.cv * p**2 + geom.dv * p**3
        cos_h, sin_h = np.cos(h0), np.sin(h0)
        return x0 + u * cos_h - v * sin_h, y0 + u * sin_h + v * cos_h
    if typeName == "Line":
        return x0 + s * np.cos(h0), y0 + s * np.sin(h0)
    return x0, y0


def plot_roads_xy(roads, title, output_path, center=None, radius=None,
                  highlight_roads=None, highlight_color="C1"):
    """도로의 중심선을 x-y 평면에 플롯."""
    fig, ax = plt.subplots(figsize=(8, 8))

    for road in roads:
        xs, ys = [], []
        for geom in road.planview._raw_geometries:
            x0 = road.planview.x_start
            y0 = road.planview.y_start
            h0 = road.planview.h_start
            length = geom.length
            n_pts = max(int(length / 0.5), 20)
            for j in range(n_pts):
                s = (j / n_pts) * length
                px, py = _eval_geom(geom, x0, y0, h0, s)
                xs.append(px)
                ys.append(py)

        is_highlight = highlight_roads and road in highlight_roads
        color = highlight_color if is_highlight else "C0"
        lw = 3.5 if is_highlight else 2.5
        alpha = 1.0 if is_highlight else 0.8
        ax.plot(xs, ys, color=color, linewidth=lw, alpha=alpha)

    if center is not None and radius is not None:
        theta = np.linspace(0, 2 * np.pi, 200)
        cx = center[0] + radius * np.cos(theta)
        cy = center[1] + radius * np.sin(theta)
        ax.plot(cx, cy, "k--", alpha=0.2, linewidth=0.8, label=f"r={radius:.1f}m")
        ax.legend(fontsize=10)

    ax.set_aspect("equal")
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Mode E stage-by-stage visualization")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--nway", type=int, default=4)
    parser.add_argument("--radius", type=float, default=None)
    parser.add_argument("--output-dir", default="output/stages")
    args = parser.parse_args()

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)
    prefix = f"seed{args.seed}_{args.nway}way"

    rng = RandomRoadDefGenerator(seed=args.seed)
    ipConfig = rng.generate(args.nway)

    gen = ClassicGenerator(country=CountryCodes.US, laneWidth=3.5)

    incidentPoints = gen.parseIncidentPoints(ipConfig)
    gen.connectionBuilder.config.dic["default_lane_width"] = gen.laneWidth

    # ── Stage 1: Perfect circular ring ──
    center, radius = gen.getCircle(incidentPoints)
    if args.radius is not None:
        radius = args.radius
    gen.center = center
    gen.radius = radius

    nSegments = 12
    nCircularLanes = 2

    circularRoads_perfect, circularRoadStartPoints_perfect = gen.getCircularRoads(
        center, radius, 0, nLanes=nCircularLanes,
        laneSides=LaneSides.RIGHT, nSegments=nSegments,
    )
    for cr in circularRoads_perfect:
        gen._addShoulders(cr, sides='right')
    gen.createSuccPreRelationBetweenCircularRoads(circularRoads_perfect)

    odr_s1 = extensions.createOdrByPredecessor(
        "stage1", circularRoads_perfect, [], countryCode=gen.countryCode
    )
    odr_s1.updateRoads(circularRoads_perfect)
    odr_s1.resetAndReadjust(byPredecessor=True)
    ODRHelper.transform(odr_s1,
                        startX=circularRoadStartPoints_perfect[0].x,
                        startY=circularRoadStartPoints_perfect[0].y, heading=0)

    plot_roads_xy(circularRoads_perfect,
                  f"Stage 1: Circular Ring (r={radius:.1f}m)",
                  os.path.join(out_dir, f"{prefix}_stage1_circle.png"),
                  center=(center.x, center.y), radius=radius)

    # ── Stage 2: Distorted ring (Perlin noise) ──
    circularRoads, circularRoadStartPoints = gen.getDistortedCircularRoads(
        center, radius, 0, nLanes=nCircularLanes,
        laneSides=LaneSides.RIGHT, nSegments=nSegments,
        distortionAmplitude=0.25, noiseFrequency=2.0, noiseSeed=0,
    )
    for cr in circularRoads:
        gen._addShoulders(cr, sides='right')
        gen._removeCenterRoadMark(cr)
        gen._setBrokenLaneMarks(cr)
    gen.createSuccPreRelationBetweenCircularRoads(circularRoads)

    odr_s2 = extensions.createOdrByPredecessor(
        "stage2", circularRoads, [], countryCode=gen.countryCode
    )
    odr_s2.updateRoads(circularRoads)
    odr_s2.resetAndReadjust(byPredecessor=True)
    ODRHelper.transform(odr_s2,
                        startX=circularRoadStartPoints[0].x,
                        startY=circularRoadStartPoints[0].y, heading=0)

    RoadLinker.createExtendedPredSuc(
        predRoad=circularRoads[-1], predCp=pyodrx.ContactPoint.end,
        sucRoad=circularRoads[0], sucCP=pyodrx.ContactPoint.start,
    )

    plot_roads_xy(circularRoads,
                  "Stage 2: Perlin-Distorted Ring",
                  os.path.join(out_dir, f"{prefix}_stage2_distorted.png"),
                  center=(center.x, center.y), radius=radius)

    # ── Stage 3: + Approach roads ──
    minClearanceFactor = (radius + nCircularLanes * gen.laneWidth + 10.0) / radius
    effectiveClearanceFactor = max(1.2, minClearanceFactor)

    firstApproachRoadId = len(circularRoads)
    approachRoads, approachEndpoints = gen.createApproachRoads(
        incidentPoints, firstApproachRoadId,
        adaptiveLength=False,
        clearanceFactor=effectiveClearanceFactor,
        roadDirection='heading',
    )

    plot_roads_xy(list(circularRoads) + list(approachRoads),
                  f"Stage 3: + Approach Roads ({args.nway}-way)",
                  os.path.join(out_dir, f"{prefix}_stage3_approach.png"),
                  center=(center.x, center.y), radius=radius,
                  highlight_roads=approachRoads, highlight_color="C3")

    # ── Stage 4: Full generation (junctions + connections) ──
    odr_full = gen.generateWithIncidentPointConfiguration(
        ipConfig=ipConfig, odrId=0, nCircularLanes=2,
        useCenterOffset=True, distorted=True,
        distortionAmplitude=0.25, noiseFrequency=2.0, noiseSeed=0,
        clearanceFactor=1.2, overrideRadius=args.radius,
    )

    all_roads = list(odr_full.roads.values())
    plot_roads_xy(all_roads,
                  "Stage 4: Complete Roundabout",
                  os.path.join(out_dir, f"{prefix}_stage4_complete.png"),
                  center=(center.x, center.y), radius=radius)

    print(f"\nDone. All stages saved to {out_dir}/")


if __name__ == "__main__":
    main()
