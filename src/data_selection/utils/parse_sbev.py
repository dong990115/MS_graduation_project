"""SBEV filename parser and road-type resolver."""

import os
import re
import csv
from bisect import bisect_right

# PSM: scenario always ends with _ST, _CU, or _IN before trailing numbers
_PSM_RE = re.compile(
    r'^Image_(\d+)_(.+?_(?:ST|CU|IN))_(\d+(?:_\d+)*)\.png$'
)
# RG3: scenario = RG3_{date}, then exactly 2 trailing numbers
_RG3_RE = re.compile(
    r'^Image_(\d+)_(RG3_\d+)_(\d+)_(\d+)\.png$'
)

SUFFIX_TO_ROAD = {'ST': 'HW', 'CU': 'URB', 'IN': 'INT'}


def parse_sbev_filename(filename):
    """Parse SBEV filename → (collision_mode, scenario, data_index, frame_index).

    Handles two formats:
      Init:  Image_{cm}_{scenario}_{dataIndex}_{frameIndex}.png
      FP:    Image_{cm}_{scenario}_{dataIndex}_{frameIndex}_{subIndex}.png
    PSM scenario always ends with _ST/_CU/_IN.
    RG3 scenario = RG3_{date}, always 2 trailing numbers.
    """
    m = _RG3_RE.match(filename)
    if m:
        return int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))

    m = _PSM_RE.match(filename)
    if m:
        cm = int(m.group(1))
        scenario = m.group(2)
        trailing = m.group(3).split('_')
        data_index = int(trailing[0])
        frame_index = int(trailing[1]) if len(trailing) >= 2 else 0
        return cm, scenario, data_index, frame_index

    raise ValueError(f'Cannot parse SBEV filename: {filename}')


def road_type_from_psm(scenario):
    """PSM scenario suffix → road type (HW / URB / INT / Others)."""
    suffix = scenario.rsplit('_', 1)[-1]
    return SUFFIX_TO_ROAD.get(suffix, 'Others')


def load_rg3_annotations(rg3_csv_dir):
    """Load all RG3 road-type CSVs.

    Returns dict: (rg3_date, data_index) → sorted list of (frame, road_type).
    """
    lookup = {}
    for rg3_subdir in os.listdir(rg3_csv_dir):
        subdir_path = os.path.join(rg3_csv_dir, rg3_subdir)
        if not os.path.isdir(subdir_path):
            continue
        for fname in os.listdir(subdir_path):
            if not fname.endswith('.csv'):
                continue
            base = os.path.splitext(fname)[0]
            segments = base.split('_')
            if len(segments) < 3 or segments[0] != 'RG3':
                continue
            rg3_date = f'{segments[0]}_{segments[1]}'
            data_idx = int(segments[2])

            annotations = []
            with open(os.path.join(subdir_path, fname), newline='') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    if len(row) >= 2:
                        try:
                            frame = int(float(row[0].strip()))
                            rt = row[1].strip().upper()
                            # Normalize: OTHERS → Others
                            rt_map = {'HW': 'HW', 'INT': 'INT', 'URB': 'URB',
                                       'RAB': 'RAB', 'OTHERS': 'Others'}
                            rt = rt_map.get(rt, rt)
                            annotations.append((frame, rt))
                        except ValueError:
                            continue
            annotations.sort(key=lambda x: x[0])
            lookup[(rg3_date, data_idx)] = annotations
    return lookup


def road_type_from_rg3(rg3_date, data_index, frame_index, rg3_lookup):
    """Look up road type for an RG3 SBEV at a given frame."""
    key = (rg3_date, data_index)
    if key not in rg3_lookup:
        return 'Unknown'

    annotations = rg3_lookup[key]
    if not annotations:
        return 'Unknown'
    frames = [a[0] for a in annotations]
    idx = bisect_right(frames, frame_index) - 1
    if idx < 0:
        return annotations[0][1]
    return annotations[idx][1]


def drive_road_type_summary(rg3_date, data_index, rg3_lookup, max_frame=None):
    """Summarize road types for an entire RG3 drive.

    Returns (dominant_type, all_types_str, segment_detail_str).
    - dominant_type: road type covering the most frames
    - all_types_str: comma-separated unique types in order of appearance
    - segment_detail_str: "HW(1-253),RAB(254-1844)" style detail

    max_frame: largest known frame for this drive (from SBEV data),
               used as the end boundary for the last segment.
    """
    key = (rg3_date, data_index)
    if key not in rg3_lookup or not rg3_lookup[key]:
        return 'Unknown', 'Unknown', ''

    annotations = rg3_lookup[key]
    if max_frame is None:
        max_frame = annotations[-1][0] + 1000

    segments = []
    for i, (frame, rt) in enumerate(annotations):
        end = annotations[i + 1][0] - 1 if i + 1 < len(annotations) else max_frame
        duration = max(end - frame + 1, 1)
        segments.append((rt, frame, end, duration))

    durations = {}
    for rt, _, _, dur in segments:
        durations[rt] = durations.get(rt, 0) + dur

    dominant = max(durations, key=durations.get)
    all_types = []
    for rt, _, _, _ in segments:
        if rt not in all_types:
            all_types.append(rt)
    all_types_str = ','.join(all_types)

    detail_parts = [f'{rt}({start}-{end})' for rt, start, end, _ in segments]
    detail_str = ','.join(detail_parts)

    return dominant, all_types_str, detail_str
