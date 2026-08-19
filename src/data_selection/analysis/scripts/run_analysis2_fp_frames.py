import os
_MONO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))  # PCG_dataSelection (repo-local, 2026-07-26)
"""Frame-level dmTTCP AT FP decision frames of the baseline evaluation.

Feeds the FP overlays of thesis Figure 3-3 (paper eq. 3.7-3.8).

Usage:
  python run_analysis2_fp_frames.py                      # baseline FP (default)
  python run_analysis2_fp_frames.py --eval <Test_Result-...mat> --out <name.csv>

Frames per event: decisionSample (the misdetection frames).
Sources: PSM events -> Scenario Catalog CarMaker mats;
         FOT events -> SF_PP (v108) with the event's frame window.
Output columns: source, scenario, dataIndex, frame, is_rab, dmttcp
"""
import argparse, csv, sys, traceback
from collections import defaultdict
from datetime import datetime

import numpy as np
from scipy.io import loadmat

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Utils"))
from traj_loader import load_carmaker, load_sfpp, sfpp_track_pairs
from metrics import compute_metric_timeseries

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "analysis2")
BASELINE_EVAL = os.path.join(_MONO, "07_ACL", "Result", "Inference", "ACLpp_iter4_origin",
                             "Test_Result-ScenarioBasedCollisionDetection-2026_06_05_12_57_06.mat")  # repo C1 eval
FP_VAR = "Test_falsePositive_concreteScenario"
PSM_ROOT = r"<SCENARIO_NAS>\Scenario Catalog for Car to Car\Data\Mat"
GEN = (r"<PROJECT_NAS>\Collision Mode\RunSimulink\Output"
       r"\{fot}_for_upload_102723_SFFIX_030425_v108\Genesis\{fot}_{trip:03d}_SF_PP.mat")
RAB_EVENTS = {("FOT_A", 87), ("FOT_A", 90)}


def read_events(eval_path):
    d = loadmat(eval_path, squeeze_me=True, struct_as_record=False,
                variable_names=[FP_VAR])
    entries = np.atleast_1d(d[FP_VAR])
    events = []
    for e in entries:
        fot = getattr(e, "FOT", None)
        is_fot = isinstance(fot, str) and len(fot) > 0
        name = fot if is_fot else str(e.logicalScenario)
        frames = sorted(set(int(x) for x in np.atleast_1d(e.decisionSample)))
        s0 = getattr(e, "startFrameIndex", None)
        s1 = getattr(e, "endFrameIndex", None)
        win = (int(s0), int(s1)) if is_fot and np.size(s0) else None
        events.append({"source": "FOT" if is_fot else "PSM", "scenario": name,
                       "dataIndex": int(e.dataIndex), "frames": frames, "win": win,
                       "is_rab": int(is_fot and (name, int(e.dataIndex)) in RAB_EVENTS)})
    return events


def base(e, fr):
    return {"source": e["source"], "scenario": e["scenario"],
            "dataIndex": e["dataIndex"], "frame": fr, "is_rab": e["is_rab"], "err": ""}


def fmt(v):
    return round(float(v), 4) if np.isfinite(v) else ""


def psm_rows(evs):
    rows = []
    for i, e in enumerate(evs):
        path = os.path.join(PSM_ROOT, e["scenario"], f"{e['scenario']}_data_{e['dataIndex']}.mat")
        try:
            pair = load_carmaker(path)
            ts = compute_metric_timeseries(pair)
            n = len(pair.t)
            for fr in e["frames"]:
                if fr > n:
                    rows.append({**base(e, fr), "err": f"frame>{n}"})
                    continue
                rows.append({**base(e, fr), "dmttcp": fmt(ts["dmttcp"][fr - 1])})
        except Exception:
            err = traceback.format_exc(limit=1).splitlines()[-1][:120]
            for fr in e["frames"]:
                rows.append({**base(e, fr), "err": err})
        if (i + 1) % 40 == 0:
            print(f"  [{datetime.now():%H:%M:%S}] PSM {i+1}/{len(evs)}")
    return rows


def fot_rows(evs):
    rows = []
    by_trip = defaultdict(list)
    for e in evs:
        by_trip[(e["scenario"], e["dataIndex"])].append(e)
    for (fot, trip), group in sorted(by_trip.items()):
        try:
            t, speed, yawrate, ftm, ROW, _ = load_sfpp(GEN.format(fot=fot, trip=trip))
        except Exception:
            err = traceback.format_exc(limit=1).splitlines()[-1][:120]
            for e in group:
                for fr in e["frames"]:
                    rows.append({**base(e, fr), "err": err})
            continue
        for e in group:
            s0, s1 = e["win"] if e["win"] else (1, len(t))
            sl = slice(s0 - 1, min(s1, len(t)))
            pairs = sfpp_track_pairs(t[sl], speed[sl], yawrate[sl], ftm[:, :, sl], ROW)
            series = [compute_metric_timeseries(p) for p in pairs]
            for fr in e["frames"]:
                k = fr - s0
                if k < 0 or k >= (sl.stop - sl.start):
                    rows.append({**base(e, fr), "err": "frame outside window"})
                    continue
                tt = t[sl][k]
                bst = np.nan
                for p, ts in zip(pairs, series):
                    j = np.searchsorted(p.t, tt)
                    if j >= len(p.t) or abs(p.t[j] - tt) > 0.06:
                        continue
                    v = ts["dmttcp"][j]
                    if np.isfinite(v) and (not np.isfinite(bst) or v < bst):
                        bst = v
                rows.append({**base(e, fr), "dmttcp": fmt(bst)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=BASELINE_EVAL, help="Test_Result-...mat path")
    ap.add_argument("--out", default="fp_frame_metrics.csv",
                    help="output csv name (in output/analysis2)")
    a = ap.parse_args()
    events = read_events(a.eval)
    n_fr = sum(len(e["frames"]) for e in events)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] FP events: {len(events)} "
          f"({sum(e['source']=='PSM' for e in events)} PSM + "
          f"{sum(e['source']=='FOT' for e in events)} FOT), frames {n_fr}, "
          f"eval={os.path.basename(a.eval)}")
    rows = psm_rows([e for e in events if e["source"] == "PSM"])
    rows += fot_rows([e for e in events if e["source"] == "FOT"])
    os.makedirs(OUT_DIR, exist_ok=True)
    keys = ["source", "scenario", "dataIndex", "frame", "is_rab", "dmttcp", "err"]
    with open(os.path.join(OUT_DIR, a.out), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(f"[{datetime.now():%H:%M:%S}] wrote {len(rows)} rows -> {a.out} "
          f"(errors: {sum(1 for r in rows if r['err'])})")
    v = np.array([r["dmttcp"] for r in rows if r.get("dmttcp", "") != ""], dtype=float)
    if len(v):
        print(f"  dmttcp : defined {len(v):3}/{len(rows):3} min={v.min():.2f} "
              f"p25={np.percentile(v,25):.2f} med={np.median(v):.2f} max={v.max():.2f}")


if __name__ == "__main__":
    main()
