# parameterDistribution_FOT.py

> ### 이 스크립트와 산출물은 저장소에 없다
>
> `parameterDistribution_FOT.py`(연구실 자산)와 그 출력인 프레임 단위 실차 로그는
> 모두 제외했다. 이 문서는 **② 샘플링 단계의 입력 형식이 무엇이었는지**를 기록해,
> 자체 주행 데이터로 파이프라인을 재현하려는 경우의 명세로 남긴 것이다.
>
> 실제로 실행할 수 있는 것은 상위 폴더의 `estimationDistributionAndSampling_FOT.m`(② 샘플링)부터다.
> 사유와 스키마 요약: [`data/README.md`](../../../data/README.md)

HARA FP 2-1 entry의 **v_ego / v_target / a_target** 프레임별 분포를 추출하여 CSV + 히스토그램 PNG로 출력.

- **Ego 파라미터**: Raw CAN 데이터에서 추출 (원본 정확도)
- **Target 파라미터**: SF_PP 센서퓨전 데이터에서 추출 (칼만 필터 정제)

---

## 코드 위치

```
03_SelectionOfParamSpace\ExampleFor_generationSingleParameterDistribution\parameterDistribution_FOT.py
```

---

## 실행 명령어

```bash
cd "03_SelectionOfParamSpace\ExampleFor_generationSingleParameterDistribution"
```

### 기본 (RAB 전부, iter4 Baseline)

```bash
python parameterDistribution_FOT.py
```

### rg_label 필터

```bash
# URB만
python parameterDistribution_FOT.py --labels URB

# RAB + URB 동시
python parameterDistribution_FOT.py --labels RAB URB
```

### 특정 entry 인덱스 (0-based)

```bash
# entry 0, 1만
python parameterDistribution_FOT.py --entries 0 1
```

### 다른 mat 파일 지정

```bash
# F_final iter1
python parameterDistribution_FOT.py --mat-path "../01_ClassificationOfFP/Output/Baseline\iter1\HARA_FP_meta_iter1.mat"

# F_final iter4
python parameterDistribution_FOT.py --mat-path "../01_ClassificationOfFP/Output/Baseline\iter4\HARA_FP_meta_iter4.mat"
```

### 출력 디렉토리 지정 (CSV+PNG 동일 폴더)

```bash
python parameterDistribution_FOT.py --output-dir "output"
```

### 조합 예시

```bash
# F_final iter1의 URB entry만, 별도 디렉토리에 출력
python parameterDistribution_FOT.py --mat-path "../01_ClassificationOfFP/Output/Baseline\iter1\HARA_FP_meta_iter1.mat" --labels URB --output-dir "output\urb_iter1"
```

---

## 출력 파일

| 파일 | 위치 | 내용 |
|------|------|------|
| `distribution_{label}.csv` | `data/processed/ScenarioParameters/` | 프레임별 v_ego, v_target, a_target 및 중간값 |
| `distribution_{label}.png` | `reports/figures/` | 3-subplot 히스토그램 (v_ego / v_target / a_target) |

`--output-dir` 지정 시 CSV와 PNG 모두 해당 디렉토리에 출력.

---

## 입력 데이터

| 항목 | 경로 | 용도 |
|------|------|------|
| HARA meta (디폴트) | `...\Output\HARA_Classification\v2_matlab\Baseline\iter4\HARA_FP_meta_iter4.mat` | FP entry 목록 (FOT, dataIndex, frame 범위, CP_max_index, rg_label) |
| Raw CAN .mat | `<FOT_NAS>\mat\{FOT}\{FOT}_{dataIndex:03d}.mat` | Ego 파라미터 (v_ego, ego_acc) |
| SF_PP .mat | `<FOT_NAS>\mat\{FOT}\Perception\SF\{FOT}_{dataIndex:03d}_SF_PP.mat` | Target 파라미터 (rel_vel, rel_acc, heading 등) |

---

## 파라미터 추출 변수 및 계산 과정

### 1. v_ego (에고 속도)

| 항목 | 내용 |
|------|------|
| 소스 | Raw CAN .mat |
| 변수 | `CLU_DisSpdVal` (Cluster Display Speed) |
| 단위 | **km/h** (변환 불필요) |
| 비고 | 계기판 표시 속도, 센서퓨전 전후 동일 값 |

### 2. v_target (타겟 속도)

| 항목 | 내용 |
|------|------|
| 소스 | Raw CAN (v_ego) + SF_PP (상대속도) |
| 타겟 선택 | HARA meta의 `CP_max_index` → Fusion_Track_Maneuver `TRACKING.ID` (row 25) 매칭 |
| 사용 변수 | `TRACKING.REL_VEL_X` (row 28, 0-based) — 종방향 상대속도, 칼만 필터 적용 [m/s] |

**계산 과정**:

```
1. v_ego_ms = CLU_DisSpdVal / 3.6                    [km/h → m/s]
2. rel_vx   = Fusion_Track_Maneuver[28, slot, frame]  [m/s, TRACKING.REL_VEL_X]
3. v_target_ms  = v_ego_ms + rel_vx                   [m/s]
4. v_target_kmh = v_target_ms × 3.6                   [m/s → km/h]
```

- 타겟 track이 active하지 않은 프레임은 스킵
- v_target < 0인 프레임은 자동 제거 (타겟이 후진하는 비정상 프레임)
- v_target < 10 km/h인 프레임은 자동 제거 (정지/저속 타겟)

### 3. a_target (타겟 가속도)

| 항목 | 내용 |
|------|------|
| 소스 | Raw CAN (ego_acc) + SF_PP (상대가속도) |
| 사용 변수 | `YRS_LongAccelVal` — 에고 종방향 가속도 [m/s²]<br>`MEASURE.REL_ACC_X` (row 8, 0-based) — 종방향 상대가속도 [m/s²] |

**계산 과정**:

```
1. ego_acc = YRS_LongAccelVal                          [m/s²]
2. rel_ax  = Fusion_Track_Maneuver[8, slot, frame]     [m/s², MEASURE.REL_ACC_X]
3. a_target = ego_acc + rel_ax                         [m/s²]
```

### Fusion_Track_Maneuver 행 인덱스 요약

| 행 (0-based) | MATLAB 행 | 필드 | 영역 | 단위 |
|:---:|:---:|------|------|------|
| 0 | 1 | REL_POS_X | MEASURE | m |
| 1 | 2 | REL_POS_Y | MEASURE | m |
| 2 | 3 | REL_VEL_X | MEASURE | m/s |
| 3 | 4 | REL_VEL_Y | MEASURE | m/s |
| 8 | 9 | REL_ACC_X | MEASURE | m/s² |
| 25 | 26 | ID | TRACKING | - |
| 26 | 27 | REL_POS_X | TRACKING | m |
| 27 | 28 | REL_POS_Y | TRACKING | m |
| 28 | 29 | REL_VEL_X | TRACKING | m/s |
| 29 | 30 | REL_VEL_Y | TRACKING | m/s |
| 30 | 31 | HEADING_ANGLE | TRACKING | rad |

---

## 프로젝트 디렉토리 구조

```
03_SelectionOfParamSpace\
├── data/
│   └── processed/
│       └── ScenarioParameters/                     # ★ 파라미터 분포 CSV 출력
│           ├── distribution_RAB.csv
│           └── distribution_entries_0_1.csv
├── reports/
│   └── figures/                                    # ★ 히스토그램 PNG 출력
│       └── distribution_raw_RAB.png
└── ExampleFor_generationSingleParameterDistribution/
    ├── utils/
    ├── parameterDistribution_FOT.py            # ★ 통합 버전 (Raw ego + SF_PP target)
    ├── parameterDistribution_FOT_SF_PP.py      # SF_PP 전용 버전
    ├── parameterDistribution_FOT_raw.py        # Raw CAN 전용 버전
    └── parameterDistribution_FOT_README.md     # 본 문서
```

---

## 의존성

```
pip install numpy scipy pandas matplotlib h5py
```
