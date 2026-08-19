"""Quick sanity summary of all analysis-2 metric CSVs."""
import csv, os
import numpy as np

A2 = os.path.join(os.path.dirname(__file__), "..", "..", "output", "analysis2")
for fn in ["metrics_fp.csv", "metrics_aug.csv", "metrics_exp.csv", "metrics_psm.csv"]:
    rows = list(csv.DictReader(open(os.path.join(A2, fn))))
    for setname in sorted({r["set"] for r in rows}):
        rs = [r for r in rows if r["set"] == setname]
        ok = [r for r in rs if r["ok"] == "1"]
        print(f"{setname}: {len(ok)}/{len(rs)} ok")
        for m in ["minTTC", "dTTCP_min", "dmTTCP", "PET"]:
            vals = np.array([float(r[m]) for r in ok if r[m] not in ("", "nan")])
            if len(vals):
                print(f"    {m:10s} n={len(vals):5d} ({len(vals)/len(ok)*100:4.0f}%) "
                      f"min={vals.min():6.2f} p10={np.percentile(vals,10):6.2f} "
                      f"med={np.median(vals):6.2f} p90={np.percentile(vals,90):6.2f}")
            else:
                print(f"    {m:10s} n=0")
        errs = {}
        for r in rs:
            if r["ok"] != "1":
                errs[r.get("err", "")[:60]] = errs.get(r.get("err", "")[:60], 0) + 1
        for e, c in errs.items():
            print(f"    ERR x{c}: {e}")
