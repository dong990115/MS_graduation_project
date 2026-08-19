# src — 본인 작성 코드

> ## 먼저 읽을 것 — 이 코드는 대부분 그대로 실행되지 않는다
>
> **입력 데이터가 전부 비공개 대상이기 때문이다.**
> 실도로 FOT 로그, CarMaker 시뮬레이션 출력, DSM 이미지, 학습 가중치는 모두
> 산학과제 자원이라 저장소에 포함하지 않았다 ([`../data/README.md`](../data/README.md)).
>
> 따라서 이 저장소를 내려받아 **코드를 실행해 결과를 재현하는 것은 불가능**하다.
> **결과는 [`../results/`](../results/)에 있는 산출물로 확인해야 한다.**
>
> 코드를 공개하는 목적은 실행이 아니라 **방법과 구현을 읽을 수 있게 하는 것**이다.
> 논문의 알고리즘이 실제로 어떻게 구현되었는지, 어떤 설계 판단이 있었는지는 코드에서 확인할 수 있다.

---

## 1. 실행 가능 여부 — 스크립트별

예외가 하나 있다. **도로 생성은 외부 입력이 전혀 필요 없어 완전히 실행된다.**

| 스크립트 | 실행 | 필요한 입력 | 상태 |
|---|:---:|---|---|
| `road_generation/run_modeE_roundabout.py` | **○** | 없음 (파라미터만) | **바로 실행 가능** |
| `road_generation/run_modeE_stages.py` | **○** | 없음 | **바로 실행 가능** |
| `road_generation/run_modeE_eval.py` | **○** | 위 스크립트가 생성한 `.xodr` | 위 실행 후 가능 |
| `data_selection/analysis/scripts/run_analysis1_figs.py` | **○** | `shape_stats.csv`, `shape_pool.npz` | **포함됨** → 논문 Figure 2-5 재생성 |
| `data_selection/analysis/scripts/run_analysis2_frame_figs.py` | ✕ | `frame_metrics.csv` (포함) + `fp_frame_metrics.csv` (**제외**) | 입력 1개 부족 |
| `data_selection/analysis/scripts/*_batch.py` | ✕ | 원 도로망 `.xodr`, DSM 이미지 | 제외 |
| `data_selection/{PCG,CMO,Remix,realroad}/extract_and_pca.py` | ✕ | DSM 이미지 세트, CP-CNN 가중치 | 제외 |
| `data_selection/{PCG,CMO,Remix,realroad}/run_kmeans.py` | ✕ | `embeddings_pca_B.mat` (① 출력) | 제외 |
| `data_selection/{PCG,CMO,Remix,realroad}/run_algorithm2_perclass.py` | ✕ | ①② 출력 | 제외 |
| `data_selection/label_road_type.py` | ✕ | 학습 SBEV 47,470장 | 제외 (proprietary) |
| `data_selection/plot_tsne_clusters.py` | ✕ | 임베딩 | 제외 |
| `param_space/hellinger_compare.py` | ✕ | 프레임 로그 CSV, 파라미터 표 | 제외 |
| `param_space/hellinger_compare_overlay.py` | ✕ | 〃 | 제외 |
| `param_space/sampling/*.m` | ✕ | 프레임 로그 CSV | 제외 |

**요약**: 15종 중 **4종이 실행 가능**하고, 나머지는 입력 데이터가 없어 코드 읽기 전용이다.

---

## 2. 경로 규약

코드에 남아 있는 경로는 **입력이 무엇이었는지를 기록하는 명세**로 읽어야 한다.

| 표기 | 의미 |
|---|---|
| `<DATA_NAS>` | 연구실 NAS 데이터 루트. 실제 경로는 공개하지 않음 |
| `<PROJECT_NAS>` | 산학과제 NAS 영역 |
| `<SCENARIO_NAS>`, `<FOT_NAS>`, `<NAS_HOST>` | 각각 시나리오 카탈로그 / FOT 원본 / NAS 호스트 |
| `05_MapBuilder/Output/DSM/…` 등 | **재구성 이전 모듈 경로.** 해당 단계와 데이터가 모두 제외되어 지금은 존재하지 않는다 |

연구실 환경에서 실행하려면 위 플레이스홀더를 실제 경로로 되돌리고,
제외된 상류 산출물을 확보해야 한다.

---

## 3. 디렉토리

### `road_generation/` — 회전교차로 절차적 생성

| 파일 | 작성 | 역할 |
|---|---|---|
| `run_modeE_roundabout.py` | **본인** | 회전교차로 1개 생성 (진입점) |
| `run_modeE_stages.py` | **본인** | 생성 단계별 시각화 — 논문 Figure 2-4 |
| `run_modeE_eval.py` | **본인** | ERA(Expressive Range Analysis) 평가 |
| `analysis/metrics/roundabout/` | **본인** | 형상 다양성·현실성 지표 |
| `junctionart/` | **외부** | JunctionArt (MPL-2.0) — [`THIRD_PARTY_NOTICE.md`](road_generation/THIRD_PARTY_NOTICE.md) |

### `param_space/` — 거동 파라미터 분포 추정·샘플링

관측 경험분포에서 행 단위 복원추출로 시나리오 파라미터 1,000행을 만든다 (`rng(42)`).
GMM은 샘플링이 아니라 다봉 구조 확인용이다.

### `data_selection/` — EIG 기반 데이터 선별 ★ 핵심 기여

CP-CNN 임베딩 → PCA(d=2,000) → k-means(K=500) → per-class EIG로 학습 데이터를 선별한다.
4개 케이스(PCG · realroad · CMO · Remix)가 동일 파이프라인 사본으로 배치되어 있다.

EIG 산출식은 참고 논문에서 가져왔고 **구현은 전부 직접 작성**했다.
원 논문은 공개 구현체를 제공하지 않는다.

> Dai, Ma et al., *"Trade-Offs Between Richness and Bias of Augmented Data in Long-Tailed Recognition"*, Entropy 27(2):201, 2025

`junctionart/`(코드를 그대로 가져옴, MPL-2.0 의무)와 달리 **수식만 참조**한 것이므로
라이선스 의무가 아니라 학술적 인용의 문제다.

---

## 4. 결과는 어디서 보는가

| 확인할 것 | 위치 |
|---|---|
| 오경보 원인 분류 (논문 Table 1-1 · 3-6, Figure 3-5) | [`../results/fp_classification/`](../results/fp_classification/) |
| 10케이스 학습 성능 (논문 4장) | [`../results/acl_training/`](../results/acl_training/) |
| EIG 선별 139장 · 수렴 이력 (Figure 3-2) | [`../results/eig_selection/PCG/`](../results/eig_selection/PCG/) |
| 도로 형상 다양성 (Figure 2-5) | [`../results/eig_selection/analysis1/`](../results/eig_selection/analysis1/) |
| ΔmTTCP 분포 (Figure 3-3) | [`../results/eig_selection/analysis2/`](../results/eig_selection/analysis2/) |
| 파라미터 분포 재현도 (Figure 2-7) | [`../results/param_space/figures/`](../results/param_space/figures/) |

방법 설명과 데이터 스키마는 [`../docs/`](../docs/)에 단계별로 정리되어 있다.
