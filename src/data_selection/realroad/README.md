# realroad — 실도로 FOT 계열 (논문 Case 8)

> **이 폴더의 스크립트는 실행되지 않는다.** 입력이 모두 비공개 대상이라 저장소에 없다.
> **산출물도 포함하지 않았다** — 실도로 FOT 계열은 실차 취득 데이터에서 유래하므로 전량 제외했다.
> 사유: [`data/README.md`](../../../data/README.md) · 실행 가능 범위: [`src/README.md`](../../README.md)

실도로 FOT 기반 학습 데이터에 대한 EIG 선별 파이프라인. 스크립트 상단 설정은 논문값으로 고정되어 있다.

## 파이프라인

```powershell
# Case 8 — EIG 선별 (203장 = LK 203 + DA 0)
python realroad/extract_and_pca.py            # ① 임베딩 + PCA (d=2,000)
python realroad/run_kmeans.py                 # ② k-means K=500
python -u realroad/run_algorithm2_perclass.py # ③ per-class EIG 선별 (GPU 권장)
```

Case 4(실도로 전량 4,500 학습)는 선별을 거치지 않으므로 이 폴더와 무관하다 —
DSM 세트가 커리큘럼 학습에 직접 입력된다.

## 입력 (전부 비공개 — 저장소에 없음)

| 입력 | 소재 | 비고 |
|------|------|------|
| 이미지 세트 (Z′) — LK·DA 2폴더 | `<DATA_NAS>` | 실도로 DSM 4,500장 서브샘플 |
| PCA 임베딩 `embeddings_pca_B.mat` | `<DATA_NAS>` | ① 출력 = ②③ 입력 |
| 학습 SBEV 47,470장 (①의 Z) | `<PROJECT_NAS>` | proprietary |
| 라벨 CSV `training_road_type_label.csv` | 제외 | 실차 FOT 프레임 라벨 |
| CP-CNN 가중치 `cp_cnn_iter4.onnx` | 제외 | 실차 학습 모델 |

## 출력

원래 `Output/realroad/realFOT_noLane_061826_sub4500/` 아래에 ① `embeddings_pca_B.mat`
→ ② `K_500/subsets.mat` → ③ `K_500/selected_scenarios.csv`·`algorithm2_result.mat`·`selected_v13/`(선별 203장)이 생성된다.
**모두 저장소에 포함하지 않았다.**

실도로 계열의 학습 성능(Case 4·8)은 [`results/acl_training/`](../../../results/acl_training/)의
`ACLpp_realFOT_4500_260618/`·`ACLpp_realFOT_K500_260618/`에서 확인할 수 있다.

---

상세 워크플로우·논문 매핑: [`docs/modules/06_eig.md`](../../../docs/modules/06_eig.md)
