# 05_MapBuilder — 복잡도 계산 · 큐레이션 · DSM 생성

> ### 코드 비공개
>
> 이 모듈의 실행 코드는 공개 저장소에 포함하지 않는다.
>
> 복잡도·큐레이션 알고리즘과 DSM 렌더러(`AVlib/`, `AVlib_s/`)는 연구실 비공개 저장소
> [VICL/Complexity-measures](https://github.com/Vehicle-Intelligence-and-Control-Lab/Complexity-measures) ·
> [VICL/Collision-prediction](https://github.com/Vehicle-Intelligence-and-Control-Lab/Collision-prediction) 자산이며,
> 센서 파라미터는 실차 캘리브레이션 정본이라 함께 제외했다.
>
> **산출물도 포함하지 않는다.** 복잡도·큐레이션 결과는 과제 시뮬레이션 데이터에서 산출된 값이라 제외했다.
> 사유와 스키마는 [`data/README.md`](../../data/README.md) 참조.
>
> 이 문서에는 **논문에 기술된 범위의 방법 설명과 지표 정의**를 둔다.

04의 시뮬레이션 시계열(mat)로부터 시나리오 복잡도를 계산하고, 층화 분할로 학습 세트를 큐레이션한 뒤, CNN 입력용 **Dynamic Semantic Map(DSM)** 이미지를 렌더링하는 모듈. 최종적으로 4,500장 서브샘플이 06_EIG(임베딩)·07_ACL(학습)의 입력이 된다.

**파이프라인 위치**: 04(SimOutput mat) → **05: 복잡도 → 큐레이션 → DSM** → 06(임베딩) · 07(학습)

**논문 대응**: DSM 3채널 정의(R = 주변 객체·명도 = 충돌확률, G = 차선, B = 예측 궤적) · 학습 데이터 4,500장 서브샘플(seed 42)

---

## 1. 방법

4단계다. 굵게 표시한 산출물이 이 저장소에 포함되어 있다.

| 단계 | 하는 일 | 입력 → 출력 | 저장소 |
|------|---------|------------|--------|
| ① 복잡도 계산 | 04의 시계열마다 전처리·예측·위협지표를 거쳐 시나리오 복잡도 지표군을 산출한다. 도로 기하(`E_curve`), 교차 구조(`E_intersection`), 주변 밀도(`E_crowd`), 객체 종류(`E_class`), 속도(`E_speed`)와 위협 지표(TTC, I_LAT, 충돌확률 CP) 기반 지표를 시나리오 단위로 집계한다 | `SimOutput/mat/**` → **`Output/complexity/PSM/complexityMeasures_*.{mat,csv}`** | **포함** |
| ② 큐레이션 | ①의 복잡도와 04의 충돌 GT를 결합해 **CollisionMode별 층화 랜덤 분할**로 학습 세트를 구성한다 | ① 출력 + `*_GT.mat` → **`Output/curation/Curation_*.mat`** | **포함** |
| ③ DSM 렌더 | 시나리오 각 프레임을 BEV 3채널 이미지로 렌더링한다. 논문 설정은 차선 표기 없음(noLane) | `SimOutput/mat/**` (+ ② 선택) → `Output/DSM/{세트}/{시나리오}/*.png` | 미포함 (수 GB) |
| ④ 서브샘플 | ③ 결과에서 4,500장을 무작위 추출한다 (seed 42) | ③ 출력 → `Output/DSM/{세트}_sub4500/` | 미포함 |

**DSM 3채널 정의**가 이 모듈의 핵심 산출물 형식이다.

| 채널 | 의미 |
|------|------|
| R | 주변 객체 (Bounding Box). **명도가 해당 객체의 충돌확률(CP)** |
| G | 차선 (논문 설정에서는 미표기) |
| B | 예측 궤적 |

### 1.1 복잡도 지표의 출처

①의 복잡도 지표군은 A. Sadat et al., ["Diverse complexity measures for dataset curation in self-driving," IROS 2021](https://ieeexplore.ieee.org/document/9636439)의 구현이다. 원 MATLAB 구현(전처리 · Threat Metrics · Motion Attribute · Complexity Measures)을 Python으로 통합 포팅했다.

| 지표 | 의미 |
|------|------|
| `E_curve` | 도로 곡률 (road curvature + line curvature derivative) |
| `E_intersection` | 교차로 여부 (`onJunction` 기반, 0/1) |
| `E_crowd`(`_norm`) | ROI 내 객체 수 평균 |
| `E_class`(`_norm`) | 객체 클래스 다양성 |
| `E_speed`(`_norm`) | 속도 분산 (트랙 간 + 트랙 내) |
| `min/mean_TTC`, `max/mean_I_LAT`, `E_threat_I_LAT` | 위협지표 (TTC, 횡방향) |
| `max/mean_CP`, `E_threat_CP` | 충돌확률 기반 위협도 |

**ROI**는 자차 기준 상대좌표(m)로 `x ∈ [-10, 30]`, `y ∈ [-10, 10]`이다.

### 1.2 ①이 요구하는 입력 필드

04의 `*_data_N.mat` 안 `data` 구조체에 아래 필드가 있어야 한다. 다른 시뮬레이터의 출력으로 재현할 때 필요한 최소 명세다.

| 분류 | 필드 |
|------|------|
| 자차 상태 | `Time`, `Car_tx`/`ty`/`Yaw`, `Car_vx`/`vy`/`v`, `Car_ax`/`ay`, `Car_YawRate` |
| 주변 객체 | `Traffic_{name}_tx`/`ty`/`rz`/… |
| 차선 | `LinePoly_{a,b,c,d}_{L,R}` (차선 다항식 계수) |
| 도로 | `Vhcl_Road_onJunction`, `Sensor_Road_*_Route_CurveXY` (곡률) |

객체 수·크기와 자차 제원은 04의 TestRun·Vehicle 정의에서 자동 파싱한다. GT mat이 없어도 동작한다(충돌 관련 지표만 비게 된다).

### 1.3 ②의 분할 파라미터

CollisionMode별 층화 랜덤 분할로 클래스 밸런스를 유지한다.

| 파라미터 | 논문 설정 | 의미 |
|----------|:---:|------|
| `ratio_trainingSet` | 1.0 | Training / Test 비율 |
| `ratio_initial_trainingSet` | 0.5 | Bench / Rest 비율 |
| `top_n_ratio` | 1.0 | 복잡도 상위 N% 사용 (1.0 = 전체) |

## 2. 산출물 (제외됨 — 스키마만 기록)

아래는 이 단계가 생성했던 산출물이다. **저장소에는 포함하지 않는다** — 과제 시뮬레이션 데이터에서 산출된 값이기 때문이다. 사유는 [`data/README.md`](../../data/README.md) 참조.

| 파일 (당시) | 단계 | 계열 | 크기 |
|------|:---:|------|------|
| `complexityMeasures_Catalog_RABaug_2026-06-01-12-31-10.mat` | ① | PCG-FOT (본 연구) | 226 KB |
| `complexityMeasures_Catalog_2026-06-01-12-31-10.csv` | ① | 위와 동일 내용의 CSV | 713 KB |
| `Curation_RABaug_2026-06-01-12-37-35.mat` | ② | PCG-FOT (본 연구) | 2.8 MB |
| `complexityMeasures_Catalog_103123.mat` | ① | 선행연구(IEEE Access) 계열 | 1.8 MB |

①과 ②는 **정합 짝**이었다 — 12:31에 생성한 복잡도를 12:37에 분할한 결과다. 파일명의 타임스탬프로 짝을 확인할 수 있다.

아래 2.1의 컬럼 정의는 다른 환경에서 같은 지표를 재현할 때의 명세로 남겨둔다.

### 2.1 `complexityMeasures_*.csv` 스키마

①의 출력이며 `.mat`과 동일 내용이다. 시나리오 1건이 1행이다.

```
source_type,scenario_name,data_index,snippet_index,impact_sample,collision_mode,...
CATALOG,LK_CIR_MER_RAB_FOT,1,0,0,0,...
```

①은 같은 내용을 `.csv` / `.pkl` / `.mat` 3포맷으로 저장한다. `.mat` 안의 구조체명은 **`Catalog_Complexity_Measures`** 이며, MATLAB에서 `load()` 후 바로 확인할 수 있다.

| 컬럼군 | 컬럼 | 의미 |
|--------|------|------|
| 식별 | `source_type` | `CATALOG` = CarMaker 시뮬 계열 |
| | `scenario_name` | 논리 시나리오명 |
| | `data_index` | Variation 번호 (04 `paramSpace`의 `Variation`과 대응) |
| | `snippet_index` | 시나리오 내 구간 번호 |
| 구간 | `start_frame_index`, `end_frame_index` | 프리크래시 구간 범위 |
| | `impact_sample` | 충돌 시점 샘플 인덱스 (0 = 미충돌) |
| GT | `collision_mode`, `long_collision_mode`, `lat_collision_mode` | 충돌 모드 (종/횡 분해) |
| 복잡도 | `E_curve` | 도로 곡률 기반 |
| | `E_intersection` | 교차 구조 |
| | `E_crowd`, `E_crowd_norm` | 주변 객체 밀도 (원값 / 정규화) |
| | `E_class`, `E_class_norm` | 객체 종류 다양도 |
| | `E_speed`, `E_speed_norm`, `mean_speed` | 속도 기반 |
| 위협 | `min_TTC`, `mean_TTC` | Time-To-Collision |
| | `max_I_LAT`, `mean_I_LAT`, `E_threat_I_LAT`, `E_threat_I_LAT_var`, `E_threat_I_LAT_var_mean` | 횡방향 위협 지표 |
| | `max_CP`, `mean_CP`, `E_threat_CP`, `E_threat_CP_var`, `E_threat_CP_var_mean` | 충돌확률 기반 |

`_norm` 접미사는 정규화값, `E_threat_*_var*`는 구간 내 분산 계열이다.

### 2.2 `Curation_*.mat` 구조

②의 출력이며 MATLAB 구조체다. ③의 `Concrete_Set_Name`이 이 파일(확장자 제외)을 가리킨다.

```
Training_Set                                   1×1 struct
  └ .full.PSM.{시나리오}(k)                     시나리오별 선택 항목 배열
        ├ .dataIndex    double                 Variation 번호 (①의 data_index)
        └ .GT           1×N double             프레임별 충돌 GT
```

> **스키마 확인 필요**: 위 구조는 모듈 문서 기록에 근거한 것이다. 필드 전체 목록·차원·단위는 MATLAB에서 `whos -file`과 구조체 덤프로 확인해 이 표를 확정할 것.

## 3. I/O 계약

**상류에서 받는 것** — 04_CarMakerSim

| 파일 | 용도 |
|------|------|
| `SimOutput/mat/{시나리오}/{시나리오}_data_{N}.mat` | ①의 복잡도 계산, ③의 DSM 렌더링 |
| `SimOutput/mat/{시나리오}/{시나리오}_GT.mat` | ②의 층화 분할 기준 |

**하류에 넘기는 것**

| 대상 | 형식 |
|------|------|
| 06_EIG | `Output/DSM/{세트}_sub4500/{시나리오}/*.png` — 임베딩 추출 입력 |
| 07_ACL | 같은 이미지 세트 — 커리큘럼 학습 입력 |

DSM 이미지 세트는 수 GB 규모라 저장소에 없다. 연구실 NAS에 계열별로 아카이브되어 있다.

## 4. 재현

| 단계 | 저장소만으로 | 필요한 것 |
|------|:---:|------|
| ① 복잡도 | ✕ | 계산 코드 + 04 시뮬 출력. **산출물이 포함되어 있어 ②의 입력 형식은 확인 가능** |
| ② 큐레이션 | ✕ | 큐레이션 코드 + ① 출력. **산출물 포함** |
| ③ DSM 렌더 | ✕ | 렌더러(`AVlib`) + 센서 파라미터 + 04 시뮬 출력 |
| ④ 서브샘플 | ✕ | 추출 스크립트 + ③ 출력 |

**논문만으로 재구현하려면** — ①의 복잡도 지표 정의는 2.1 스키마의 컬럼명으로 무엇을 계산하는지 파악할 수 있고, 수식은 논문 본문에 있다. ③의 DSM 3채널 정의도 논문에 기술되어 있다. 다만 렌더링에 쓰이는 센서 FOV·검지 범위는 실차 캘리브레이션 값이라 공개할 수 없으므로, 재구현 시 임의의 센서 모델을 가정해야 하고 이 경우 이미지가 논문 것과 동일하지 않다.

## 5. Notes

- **noLane은 별본이 아니라 스위치**였다. 논문 설정은 차선 표기를 끈 상태다.
- **계열별 3종 세트 중 1종이 빠졌다.** 원래 이 모듈에는 선행연구 / PCG-FOT / realroad-FOT 세 계열의 복잡도·큐레이션이 모두 있었으나, realroad-FOT 계열은 실차 데이터 유래라 제외했다.
- **`Output/DSM/`은 저장소에 없다.** 이미지가 수 GB 규모다.
- **선행연구 계열 파일은 05가 생성한 것이 아니다.** `complexityMeasures_Catalog_103123.mat`은 07_ACL 학습의 입력이며, 정본은 `07_ACL/Data/ComplexityMeasure/`에 있다. 여기 있는 것은 동일 파일 사본이다.
