"""
Step 4: Algorithm 2 — Per-class EIG 기반 subset 선별 (GPU 가속)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
논문 Definition 4 기반 per-class EIG:
  - Z = Z_RAB (학습 데이터 중 RAB road type만, 9장)
  - Z' = v13 증강 RAB 데이터 (5,033장)
  - mean normalization 적용 (Definition 4)
  - EIG = (V(F) - V(Z)) / V(Z),  F = [Z, Z'_selected]

최적화:
  gram_centered = gram_raw - N * mean ⊗ mean
  → gram_raw는 누적 가능, mean만 재계산

Input:
  - embeddings_pca_B.mat (Z_pca, Z_prime_pca, Z_prime_filenames)
  - subsets.mat (cluster_labels)
  - training_road_type_label.csv (RAB 인덱스 추출용)
Output:
  - selected_scenarios.csv
  - algorithm2_result.mat
  - selected_v13/ (선별된 SBEV + mode_classification 복사)
  - selected_subsets/ (선택된 서브셋별 디렉토리)
"""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 유니코드 출력 크래시 방지
import shutil
import time
import csv
import numpy as np
import torch
from scipy.io import loadmat, savemat

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(_SCRIPT_DIR)

# 임베딩 경로는 06_EIG 공통 헬퍼가 결정한다 (--emb / --nas / local / NAS fallback)
sys.path.insert(0, MODULE_ROOT)
from _emb_path import parse_emb_args, resolve_emb_path
_EMB_ARGS = parse_emb_args()


# ━━ Experiment Config ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUN_NAME = "CMO_4500"  # ①과 통일 (구 tail_Others_RAB 중첩 구조는 E 원본에 보존)
K = 500

OUTPUT_ROOT = os.path.join(MODULE_ROOT, 'Output', 'CMO', RUN_NAME)
K_DIR = os.path.join(OUTPUT_ROOT, f"K_{K}")

EMB_PATH = resolve_emb_path("CMO", "CMO_4500", MODULE_ROOT, _EMB_ARGS)
SUB_PATH = os.path.join(K_DIR, "subsets.mat")
LABEL_PATH = os.path.join(MODULE_ROOT, 'Output', 'common', 'training_road_type_label.csv')
OUTPUT_CSV = os.path.join(K_DIR, "selected_scenarios.csv")
OUTPUT_MAT = os.path.join(K_DIR, "algorithm2_result.mat")

_IMG_LOCAL = os.path.join(MODULE_ROOT, 'Output', 'CMO', 'tail_RAB')
# NOTE: "LK_CIR_MER_RAB_FOT"는 07 학습 로더의 클래스 폴더 "규약명"이다.
#       CMO/Remix는 시뮬레이션 시나리오 생성이 아니라 기존 학습 SBEV의 이미지
#       합성/재조합이며, 전방 합류(LK) 클래스 슬롯으로 학습에 투입하기 위해
#       이 폴더명을 사용할 뿐이다 (파일명 Image_*_{CMO|Remix}_*.png 로 구분).
V13_SRC_DIR = _IMG_LOCAL if os.path.isdir(os.path.join(_IMG_LOCAL, 'LK_CIR_MER_RAB_FOT')) else r'<DATA_NAS>\MapBuilder\augmented_dataset\CMO_4500'  # 로컬 우선 → NAS 정본
V13_SBEV_DIRS = ["LK_CIR_MER_RAB_FOT"]
SELECTED_DST_DIR = os.path.join(K_DIR, "selected_v13")
SELECTED_SUBSETS_DIR = os.path.join(K_DIR, "selected_subsets")

EIG_TARGET = 5.5
EPSILON = 0.01

FORCE_CPU = False
DEVICE = "cpu" if FORCE_CPU else ("cuda" if torch.cuda.is_available() else "cpu")


def volume_from_gram(gram_centered, N, eye):
    """V(X) = 0.5 * log2 det(I + 1/N * gram_centered)"""
    if N == 0:
        return 0.0
    M = eye + (1.0 / N) * gram_centered
    sign, logabsdet = torch.linalg.slogdet(M)
    return 0.5 * logabsdet.item() / np.log(2)


def centered_gram(gram_raw, sum_vec, N, device):
    """gram_centered = gram_raw - N * mean ⊗ mean
    where mean = sum_vec / N"""
    mean = sum_vec / N  # (d,)
    return gram_raw - N * torch.outer(mean, mean)


def load_rab_indices(label_path):
    rab_indices = []
    with open(label_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if "RAB" in row.get("road_type", "").upper():
                rab_indices.append(i)
    return rab_indices


def organize_selected_subsets(aug_indices, cluster_labels, filenames,
                              selected_clusters_order, src_dir, sbev_dirs, dst_root):
    """선택된 서브셋을 클러스터별 디렉토리로 복사."""
    print(f"\n[추가] 선택된 서브셋 디렉토리 생성: {dst_root}")

    if os.path.exists(dst_root):
        shutil.rmtree(dst_root)

    sbev_srcs = [os.path.join(src_dir, d) for d in sbev_dirs]
    total_copied = 0

    for order_idx, cid in enumerate(selected_clusters_order, start=1):
        indices = np.where(cluster_labels == cid)[0]
        subset_dir = os.path.join(dst_root, f"subset_{cid+1:03d}")
        os.makedirs(subset_dir, exist_ok=True)

        copied = 0
        for idx in indices:
            fname = filenames[idx]
            for sbev_src in sbev_srcs:
                src = os.path.join(sbev_src, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(subset_dir, fname))
                    copied += 1
                    break
        total_copied += copied

    print(f"  선택된 클러스터: {len(selected_clusters_order)}개")
    print(f"  이미지 복사: {total_copied:,d}장")


def main():
    os.makedirs(K_DIR, exist_ok=True)
    print(f"=== Step 4: Algorithm 2 — Per-class EIG (GPU: {DEVICE}) ===")
    print(f"  RUN_NAME:   {RUN_NAME}")
    print(f"  K:          {K}")
    print(f"  Output:     {K_DIR}")
    print(f"  EIG_target: {EIG_TARGET}")
    print(f"  epsilon:    {EPSILON}")
    if DEVICE == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}\n")
    else:
        print("  WARNING: CUDA not available, falling back to CPU\n")

    # ─── [1/5] 데이터 로드 ───
    print("[1/5] 데이터 로드...")
    emb_data = loadmat(EMB_PATH)
    sub_data = loadmat(SUB_PATH)

    Z_pca_all = emb_data["Z_pca"]
    Z_prime_pca = emb_data["Z_prime_pca"]
    Z_prime_fnames = [str(s[0]) if isinstance(s, np.ndarray) else str(s).strip()
                      for s in emb_data["Z_prime_filenames"].flatten()]
    cluster_labels = sub_data["cluster_labels"].flatten()
    k = int(sub_data["k"].item())
    d = Z_pca_all.shape[1]

    # Z_RAB 추출
    rab_indices = load_rab_indices(LABEL_PATH)
    Z_rab = Z_pca_all[rab_indices].astype(np.float64)
    N_z = len(rab_indices)
    print(f"  Z_RAB: {Z_rab.shape} ({N_z}장)")
    print(f"  Z': {Z_prime_pca.shape}, d={d}, k={k}")

    # ─── [1.5/5] 사전계산 ───
    print(f"\n[1.5/5] 사전계산 (on {DEVICE})...")
    t0 = time.time()

    eye = torch.eye(d, dtype=torch.float64, device=DEVICE)

    # Z_RAB: gram_raw, sum
    Z_rab_torch = torch.from_numpy(Z_rab).to(DEVICE)
    gram_z_raw = Z_rab_torch.T @ Z_rab_torch     # (d, d)
    sum_z = Z_rab_torch.sum(dim=0)                # (d,)

    # V(Z_RAB) — mean normalized
    gram_z_centered = centered_gram(gram_z_raw, sum_z, N_z, DEVICE)
    v_z = volume_from_gram(gram_z_centered, N_z, eye)
    print(f"  V(Z_RAB) = {v_z:.6f} (N={N_z})")

    if v_z == 0:
        print("  ERROR: V(Z_RAB) = 0")
        return

    # Z' 전체를 GPU에, subset별 sum만 사전계산 (gram은 on-the-fly)
    Z_prime_torch = torch.from_numpy(Z_prime_pca.astype(np.float64)).to(DEVICE)

    subsets = {}
    subset_sum = {}
    subset_N = {}
    for cid in range(k):
        indices = np.where(cluster_labels == cid)[0]
        if len(indices) > 0:
            subsets[cid] = indices
            subset_N[cid] = len(indices)
            subset_sum[cid] = Z_prime_torch[indices].sum(dim=0)

    if DEVICE == "cuda":
        torch.cuda.synchronize()
    print(f"  non-empty subsets: {len(subsets)}")
    print(f"  subset sum 사전계산 완료 ({time.time()-t0:.1f}s)")
    if DEVICE == "cuda":
        alloc = torch.cuda.memory_allocated() / 1e9
        print(f"  GPU memory: {alloc:.1f} GB")

    # ─── [2/5] Algorithm 2 ───
    print(f"\n[2/5] Algorithm 2 실행 (per-class, Z=RAB {N_z}장)...\n")
    aug_indices = []
    remaining = set(subsets.keys())
    eig_history = []
    selected_clusters_order = []

    # 누적 gram_raw, sum (Z_RAB + 선택된 Z' subsets)
    base_gram_raw = gram_z_raw.clone()
    base_sum = sum_z.clone()
    N_base = N_z

    iteration = 0
    t_start = time.time()

    while remaining:
        best_k = None
        best_diff = float("inf")
        best_eig = 0.0

        n_remaining = len(remaining)
        for eval_idx, sk in enumerate(remaining):
            if eval_idx % 100 == 0:
                print(f"    evaluating {eval_idx}/{n_remaining}...", end="\r", flush=True)
            # S_k gram on-the-fly
            S = Z_prime_torch[subsets[sk]]
            sk_gram = S.T @ S

            cand_gram_raw = base_gram_raw + sk_gram
            cand_sum = base_sum + subset_sum[sk]
            N_cand = N_base + subset_N[sk]

            cand_gram_centered = centered_gram(cand_gram_raw, cand_sum, N_cand, DEVICE)
            v_f = volume_from_gram(cand_gram_centered, N_cand, eye)
            eig_val = (v_f - v_z) / v_z

            diff = abs(eig_val - EIG_TARGET)
            if diff < best_diff:
                best_diff = diff
                best_k = sk
                best_eig = eig_val
                best_sk_gram = sk_gram

        # 최적 subset 추가
        aug_indices.extend(subsets[best_k].tolist())
        selected_clusters_order.append(best_k)
        base_gram_raw += best_sk_gram
        base_sum += subset_sum[best_k]
        N_base += subset_N[best_k]
        remaining.remove(best_k)
        eig_current = best_eig
        eig_history.append(eig_current)
        iteration += 1

        elapsed = time.time() - t_start
        if iteration <= 10 or iteration % 10 == 0 or abs(eig_current - EIG_TARGET) <= EPSILON:
            print(f"  iter {iteration:3d}: +subset {best_k+1:3d} "
                  f"({subset_N[best_k]:3d} samples), "
                  f"aug={len(aug_indices):>5,d}, "
                  f"EIG={eig_current:.6f}, "
                  f"|diff|={abs(eig_current - EIG_TARGET):.6f}  "
                  f"({elapsed:.0f}s)")

        if abs(eig_current - EIG_TARGET) <= EPSILON:
            print(f"\n  *** 수렴: EIG={eig_current:.6f} (target={EIG_TARGET}, eps={EPSILON}) ***")
            break

        # EIG가 target을 넘어서면 (overshoot) 경고 후 계속
        if eig_current > EIG_TARGET + EPSILON and iteration > 1:
            prev_eig = eig_history[-2] if len(eig_history) > 1 else 0
            if prev_eig < EIG_TARGET:
                print(f"\n  *** Overshoot: EIG={eig_current:.6f} > target={EIG_TARGET}")
                print(f"      이전 iter EIG={prev_eig:.6f}에서 target에 더 가까웠음")
                print(f"      현재 결과 그대로 사용 ***")
                break
    else:
        print(f"\n  subset 소진: EIG={eig_current:.6f} (target={EIG_TARGET})")
        if abs(eig_current - EIG_TARGET) > EPSILON:
            print(f"  WARNING: 목표 미달 (|diff|={abs(eig_current - EIG_TARGET):.6f} > eps)")

    total_time = time.time() - t_start
    print(f"  총 소요: {total_time:.0f}s ({total_time/60:.1f}min)")

    # ─── [3/5] 결과 정리 ───
    print(f"\n[3/5] 결과 정리...")
    selected_fnames = [Z_prime_fnames[i] for i in aug_indices]
    n_selected = len(selected_fnames)
    n_total = len(Z_prime_fnames)
    print(f"  선별: {n_selected:,d} / {n_total:,d} ({n_selected/n_total*100:.1f}%)")
    print(f"  최종 EIG: {eig_history[-1]:.6f}")
    print(f"  iterations: {iteration}")
    print(f"  선택된 클러스터: {[c+1 for c in selected_clusters_order]}")

    # ─── [4/5] 저장 ───
    print(f"\n[4/5] 저장...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "original_index"])
        for idx in aug_indices:
            writer.writerow([Z_prime_fnames[idx], idx])
    print(f"  CSV -> {OUTPUT_CSV}")

    savemat(OUTPUT_MAT, {
        "selected_indices": np.array(aug_indices, dtype=np.int32),
        "selected_filenames": np.array(selected_fnames, dtype=object),
        "eig_history": np.array(eig_history),
        "eig_target": EIG_TARGET,
        "epsilon": EPSILON,
        "final_eig": eig_history[-1],
        "n_iterations": iteration,
        "z_rab_count": N_z,
        "z_rab_indices": np.array(rab_indices, dtype=np.int32),
        "selected_clusters_order": np.array(selected_clusters_order, dtype=np.int32),
    })
    print(f"  MAT -> {OUTPUT_MAT}")

    # ─── [5/5] 선별 데이터 복사 ───
    print(f"\n[5/5] 선별 데이터 복사...")
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

    print(f"  SBEV: {copied_sbev}/{n_selected} -> {SELECTED_DST_DIR}")
    print(f"  mode_classification: {copied_mode}/{n_selected} -> {mode_dst}")

    mode_counts = {}
    for fname in selected_fnames:
        m = mode_lookup.get(fname, "Unknown")
        mode_counts[m] = mode_counts.get(m, 0) + 1
    print(f"\n  Collision mode 분포:")
    for m in sorted(mode_counts.keys()):
        print(f"    {m}: {mode_counts[m]}")

    # ─── [수정 D] 선택된 서브셋 디렉토리 ───
    organize_selected_subsets(
        aug_indices, cluster_labels, Z_prime_fnames,
        selected_clusters_order, V13_SRC_DIR, V13_SBEV_DIRS, SELECTED_SUBSETS_DIR
    )

    print(f"\n=== 완료 ===")
    print(f"선별 결과: {SELECTED_DST_DIR}")
    print(f"서브셋 디렉토리: {SELECTED_SUBSETS_DIR}")


if __name__ == "__main__":
    main()
