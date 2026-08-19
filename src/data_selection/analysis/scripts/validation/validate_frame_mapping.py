"""Step 0: verify image-filename timestep <-> .mat sample index mapping.

Checks, per scenario type (LK_CIR_MER / drivingAlone):
  a) timestep range of pool images per concrete vs the .mat sample count
  b) spacing pattern of timesteps within one concrete (SBEV frame stride)
  c) at sampled (concrete, timestep): target validity in the .mat
"""
import os, re, sys
_MONO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))  # PCG_dataSelection (repo-local, 2026-07-26)
from datetime import datetime
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Utils"))
from traj_loader import load_carmaker

POOL = os.path.join(_MONO, "05_MapBuilder", "Output", "DSM", "RAB_v13_Train_060126_noLane_sub4500")
if not os.path.isdir(POOL):
    POOL = r"<DATA_NAS>\MapBuilder\augmented_dataset\PCG_4500"  # NAS 폴백 (동일 세트)
MAT = r"<SCENARIO_NAS>\cm13\Scenario Catalog for Car to Car\Data\mat"
TYPES = {"LK_CIR_MER_RAB_FOT": "LK_CIR_MER_RAB_FOT",
         "drivingAlone_RVL_RAB_FOT": "drivingAlone_RVL_RAB_FOT"}

print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] frame-mapping validation")
rng = np.random.default_rng(0)
for folder, scen in TYPES.items():
    by_concrete = defaultdict(list)
    for fn in os.listdir(os.path.join(POOL, folder)):
        m = re.match(rf"Image_(\d+)_{scen}_(\d+)_(\d+)\.png", fn)
        if m:
            by_concrete[int(m.group(2))].append(int(m.group(3)))
    n_img = sum(len(v) for v in by_concrete.values())
    print(f"\n=== {scen}: {n_img} images, {len(by_concrete)} concretes ===")
    # spacing pattern (one example concrete with many frames)
    ex = max(by_concrete, key=lambda c: len(by_concrete[c]))
    ts = sorted(by_concrete[ex])
    print(f"  example concrete {ex}: timesteps {ts}")
    print(f"  diffs: {np.diff(ts).tolist()}")
    # bounds check on a random sample of concretes
    sample = rng.choice(sorted(by_concrete), min(12, len(by_concrete)), replace=False)
    bad = 0
    for c in sample:
        p = os.path.join(MAT, scen, f"{scen}_data_{c}.mat")
        pair = load_carmaker(p)
        n = len(pair.t)
        tmax = max(by_concrete[c])
        ok = tmax <= n
        if not ok:
            bad += 1
        # target validity at the image frames (1-based -> 0-based)
        val = [bool(pair.valid[t - 1]) for t in by_concrete[c] if t <= n]
        print(f"  concrete {c:4d}: mat n={n:5d}, img timesteps [{min(by_concrete[c])},{tmax}]"
              f" {'OK' if ok else '** OUT OF RANGE **'}, target valid at frames: {sum(val)}/{len(val)}")
    # global max timestep vs typical n
    all_ts = [t for v in by_concrete.values() for t in v]
    print(f"  all timesteps: min={min(all_ts)}, max={max(all_ts)}")
print(f"\n[{datetime.now():%H:%M:%S}] done")
