"""Interaction metrics on an ego-target Pair (verified reference definitions).

minTTC     TTC = range / closing-rate while approaching; scenario min.
           (CVAE-T, arXiv:2510.24671: "remaining time before a collision would
            occur if both vehicles maintain their current speed and direction")
dTTCP_min  min_t |TTCP_ego - TTCP_tgt| at the first conflict point of the two
           driven paths ahead of both vehicles; TTCP_i = dist along own path /
           current speed (INTERACTION, arXiv:1910.03088; arXiv:2212.11167 App.A)
dmTTCP     min over ALL shared points of the real driven paths and over time of
           |mTTCP_1 - mTTCP_2| (arXiv:2202.07438)
PET        time gap between the first vehicle leaving and the second entering
           the shared conflict zone (CVAE-T, arXiv:2510.24671). Undefined (NaN)
           for pure same-direction following (paths never cross), per the
           analysis spec.

Conventions (documented in REPORT):
  - vehicle reference-point kinematics, no size correction (consistent across
    every data set; same convention as the project's own GT pipeline)
  - conflict points from path proximity < SHARE_TOL between driven paths
  - occupancy length OCC_LEN around the conflict point for PET
  - speeds clamped at V_MIN to keep TTCP finite; TTCP values capped at T_CAP
"""
import numpy as np
from scipy.spatial import cKDTree

SHARE_TOL = 1.0     # [m] two path points closer than this are "shared"
OCC_LEN = 5.0       # [m] conflict-zone occupancy length for PET
V_MIN = 0.1         # [m/s]
T_CAP = 30.0        # [s] cap for TTCP-type values
FOLLOW_ANG = 15.0   # [deg] tangent angle below which a long overlap = following
FOLLOW_LEN = 10.0   # [m] overlap length above which it counts as following
RESAMPLE = 0.5      # [m] path resampling step


def _path(xy):
    """polyline -> (points at ~RESAMPLE spacing, arc values, tangents)."""
    seg = np.hypot(*np.diff(xy, axis=0).T)
    keep = np.concatenate([[True], seg > 1e-6])
    xy = xy[keep]
    if len(xy) < 2:
        return None
    seg = np.hypot(*np.diff(xy, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    su = np.arange(0.0, s[-1], RESAMPLE)
    if len(su) < 2:
        return None
    pts = np.column_stack([np.interp(su, s, xy[:, 0]), np.interp(su, s, xy[:, 1])])
    tang = np.gradient(pts, su, axis=0)
    norm = np.hypot(*tang.T)
    tang = tang / np.maximum(norm, 1e-9)[:, None]
    return pts, su, tang


def _arc_of_frames(xy):
    seg = np.hypot(*np.diff(xy, axis=0).T)
    return np.concatenate([[0.0], np.cumsum(seg)])


def compute_metrics(pair):
    """-> dict(minTTC, dTTCP_min, dmTTCP, PET, n_shared, following)"""
    v = pair.valid
    if v.sum() < 2:
        return None
    t = pair.t[v]
    e_xy, e_v = pair.ego_xy[v], np.maximum(pair.ego_v[v], 0.0)
    g_xy, g_v = pair.tgt_xy[v], np.maximum(pair.tgt_v[v], 0.0)

    out = {"minTTC": np.nan, "dTTCP_min": np.nan, "dmTTCP": np.nan,
           "PET": np.nan, "n_shared": 0, "following": False}

    # ---------------- minTTC (relative kinematics only)
    rng = np.hypot(*(g_xy - e_xy).T)
    if len(t) >= 3:
        drdt = np.gradient(rng, t)
        closing = -drdt
        ttc = np.where(closing > 0.2, rng / np.maximum(closing, 1e-9), np.nan)
        if np.isfinite(ttc).any():
            out["minTTC"] = float(np.nanmin(ttc))

    # ---------------- shared points of the driven paths
    pe = _path(e_xy)
    pg = _path(g_xy)
    if pe is None or pg is None:
        return out
    e_pts, e_s, e_tan = pe
    g_pts, g_s, g_tan = pg
    tree = cKDTree(g_pts)
    dist, j = tree.query(e_pts, k=1)
    shared = dist <= SHARE_TOL
    out["n_shared"] = int(shared.sum())
    if not shared.any():
        return out
    se = e_s[shared]                    # ego-path arc of shared points
    sg = g_s[j[shared]]                 # target-path arc of the same points
    cosang = np.abs(np.sum(e_tan[shared] * g_tan[j[shared]], axis=1))
    ang = np.degrees(np.arccos(np.clip(cosang, 0, 1)))
    overlap_len = shared.sum() * RESAMPLE
    # following vs merge/cross: judge by the path angle where the shared
    # region BEGINS (a merge converges at an angle there; pure following is
    # parallel from the first shared point on)
    order = np.argsort(se)
    ang_first = float(np.max(ang[order[:6]]))
    following = bool(ang_first < FOLLOW_ANG and overlap_len > FOLLOW_LEN)
    out["following"] = following

    a_e = _arc_of_frames(e_xy)          # ego arc position per frame
    a_g = _arc_of_frames(g_xy)

    # ---------------- dTTCP_min / dmTTCP (subsampled in time)
    step = max(1, len(t) // 400)
    best_first, best_any = np.inf, np.inf
    for k in range(0, len(t), step):
        ahead = (se >= a_e[k]) & (sg >= a_g[k])
        if not ahead.any():
            continue
        ve = max(e_v[k], V_MIN)
        vg = max(g_v[k], V_MIN)
        tte = np.minimum((se[ahead] - a_e[k]) / ve, T_CAP)
        ttg = np.minimum((sg[ahead] - a_g[k]) / vg, T_CAP)
        dd = np.abs(tte - ttg)
        best_any = min(best_any, dd.min())
        first = np.argmin(se[ahead])    # first conflict point on ego path
        best_first = min(best_first, dd[first])
    if np.isfinite(best_first):
        out["dTTCP_min"] = float(best_first)
    if np.isfinite(best_any):
        out["dmTTCP"] = float(best_any)

    # ---------------- PET at the static first conflict point
    if not following:
        s_cp_e = se.min()
        s_cp_g = sg[np.argmin(se)]
        te_in = t[a_e >= s_cp_e - OCC_LEN / 2]
        te_out = t[a_e >= s_cp_e + OCC_LEN / 2]
        tg_in = t[a_g >= s_cp_g - OCC_LEN / 2]
        tg_out = t[a_g >= s_cp_g + OCC_LEN / 2]
        if len(te_in) and len(tg_in) and len(te_out) and len(tg_out):
            if te_in[0] <= tg_in[0]:        # ego passes first
                pet = tg_in[0] - te_out[0]
            else:
                pet = te_in[0] - tg_out[0]
            if pet >= 0:
                out["PET"] = float(pet)
    return out


def compute_metric_timeseries(pair):
    """FRAME-level metrics (2026-07-13 redesign): per-frame arrays aligned to
    pair.t, NaN where undefined at that frame.

      ttc[k]    = range / closing-rate at frame k (approaching only)
      dttcp[k]  = |TTCP_ego - TTCP_tgt| at the FIRST conflict point still
                  ahead of both vehicles at frame k
      dmttcp[k] = min over ALL shared path points ahead of both at frame k

    These are the reference definitions with the scenario-level min_t
    aggregation removed (TTCP_i^t and TTC(t) are per-time quantities in the
    original papers). PET has no per-frame form and is not provided.
    Conflict points are derived from the FULL driven paths (scenario
    context); only the VALUE is taken at frame k.
    """
    n = len(pair.t)
    out = {"ttc": np.full(n, np.nan), "dttcp": np.full(n, np.nan),
           "dmttcp": np.full(n, np.nan)}
    v = pair.valid
    if v.sum() < 3:
        return out
    idx = np.where(v)[0]
    t = pair.t[v]
    e_xy, e_v = pair.ego_xy[v], np.maximum(pair.ego_v[v], 0.0)
    g_xy, g_v = pair.tgt_xy[v], np.maximum(pair.tgt_v[v], 0.0)

    # ---- TTC(t)
    rng = np.hypot(*(g_xy - e_xy).T)
    closing = -np.gradient(rng, t)
    ttc = np.where(closing > 0.2, rng / np.maximum(closing, 1e-9), np.nan)
    out["ttc"][idx] = ttc

    # ---- shared points of the driven paths (same machinery as scenario level)
    pe = _path(e_xy)
    pg = _path(g_xy)
    if pe is None or pg is None:
        return out
    e_pts, e_s, _ = pe
    g_pts, g_s, _ = pg
    tree = cKDTree(g_pts)
    dist, j = tree.query(e_pts, k=1)
    shared = dist <= SHARE_TOL
    if not shared.any():
        return out
    se = e_s[shared]
    sg = g_s[j[shared]]
    a_e = _arc_of_frames(e_xy)
    a_g = _arc_of_frames(g_xy)

    dttcp = np.full(len(t), np.nan)
    dmttcp = np.full(len(t), np.nan)
    for k in range(len(t)):
        ahead = (se >= a_e[k]) & (sg >= a_g[k])
        if not ahead.any():
            continue
        ve = max(e_v[k], V_MIN)
        vg = max(g_v[k], V_MIN)
        tte = np.minimum((se[ahead] - a_e[k]) / ve, T_CAP)
        ttg = np.minimum((sg[ahead] - a_g[k]) / vg, T_CAP)
        dd = np.abs(tte - ttg)
        dmttcp[k] = dd.min()
        dttcp[k] = dd[np.argmin(se[ahead])]   # first conflict point on ego path
    out["dttcp"][idx] = dttcp
    out["dmttcp"][idx] = dmttcp
    return out
