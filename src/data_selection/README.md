# EIG 기반 증강 데이터 선별

> ### 이 파이프라인(①②③)은 실행되지 않는다 — 입력이 전부 비공개 대상이다
>
> | 입력 | 소재 | 사유 |
> |------|------|------|
> | DSM 이미지 세트 (Z′) | `<DATA_NAS>` | 과제 시뮬레이션 데이터 렌더링 결과 |
> | PCA 임베딩 `embeddings_pca_B.mat` | `<DATA_NAS>` | ① 출력, 케이스당 약 400 MB |
> | 학습 SBEV 47,470장 (①의 Z) | `<PROJECT_NAS>` | proprietary |
> | 라벨 CSV `training_road_type_label.csv` | 제외 | 실차 FOT 프레임별 라벨 |
> | CP-CNN 가중치 `cp_cnn_iter4.onnx` | 제외 | 실차 학습 모델 (내보내기 스크립트는 포함) |
>
> **결과는 [`results/eig_selection/`](../../results/eig_selection/)에서 확인한다** —
> PCG 계열(논문 제안 기법)의 선별 139장 목록과 EIG 수렴 이력이 들어 있다.
> 비교군(CMO·Remix)과 실도로 계열의 선별 결과는 포함하지 않았다.
>
> 아래 실행 명령은 **연구실 환경에서의 절차를 기록한 것**이며, 공개 저장소에서는 동작하지 않는다.
> 실행 가능 범위: [`src/README.md`](../README.md) · 데이터 사유: [`data/README.md`](../../data/README.md)
> 상세: **[docs/modules/06_eig.md](../../docs/modules/06_eig.md)**

> 참고 논문: Dai, Ma et al., "Trade-Offs Between Richness and Bias of Augmented Data in Long-Tailed Recognition", Entropy 27(2):201, 2025

05가 만든 DSM에서 CP-CNN embedding을 추출(PCA)하고, k-means(K=500) subset 위에서
Greedy Algorithm 2로 per-class EIG target(5.5)에 도달할 때까지 subset을 추가 선별한다.
논문 EIG **4케이스가 케이스 폴더로 대칭 배치**돼 있다 (2026-07-26 재편):

| 케이스 | 폴더 | RUN_NAME | 선별 장수 | 결과 저장소 포함 |
|--------|------|----------|----------|:---:|
| **PCG** (제안 기법) | `PCG/` | `noLane_060126_sub4500` | 139 (+ 비교군 random 139) | **✅ [`results/eig_selection/PCG/`](../../results/eig_selection/PCG/)** |
| 실도로 (realFOT) | `realroad/` | `realFOT_noLane_061826_sub4500` | 203 | ✕ 실차 데이터 유래 |
| CMO 증강 | `CMO/` | `CMO_4500` | 227 | ✕ 비교군 |
| Remix 증강 | `Remix/` | `Remix_4500` | 164 | ✕ 비교군 |

네 케이스 모두의 **학습 성능 결과**는 [`results/acl_training/`](../../results/acl_training/)에 있다.

---

## 파이프라인 (케이스 공통)

```
[Phase 0]  label_road_type.py (공용) — 도로 유형 라벨링
  Input:  NAS SBEV 47,470장 (proprietary), RG3 CSV
  Output: Output/common/training_road_type_label.csv   ← pre-computed 포함 (재실행 불필요)
       │
       ▼
[①] {case}/extract_and_pca.py — CP-CNN Embedding + PCA
  Input:  weight/cp_cnn_iter4.onnx, Phase 0 CSV,
          DSM (05 Output/DSM → 없으면 NAS augmented_dataset 폴백),
          학습 SBEV 47,470장 (proprietary NAS Curricula — ①이 Z 임베딩 직접 추출)
  Output: Output/{case}/{RUN_NAME}/embeddings_pca_B.mat  (①의 유일한 출력)
       │
       ▼
[②] {case}/run_kmeans.py — k-means subset 분할 (K=500)
  Output: Output/{case}/{RUN_NAME}/K_500/subsets.mat        ← pre-computed 포함
       │
       ▼
[③] {case}/run_algorithm2_perclass.py — Greedy per-class EIG 선별
  Output: …/K_500{_EIG5_5}/selected_scenarios.csv           ← pre-computed 포함
          …/algorithm2_result.mat                           ← pre-computed 포함

[비교군]  PCG/run_random_select.py (N=139, seed 42)          ← pre-computed 포함
[시각화]  plot_tsne_clusters.py (상단 CASE 변수로 케이스 지정)
```

모든 스크립트는 자기 위치 앵커 기반이라 어느 디렉토리에서 실행해도 동작한다.
**목적에 따라 실행 명령이 다르다** — 아래 A/B 중 하나를 고를 것.

### A. 논문 수치 재현 (권장 — `--nas`)

①을 건너뛰고 **NAS 정본 임베딩**을 강제로 사용한다. ①을 재실행하면 PCA randomized SVD
때문에 다른 임베딩이 나와 선별 결과가 논문과 달라지므로(아래 '주의' 참조), 재현이
목적이면 반드시 이 경로로 실행한다.

```powershell
cd <repo>/test_layer/scripts/PCG_dataSelection/06_EIG

python PCG/run_kmeans.py --nas                # ① 실행하지 않음
python -u PCG/run_algorithm2_perclass.py --nas
python PCG/run_random_select.py --nas         # 비교군(N=139, seed 42)
```

기대 결과 (검증 완료, 2026-08-11):

| 케이스 | 선별 장수 | 최종 EIG | 선택 클러스터 |
|--------|----------|----------|---------------|
| PCG    | **139** / 4,500 | 5.500004 | `[163, 492, 124, 45, 314, 432, 491, 482, 218]` |

로컬에 ① 재실행본이 남아 있어도 `--nas` 가 우선하므로 파일을 지울 필요는 없다.

### B. 코드 동작 확인 (로컬 임베딩 사용)

파이프라인을 처음부터 돌려보는 경우. **결과 수치는 논문과 달라진다**(재현 목적 아님).

```powershell
cd <repo>/test_layer/scripts/PCG_dataSelection/06_EIG

python PCG/extract_and_pca.py                 # 로컬에 embeddings_pca_B.mat 생성
python PCG/run_kmeans.py                      # 로컬 우선 → 방금 만든 것 사용
python -u PCG/run_algorithm2_perclass.py
```

인자를 주지 않으면 **로컬 우선 → 없으면 NAS 폴백**이며, 실행 시작 시
`[emb] path` / `[emb] source` 로 실제 사용한 임베딩과 그 출처를 출력한다.
임의 파일을 쓰려면 `--emb <경로>` 를 준다.

다른 케이스(`CMO/`, `Remix/`, `realroad/`)도 동일한 인자를 지원한다.

---

## 데이터 배치

| 위치 | 내용 | 공개 |
|------|------|:---:|
| [`results/eig_selection/PCG/`](../../results/eig_selection/PCG/) | PCG 계열 선별 정본 (subsets / selected_scenarios / algorithm2_result / random) | **✅** |
| [`results/eig_selection/analysis1,2/`](../../results/eig_selection/) | 논문 Figure 2-5 · 3-3 소재 | **✅** |
| `<DATA_NAS>\EIG\` | 케이스별 임베딩 정본 (pca 397 MB · raw 688 MB) | ✕ |
| `<DATA_NAS>\MapBuilder\augmented_dataset\` | 4케이스 선별·증강 이미지 세트 9종 | ✕ |

## 주의

- Phase 0은 proprietary NAS 필요. 산출 CSV도 실차 프레임 라벨이라 제외했다.
- **①은 재실행해도 논문과 같은 임베딩이 나오지 않는다** (아래 상자 참조 — 정본은 NAS 사용).

> **①(extract_and_pca) 재실행 시 논문 임베딩은 재현되지 않는다.**
> 임베딩은 `relu_Layer_3` 출력 40,000차원이고 `n_components=2000` 이라,
> sklearn 의 `svd_solver='auto'` 가 **randomized SVD** 를 고른다
> (규칙: 데이터 500×500 초과 + n_components < 0.8·min(n,d) → randomized).
> 이 solver 는 `random_state` 에 의존하는데 **정본 산출 당시 코드에는 지정이 없었다**.
> 그래서 같은 입력·같은 코드로 다시 돌려도 **매번 다른 PCA 축**이 나오고,
> 그 결과 k-means 클러스터와 EIG 선별 결과까지 달라진다
> (실측: 정본 139장 → 재실행 158장, k-means 라벨 일치율 0.09%).
>
> 현재 코드에는 `random_state=42` 를 지정해 **앞으로의 실행은 재현**되지만,
> 정본과 동일한 값이 나오지는 **않는다**. 논문 수치를 재현하려면
> ①을 건너뛰고 **NAS 정본 임베딩을 사용**해야 한다:
> `<DATA_NAS>\EIG\<케이스>\<RUN_NAME>\embeddings_pca_B.mat`
> (②`run_kmeans.py` 는 로컬 `Output/.../embeddings_pca_B.mat` 이 있으면 그것을 먼저 쓰므로,
> 로컬에 다른 판이 있으면 지우거나 NAS 정본으로 덮어쓸 것)

- ③은 GPU 권장 (iteration당 ~3분, CPU ~10분+). 없으면 스크립트 상단 `FORCE_CPU=True`.
- `analysis/`는 논문 그림 재현 코드 — analysis1 = Figure 2-5(a·b·c, 형상 다양성·현실성), analysis2 = Figure 3-3(a·b, ΔmTTCP 분포·FP 대역 농축 2.6%→13.2%). Utils(지표 라이브러리)와 scripts/validation(구현 검증 7종)이 뒷받침한다.
