"""OpenDRIVE planView parser: reference-line centerline sampling + connectivity.

Measures ONLY the emergent geometry in the .xodr output files (never generator
input parameters), per the analysis spec's circular-reasoning caveat.

Supported geometry primitives: line, arc, spiral (clothoid), paramPoly3.
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Road:
    id: str
    junction: str            # "-1" for normal roads, else junction id
    length: float
    xy: np.ndarray           # (N, 2) sampled centerline (reference line)
    s: np.ndarray            # (N,) arc length of samples
    hdg: np.ndarray          # (N,) heading at samples [rad]
    predecessor: tuple = None  # (elementType, elementId, contactPoint)
    successor: tuple = None


@dataclass
class Connection:
    junction: str
    incoming_road: str
    connecting_road: str
    contact_point: str


@dataclass
class Network:
    roads: dict = field(default_factory=dict)        # id -> Road
    connections: list = field(default_factory=list)  # [Connection]


def _sample_line(x, y, hdg, length, ds):
    n = max(2, int(np.ceil(length / ds)) + 1)
    s = np.linspace(0.0, length, n)
    xs = x + s * np.cos(hdg)
    ys = y + s * np.sin(hdg)
    h = np.full(n, hdg)
    return s, xs, ys, h


def _sample_arc(x, y, hdg, length, curv, ds):
    n = max(2, int(np.ceil(length / ds)) + 1)
    s = np.linspace(0.0, length, n)
    h = hdg + curv * s
    # closed form: integral of cos/sin of linear heading
    xs = x + (np.sin(h) - np.sin(hdg)) / curv
    ys = y - (np.cos(h) - np.cos(hdg)) / curv
    return s, xs, ys, h


def _sample_spiral(x, y, hdg, length, c0, c1, ds):
    # numeric integration with fine step (clothoid: curvature linear in s)
    step = min(ds, 0.1)
    n = max(2, int(np.ceil(length / step)) + 1)
    s = np.linspace(0.0, length, n)
    h = hdg + c0 * s + 0.5 * (c1 - c0) / length * s ** 2
    xs = x + np.concatenate([[0.0], np.cumsum(0.5 * (np.cos(h[1:]) + np.cos(h[:-1])) * np.diff(s))])
    ys = y + np.concatenate([[0.0], np.cumsum(0.5 * (np.sin(h[1:]) + np.sin(h[:-1])) * np.diff(s))])
    # decimate back to ~ds spacing
    keep = np.unique(np.concatenate([np.arange(0, n, max(1, int(round(ds / step)))), [n - 1]]))
    return s[keep], xs[keep], ys[keep], h[keep]


def _sample_parampoly3(x, y, hdg, length, coeffs, p_range, ds):
    aU, bU, cU, dU, aV, bV, cV, dV = coeffs
    n_fine = max(3, int(np.ceil(length / min(ds, 0.1))) + 1)
    p_end = 1.0 if p_range == "normalized" else length
    p = np.linspace(0.0, p_end, n_fine)
    u = aU + bU * p + cU * p ** 2 + dU * p ** 3
    v = aV + bV * p + cV * p ** 2 + dV * p ** 3
    ca, sa = np.cos(hdg), np.sin(hdg)
    xs = x + u * ca - v * sa
    ys = y + u * sa + v * ca
    seg = np.hypot(np.diff(xs), np.diff(ys))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    h = np.arctan2(np.gradient(ys, s, edge_order=1), np.gradient(xs, s, edge_order=1))
    keep = np.unique(np.concatenate([np.searchsorted(s, np.arange(0.0, s[-1], ds)), [n_fine - 1]]))
    return s[keep], xs[keep], ys[keep], h[keep]


def _parse_link(road_el):
    pred = succ = None
    link = road_el.find("link")
    if link is not None:
        p = link.find("predecessor")
        if p is not None and p.get("elementId") is not None:
            pred = (p.get("elementType"), p.get("elementId"), p.get("contactPoint"))
        sc = link.find("successor")
        if sc is not None and sc.get("elementId") is not None:
            succ = (sc.get("elementType"), sc.get("elementId"), sc.get("contactPoint"))
    return pred, succ


def parse_xodr(path, ds=0.5):
    """Parse an .xodr into a Network with sampled reference-line centerlines."""
    root = ET.parse(path).getroot()
    net = Network()
    for road_el in root.findall("road"):
        rid = road_el.get("id")
        length = float(road_el.get("length"))
        pieces_s, pieces_x, pieces_y, pieces_h = [], [], [], []
        for g in road_el.findall("./planView/geometry"):
            gx, gy = float(g.get("x")), float(g.get("y"))
            ghdg, gs0 = float(g.get("hdg")), float(g.get("s"))
            glen = float(g.get("length"))
            if glen <= 0:
                continue
            child = list(g)[0] if len(g) else None
            tag = child.tag if child is not None else "line"
            if tag == "line":
                s, xs, ys, h = _sample_line(gx, gy, ghdg, glen, ds)
            elif tag == "arc":
                s, xs, ys, h = _sample_arc(gx, gy, ghdg, glen, float(child.get("curvature")), ds)
            elif tag == "spiral":
                s, xs, ys, h = _sample_spiral(gx, gy, ghdg, glen,
                                              float(child.get("curvStart")), float(child.get("curvEnd")), ds)
            elif tag == "paramPoly3":
                coeffs = [float(child.get(k)) for k in ("aU", "bU", "cU", "dU", "aV", "bV", "cV", "dV")]
                s, xs, ys, h = _sample_parampoly3(gx, gy, ghdg, glen, coeffs,
                                                  child.get("pRange", "normalized"), ds)
            else:
                raise ValueError(f"unsupported geometry <{tag}> in {path} road {rid}")
            pieces_s.append(s + gs0)
            pieces_x.append(xs)
            pieces_y.append(ys)
            pieces_h.append(h)
        if not pieces_s:
            continue
        s = np.concatenate(pieces_s)
        xy = np.column_stack([np.concatenate(pieces_x), np.concatenate(pieces_y)])
        h = np.concatenate(pieces_h)
        # drop duplicated joints
        keep = np.concatenate([[True], np.diff(s) > 1e-9])
        pred, succ = _parse_link(road_el)
        net.roads[rid] = Road(rid, road_el.get("junction", "-1"), length,
                              xy[keep], s[keep], h[keep], pred, succ)
    for j in root.findall("junction"):
        jid = j.get("id")
        for c in j.findall("connection"):
            net.connections.append(Connection(jid, c.get("incomingRoad"),
                                              c.get("connectingRoad"), c.get("contactPoint")))
    return net
