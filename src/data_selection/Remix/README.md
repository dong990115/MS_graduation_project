# Remix — Remix 증강 계열 (논문 Case 3·7)

> **이 폴더의 스크립트는 실행되지 않는다.** 입력(학습 SBEV, 증강 이미지 세트, PCA 임베딩, CP-CNN 가중치)이
> 모두 비공개 대상이라 저장소에 없다. **산출물도 포함하지 않았다** — Remix 계열은 논문 비교군이라
> 선별 결과를 저장소에 두지 않았다(포함된 것은 PCG 계열뿐).
> 사유: [`data/README.md`](../../../data/README.md) · 실행 가능 범위: [`src/README.md`](../../README.md)

증강 후보군 Remix에 대한 EIG 선별 파이프라인. 스크립트 상단 설정은 논문값으로 고정되어 있다.

## 파이프라인

```powershell
# Case 3 — Remix 전량 4,500 (선별 없음): ⓪까지만 실행
python Remix/remix_augment.py              # ⓪ 증강 생성 (tail RAB · 4,500장 · seed 42)

# Case 7 — Remix EIG 선별 (164장): ⓪ 이후 ①②③
python Remix/extract_and_pca.py            # ① 임베딩 + PCA (d=2,000)
python Remix/run_kmeans.py                 # ② k-means K=500
python -u Remix/run_algorithm2_perclass.py # ③ per-class EIG 선별 (GPU 권장)
```

> ⚠️ **폴더명 안내**: 출력의 하위 폴더명 `LK_CIR_MER_RAB_FOT`는 커리큘럼 학습 로더의
> **클래스 폴더 규약명**일 뿐이다. CMO/Remix는 시뮬레이션으로 시나리오를 생성한 것이 아니라
> 기존 학습 SBEV를 이미지 합성·재조합한 것이며(파일명 `Image_*_Remix_*.png`로 구분),
> 전방 합류(LK) 클래스 슬롯으로 학습에 투입하기 위해 이 폴더명을 쓴다.

## 입력 (전부 비공개 — 저장소에 없음)

| 입력 | 소재 | 비고 |
|------|------|------|
| 학습 SBEV 47,470장 | `<PROJECT_NAS>` | ⓪의 재조합 원천이자 ①의 Z. proprietary |
| 증강 이미지 세트 (Z′) — LK 단일 | `<DATA_NAS>` | ⓪ 산출 4,500장 |
| PCA 임베딩 `embeddings_pca_B.mat` | `<DATA_NAS>` | ① 출력 = ②③ 입력 |
| 라벨 CSV `training_road_type_label.csv` | 제외 | 실차 FOT 프레임 라벨 |
| CP-CNN 가중치 `cp_cnn_iter4.onnx` | 제외 | 실차 학습 모델 |

## 출력

원래 `Output/Remix/Remix_4500/` 아래에 ① `embeddings_pca_B.mat` → ② `K_500/subsets.mat`
→ ③ `K_500/selected_scenarios.csv`·`algorithm2_result.mat`·`selected_v13/`(선별 164장)이 생성된다.
**모두 저장소에 포함하지 않았다.**

Remix 계열의 학습 성능(Case 3·7)은 [`results/acl_training/`](../../../results/acl_training/)의
`ACLpp_Remix_4500_260609/`·`ACLpp_Remix_EIG_K500_260609/`에서 확인할 수 있다.

---

상세 워크플로우·논문 매핑: [`docs/modules/06_eig.md`](../../../docs/modules/06_eig.md)
