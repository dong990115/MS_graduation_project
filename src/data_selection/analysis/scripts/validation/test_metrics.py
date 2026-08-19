"""Hand-computable synthetic cases for the four interaction metrics."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Utils"))
import numpy as np
from traj_loader import Pair
from metrics import compute_metrics


def make_pair(t, e_xy, g_xy):
    def spd(xy):
        v = np.hypot(*np.gradient(xy, t, axis=0).T)
        return v
    yaw = lambda xy: np.arctan2(*np.gradient(xy, t, axis=0).T[::-1])
    return Pair(t, e_xy, spd(e_xy), yaw(e_xy), g_xy, spd(g_xy), yaw(g_xy),
                np.ones(len(t), bool), {})


fails = 0

def check(name, val, lo, hi):
    global fails
    ok = (np.isnan(lo) and np.isnan(val)) or (not np.isnan(lo) and lo <= val <= hi)
    print(f"  {'PASS' if ok else 'FAIL'} {name} = {val} (expect {lo}..{hi})")
    if not ok:
        fails += 1


# --- 1. perpendicular crossing, target 1 s behind ------------------------
t = np.arange(0, 10.001, 0.02)
ego = np.column_stack([-50 + 10 * t, np.zeros_like(t)])          # crosses O at t=5
tgt = np.column_stack([np.zeros_like(t), -60 + 10 * t])          # crosses O at t=6
m = compute_metrics(make_pair(t, ego, tgt))
print("case 1: perpendicular crossing (dt at CP = 1.0 s)")
check("dTTCP_min", m["dTTCP_min"], 0.9, 1.1)
check("dmTTCP", m["dmTTCP"], 0.85, 1.15)   # +-SHARE_TOL/v resolution
check("PET", m["PET"], 0.4, 0.6)          # 1.0 s minus 0.5 s occupancy span
check("minTTC", m["minTTC"], 0.8, 1.3)
check("following", float(m["following"]), 0, 0)

# --- 2. same-lane following ----------------------------------------------
t = np.arange(0, 3.001, 0.02)
ego = np.column_stack([10 * t, np.zeros_like(t)])
tgt = np.column_stack([20 + 5 * t, np.zeros_like(t)])
m = compute_metrics(make_pair(t, ego, tgt))
print("case 2: following (gap 20->5 m, closing 5 m/s)")
check("minTTC", m["minTTC"], 0.9, 1.15)
check("PET (NaN expected)", m["PET"], np.nan, np.nan)
check("following", float(m["following"]), 1, 1)

# --- 3. no interaction: opposite directions, 10 m lateral offset ----------
t = np.arange(0, 8.001, 0.02)
ego = np.column_stack([-40 + 10 * t, np.zeros_like(t)])
tgt = np.column_stack([40 - 10 * t, 10 * np.ones_like(t)])
m = compute_metrics(make_pair(t, ego, tgt))
print("case 3: disjoint paths")
check("n_shared", m["n_shared"], 0, 0)
check("dTTCP_min (NaN)", m["dTTCP_min"], np.nan, np.nan)
check("PET (NaN)", m["PET"], np.nan, np.nan)

# --- 4. merge: target joins ego lane 30 m ahead via a quarter circle ------
t = np.arange(0, 10.001, 0.02)
ego = np.column_stack([-20 + 10 * t, np.zeros_like(t)])          # at x=30 at t=5
R, v_t = 20.0, 8.0
s_t = v_t * t
s_merge = R * np.pi / 2                                          # target at CP t~3.93
ang = np.minimum(s_t, s_merge) / R
h = np.pi / 2 - ang                                              # heading north -> east
dt = np.diff(t)
gx = np.concatenate([[0.0], np.cumsum(0.5 * (np.cos(h[1:]) + np.cos(h[:-1])) * v_t * dt)])
gy = np.concatenate([[0.0], np.cumsum(0.5 * (np.sin(h[1:]) + np.sin(h[:-1])) * v_t * dt)])
k_m = int(np.argmin(np.abs(s_t - s_merge)))
gx, gy = gx - gx[k_m] + 30.0, gy - gy[k_m]                       # merge point = (30, 0)
tgt = np.column_stack([gx, gy])
m = compute_metrics(make_pair(t, ego, tgt))
print("case 4: curved merge (ego at CP t=5, target t~3.9)")
print("   ", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()})
check("n_shared>0", float(m["n_shared"] > 0), 1, 1)
check("PET defined", float(np.isfinite(m["PET"])), 1, 1)

# ==========================================================================
# frame-level timeseries (compute_metric_timeseries) — hand-computed values
from metrics import compute_metric_timeseries

# --- 5. perpendicular crossing, frame values --------------------------------
t = np.arange(0, 10.001, 0.02)
ego = np.column_stack([-50 + 10 * t, np.zeros_like(t)])          # at CP t=5
tgt = np.column_stack([np.zeros_like(t), -60 + 10 * t])          # at CP t=6
ts = compute_metric_timeseries(make_pair(t, ego, tgt))
k0 = 0                                   # t=0
k2 = int(2.0 / 0.02)                     # t=2
print("case 5: frame-level values (perpendicular crossing)")
# TTC(0): range 78.10 m, closing 14.08 m/s -> 5.546 s
check("ttc[t=0]", ts["ttc"][k0], 5.35, 5.75)
# dTTCP(t) = |(50-10t)/10 - (60-10t)/10| = 1.0 while both ahead
check("dttcp[t=0]", ts["dttcp"][k0], 0.85, 1.15)
check("dttcp[t=2]", ts["dttcp"][k2], 0.85, 1.15)
check("dmttcp[t=2]", ts["dmttcp"][k2], 0.85, 1.15)
# after ego passes the CP (t>5.2): no conflict point ahead of both -> NaN
k6 = int(6.0 / 0.02)
check("dttcp[t=6] (NaN)", ts["dttcp"][k6], np.nan, np.nan)

# --- 6. following, frame values ---------------------------------------------
t = np.arange(0, 3.001, 0.02)
ego = np.column_stack([10 * t, np.zeros_like(t)])
tgt = np.column_stack([20 + 5 * t, np.zeros_like(t)])
ts = compute_metric_timeseries(make_pair(t, ego, tgt))
k1 = int(1.0 / 0.02)
print("case 6: frame-level values (following, gap 20-5t)")
# TTC(t) = (20-5t)/5 = 4-t -> at t=1: 3.0
check("ttc[t=1]", ts["ttc"][k1], 2.85, 3.15)
# scenario aggregation consistency: min_t of frame TTC == scenario minTTC
m = compute_metrics(make_pair(t, ego, tgt))
check("min(ttc[t]) == scenario minTTC", float(np.nanmin(ts["ttc"])),
      m["minTTC"] - 0.05, m["minTTC"] + 0.05)

print("\nTOTAL:", "ALL PASS" if fails == 0 else f"{fails} FAILURES")
