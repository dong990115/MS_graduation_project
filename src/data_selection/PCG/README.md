# PCG — PCG-FOT 계열 (논문 Case 9·10)

> **이 폴더의 스크립트는 실행되지 않는다.** 입력(DSM 이미지 세트, PCA 임베딩, 학습 SBEV, CP-CNN 가중치)이
> 모두 비공개 대상이라 저장소에 없다. 결과는 [`results/eig_selection/PCG/`](../../../results/eig_selection/PCG/)에서 확인한다.
> 자세한 사유: [`data/README.md`](../../../data/README.md) · 실행 가능 범위: [`src/README.md`](../../README.md)

논문 제안 기법(Case 10)의 EIG 선별 파이프라인. 스크립트 상단 설정은 논문값으로 고정되어 있다.

## 파이프라인

```powershell
# Case 10 — EIG 선별 (139장 = LK 130 + DA 9)
python PCG/extract_and_pca.py            # ① 임베딩 + PCA (d=2,000)
python PCG/run_kmeans.py                 # ② k-means K=500
python -u PCG/run_algorithm2_perclass.py # ③ per-class EIG 선별 (GPU 권장)

# Case 9 — 비교군 무작위 선별 (①의 PCA 임베딩 공유)
python PCG/run_random_select.py          # seed 42
```

Case 5(PCG 전량 4,500 학습)는 선별을 거치지 않으므로 이 폴더와 무관하다 —
DSM 세트가 커리큘럼 학습에 직접 입력된다.

## 입력 (전부 비공개 — 저장소에 없음)

| 입력 | 소재 | 비고 |
|------|------|------|
| 이미지 세트 (Z′) — LK·DA 2폴더 | `<DATA_NAS>` | DSM 4,500장 서브샘플 |
| PCA 임베딩 `embeddings_pca_B.mat` | `<DATA_NAS>` | ① 출력 = ②③ 입력, 케이스당 약 400 MB |
| 학습 SBEV 47,470장 (①의 Z) | `<PROJECT_NAS>` | proprietary |
| 라벨 CSV `training_road_type_label.csv` | 제외 | 실차 FOT 프레임 라벨 |
| CP-CNN 가중치 `cp_cnn_iter4.onnx` | 제외 | 실차 학습 모델 |

코드는 **로컬(앞 단계 산출) 우선 → 없으면 NAS 정본 참조**로 작성되어 있다.
공개 저장소에는 둘 다 없으므로 어느 경로로도 해결되지 않는다.

## 출력 (저장소 포함 ✅)

논문 정본 산출물은 [`results/eig_selection/PCG/noLane_060126_sub4500/`](../../../results/eig_selection/PCG/noLane_060126_sub4500/)에 있다.

| 파일 | 단계 | 내용 |
|------|:---:|------|
| `K_500/subsets.mat` | ② | k-means K=500 클러스터 할당 |
| `K_500/selected_scenarios.csv` | ③ | **EIG 선별 139장 목록** — 논문 Case 10의 D_aug |
| `K_500/algorithm2_result.mat` | ③ | EIG 수렴 이력 — **논문 Figure 3-2** |
| `random_select/selected_scenarios.csv` | — | 무작위 비교군 — 논문 Case 9 |
| `random_select/random_select_result.mat` | — | 〃 |

**검증 기록**: 139/4,500 선별, 최종 EIG 5.500004,
선택 클러스터 `[163, 492, 124, 45, 314, 432, 491, 482, 218]`.

미포함: `embeddings_pca_B.mat`(①), `selected_v13/`(③의 이미지 실물) — 둘 다 비공개 대상이다.

---

상세 워크플로우·논문 매핑: [`docs/modules/06_eig.md`](../../../docs/modules/06_eig.md)
