"""Reconstruct the 3 real FP windows and check the paths look like a roundabout."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Utils"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from traj_loader import load_sfpp, reconstruct_pair

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "output", "loader_check")
os.makedirs(OUT, exist_ok=True)
BASE = r"<PROJECT_NAS>\Collision Mode\RunSimulink\Output\FOT_A_for_upload_102723_SFFIX_030425_v108\Genesis"
FP = [("FOT_A_087", 1201, 1600), ("FOT_A_087", 1601, 2000),
      ("FOT_A_090", 401, 800)]

for trip, s0, s1 in FP:
    t, speed, yawrate, ftm, ROW, meta = load_sfpp(os.path.join(BASE, f"{trip}_SF_PP.mat"), s0, s1)
    pair = reconstruct_pair(t, speed, yawrate, ftm, ROW)
    v = pair.valid
    rel = np.hypot(*(pair.tgt_xy - pair.ego_xy).T)
    print(f"{trip}[{s0}:{s1}]: valid={v.mean()*100:.0f}% "
          f"rel_dist=[{rel[v].min():.1f},{rel[v].max():.1f}]m "
          f"tgt_v=[{pair.tgt_v[v].min():.1f},{pair.tgt_v[v].max():.1f}]m/s "
          f"ego_turn={np.degrees(pair.ego_yaw[-1]-pair.ego_yaw[0]):.0f}deg")
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(pair.ego_xy[:, 0], pair.ego_xy[:, 1], label="ego (recon)")
    ax.scatter(pair.tgt_xy[v, 0], pair.tgt_xy[v, 1], s=4, color="tab:orange", label="target (nearest veh)")
    ax.plot(*pair.ego_xy[0], "go")
    ax.set_aspect("equal"); ax.legend(); ax.set_title(f"{trip} frames {s0}-{s1}")
    fig.savefig(os.path.join(OUT, f"FP_{trip}_{s0}.png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
print("->", OUT)
