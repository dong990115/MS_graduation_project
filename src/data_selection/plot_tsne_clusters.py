"""
Z + Z' t-SNE 시각화
- Z (47,470): 도로유형별 색상
- Z' (4,500): k-means 클러스터별 색상
2,000차원 → t-SNE 2D
"""
import numpy as np
from scipy.io import loadmat
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import csv
import os

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MONOREPO_ROOT = os.path.dirname(_SCRIPT_DIR)

# ━━ Config ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CASE = "PCG"  # PCG | realroad | CMO | Remix
RUN_NAME = "noLane_060126_sub4500"
K_DIR = "K_500"
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, 'Output', CASE, RUN_NAME)

_PCA_LOCAL = os.path.join(OUTPUT_DIR, 'embeddings_pca_B.mat')
PCA_PATH = _PCA_LOCAL if os.path.isfile(_PCA_LOCAL) else os.path.join(r'<DATA_NAS>\EIG', CASE, RUN_NAME, 'embeddings_pca_B.mat')  # 로컬 우선 → NAS 정본
SUBSETS_PATH = os.path.join(OUTPUT_DIR, K_DIR, "subsets.mat")
LABEL_CSV = os.path.join(_SCRIPT_DIR, 'Output', 'common', 'training_road_type_label.csv')
SAVE_PATH = os.path.join(OUTPUT_DIR, f"tsne_Z_Zprime_{K_DIR}.png")

TSNE_PERPLEXITY = 30
TSNE_SEED = 42
# ━━ Load ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("[1/3] 데이터 로드...")
pca_data = loadmat(PCA_PATH)
Zp_pca = pca_data["Z_prime_pca"]

sub_data = loadmat(SUBSETS_PATH)
cluster_labels = sub_data["cluster_labels"].flatten()

n_clusters = len(set(cluster_labels.tolist()))
print(f"  Z': {Zp_pca.shape}, clusters: {n_clusters}")

# ━━ t-SNE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print(f"[2/3] t-SNE 실행 ({len(Zp_pca)}개 포인트)...")
tsne = TSNE(n_components=2, perplexity=TSNE_PERPLEXITY, random_state=TSNE_SEED, n_iter=1000)
zp_2d = tsne.fit_transform(Zp_pca)

# ━━ Plot ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("[3/3] 플롯 생성...")
fig, ax = plt.subplots(figsize=(12, 10))

cmap = cm.get_cmap("tab20", min(n_clusters, 20))
scatter = ax.scatter(zp_2d[:, 0], zp_2d[:, 1], c=cluster_labels, cmap=cmap, s=8, alpha=0.6)
ax.set_title(f"Z' k-means clusters (N={len(Zp_pca)}, K={n_clusters}, PCA d=2000 → t-SNE 2D)", fontsize=14)
ax.set_xticks([])
ax.set_yticks([])

plt.tight_layout()
plt.savefig(SAVE_PATH, dpi=150, bbox_inches="tight")
print(f"\n  저장: {SAVE_PATH}")
plt.show()
