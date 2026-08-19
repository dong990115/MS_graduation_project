"""Roundabout ring extraction + curvature/entry-angle measurement.

All measurements are taken from the emergent road-network geometry (sampled
centerlines), never from generator input parameters.

Ring finding:
 1. least-squares circle fit per road piece -> near-circular candidates
 2. cluster candidates by (center, radius); pick the cluster with the largest
    total subtended arc  -> circulating-lane centerline radius R and center
 3. members = candidate pieces of that cluster (+ tiny stubs inside the band)
 4. star-shaped parameterization r(theta) around the center; theta ranges not
    covered by any member are filled with the fitted circle and MASKED so they
    never enter curvature statistics
 5. uniform arc-length resampling -> Menger curvature kappa(s)

Entry angle phi (realized, from output geometry only):
    at the conflict point p* where an entry/exit connecting road crosses the
    circulating centerline (r = R), phi = angle between the connector tangent
    and the ring tangent, folded to [0, 90] deg. A secondary measurement at
    r = R + 3.5 m (approx. yield-line position, one lane outward) is also
    returned for robustness checks.
"""
from dataclasses import dataclass, field

import numpy as np

RING_R_MIN, RING_R_MAX = 5.0, 60.0
FIT_RMS_MAX = 0.6           # [m] near-circular piece threshold (candidates only)
BAND_LOOSE = 5.0            # [m] |d-R| prefilter for member-candidate pieces
MEAN_LOOSE = 3.5            # [m] mean|d-R| prefilter (drops far bypass arcs)
CHAIN_DR = 0.8              # [m] max radial jump between chained pieces
CHAIN_DS = 6.0              # [m] max along-ring gap between chained pieces
DTHETA = np.radians(0.25)   # theta grid


def fit_circle(xy):
    """Kasa algebraic circle fit -> (cx, cy, r, rms)."""
    x, y = xy[:, 0], xy[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x ** 2 + y ** 2
    try:
        c, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan, np.nan, np.nan, np.inf
    cx, cy = c[0] / 2, c[1] / 2
    r = np.sqrt(max(c[2] + cx ** 2 + cy ** 2, 0.0))
    rms = np.sqrt(np.mean((np.hypot(x - cx, y - cy) - r) ** 2))
    return cx, cy, r, rms


def _subtended(xy, cx, cy):
    ang = np.unwrap(np.arctan2(xy[:, 1] - cy, xy[:, 0] - cx))
    return abs(ang[-1] - ang[0])


@dataclass
class Ring:
    center: np.ndarray
    radius: float
    loop_xy: np.ndarray        # (N,2) closed loop, CCW, ~uniform arc spacing
    loop_real: np.ndarray      # (N,) bool: True where geometry comes from roads
    member_ids: list
    coverage: float            # fraction of theta covered by real geometry
    diag: dict = field(default_factory=dict)


def find_ring_members(net):
    """center/R + member pieces.

    1. candidate (center, radius) from per-piece circle fits
    2. score each candidate by theta-bin coverage of ALL road points within a
       deformation-tolerant band -> robust against strongly deformed rings
       whose individual piece fits scatter
    3. loose band prefilter -> member-candidate pieces
    4. keep the endpoint-chained component (radial jump <= CHAIN_DR, along-
       ring gap <= CHAIN_DS): the circulating line is radially continuous,
       parallel-offset pieces (outer lanes, junction-mouth stubs) are not
    """
    allpts = np.vstack([r.xy for r in net.roads.values() if len(r.xy) >= 2])
    cands = []
    for r in net.roads.values():
        if len(r.xy) < 4:
            continue
        cx, cy, rad, rms = fit_circle(r.xy)
        if RING_R_MIN <= rad <= RING_R_MAX and rms <= FIT_RMS_MAX:
            cands.append((cx, cy, rad))
    if not cands:
        raise RuntimeError("no near-circular road pieces found")
    nbins = 72
    best, best_score = None, -np.inf
    for cx, cy, rad in cands:
        d = np.hypot(allpts[:, 0] - cx, allpts[:, 1] - cy)
        dev = np.abs(d - rad)
        band = dev <= max(2.0, 0.20 * rad)
        if not band.any():
            continue
        th = np.arctan2(allpts[band, 1] - cy, allpts[band, 0] - cx)
        cov = len(np.unique(((th + np.pi) / (2 * np.pi) * nbins).astype(int))) / nbins
        # alignment penalty separates the true circulating circle (band points
        # hug it) from spurious circles that merely graze many roads
        score = cov - 0.08 * float(dev[band].mean())
        if score > best_score:
            best_score, best = score, (cx, cy, rad)
    cx, cy, R = best
    center = np.array([cx, cy])

    cand_pieces = []
    for r in net.roads.values():
        d = np.hypot(r.xy[:, 0] - cx, r.xy[:, 1] - cy)
        if np.abs(d - R).max() <= BAND_LOOSE and abs(np.mean(d) - R) <= MEAN_LOOSE:
            cand_pieces.append(r)
    if not cand_pieces:
        raise RuntimeError("no ring member candidates")

    def polar_end(r, which):
        p = r.xy[0] if which == 0 else r.xy[-1]
        return (np.hypot(p[0] - cx, p[1] - cy), np.arctan2(p[1] - cy, p[0] - cx))

    n = len(cand_pieces)
    ends = [(polar_end(r, 0), polar_end(r, 1)) for r in cand_pieces]

    def linked(ei, ek):
        (ri, ti), (rk, tk) = ei, ek
        dth = np.angle(np.exp(1j * (ti - tk)))
        return abs(ri - rk) <= CHAIN_DR and R * abs(dth) <= CHAIN_DS

    # connected components under radial-continuity linkage; parallel-offset
    # pieces (outer lanes, mouth stubs at a radial jump) fall into their own
    # component. Slip connectors that touch the ring at both ends may join
    # the ring component here — they are removed later by the loop-distance
    # refinement in extract_ring.
    adj = {i: [] for i in range(n)}
    for i in range(n):
        for k in range(i + 1, n):
            if any(linked(ends[i][a], ends[k][b]) for a in (0, 1) for b in (0, 1)):
                adj[i].append(k)
                adj[k].append(i)
    seen, comps = set(), []
    for i in range(n):
        if i in seen:
            continue
        stack, comp = [i], []
        seen.add(i)
        while stack:
            u = stack.pop()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        comps.append(comp)
    arcs = [sum(_subtended(cand_pieces[i].xy, cx, cy) for i in c) for c in comps]
    members = [cand_pieces[i] for i in comps[int(np.argmax(arcs))]]
    pts = np.vstack([r.xy for r in members])
    cx2, cy2, R2, _ = fit_circle(pts)
    return np.array([cx2, cy2]), R2, members


def _build_rgrid(members, center, R, theta):
    rgrid = np.full(theta.shape, np.nan)
    for r in members:
        th = np.arctan2(r.xy[:, 1] - center[1], r.xy[:, 0] - center[0])
        rad = np.hypot(r.xy[:, 0] - center[0], r.xy[:, 1] - center[1])
        thu = np.unwrap(th)
        if thu[-1] < thu[0]:            # orient CCW
            thu, rad = thu[::-1], rad[::-1]
        # map onto grid (piece may wrap the -pi/pi seam)
        for k in range(len(thu) - 1):
            t0, t1 = thu[k], thu[k + 1]
            if t1 - t0 <= 0:
                continue
            tt = theta[:, None] + np.array([-2 * np.pi, 0, 2 * np.pi])[None, :]
            hit = (tt >= t0) & (tt < t1)
            rows, cols = np.where(hit)
            if len(rows) == 0:
                continue
            tvals = tt[rows, cols]
            w = (tvals - t0) / (t1 - t0)
            vals = rad[k] * (1 - w) + rad[k + 1] * w
            take = np.isnan(rgrid[rows]) | (np.abs(vals - R) < np.abs(rgrid[rows] - R))
            rgrid[rows[take]] = vals[take]
    return rgrid


def extract_ring(net, ds=0.5):
    center, R, members = find_ring_members(net)
    theta = np.arange(-np.pi, np.pi, DTHETA)
    rgrid = _build_rgrid(members, center, R, theta)
    # refinement passes: drop chained-in pieces that veer off the assembled
    # loop (entry/exit slip connectors touching the ring at both ends). A
    # piece alone at its theta IS the loop there (deviation 0), so genuinely
    # deformed unique ring pieces are never dropped.
    for _ in range(3):
        keep = []
        for r in members:
            th = np.arctan2(r.xy[:, 1] - center[1], r.xy[:, 0] - center[0])
            rad = np.hypot(r.xy[:, 0] - center[0], r.xy[:, 1] - center[1])
            bins = np.clip(((th + np.pi) / DTHETA).astype(int), 0, len(theta) - 1)
            ref = rgrid[bins]
            ok = np.isfinite(ref)
            if ok.any() and float(np.max(np.abs(rad[ok] - ref[ok]))) <= 1.5:
                keep.append(r)
        if len(keep) == len(members) or not keep:
            break
        members = keep
        rgrid = _build_rgrid(members, center, R, theta)
    real = ~np.isnan(rgrid)
    coverage = float(real.mean())
    rgrid = np.where(real, rgrid, R)   # fill gaps with fitted circle (masked)
    xy = np.column_stack([center[0] + rgrid * np.cos(theta),
                          center[1] + rgrid * np.sin(theta)])
    # arc-length resample, carrying the real/filled mask
    closed = np.vstack([xy, xy[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    su = np.arange(0.0, s[-1], ds)
    loop = np.column_stack([np.interp(su, s, closed[:, 0]),
                            np.interp(su, s, closed[:, 1])])
    idx = np.minimum(np.searchsorted(s, su), len(real) - 1)
    real_mask = real[idx]
    return Ring(center, R, loop, real_mask, [r.id for r in members], coverage,
                diag={"n_members": len(members), "loop_len": float(s[-1]), "ds": ds})


def menger_curvature(ring, span=4):
    """kappa(s) on the closed loop; returns (kappa, valid_mask).

    valid excludes filled gaps plus a +-span buffer around them so that
    circle-filled bridging never contaminates the statistics.
    """
    loop = ring.loop_xy
    A = np.roll(loop, span, axis=0)
    B = loop
    C = np.roll(loop, -span, axis=0)
    ab = np.hypot(*(B - A).T)
    bc = np.hypot(*(C - B).T)
    ca = np.hypot(*(A - C).T)
    cross = (B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])
    kappa = np.where(ab * bc * ca > 1e-12, 2.0 * np.abs(cross) / (ab * bc * ca), 0.0)
    valid = ring.loop_real.copy()
    for k in range(1, 2 * span + 1):   # wide buffer: joints next to masked
        valid &= np.roll(ring.loop_real, k) & np.roll(ring.loop_real, -k)
    return kappa, valid


def _ring_tangent(ring, p):
    loop = ring.loop_xy
    j = int(np.argmin(np.hypot(loop[:, 0] - p[0], loop[:, 1] - p[1])))
    t = np.roll(loop, -2, axis=0)[j] - np.roll(loop, 2, axis=0)[j]
    return t / (np.hypot(*t) + 1e-12)


def _crossings(xy, center, r_cross):
    """indices k where the polyline crosses radius r_cross (either way)."""
    d = np.hypot(xy[:, 0] - center[0], xy[:, 1] - center[1])
    sign = d - r_cross
    return np.where(sign[:-1] * sign[1:] < 0)[0], d


def entry_angles(net, ring):
    """Realized conflict angle per connecting road crossing the ring band.

    Returns one record per (connector, crossing of r=R): phi at the
    circulating centerline and phi at r=R+3.5 m (yield-line proxy).
    """
    center, R = ring.center, ring.radius
    ring_ids = set(ring.member_ids)
    out = []
    for r in net.roads.values():
        if r.id in ring_ids or r.junction == "-1" or len(r.xy) < 5:
            continue
        d = np.hypot(r.xy[:, 0] - center[0], r.xy[:, 1] - center[1])
        if d.min() > R + 2.0 or d.max() < R + 4.5:
            continue  # does not bridge from outside into the circulating lane
        for r_cross, key in ((R, "phi_deg"), (R + 3.5, "phi_yield_deg")):
            ks, dd = _crossings(r.xy, center, r_cross)
            for k in ks:
                w = (r_cross - dd[k]) / (dd[k + 1] - dd[k] + 1e-12)
                p = r.xy[k] * (1 - w) + r.xy[k + 1] * w
                a = r.xy[max(k - 2, 0)]
                b = r.xy[min(k + 3, len(r.xy) - 1)]
                t = (b - a) / (np.hypot(*(b - a)) + 1e-12)
                tr = _ring_tangent(ring, p)
                phi = np.degrees(np.arccos(np.clip(abs(np.dot(t, tr)), 0, 1)))
                rec = next((q for q in out if q["road"] == r.id), None)
                if rec is None:
                    rec = {"road": r.id, "junction": r.junction}
                    out.append(rec)
                rec.setdefault(key, []).append(float(phi))
                rec.setdefault(key + "_p", []).append(p)
    return out
