"""Loader smoke test: units, dt, and reconstructed FP-window paths."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Utils"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from traj_loader import load_carmaker, load_sfpp, reconstruct_pair

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "output", "loader_check")
os.makedirs(OUT, exist_ok=True)

# --- CarMaker: one PSM + one PCG + one realFOT
for name, path in [
    ("PSM_LK_CIR_MER_1", r"<SCENARIO_NAS>\Scenario Catalog for Car to Car\Data\Mat\LK_CIR_MER\LK_CIR_MER_data_1.mat"),
    ("PCG_233", r"<SCENARIO_NAS>\cm13\Scenario Catalog for Car to Car\Data\mat\LK_CIR_MER_RAB_FOT\LK_CIR_MER_RAB_FOT_data_233.mat"),
    ("realFOT_170", r"<SCENARIO_NAS>\cm13\Scenario Catalog for Car to Car\Data\mat\LK_CIR_MER_RAB_realFOT\LK_CIR_MER_RAB_realFOT_data_170.mat"),
]:
    p = load_carmaker(path)
    dt = np.median(np.diff(p.t))
    print(f"{name}: n={len(p.t)} dt={dt:.4f}s dur={p.t[-1]-p.t[0]:.1f}s "
          f"ego_v=[{p.ego_v.min():.1f},{p.ego_v.max():.1f}]m/s "
          f"tgt_v=[{p.tgt_v[p.valid].min():.1f},{p.tgt_v[p.valid].max():.1f}]m/s "
          f"valid={p.valid.mean()*100:.0f}%")
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(p.ego_xy[:, 0], p.ego_xy[:, 1], label="ego")
    ax.plot(p.tgt_xy[p.valid, 0], p.tgt_xy[p.valid, 1], label="target")
    ax.plot(*p.ego_xy[0], "go"); ax.plot(*p.tgt_xy[p.valid][0], "g^")
    ax.set_aspect("equal"); ax.legend(); ax.set_title(name)
    fig.savefig(os.path.join(OUT, f"{name}.png"), dpi=120, bbox_inches="tight")
    plt.close(fig)

# --- SF_PP FP windows
FP = [("FOT_A_087", 1201, 1600), ("FOT_A_087", 1601, 2000),
      ("FOT_A_090", 401, 800)]
BASE = r"<PROJECT_NAS>\Collision Mode\RunSimulink\Output\FOT_A_for_upload_102723_SFFIX_030425_v108\Genesis"
for trip, s0, s1 in FP:
    path = os.path.join(BASE, f"{trip}_SF_PP.mat")
    t, speed, yawrate, ftm, ROW, meta = load_sfpp(path, s0, s1)
    dt = np.median(np.diff(t))
    print(f"{trip}[{s0}:{s1}]: dt={dt:.4f}s raw_speed=[{speed.min():.2f},{speed.max():.2f}] "
          f"raw_yawrate=[{yawrate.min():.3f},{yawrate.max():.3f}]")
