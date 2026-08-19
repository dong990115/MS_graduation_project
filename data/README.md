# 데이터 안내

**이 저장소에는 데이터가 포함되어 있지 않다.**

본 연구에 사용·생성된 데이터는 모두 산학과제 수행 과정에서 나온 자원이므로,
계약상 공개 대상이 아니라고 판단해 저장소에서 제외했다.
이 문서는 **어떤 데이터가 있었고, 각각 어떤 구조였는지**를 기록해
논문의 방법과 결과를 검증하려는 사람이 필요한 정보를 얻을 수 있도록 한다.

집계 결과(논문 게재 그림·표)는 [`../results/`](../results/)에 포함되어 있다.

---

## 1. 제외 대상과 사유

| 데이터 | 규모 | 성격 | 제외 사유 |
|---|---:|---|---|
| **실도로 FOT 원본** | 약 50 GB | 실차 주행 센서퓨전 로그 | 산학과제 계약 대상. 취득 회차·프레임 구간 식별자 포함 |
| **CarMaker 시뮬레이션 출력** | 약 470 MB | concrete 시나리오 2,000개의 시계열·충돌 GT | 과제 시뮬레이션 환경 산출물 |
| **회전교차로 도로망 (`.rd5`)** | 1,000개 / 58.8 MB | CarMaker 도로 포맷 | JunctionArt로 생성했으나 **CarMaker(과제 라이선스 도구)로 변환**한 산출물 |
| **파라미터 표** | 1,000행 × 2종 | 시나리오 거동 파라미터 | 실차 FOT 분포에서 추출·샘플링 |
| **복잡도·큐레이션** | 5.4 MB | 시나리오 복잡도 지표, 층화 분할 결과 | 과제 시뮬레이션 데이터에서 산출 |
| **DSM 이미지** | 수 GB | CNN 입력용 BEV 3채널 이미지 | 과제 데이터 렌더링 결과 |
| **학습 가중치** | 22.8 MB | CP-CNN 모델 | 실차 데이터로 학습됨 |

> **판단 기준 1 — 제외**: 실차 데이터인지 여부가 아니라 **"산학과제 자원으로 생성되었는지"**를 기준으로 삼았다.
> 시뮬레이션 생성물이라도 과제 환경·라이선스 도구를 거쳤다면 제외 대상으로 보았다.
>
> **판단 기준 2 — 예외**: 단, **학위논문에 실린 그림·표의 직접 입력이 되는 데이터는 포함**한다.
> 이것이 없으면 논문 결과를 검증할 수 없어 저장소를 공개하는 의미가 사라지기 때문이다.
> 해당 파일은 아래 1.1절에 명시했다.

### 1.1 예외 — 논문 그림·표의 직접 입력

아래 3개는 위 기준 1에 따르면 제외 대상이지만, **논문 게재 그림·표를 재생성하는 데
반드시 필요한 입력**이므로 [`../results/`](../results/)에 포함했다.

| 파일 | 규모 | 소비하는 코드 | 만드는 논문 산출물 |
|---|---:|---|---|
| `results/eig_selection/analysis1/shape_stats.csv` | 1,003행 | `analysis/scripts/run_analysis1_figs.py` | **Figure 2-5** (Fig1a·1b·1c) + `Table1_shape_diversity.csv` |
| `results/eig_selection/analysis1/shape_pool.npz` | 1.5 MB | 〃 | 〃 (밀도 분포용 원 샘플) |
| `results/eig_selection/analysis2/frame_metrics.csv` | 4,500행 | `analysis/scripts/run_analysis2_frame_figs.py` | **Figure 3-3** (ΔmTTCP 분포) |

`shape_stats.csv`는 도로망별 반경 요약 통계이고 `shape_pool.npz`는 그 원 샘플 풀이다.
`run_analysis1_figs.py`가 **둘 다** 읽어 하나로는 그림이 재생성되지 않는다.
셋 모두 절차적으로 생성된 가상 도로·시뮬레이션 이미지에서 산출된 값이며,
실차 주행 기록이나 개별 도로의 원 기하를 복원할 수 있는 정보는 담지 않는다.

### 도로망은 재생성할 수 있다

`.rd5` 1,000개는 제외했지만, **이를 만든 코드는 저장소에 포함되어 있다**
([`../src/road_generation/`](../src/road_generation/)).
`run_modeE_roundabout.py`로 OpenDRIVE(`.xodr`) 도로망을 새로 생성할 수 있으며,
CarMaker 라이선스가 있으면 `.rd5`로 변환할 수 있다.
즉 **절차적 도로 생성이라는 기여 자체는 코드로 검증 가능**하다.

---

## 2. 데이터 스키마

제외된 데이터의 구조다. 다른 환경에서 같은 파이프라인을 재현할 때의 인터페이스 명세이기도 하다.

### 2.1 시나리오 파라미터 표

절차적 생성 도로와 거동 파라미터를 1:1 결합한 concrete 시나리오 정의.

```
Variation,road,v_ego,v_target,a_target
1,roundabout_PCG_821.rd5,21.5,10.34,-0.150221
```

| 컬럼 | 단위 | 의미 |
|---|---|---|
| `Variation` | — | 1..1000, 시나리오 일련번호 |
| `road` | — | 결합된 도로 파일명 |
| `v_ego` | **km/h** | 자차 주행 속도 |
| `v_target` | **km/h** | 타겟 차량 초기 속도 |
| `a_target` | **m/s²** | 타겟 차량 감속도 — 전방충돌 시나리오에만 존재 |
| `ego_route`, `target_route` | — | 주행 경로 ID (`_extended` 판에만) |

후방추돌 시나리오(`drivingAlone_RVL`)는 (v_ego, v_target) 2-D 설계라 `a_target`이 없다.
결함이 아니라 논문이 공시한 설계 한계다.

**샘플링 방법**: 제약(`v_target ≥ 10 km/h`, `v_ego > v_target`)을 만족하는 관측 프레임의
경험분포에서 **행 단위 복원추출** 1,000행 (`rng(42)`). 행 단위라 파라미터 간 상관 구조가 보존된다.

### 2.2 시뮬레이션 출력

시나리오당 2개 파일이 생성된다.

| 파일 | 내용 |
|---|---|
| `{시나리오}_data_{N}.mat` | Variation N의 프리크래시 구간 시계열 |
| `{시나리오}_GT.mat` | 충돌 GT (impact 시점·충돌 모드) |

`data` 구조체가 가져야 할 필드:

| 분류 | 필드 |
|---|---|
| 자차 상태 | `Time`, `Car_tx`/`ty`/`Yaw`, `Car_vx`/`vy`/`v`, `Car_ax`/`ay`, `Car_YawRate` |
| 주변 객체 | `Traffic_{name}_tx`/`ty`/`rz`/… |
| 차선 | `LinePoly_{a,b,c,d}_{L,R}` (차선 다항식 계수) |
| 도로 | `Vhcl_Road_onJunction`, `Sensor_Road_*_Route_CurveXY` (곡률) |

### 2.3 복잡도 지표

시나리오 1건이 1행. 31개 컬럼.

| 컬럼군 | 컬럼 | 의미 |
|---|---|---|
| 식별 | `source_type`, `scenario_name`, `data_index`, `snippet_index` | 시나리오 특정 |
| 구간 | `start_frame_index`, `end_frame_index`, `impact_sample` | 프리크래시 구간 |
| GT | `collision_mode`, `long_collision_mode`, `lat_collision_mode` | 충돌 모드 |
| 복잡도 | `E_curve` | 도로 곡률 |
| | `E_intersection` | 교차 구조 (0/1) |
| | `E_crowd`(`_norm`) | ROI 내 객체 밀도 |
| | `E_class`(`_norm`) | 객체 종류 다양도 |
| | `E_speed`(`_norm`), `mean_speed` | 속도 분산 |
| 위협 | `min/mean_TTC` | Time-To-Collision |
| | `max/mean_I_LAT`, `E_threat_I_LAT`(`_var`,`_var_mean`) | 횡방향 위협 |
| | `max/mean_CP`, `E_threat_CP`(`_var`,`_var_mean`) | 충돌확률 기반 |

**ROI**: 자차 기준 상대좌표(m)로 `x ∈ [-10, 30]`, `y ∈ [-10, 10]`.

지표 정의는 A. Sadat et al., *"Diverse complexity measures for dataset curation in self-driving"*, IROS 2021을 따른다.

### 2.4 DSM (Dynamic Semantic Map)

CNN 입력용 BEV 3채널 이미지.

| 채널 | 의미 |
|---|---|
| R | 주변 객체 (Bounding Box). **명도 = 충돌확률(CP)** |
| G | 차선 (논문 설정에서는 미표기) |
| B | 예측 궤적 |

학습에는 전체에서 4,500장을 무작위 추출해 사용했다 (seed 42).

### 2.5 실차 FOT 로그

파라미터 추출의 원천. 프레임 단위 기록이다.

| 컬럼 | 의미 |
|---|---|
| `frame` | 프레임 번호 |
| `v_ego_kmh`, `v_target_kmh`, `a_target_ms2` | 거동 파라미터 |
| `rel_vel_x`, `rel_vel_y`, `rel_acc_x` | 상대 속도·가속도 |
| `heading_angle_rad` | 상대 헤딩각 |
| `entry_index` | 회전교차로 진입로 인덱스 |
| `rg_label` | 도로유형 라벨 |

논문의 153프레임은 전방충돌 계열 entry 0(62) + entry 1(91)이고, 후방추돌 계열은 1프레임이다.

---

## 3. 익명화

[`../results/fp_classification/`](../results/fp_classification/)의 `FP_HMEA_*.csv`에는
오경보가 발생한 **취득 세션 구분자**가 남아 있다. 이 값은 `FOT_A`~`FOT_E`로 익명화되어
실제 취득 회차를 식별할 수 없다. 세션 간 구분은 유지되므로 세션별 비교 분석은 가능하다.

각 행은 *"어느 세션의 몇 번 주행, 몇 프레임 구간에서 오경보가 났고 도로유형이 무엇인가"*만 담으며,
속도·가속도·센서값 등 **측정치는 포함하지 않는다**. 총 169행이다.

---

## 4. 데이터 없이 확인할 수 있는 것

| 확인 대상 | 위치 |
|---|---|
| 오경보 원인 분류 결과 (논문 Table 1-1 · 3-6, Figure 3-5) | [`../results/fp_classification/`](../results/fp_classification/) |
| 10케이스 학습 성능 비교 (논문 4장) | [`../results/acl_training/`](../results/acl_training/) |
| EIG 선별 결과·수렴 이력 (논문 Figure 3-2) | [`../results/eig_selection/PCG/`](../results/eig_selection/PCG/) |
| 도로 형상 다양성 (논문 Figure 2-5) | [`../results/eig_selection/analysis1/`](../results/eig_selection/analysis1/) |
| ΔmTTCP 분포 (논문 Figure 3-3) | [`../results/eig_selection/analysis2/`](../results/eig_selection/analysis2/) |
| 파라미터 분포 재현도 (논문 Figure 2-7) | [`../results/param_space/figures/`](../results/param_space/figures/) |
