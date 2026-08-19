"""
Step 1+2 (B 정의): Embedding 추출 + PCA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Z = 전체 학습 데이터 47,470장 (per-class가 아닌 전체 manifold 기준)
Z' = 후보 DSM (이미지에서 직접 추출)

1) Z 47,470장 embedding: NAS 학습 SBEV(Curricula)에서 추출
2) Z' embedding: 후보 DSM 디렉토리에서 추출
3) PCA fit on Z → d 결정 (explained variance ≥ 95%)
4) Transform Z, Z' → embeddings_pca.mat
"""

import os
import sys
import csv
import glob
import numpy as np
import onnx
import onnxruntime as ort
from onnx import helper
from PIL import Image
from scipy.io import loadmat, savemat
from sklearn.decomposition import IncrementalPCA, PCA
import time

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(_SCRIPT_DIR)
MONOREPO_ROOT = os.path.dirname(MODULE_ROOT)

# ━━ Experiment Config ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUN_NAME = "realFOT_noLane_061826_sub4500"


# 이미지 세트: 로컬(레포/⓪ 산출) 우선 → 없으면 NAS 정본
_IMG_LOCAL = os.path.join(MONOREPO_ROOT, '05_MapBuilder', 'Output', 'DSM', 'realRAB_v13_Train_061826_noLane_sub4500')
_IMG_NAS = r'<DATA_NAS>\MapBuilder\augmented_dataset\realroad_4500'
_IMG_BASE = _IMG_LOCAL if os.path.isdir(os.path.join(_IMG_LOCAL, 'LK_CIR_MER_RAB_realFOT')) else _IMG_NAS
Z_PRIME_SRC_DIRS = [
    os.path.join(_IMG_BASE, 'LK_CIR_MER_RAB_realFOT'),
    os.path.join(_IMG_BASE, 'drivingAlone_RVL_RAB_realFOT'),
]


# ━━ Paths ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ONNX_PATH = os.path.join(MODULE_ROOT, "weight", "cp_cnn_iter4.onnx")
LABEL_CSV = os.path.join(MODULE_ROOT, 'Output', 'common', 'training_road_type_label.csv')
CURRICULA_DIR = (
    r"<PROJECT_NAS>\Collision Mode\Training\Result"
    r"\ACLpp_iter4_1_0s_051625_SIM3_spl10_wCB_mFtv2\Curricula"
)

OUTPUT_DIR = os.path.join(MODULE_ROOT, 'Output', 'realroad', RUN_NAME)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "embeddings_pca_B.mat")

EMBEDDING_LAYER = "relu_Layer_3"
BATCH_SIZE = 128
PCA_MAX_COMPONENTS = 2000
VARIANCE_THRESHOLD = 0.95



def create_embedding_session(onnx_path, layer_name):
    model = onnx.load(onnx_path)
    intermediate = helper.make_tensor_value_info(
        layer_name, onnx.TensorProto.FLOAT, None
    )
    model.graph.output.append(intermediate)
    return ort.InferenceSession(model.SerializeToString())


def load_image(path):
    img = Image.open(path).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    return arr.transpose(2, 0, 1)  # CHW


def get_training_paths(csv_path, curricula_dir):
    """Read label CSV → full paths for all 47,470 training SBEV."""
    paths = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            full = os.path.join(
                curricula_dir, row["level"], row["collision_mode_dir"], row["filename"]
            )
            paths.append(full)
    return paths


def extract_embeddings_batched(session, input_name, paths, batch_size):
    """Extract embeddings in batches, return full (N, 40000) array."""
    n = len(paths)
    emb_dim = None
    all_emb = []

    t0 = time.time()
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch = np.stack([load_image(p) for p in paths[start:end]])
        outputs = session.run([EMBEDDING_LAYER], {input_name: batch})
        emb = outputs[0].reshape(outputs[0].shape[0], -1)

        if emb_dim is None:
            emb_dim = emb.shape[1]
        all_emb.append(emb)

        elapsed = time.time() - t0
        if start == 0 or end == n or (start // batch_size) % 50 == 0:
            rate = end / elapsed if elapsed > 0 else 0
            eta = (n - end) / rate if rate > 0 else 0
            print(f"  {end:,d}/{n:,d}  ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

    return np.concatenate(all_emb, axis=0)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"=== Step 1+2 (B): Embedding + PCA ===")
    print(f"  RUN_NAME: {RUN_NAME}")
    print(f"  Output:   {OUTPUT_DIR}\n")

    # 1. Load model
    print("[1/5] ONNX 모델 로드...")
    session = create_embedding_session(ONNX_PATH, EMBEDDING_LAYER)
    input_name = session.get_inputs()[0].name
    print(f"  {os.path.basename(ONNX_PATH)}, input={input_name}\n")

    # 2. Z embeddings (학습 SBEV에서 직접 추출)
    print("[2/5] Z embedding 추출 (47,470장, NAS)...")
    z_paths = get_training_paths(LABEL_CSV, CURRICULA_DIR)
    print(f"  Z: {len(z_paths):,d}장")
    Z_raw = extract_embeddings_batched(session, input_name, z_paths, BATCH_SIZE)
    print(f"  Z_raw: {Z_raw.shape}  ({Z_raw.nbytes / 1e9:.1f} GB)\n")

    # 3. Z' embeddings (후보 DSM에서 직접 추출)
    print(f"[3/5] Z' embedding 직접 추출: {Z_PRIME_SRC_DIRS}")
    zp_paths = sorted([p for d in Z_PRIME_SRC_DIRS for p in glob.glob(os.path.join(d, "*.png"))])
    zp_fnames = [os.path.basename(p) for p in zp_paths]
    print(f"  Z': {len(zp_paths):,d}장")
    if len(zp_paths) == 0:
        print("  ERROR: 이미지가 없습니다.")
        return
    Z_prime_raw = extract_embeddings_batched(session, input_name, zp_paths, BATCH_SIZE)
    print(f"  Z'_raw: {Z_prime_raw.shape}\n")


    # 4. PCA
    print(f"[4/5] PCA (max {PCA_MAX_COMPONENTS} components)...")
    # [재현성] 임베딩 40,000차원 · n_components=2000 이면 sklearn 의 svd_solver='auto' 가
    #   randomized 를 고르며, random_state 미지정 시 실행마다 다른 축이 나온다.
    #   (논문 정본 임베딩은 이 인자가 없던 시절 산출물이라 아래 시드로도 재현되지 않는다 — README 참조)
    pca = PCA(n_components=min(PCA_MAX_COMPONENTS, Z_raw.shape[0] - 1),
              svd_solver="randomized", random_state=42)
    pca.fit(Z_raw)

    ev = pca.explained_variance_ratio_
    cum_ev = np.cumsum(ev)

    d_candidates = np.where(cum_ev >= VARIANCE_THRESHOLD)[0]
    d = int(d_candidates[0]) + 1 if len(d_candidates) > 0 else len(ev)

    print(f"\n  Explained variance:")
    milestones = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, d, len(ev)]
    for m in sorted(set(m for m in milestones if m <= len(ev))):
        marker = "  ← selected d" if m == d else ""
        print(f"    PC{m:4d}: cum {cum_ev[m-1]*100:6.2f}%{marker}")

    print(f"\n  d = {d} (cum variance = {cum_ev[d-1]*100:.2f}%)")

    # Transform
    Z_pca = pca.transform(Z_raw)[:, :d]
    Z_prime_pca = pca.transform(Z_prime_raw)[:, :d]
    print(f"  Z_pca: {Z_pca.shape}, Z_prime_pca: {Z_prime_pca.shape}")

    # 5. Save PCA result
    print(f"\n[5/5] PCA 결과 저장: {OUTPUT_PATH}")
    Z_prime_fnames_arr = np.array(zp_fnames, dtype=object)
    savemat(OUTPUT_PATH, {
        "Z_pca": Z_pca,
        "Z_prime_pca": Z_prime_pca,
        "explained_variance_ratio": ev,
        "cumulative_variance": cum_ev,
        "d": d,
        "Z_prime_filenames": Z_prime_fnames_arr,
    })

    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"  Z: {Z_pca.shape}, Z': {Z_prime_pca.shape}, d={d}, size={size_mb:.1f} MB")


    del Z_raw, Z_prime_raw
    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
