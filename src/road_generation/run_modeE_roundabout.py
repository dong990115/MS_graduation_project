"""Mode E: 안쪽 숄더 포함 라운드어바웃 생성

기존 run_modeE_roundabout.py와 동일하되,
생성 후 링/bridge 세그먼트에 안쪽(left) 숄더를 추가하고
center lane 마크를 solid로 복구합니다.

Usage:
    python run_modeE_roundabout_inner_shoulder.py --seed 0 --radius 11.2 --output output/modeE_inner_seed0.xodr
"""
import argparse
import os
import math
import pyodrx
from junctionart.extensions.CountryCodes import CountryCodes
from junctionart.roundabout.ClassicGenerator import ClassicGenerator
from junctionart.roundabout.RandomRoadDefGenerator import RandomRoadDefGenerator


def parse_ip_string(s):
    parts = s.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"IP format must be 'x,y,heading_deg', got: '{s}'"
        )
    x, y, hdeg = float(parts[0]), float(parts[1]), float(parts[2])
    return {"x": x, "y": y, "heading": math.radians(hdeg)}


def _is_ring_road(road):
    """비정션 + right shoulder 있음 + left lane 없음 = 링/bridge 세그먼트."""
    if getattr(road, 'junctionId', None) is not None:
        return False
    has_right_shoulder = False
    for ls in road.lanes.lanesections:
        if len(ls.leftlanes) > 0:
            return False
        for lane in ls.rightlanes:
            if lane.lane_type == pyodrx.LaneType.shoulder:
                has_right_shoulder = True
    return has_right_shoulder


def add_inner_shoulder(odr, shoulder_width=3.0):
    """링/bridge + 정션 내 inner through road에 안쪽 숄더 추가 + center solid mark."""
    solid_mark = pyodrx.RoadMark(pyodrx.RoadMarkType.solid, 0.2,
                                 color=pyodrx.RoadMarkColor.standard)
    roads = odr.roads

    ring_ids = set()
    for rid, road in roads.items():
        if _is_ring_road(road):
            ring_ids.add(int(rid))

    for road in roads.values():
        is_ring = _is_ring_road(road)
        is_inner_through = (
            getattr(road, 'junctionId', None) is not None
            and getattr(road, 'predecessorOffset', None) == 0
            and road.predecessor is not None
            and road.successor is not None
            and int(road.predecessor.element_id) in ring_ids
            and int(road.successor.element_id) in ring_ids
        )

        if not (is_ring or is_inner_through):
            continue

        has_left = any(len(ls.leftlanes) > 0 for ls in road.lanes.lanesections)
        if has_left:
            continue

        for ls in road.lanes.lanesections:
            s = pyodrx.Lane(lane_type=pyodrx.LaneType.shoulder,
                            a=shoulder_width)
            s.set_material(surface="concrete")
            ls.add_left_lane(s)
            ls.centerlane.roadmark = solid_mark


def main():
    parser = argparse.ArgumentParser(
        description="Mode E roundabout with inner shoulder")
    parser.add_argument("--mode", default="random", choices=["random", "manual"])
    parser.add_argument("--nway", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ip", nargs="+", type=parse_ip_string)
    parser.add_argument("--laneWidth", type=float, default=3.5)
    parser.add_argument("--distorted", action="store_true", default=True)
    parser.add_argument("--useCenterOffset", action="store_true", default=True)
    parser.add_argument("--distortionAmplitude", type=float, default=0.25)
    parser.add_argument("--noiseFrequency", type=float, default=2.0)
    parser.add_argument("--noiseSeed", type=int, default=0)
    parser.add_argument("--clearanceFactor", type=float, default=1.2)
    parser.add_argument("--radius", type=float, default=None)
    parser.add_argument("--output", default="output/modeE_inner_roundabout.xodr")
    args = parser.parse_args()

    if args.mode == "manual":
        if not args.ip or len(args.ip) < 2:
            parser.error("--mode manual requires at least 2 --ip values")
        ipConfig = args.ip
        desc = f"manual {len(ipConfig)}-way"
    else:
        rng = RandomRoadDefGenerator(seed=args.seed)
        ipConfig = rng.generate(args.nway)
        desc = f"random {args.nway}-way (seed={args.seed})"

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    gen = ClassicGenerator(country=CountryCodes.US, laneWidth=args.laneWidth)
    odr = gen.generateWithIncidentPointConfiguration(
        ipConfig=ipConfig,
        odrId=0,
        nCircularLanes=2,
        useCenterOffset=args.useCenterOffset,
        distorted=args.distorted,
        distortionAmplitude=args.distortionAmplitude,
        noiseFrequency=args.noiseFrequency,
        noiseSeed=args.noiseSeed,
        clearanceFactor=args.clearanceFactor,
        overrideRadius=args.radius,
    )

    add_inner_shoulder(odr, shoulder_width=gen.shoulderWidth)

    odr.write_xml(args.output)
    print(f"[E+inner] {desc} → {args.output}")


if __name__ == "__main__":
    main()
