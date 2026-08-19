"""
Step 3: k-means subset 분할
━━━━━━━━━━━━━━━━━━━━━━━━━━
Z' embedding을 k=500 subset으로 분할. Algorithm 2의 선택 단위.

Input:  embeddings_pca_B.mat (Z_prime_pca: 5033×d)
Output: subsets.mat (cluster_labels, centroids, subset_sizes)
        subsets_dirs/ (물리적 서브셋 디렉토리, 토글)
"""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 유니코드 출력 크래시 방지
import shutil
import numpy as np
from scipy.io import loadmat, savemat
from sklearn.cluster import KMeans

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(_SCRIPT_DIR)

# 임베딩 경로는 06_EIG 공통 헬퍼가 결정한다 (--emb / --nas / local / NAS fallback)
sys.path.insert(0, MODULE_ROOT)
from _emb_path import parse_emb_args, resolve_emb_path
_EMB_ARGS = parse_emb_args()


# ━━ Experiment Config ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUN_NAME = "Remix_4500"

# ━━ 서브셋 디렉토리 생성 토글 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORGANIZE_DIRS = True

# 이미지 세트: 로컬(레포/⓪ 산출) 우선 → 없으면 NAS 정본
_IMG_LOCAL = os.path.join(MODULE_ROOT, 'Output', 'Remix', 'tail_RAB')
_IMG_NAS = r'<DATA_NAS>\MapBuilder\augmented_dataset\Remix_4500'
# NOTE: "LK_CIR_MER_RAB_FOT"는 07 학습 로더의 클래스 폴더 "규약명"이다.
#       CMO/Remix는 시뮬레이션 시나리오 생성이 아니라 기존 학습 SBEV의 이미지
#       합성/재조합이며, 전방 합류(LK) 클래스 슬롯으로 학습에 투입하기 위해
#       이 폴더명을 사용할 뿐이다 (파일명 Image_*_{CMO|Remix}_*.png 로 구분).
_IMG_BASE = _IMG_LOCAL if os.path.isdir(os.path.join(_IMG_LOCAL, 'LK_CIR_MER_RAB_FOT')) else _IMG_NAS
Z_PRIME_SRC_DIRS = [
    os.path.join(_IMG_BASE, 'LK_CIR_MER_RAB_FOT'),
]

# ━━ Paths ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
K = 500

OUTPUT_ROOT = os.path.join(os.path.join(MODULE_ROOT, 'Output', 'Remix'), RUN_NAME)
K_DIR = os.path.join(OUTPUT_ROOT, f"K_{K}")
INPUT_PATH = resolve_emb_path("Remix", "Remix_4500", MODULE_ROOT, _EMB_ARGS)
OUTPUT_PATH = os.path.join(K_DIR, "subsets.mat")
SUBSETS_DIR = os.path.join(K_DIR, "subsets_dirs")


def organize_subset_dirs(cluster_labels, filenames, src_dirs, dst_root):
    """클러스터별 물리적 디렉토리 생성 및 DSM 이미지 복사."""
    print(f"\n[추가] 서브셋 디렉토리 생성: {dst_root}")

    if os.path.exists(dst_root):
        shutil.rmtree(dst_root)

    unique_labels = np.unique(cluster_labels)
    total_copied = 0
    empty_clusters = 0

    for cid in unique_labels:
        indices = np.where(cluster_labels == cid)[0]
        subset_dir = os.path.join(dst_root, f"subset_{cid+1:03d}")
        os.makedirs(subset_dir, exist_ok=True)

        copied = 0
        for idx in indices:
            fname = filenames[idx]
            for sd in src_dirs:
                src = os.path.join(sd, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(subset_dir, fname))
                    copied += 1
                    break

        total_copied += copied
        if copied == 0:
            empty_clusters += 1

    print(f"  디렉토리: {len(unique_labels)}개 생성")
    print(f"  이미지 복사: {total_copied:,d}장")
    if empty_clusters > 0:
        print(f"  빈 클러스터: {empty_clusters}개 (원본 이미지 없음)")


def main():
    os.makedirs(K_DIR, exist_ok=True)
    print(f"=== Step 3: k-means ===")
    print(f"  RUN_NAME: {RUN_NAME}")
    print(f"  Output:   {K_DIR}\n")

    print("[1/3] 로드...")
    data = loadmat(INPUT_PATH)
    Z_prime_pca = data["Z_prime_pca"]
    d = int(data["d"].item())
    Z_prime_fnames = [
        str(s[0]) if isinstance(s, np.ndarray) else str(s).strip()
        for s in data["Z_prime_filenames"].flatten()
    ]
    print(f"  Z': {Z_prime_pca.shape}, d={d}")

    print(f"\n[2/3] k-means (k={K})...")
    kmeans = KMeans(n_clusters=K, random_state=42, n_init=10)
    labels = kmeans.fit_predict(Z_prime_pca)
    centroids = kmeans.cluster_centers_

    unique, counts = np.unique(labels, return_counts=True)
    print(f"  {K} subsets 생성")
    print(f"  subset 크기: min={counts.min()}, max={counts.max()}, "
          f"mean={counts.mean():.1f}, median={np.median(counts):.0f}")

    print(f"\n[3/3] 저장: {OUTPUT_PATH}")
    savemat(OUTPUT_PATH, {
        "cluster_labels": labels,
        "centroids": centroids,
        "subset_sizes": counts,
        "k": K,
        "Z_prime_filenames": data["Z_prime_filenames"],
    })

    if ORGANIZE_DIRS:
        organize_subset_dirs(labels, Z_prime_fnames, Z_PRIME_SRC_DIRS, SUBSETS_DIR)

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
