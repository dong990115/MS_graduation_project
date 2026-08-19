import os
_MONO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))  # PCG_dataSelection (repo-local, 2026-07-26)
"""Analysis 1 batch (spec 2026-07-13): radius r_k and radius change dr_k.

Per network: extract the ring centerline loop (0.5 m uniform sampling,
circle-filled gaps masked), then measure on REAL samples only:
    centroid (c_x, c_y) = mean of real loop samples          (spec step)
    r_k  = distance of sample k from the centroid            (paper eq. 2.2)
    dr_k = r_k - r_{k-1}                                     (paper eq. 2.3)
dr_k pairs that touch a masked sample are dropped. Values are stored RAW
(user decision 2026-07-13); the per-network mean radius r_bar is stored too
so the normalized variant (r_k/r_bar, dr_k/r_bar) can be produced without
re-running the batch.

Outputs (output/analysis1/):
  shape_stats.csv  : one row per network (r_bar, r/dr summaries, coverage)
  shape_pool.npz   : per-network arrays  r_<name>, dr_<name>
"""
import sys, os, glob, traceback
from concurrent.futures import ProcessPoolExecutor

import numpy as np

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Utils")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "analysis1")

PCG_GLOB = os.path.join(_MONO, "02_JunctionArt", "output", "roundabout_PCG_*.xodr")
REAL = {
    "FOT_A_087": os.path.join(_MONO, "04_CarMakerSim", "Data", "Road", "example", "FOT_A_087.xodr"),
    "FOT_A_090": os.path.join(_MONO, "04_CarMakerSim", "Data", "Road", "example", "FOT_A_090.xodr"),
}


def process(args):
    name, path, group = args
    sys.path.insert(0, SRC)
    from xodr_centerline import parse_xodr
    from ring_extract import extract_ring
    try:
        net = parse_xodr(path)
        ring = extract_ring(net)                    # ds = 0.5 m uniform
        real = ring.loop_real
        xy = ring.loop_xy[real]
        c = xy.mean(axis=0)                         # centroid of real samples
        # r_k over the full loop order (needed for adjacent dr pairs)
        r_full = np.hypot(ring.loop_xy[:, 0] - c[0], ring.loop_xy[:, 1] - c[1])
        r = r_full[real]
        rbar = float(r.mean())
        # dr_k: adjacent pairs (closed loop) where BOTH samples are real
        dr_full = r_full - np.roll(r_full, 1)
        pair_ok = real & np.roll(real, 1)
        dr = dr_full[pair_ok]
        row = {"name": name, "group": group, "ok": 1,
               "r_bar": rbar, "coverage": ring.coverage,
               "n_r": len(r), "n_dr": len(dr),
               "r_min": r.min(), "r_max": r.max(), "r_sd": r.std(),
               "r_p25": np.percentile(r, 25), "r_p75": np.percentile(r, 75),
               "dr_min": dr.min(), "dr_max": dr.max(), "dr_sd": dr.std(),
               "dr_p25": np.percentile(dr, 25), "dr_p75": np.percentile(dr, 75)}
        return row, r.astype(np.float32), dr.astype(np.float32)
    except Exception:
        return ({"name": name, "group": group, "ok": 0,
                 "err": traceback.format_exc(limit=1).splitlines()[-1][:200]}, None, None)


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [(os.path.splitext(os.path.basename(p))[0], p, "PCG")
            for p in sorted(glob.glob(PCG_GLOB))]
    jobs += [(n, p, "Real") for n, p in REAL.items()]
    print(f"{len(jobs)} networks")
    rows, pools = [], {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for i, (row, r, dr) in enumerate(ex.map(process, jobs, chunksize=8)):
            rows.append(row)
            if r is not None:
                pools["r_" + row["name"]] = r
                pools["dr_" + row["name"]] = dr
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(jobs)}")
    import csv
    keys = ["name", "group", "ok", "r_bar", "coverage", "n_r", "n_dr",
            "r_min", "r_max", "r_sd", "r_p25", "r_p75",
            "dr_min", "dr_max", "dr_sd", "dr_p25", "dr_p75", "err"]
    with open(os.path.join(OUT, "shape_stats.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in keys})
    np.savez_compressed(os.path.join(OUT, "shape_pool.npz"), **pools)
    nfail = sum(1 for r in rows if not r["ok"])
    print(f"done: {len(rows)-nfail} ok, {nfail} failed -> {OUT}")
    for r in rows:
        if not r["ok"]:
            print("  FAIL", r["name"], r.get("err"))


if __name__ == "__main__":
    main()
