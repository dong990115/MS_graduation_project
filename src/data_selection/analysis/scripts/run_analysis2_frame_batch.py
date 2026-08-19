import os
_MONO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))  # PCG_dataSelection (repo-local, 2026-07-26)
"""Analysis 2 frame-level batch (2026-07-13 redesign).

Unit of analysis = ONE SBEV IMAGE (scenario, frame). For every image in the
4,500-image generation pool (and the EIG-selected 139 subset within it),
compute the frame-level dmTTCP (paper eq. 3.7-3.8) at the image's frame.

Per scenario: the .mat is loaded ONCE, the metric time series is computed
over all frames, and the image frames (1-based sample index — validated by
scripts/validation/validate_frame_mapping.py) are then sampled from it.

Output: output/analysis2/frame_metrics.csv
  image, scen_type, concrete, timestep, cm, selected, dmttcp
"""
import csv, os, re, sys, traceback
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Utils")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "analysis2")
POOL = os.path.join(_MONO, "05_MapBuilder", "Output", "DSM", "RAB_v13_Train_060126_noLane_sub4500")
if not os.path.isdir(POOL):
    POOL = r"<DATA_NAS>\MapBuilder\augmented_dataset\PCG_4500"  # NAS 폴백 (동일 세트)
MAT = r"<SCENARIO_NAS>\cm13\Scenario Catalog for Car to Car\Data\mat"
SEL = os.path.join(_MONO, "06_EIG", "Output", "PCG", "noLane_060126_sub4500", "K_500", "selected_scenarios.csv")
SCENS = ["LK_CIR_MER_RAB_FOT", "drivingAlone_RVL_RAB_FOT"]
PAT = re.compile(r"Image_(\d+)_(LK_CIR_MER_RAB_FOT|drivingAlone_RVL_RAB_FOT)_(\d+)_(\d+)\.png")


def collect_images():
    """-> {(scen, concrete): [(filename, cm, timestep), ...]}, selected set"""
    groups = defaultdict(list)
    for scen in SCENS:
        for fn in os.listdir(os.path.join(POOL, scen)):
            m = PAT.match(fn)
            if m:
                groups[(scen, int(m.group(3)))].append((fn, int(m.group(1)), int(m.group(4))))
    selected = set()
    with open(SEL) as f:
        next(f)
        for line in f:
            fn = line.split(",")[0].strip()
            if PAT.match(fn):
                selected.add(fn)
    return groups, selected


def work(args):
    (scen, concrete), images = args
    sys.path.insert(0, SRC)
    from traj_loader import load_carmaker
    from metrics import compute_metric_timeseries
    rows = []
    try:
        pair = load_carmaker(os.path.join(MAT, scen, f"{scen}_data_{concrete}.mat"))
        ts = compute_metric_timeseries(pair)
        n = len(pair.t)
        for fn, cm, k in images:
            if k > n:
                rows.append({"image": fn, "scen_type": scen, "concrete": concrete,
                             "timestep": k, "cm": cm, "err": f"frame {k} > n {n}"})
                continue
            i = k - 1                       # 1-based image frame -> 0-based sample
            rows.append({"image": fn, "scen_type": scen, "concrete": concrete,
                         "timestep": k, "cm": cm,
                         "dmttcp": ts["dmttcp"][i], "err": ""})
    except Exception:
        err = traceback.format_exc(limit=1).splitlines()[-1][:150]
        for fn, cm, k in images:
            rows.append({"image": fn, "scen_type": scen, "concrete": concrete,
                         "timestep": k, "cm": cm, "err": err})
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    groups, selected = collect_images()
    n_img = sum(len(v) for v in groups.values())
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {n_img} images / "
          f"{len(groups)} scenarios / {len(selected)} selected")
    rows = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for i, rs in enumerate(ex.map(work, sorted(groups.items()), chunksize=8)):
            rows.extend(rs)
            if (i + 1) % 200 == 0:
                print(f"  [{datetime.now():%H:%M:%S}] {i+1}/{len(groups)} scenarios")
    for r in rows:
        r["selected"] = int(r["image"] in selected)
    keys = ["image", "scen_type", "concrete", "timestep", "cm", "selected",
            "dmttcp", "err"]
    with open(os.path.join(OUT, "frame_metrics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    # summary
    print(f"[{datetime.now():%H:%M:%S}] wrote {len(rows)} rows")
    for scen in SCENS:
        for sel in (0, 1):
            sub = [r for r in rows if r["scen_type"] == scen and r["selected"] == sel]
            if not sub:
                continue
            for m in ("dmttcp",):
                v = np.array([r[m] for r in sub if r.get(m, "") != ""
                              and np.isfinite(r.get(m, np.nan))])
                tag = "SEL" if sel else "pool"
                if len(v):
                    print(f"  {scen[:12]:12} {tag:4} {m:7} defined {len(v):5}/{len(sub):5} "
                          f"({len(v)/len(sub)*100:3.0f}%) min={v.min():.2f} med={np.median(v):.2f}")
                else:
                    print(f"  {scen[:12]:12} {tag:4} {m:7} defined 0/{len(sub)}")
    nerr = sum(1 for r in rows if r.get("err"))
    print(f"  errors: {nerr}")


if __name__ == "__main__":
    main()
