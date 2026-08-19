# 학위논문

## 서지

| 항목 | 내용 |
|------|------|
| 제목 | 회전교차로 충돌 예측의 성능 개선을 위한 절차적 도로 생성 및 데이터 선별 연구 |
| 학위 | 공학석사 |
| 소속 | 아주대학교 — Vehicle Intelligence and Control Lab |
| 출판본 | [`../[학위논문]회전교차로 충돌 예측의 성능 개선을 위한 절차적 도로 생성 및 데이터 선별 연구.pdf`](../) (저장소 루트, 2.0 MB) |
| 공개 링크 | *학위수여 후 학술정보원 링크 기재 예정* |

> **링크 갱신 필요**: 학위논문이 교내 학술정보원에 공개되면 위 "공개 링크" 행에 URL을 넣을 것.
> 그때 저장소 루트의 PDF는 제거하고 링크로 대체해도 된다.

---

## 논문 ↔ 저장소 대응

논문에 실린 표·그림이 저장소의 어느 산출물에서 나왔는지의 대응표다.

### 2장 — 문제 정의와 시나리오 생성

| 논문 | 내용 | 저장소 |
|---|---|---|
| Table 1-1 | ACL 반복별 오경보 118 / 16 / 6 / 10 | [`results/fp_classification/Baseline/iter{1..4}/summary_*.csv`](../results/fp_classification/Baseline/) |
| Figure 2-2, Table 2-4 | 오경보 원인 분류 체계 | — (방법: [`modules/01_classification_of_fp.md`](modules/01_classification_of_fp.md)) |
| Figure 2-4 | 회전교차로 생성 단계 시각화 | [`src/road_generation/run_modeE_stages.py`](../src/road_generation/run_modeE_stages.py) 로 재생성 |
| **Figure 2-5** | 도로 형상 다양성·현실성 (ERA) | [`results/eig_selection/analysis1/`](../results/eig_selection/analysis1/) — `Fig1a`·`Fig1b`·`Fig1c` + `Table1_shape_diversity.csv` |
| Figure 2-6 | 생성 도로 현실성 평가 | [`src/road_generation/run_modeE_eval.py`](../src/road_generation/run_modeE_eval.py) 로 재생성 |
| **Figure 2-7** | 파라미터 분포 재현도 (Hellinger) | [`results/param_space/figures/`](../results/param_space/figures/) — HD 0.3585 / 0.3327 / 0.1419 |
| 2.5절 | concrete 시나리오 2,000개 생성 | 방법: [`modules/04_carmaker_sim.md`](modules/04_carmaker_sim.md) |

### 3장 — 데이터 선별

| 논문 | 내용 | 저장소 |
|---|---|---|
| Figure 3-1 | 임베딩 → PCA → k-means 분류 | [`results/eig_selection/PCG/…/K_500/subsets.mat`](../results/eig_selection/PCG/) |
| **Figure 3-2** | EIG 수렴 이력 | [`results/eig_selection/PCG/…/K_500/algorithm2_result.mat`](../results/eig_selection/PCG/) |
| **Figure 3-3** | ΔmTTCP 분포 · FP 대역 농축 (2.6% → 13.2%) | [`results/eig_selection/analysis2/`](../results/eig_selection/analysis2/) |
| Algorithm 1 | per-class EIG 선별 | 구현: [`src/data_selection/*/run_algorithm2_perclass.py`](../src/data_selection/) |
| 식 3.1~3.6 | V(X) 로그-행렬식, EIG 정의 | 〃 |
| **Figure 3-5** | 조건별 도로유형 잔존 오경보 | [`results/fp_classification/comparison/compare_road_geometry.png`](../results/fp_classification/comparison/) |
| **Table 3-6** | 조건별 원인 분해 | [`results/fp_classification/*/summary_*.csv`](../results/fp_classification/) |

### 4장 — 실험 결과

10케이스 성능 비교. 각 케이스의 FN/FP는 [`results/acl_training/`](../results/acl_training/)의
`Test_Result-ScenarioBasedCollisionDetection-*.mat`에서 추출한 값이다.

| C# | 조건 | Acc% | FNR%(FN) | FPR%(FP) |
|----|------|------|----------|----------|
| C1 | 베이스라인 | 97.0 | 1.66(43) | 3.65(204) |
| C2 | CMO 전량 4,500 | 97.3 | 2.62(68) | 2.69(150) |
| C3 | Remix 전량 4,500 | 97.3 | 1.70(44) | 3.23(181) |
| C4 | 실도로 전량 4,500 | 97.1 | 2.19(57) | 3.30(184) |
| C5 | PCG 전량 4,500 | 93.9 | 1.86(48) | 8.12(455) |
| C6 | CMO EIG 227 | 96.1 | 1.97(51) | 4.74(265) |
| C7 | Remix EIG 164 | 97.4 | 2.08(54) | 2.90(162) |
| C8 | 실도로 EIG 203 | 96.9 | 2.05(53) | 3.61(202) |
| C9 | PCG 무작위 139 | 95.8 | 1.82(47) | 5.25(296) |
| **C10** | **PCG EIG 139 (제안)** | **97.6** | 2.62(68) | **2.31(129)** |

**최종 검증**: C10 재학습 후 오경보 **10건 → 3건**, 회전교차로 **3건 → 0건**
([`results/fp_classification/PCGFOT_EIG/`](../results/fp_classification/PCGFOT_EIG/)).

---

## 인용

이 저장소나 결과를 인용할 경우 학위논문을 인용해 주기 바란다.
공개 링크가 확정되면 BibTeX 항목을 이 절에 추가할 것.

## 참고 문헌

이 연구가 직접 참조한 외부 성과다.

| 문헌 | 참조 범위 |
|---|---|
| Dai, Ma et al., *"Trade-Offs Between Richness and Bias of Augmented Data in Long-Tailed Recognition"*, Entropy 27(2):201, 2025 | **EIG 산출식(식 3.1~3.6)**. 구현 코드는 직접 작성 — 원 논문은 공개 구현체 없음 |
| A. Sadat et al., *"Diverse complexity measures for dataset curation in self-driving"*, IROS 2021 | 시나리오 복잡도 지표 정의 |
| [JunctionArt](https://github.com/Adhocmaster/junction-art) (MPL-2.0) | **도로망 생성 엔진 — 코드 사용**. [`src/road_generation/THIRD_PARTY_NOTICE.md`](../src/road_generation/THIRD_PARTY_NOTICE.md) |
