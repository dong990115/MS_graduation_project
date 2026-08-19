"""
Case 4: 랜덤 선별 (EIG 없이)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Z' 중 N_SELECT장을 랜덤으로 선별. EIG 기반 선별과의 비교용 baseline.

Input:  embeddings_pca_B.mat (Z_prime_filenames)
Output: selected_scenarios.csv, selected_v13/
"""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 유니코드 출력 크래시 방지
import shutil
import csv
import numpy as np
from scipy.io import loadmat, savemat

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(_SCRIPT_DIR)

# 임베딩 경로는 06_EIG 공통 헬퍼가 결정한다 (--emb / --nas / local / NAS fallback)
sys.path.insert(0, MODULE_ROOT)
from _emb_path import parse_emb_args, resolve_emb_path
_EMB_ARGS = parse_emb_args()
MONOREPO_ROOT = os.path.dirname(MODULE_ROOT)

# ━━ Experiment Config ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUN_NAME = "noLane_060126_sub4500"
N_SELECT = 139  # 논문 학습 사용본과 동수 (EIG 선별 139장 기준).
# 주의: 재실행 산출이 논문 학습 사용 세트와 동일하다는 보장은 없음
#       — 논문 세트 정본은 NAS augmented_dataset/PCG_random 참조.
SEED = 42

OUTPUT_ROOT = os.path.join(MODULE_ROOT, 'Output', 'PCG', RUN_NAME)
RANDOM_DIR = os.path.join(OUTPUT_ROOT, "random_select")

EMB_PATH = resolve_emb_path("PCG", "noLane_060126_sub4500", MODULE_ROOT, _EMB_ARGS)
OUTPUT_CSV = os.path.join(RANDOM_DIR, "selected_scenarios.csv")
OUTPUT_MAT = os.path.join(RANDOM_DIR, "random_select_result.mat")

_FULL_LOCAL = os.path.join(MONOREPO_ROOT, '05_MapBuilder', 'Output', 'DSM', 'RAB_v13_Train_060126_noLane')
V13_SRC_DIR = _FULL_LOCAL if os.path.isdir(_FULL_LOCAL) else r'<DATA_NAS>\MapBuilder\output\RAB_v13_Train_060126_noLane'  # 로컬 우선 → NAS full set
V13_SBEV_DIRS = ["LK_CIR_MER_RAB_FOT", "drivingAlone_RVL_RAB_FOT"]
SELECTED_DST_DIR = os.path.join(RANDOM_DIR, "selected_v13")


def main():
    os.makedirs(RANDOM_DIR, exist_ok=True)
    print(f"=== Case 4: Random Select (N={N_SELECT}, seed={SEED}) ===")
    print(f"  RUN_NAME: {RUN_NAME}")
    print(f"  Output:   {RANDOM_DIR}\n")

    print("[1/3] 로드...")
    emb_data = loadmat(EMB_PATH)
    Z_prime_fnames = [
        str(s[0]) if isinstance(s, np.ndarray) else str(s).strip()
        for s in emb_data["Z_prime_filenames"].flatten()
    ]
    n_total = len(Z_prime_fnames)
    print(f"  Z': {n_total}장")

    print(f"\n[2/3] 랜덤 선별 ({N_SELECT}장)...")
    rng = np.random.RandomState(SEED)
    selected_indices = rng.choice(n_total, size=min(N_SELECT, n_total), replace=False)
    selected_indices.sort()
    selected_fnames = [Z_prime_fnames[i] for i in selected_indices]
    print(f"  선별: {len(selected_fnames)}장 / {n_total}장")

    print(f"\n[3/3] 저장 + 복사...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "original_index"])
        for idx in selected_indices:
            writer.writerow([Z_prime_fnames[idx], idx])
    print(f"  CSV -> {OUTPUT_CSV}")

    savemat(OUTPUT_MAT, {
        "selected_indices": np.array(selected_indices, dtype=np.int32),
        "selected_filenames": np.array(selected_fnames, dtype=object),
        "n_select": N_SELECT,
        "seed": SEED,
    })
    print(f"  MAT -> {OUTPUT_MAT}")

    sbev_srcs = {d: os.path.join(V13_SRC_DIR, d) for d in V13_SBEV_DIRS}
    mode_src = os.path.join(V13_SRC_DIR, "mode_classification")
    mode_dst = os.path.join(SELECTED_DST_DIR, "mode_classification")

    for d in V13_SBEV_DIRS:
        os.makedirs(os.path.join(SELECTED_DST_DIR, d), exist_ok=True)

    mode_lookup = {}
    if os.path.isdir(mode_src):
        for mode_dir in os.listdir(mode_src):
            mode_path = os.path.join(mode_src, mode_dir)
            if os.path.isdir(mode_path):
                for fname in os.listdir(mode_path):
                    mode_lookup[fname] = mode_dir

    copied_sbev = 0
    copied_mode = 0
    for fname in selected_fnames:
        for d, sbev_src in sbev_srcs.items():
            src = os.path.join(sbev_src, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(SELECTED_DST_DIR, d, fname))
                copied_sbev += 1
                break

        if fname in mode_lookup:
            sub = mode_lookup[fname]
            dst_sub = os.path.join(mode_dst, sub)
            os.makedirs(dst_sub, exist_ok=True)
            mc_src = os.path.join(mode_src, sub, fname)
            if os.path.exists(mc_src):
                shutil.copy2(mc_src, os.path.join(dst_sub, fname))
                copied_mode += 1

    print(f"  SBEV: {copied_sbev}/{len(selected_fnames)} -> {SELECTED_DST_DIR}")
    print(f"  mode_classification: {copied_mode}/{len(selected_fnames)} -> {mode_dst}")

    mode_counts = {}
    for fname in selected_fnames:
        m = mode_lookup.get(fname, "Unknown")
        mode_counts[m] = mode_counts.get(m, 0) + 1
    print(f"\n  Collision mode 분포:")
    for m in sorted(mode_counts.keys()):
        print(f"    {m}: {mode_counts[m]}")

    print(f"\n=== 완료 ===")


if __name__ == "__main__":
    main()
