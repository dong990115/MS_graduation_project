import os
_MONO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))  # PCG_dataSelection (repo-local, 2026-07-26)
"""Parser validation: length agreement + shape plots for visual check."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Utils"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xodr_centerline import parse_xodr

FILES = {
    "roundabout_PCG_0": os.path.join(_MONO, "02_JunctionArt", "output", "roundabout_PCG_0.xodr"),
    "FOT_A_087": os.path.join(_MONO, "04_CarMakerSim", "Data", "Road", "example", "FOT_A_087.xodr"),
    "FOT_A_090": os.path.join(_MONO, "04_CarMakerSim", "Data", "Road", "example", "FOT_A_090.xodr"),
}
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "output", "parser_check")
os.makedirs(OUT, exist_ok=True)

for name, path in FILES.items():
    net = parse_xodr(path)
    worst = 0.0
    for r in net.roads.values():
        sampled_len = np.hypot(*np.diff(r.xy, axis=0).T).sum()
        rel = abs(sampled_len - r.length) / max(r.length, 1e-6)
        worst = max(worst, rel)
    print(f"{name}: {len(net.roads)} roads, worst length mismatch {worst*100:.3f}%")
    fig, ax = plt.subplots(figsize=(8, 8))
    for r in net.roads.values():
        ax.plot(r.xy[:, 0], r.xy[:, 1], lw=1.2,
                color="tab:red" if r.junction != "-1" else "tab:blue")
        mid = r.xy[len(r.xy) // 2]
        ax.annotate(r.id, mid, fontsize=6)
    ax.set_aspect("equal"); ax.set_title(f"{name} (blue=road, red=junction-connecting)")
    fig.savefig(os.path.join(OUT, f"{name}.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
print("plots ->", OUT)
