# 인터페이스 명세 — 비공개 단계와의 입출력 계약

파이프라인 7단계 중 **4단계(01·04·05·07)는 코드가 공개되지 않는다.**
연구실 자산이거나 상용 라이선스 대상이기 때문이다.

이 문서는 그 단계들이 **무엇을 받아 무엇을 내놓는지**를 형식 수준에서 규정한다.
공개된 단계(02·03·06)를 이해하거나 비공개 단계를 다른 구현으로 대체하려 할 때의 계약서다.

관련 문서 — 데이터 스키마 상세: [`../data/README.md`](../data/README.md) ·
단계별 방법: [`modules/`](modules/) · 실행 가능 범위: [`../src/README.md`](../src/README.md)

---

## 1. 전체 데이터 흐름

```
                        [비공개]                    [공개]
                           │                          │
  실차 FOT 로그 ──→ ① 오경보 분류 ─┬──────────────→ ② 도로 생성
      (비공개)                     │                    │  .xodr ×1,000
                                   └──→ ③ 파라미터 추정 │
                                            │ .csv ×1,000행
                                            ↓          ↓
                                    ④ CarMaker 시뮬레이션  [비공개]
                                            │ 시계열 + 충돌 GT
                                            ↓
                                    ⑤ 복잡도·큐레이션·DSM  [비공개]
                                            │ DSM 이미지
                                            ↓
                                    ⑥ EIG 선별            [공개]
                                            │ 선별 목록
                                            ↓
                                    ⑦ 커리큘럼 학습·평가   [비공개]
                                            │ 평가 지표
                                            └──→ ① 로 회귀 (오경보 재측정)
```

경계는 두 곳이다. **③→④**(공개 코드가 비공개 코드에 넘김)와
**⑤→⑥**(비공개 코드가 공개 코드에 넘김). 아래 2·3절이 이 두 지점의 계약이다.

---

## 2. 경계 ① — ③ 파라미터 → ④ 시뮬레이션

공개 코드([`src/param_space/`](../src/param_space/))가 비공개 시뮬레이션에 넘기는 형식이다.

**형식**: CSV, 1,000행, 헤더 있음

```
Variation,road,v_ego,v_target,a_target
1,roundabout_PCG_821.rd5,21.5,10.34,-0.150221
```

| 컬럼 | 타입 | 단위 | 필수 | 의미 |
|---|---|---|:---:|---|
| `Variation` | int | — | ✔ | 1..1000 시나리오 번호 |
| `road` | str | — | ✔ | 결합할 도로 파일명 (②의 산출물) |
| `v_ego` | float | **km/h** | ✔ | 자차 주행 속도 |
| `v_target` | float | **km/h** | ✔ | 타겟 차량 초기 속도 |
| `a_target` | float | **m/s²** | 조건부 | 타겟 감속도 — 전방충돌 시나리오만 |

**시나리오 2종**

| 논리 시나리오 | 타겟 행동 | `a_target` | 오경보 유형 |
|---|---|:---:|---|
| `LK_CIR_MER_RAB_FOT` | 접근로 → Ring 진입 → 퇴출 | 있음 | 전방 충돌 오인 |
| `drivingAlone_RVL_RAB_FOT` | Ring 내부 주행 → 퇴출 | 없음 | 후방 추돌 오인 |

후자에 `a_target`이 없는 것은 (v_ego, v_target) 2-D 설계이기 때문이며, 논문이 공시한 한계다.

**시뮬레이터 측 매핑** — ④가 각 값을 주입하는 위치

| 컬럼 | CarMaker TestRun 필드 |
|---|---|
| `road` | `Road.FName` |
| `v_ego` | DrivMan 속도 |
| `v_target` | `Traffic.0` 속도 |
| `a_target` | `Traffic.0` 감속도 |
| `ego_route` / `target_route` | `Vehicle.Routing.ObjId` / `Traffic.0.Routing.ObjId` |

`*_route` 2개는 ④의 전처리 단계가 도로 파일에서 읽어 붙인다 (`_extended.csv`).

### 도로망 형식 (② → ④)

②가 내놓는 것은 **OpenDRIVE 1.4 (`.xodr`)** 이며, ④가 시뮬레이터 전용 포맷으로 변환한다.
변환 산출물(`.rd5`)은 UTF-8 텍스트이고 헤더에 링크 수·접속부 수·객체 수가 기록된다.

---

## 3. 경계 ② — ⑤ DSM → ⑥ EIG 선별

비공개 코드가 공개 코드([`src/data_selection/`](../src/data_selection/))에 넘기는 형식이다.

**형식**: PNG 이미지 세트, 디렉토리 구조

```
{세트명}/
├── LK_CIR_MER_RAB_FOT/     ← 클래스 폴더 (학습 로더 규약명)
│   └── Image_{k}_{시나리오}_{concrete}_{frame}.png
└── drivingAlone_RVL_RAB_FOT/
    └── …
```

**이미지 규격 — Dynamic Semantic Map (DSM)**

BEV(Bird's Eye View) 3채널 이미지다.

| 채널 | 내용 |
|:---:|---|
| **R** | 주변 객체 Bounding Box. **명도 = 해당 객체의 충돌확률(CP)** |
| **G** | 차선. 논문 설정은 미표기(noLane) |
| **B** | 예측 궤적 |

학습에는 전체에서 **4,500장을 무작위 추출**(seed 42)해 사용했다.

**파일명 규약**

| 필드 | 의미 |
|---|---|
| `k` | 이미지 인덱스 |
| `시나리오` | 논리 시나리오명 |
| `concrete` | Variation 번호 — 2절 CSV의 `Variation`과 대응 |
| `frame` | 프레임 인덱스 |

이 대응 덕분에 선별된 이미지에서 **원 시나리오 파라미터를 역추적**할 수 있다.
⑥의 산출물 `selected_scenarios.csv`가 이 파일명 목록이다.

> CMO·Remix 계열의 클래스 폴더명 `LK_CIR_MER_RAB_FOT`는 **학습 로더의 규약명일 뿐**이며,
> 시뮬레이션으로 생성한 시나리오가 아니라 기존 학습 이미지를 합성·재조합한 것이다
> (파일명 `Image_*_{CMO,Remix}_*.png`로 구분).

---

## 4. 비공개 단계별 계약 요약

### ① 오경보 원인 분류 (비공개)

| | 형식 |
|---|---|
| **입력** | 실차 FOT 센서퓨전 로그, 물리기반 충돌확률(CP) 판정 캐시, CNN 추론 결과, 도로유형 수동 주석 |
| **출력** | 오경보 목록 CSV (`FOT`, `dataIndex`, `startFrameIndex`, `endFrameIndex`, `collisionModeGT`, `roadGeometry`) + 원인별 집계 |
| **판정 로직** | D1(물리 TM × 신경망 NN을 High/Low 이진화 → HH/HL/LH/LL) → D2(차선 신뢰도·센서퓨전 품질) |
| **결과 위치** | [`../results/fp_classification/`](../results/fp_classification/) |

### ④ CarMaker 시뮬레이션 (비공개 — 상용 라이선스)

| | 형식 |
|---|---|
| **입력** | 2절 CSV + OpenDRIVE 도로망 |
| **출력** | `{시나리오}_data_{N}.mat` (프리크래시 구간 시계열), `{시나리오}_GT.mat` (충돌 시점·모드) |
| **필수 신호** | `Time`, `Car_tx/ty/Yaw`, `Car_vx/vy/v`, `Car_ax/ay`, `Car_YawRate`, `Traffic_{name}_tx/ty/rz`, `LinePoly_{a,b,c,d}_{L,R}`, `Vhcl_Road_onJunction`, `Sensor_Road_*_Route_CurveXY` |

### ⑤ 복잡도·큐레이션·DSM (비공개)

| | 형식 |
|---|---|
| **입력** | ④의 시계열 + 충돌 GT |
| **출력 1** | 복잡도 지표 — 시나리오당 1행, 31컬럼 (스키마: [`../data/README.md`](../data/README.md) 2.3절) |
| **출력 2** | 큐레이션 — CollisionMode별 층화 랜덤 분할 결과 |
| **출력 3** | DSM 이미지 세트 (3절 형식) |
| **ROI** | 자차 기준 상대좌표 `x ∈ [-10, 30]`, `y ∈ [-10, 10]` (m) |

지표 정의는 A. Sadat et al., *"Diverse complexity measures for dataset curation in self-driving"*, IROS 2021을 따른다.

### ⑦ 커리큘럼 학습·평가 (비공개)

| | 형식 |
|---|---|
| **입력** | 베이스 커리큘럼 이미지 + ⑥이 선별한 증강 세트 + 복잡도 지표(난이도 산정) |
| **출력** | 평가 결과 `.mat` 3종 — 시나리오 단위 충돌 검출 / 충돌 모드 분류 / 샘플 단위 |
| **결과 위치** | [`../results/acl_training/`](../results/acl_training/) — 10케이스 × 3종 |

---

## 5. 다른 구현으로 대체하려면

| 대체 대상 | 필요한 것 |
|---|---|
| ④ 시뮬레이터 | 2절 CSV를 읽어 ⑤가 요구하는 신호 필드를 내놓으면 된다. CarMaker일 필요는 없다 |
| ⑤ DSM 렌더러 | 3절 3채널 규격과 파일명 규약을 지키면 된다. 다만 **센서 FOV·검지 범위가 실차 캘리브레이션 값**이라, 임의 센서 모델로 렌더링하면 이미지가 논문과 동일하지 않다 |
| ① 분류기 | D1/D2 판정 기준은 논문 2.2절에 있으나 **위협지표 임계값이 실차 파라미터에 의존**한다 |
| ⑦ 학습기 | 3절 이미지 세트를 입력으로 받는 CNN이면 된다. 커리큘럼 스케줄은 논문 3.4절 |

**②·③·⑥은 대체할 필요가 없다** — 코드가 공개되어 있다.
