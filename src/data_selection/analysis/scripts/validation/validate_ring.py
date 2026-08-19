import os
_MONO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))  # PCG_dataSelection (repo-local, 2026-07-26)
"""Ring extraction validation on sample PCG networks and the two real roundabouts."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Utils"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xodr_centerline import parse_xodr
from ring_extract import extract_ring, menger_curvature, entry_angles

FILES = {
    "roundabout_PCG_0": os.path.join(_MONO, "02_JunctionArt", "output", "roundabout_PCG_0.xodr"),
    "roundabout_PCG_1": os.path.join(_MONO, "02_JunctionArt", "output", "roundabout_PCG_1.xodr"),
    "roundabout_PCG_500": os.path.join(_MONO, "02_JunctionArt", "output", "roundabout_PCG_500.xodr"),
    "roundabout_PCG_777": os.path.join(_MONO, "02_JunctionArt", "output", "roundabout_PCG_777.xodr"),
    "FOT_A_087": os.path.join(_MONO, "04_CarMakerSim", "Data", "Road", "example", "FOT_A_087.xodr"),
    "FOT_A_090": os.path.join(_MONO, "04_CarMakerSim", "Data", "Road", "example", "FOT_A_090.xodr"),
}
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "output", "ring_check")
os.makedirs(OUT, exist_ok=True)

for name, path in FILES.items():
    net = parse_xodr(path)
    try:
        ring = extract_ring(net)
    except Exception as e:
        print(f"{name}: FAIL — {e}")
        continue
    kappa, valid = menger_curvature(ring, span=4)
    kv = kappa[valid]
    phis = entry_angles(net, ring)
    phi_c = [round(np.mean(p["phi_deg"]), 1) for p in phis if "phi_deg" in p]
    phi_y = [round(np.mean(p["phi_yield_deg"]), 1) for p in phis if "phi_yield_deg" in p]
    print(f"{name}: R={ring.radius:.2f} loop={ring.diag['loop_len']:.1f}m "
          f"members={ring.diag['n_members']} coverage={ring.coverage*100:.1f}% | "
          f"kappa mean={kv.mean():.4f} (1/R={1/ring.radius:.4f}) sd={kv.std():.5f} "
          f"range=[{kv.min():.4f},{kv.max():.4f}] | phi@R={phi_c} | phi@R+3.5={phi_y}")
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    ax = axes[0]
    for r in net.roads.values():
        ax.plot(r.xy[:, 0], r.xy[:, 1], lw=0.7, color="lightgray")
    lp = ring.loop_xy
    ax.scatter(lp[ring.loop_real, 0], lp[ring.loop_real, 1], s=2, color="tab:blue")
    ax.scatter(lp[~ring.loop_real, 0], lp[~ring.loop_real, 1], s=2, color="orange")
    ax.plot(*ring.center, "r+", ms=12)
    for p in phis:
        if "phi_deg_p" in p:
            pt = p["phi_deg_p"][0]
            ax.plot(*pt, "g^", ms=6)
            ax.annotate(f"{np.mean(p['phi_deg']):.0f}°", pt, fontsize=8, color="green")
    lim = ring.radius * 2.6
    ax.set_xlim(ring.center[0] - lim, ring.center[0] + lim)
    ax.set_ylim(ring.center[1] - lim, ring.center[1] + lim)
    ax.set_aspect("equal"); ax.set_title(f"{name} (blue=real, orange=filled, green=phi@R)")
    ax2 = axes[1]
    s = np.arange(len(kappa)) * ring.diag["ds"]
    kplot = np.where(valid, kappa, np.nan)
    ax2.plot(s, kplot, lw=1)
    ax2.axhline(1 / ring.radius, color="r", ls="--", label="1/R")
    ax2.set_xlabel("s [m]"); ax2.set_ylabel("kappa [1/m]"); ax2.legend()
    ax2.set_title("Menger curvature (valid only)")
    fig.savefig(os.path.join(OUT, f"{name}.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
print("plots ->", OUT)
