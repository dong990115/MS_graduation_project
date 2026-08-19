"""Trajectory loaders for interaction-metric computation.

Two sources, one output convention:
  ego_xy (N,2) [m] global,  ego_v (N,) [m/s],  ego_yaw (N,) [rad]
  tgt_xy (N,2) [m] global,  tgt_v (N,) [m/s],  tgt_yaw (N,) [rad]
  t (N,) [s],  valid (N,) bool  (frames where the target track exists)

1) CarMaker time-series .mat (PSM training data / v13 PCG / v13 realFOT):
   positions are already global (Car.tx/ty, Traffic.T00.tx/ty). Vehicle
   reference-point kinematics are used as-is (same convention as the
   project's own GT pipeline, cm13/tools/diagnose_gt.m).

2) FOT SF_PP .mat (EXP_RG3): sensor-fusion tracks are ego-relative. The ego
   path is reconstructed by integrating vehicle speed and yaw rate; targets
   are placed by rotating the relative position into that frame. The target
   is the nearest fusion track with vehicle recognition, following the
   project's own convention (ClassificationOfFalsePositive/SubFcn/
   getFalsePositiveState.m).
"""
from dataclasses import dataclass

import numpy as np
from scipy.io import loadmat


@dataclass
class Pair:
    t: np.ndarray
    ego_xy: np.ndarray
    ego_v: np.ndarray
    ego_yaw: np.ndarray
    tgt_xy: np.ndarray
    tgt_v: np.ndarray
    tgt_yaw: np.ndarray
    valid: np.ndarray
    meta: dict


# ---------------------------------------------------------------- CarMaker
def _cm_field(data, name):
    item = data.flat[0][name].flat[0]
    return np.asarray(item["data"]).ravel().astype(float)


def load_carmaker(path):
    d = loadmat(path, squeeze_me=False, struct_as_record=True)
    data = d["data"]
    f = lambda n: _cm_field(data, n)
    t = f("Time")
    ego_xy = np.column_stack([f("Car_tx"), f("Car_ty")])
    ego_v = f("Car_v")
    ego_yaw = f("Car_Yaw")
    tgt_xy = np.column_stack([f("Traffic_T00_tx"), f("Traffic_T00_ty")])
    tgt_v = f("Traffic_T00_LongVel")
    tgt_yaw = f("Traffic_T00_rz")
    # target exists while it moves or sits away from the world origin
    valid = (np.hypot(tgt_xy[:, 0], tgt_xy[:, 1]) > 1e-6)
    return Pair(t, ego_xy, ego_v, ego_yaw, tgt_xy, tgt_v, tgt_yaw, valid,
                {"source": "carmaker", "path": path})


# ---------------------------------------------------------------- SF_PP
def _idx(struct_arr, *names):
    """walk nested (1,1) struct arrays by field name, return int index."""
    cur = struct_arr
    for n in names:
        cur = cur[n].flat[0]
    return int(np.asarray(cur).ravel()[0])


def load_sfpp(path, start=None, end=None):
    """Load one SF_PP trip (optionally a [start, end] 1-based frame window)."""
    d = loadmat(path, squeeze_me=False, struct_as_record=True)
    sf = d["SF_PP"].flat[0]
    sim_time = np.asarray(sf["sim_time"]).ravel().astype(float)
    n = len(sim_time)
    ivs = np.asarray(sf["In_Vehicle_Sensor_sim"], dtype=float)          # (n, 20)
    ivs_idx = sf["IN_VEHICLE_SENSOR"].flat[0]
    i_speed = _idx(ivs_idx, "PREPROCESSING", "VEHICLE_SPEED") - 1
    i_yawrate = _idx(ivs_idx, "PREPROCESSING", "YAW_RATE") - 1
    speed = ivs[:, i_speed]          # units checked at call site (see smoke test)
    yawrate = ivs[:, i_yawrate]
    ftm = np.asarray(sf["Fusion_Track_Maneuver"], dtype=float)          # (58, 64, n)
    ft = sf["FUSION_TRACK"].flat[0]
    g = lambda *nm: _idx(ft, *nm) - 1
    ROW = {
        "id": g("TRACKING", "ID"),
        "px": g("TRACKING", "REL_POS_X"),
        "py": g("TRACKING", "REL_POS_Y"),
        "vx": g("TRACKING", "REL_VEL_X"),
        "vy": g("TRACKING", "REL_VEL_Y"),
        "heading": g("TRACKING", "HEADING_ANGLE"),
        "veh": g("VEHICLE_RECOGNITION", "RECOGNITION"),
    }
    if start is None:
        start, end = 1, n
    sl = slice(start - 1, end)
    t = sim_time[sl]
    speed, yawrate = speed[sl], yawrate[sl]
    ftm = ftm[:, :, sl]
    return t, speed, yawrate, ftm, ROW, {"path": path, "start": start, "end": end}


def _ego_dead_reckoning(t, speed_mps, yawrate_rps):
    dt = np.diff(t)
    yaw = np.concatenate([[0.0], np.cumsum(0.5 * (yawrate_rps[1:] + yawrate_rps[:-1]) * dt)])
    vx = speed_mps * np.cos(yaw)
    vy = speed_mps * np.sin(yaw)
    ex = np.concatenate([[0.0], np.cumsum(0.5 * (vx[1:] + vx[:-1]) * dt)])
    ey = np.concatenate([[0.0], np.cumsum(0.5 * (vy[1:] + vy[:-1]) * dt)])
    return np.column_stack([ex, ey]), yaw, vx, vy


def sfpp_track_pairs(t, speed_mps, yawrate_rps, ftm, ROW,
                     min_dur=1.0, max_gap=0.5):
    """One Pair per physical fusion track (recognized vehicles, by track ID).

    Frames of one track ID are grouped into contiguous segments (gaps up to
    max_gap seconds are tolerated); segments shorter than min_dur are dropped.
    """
    n = len(t)
    ego_xy, yaw, vx, vy = _ego_dead_reckoning(t, speed_mps, yawrate_rps)
    ca, sa = np.cos(yaw), np.sin(yaw)
    ids = ftm[ROW["id"]]
    px, py = ftm[ROW["px"]], ftm[ROW["py"]]
    veh = ftm[ROW["veh"]]
    ok = (np.hypot(px, py) > 0) & (veh != 0) & (ids != 0)
    pairs = []
    for tid in np.unique(ids[ok]):
        slot_mask = (ids == tid) & ok           # (64, n)
        frame_has = slot_mask.any(axis=0)
        frames = np.where(frame_has)[0]
        if len(frames) < 2:
            continue
        # split at temporal gaps
        cut = np.where(np.diff(t[frames]) > max_gap)[0]
        for seg in np.split(frames, cut + 1):
            if len(seg) < 2 or t[seg[-1]] - t[seg[0]] < min_dur:
                continue
            slot = np.argmax(slot_mask[:, seg], axis=0)
            rx, ry = px[slot, seg], py[slot, seg]
            rvx, rvy = ftm[ROW["vx"]][slot, seg], ftm[ROW["vy"]][slot, seg]
            rhead = ftm[ROW["heading"]][slot, seg]
            txy = np.column_stack([ego_xy[seg, 0] + rx * ca[seg] - ry * sa[seg],
                                   ego_xy[seg, 1] + rx * sa[seg] + ry * ca[seg]])
            tvx = vx[seg] + rvx * ca[seg] - rvy * sa[seg]
            tvy = vy[seg] + rvx * sa[seg] + rvy * ca[seg]
            pairs.append(Pair(t[seg], ego_xy[seg], speed_mps[seg], yaw[seg],
                              txy, np.hypot(tvx, tvy), yaw[seg] + rhead,
                              np.ones(len(seg), bool),
                              {"source": "sfpp", "track_id": int(tid)}))
    return pairs
