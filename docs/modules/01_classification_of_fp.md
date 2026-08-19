# 01_ClassificationOfFP — HARA/HMEA 기반 오경보 원인 분류

> ### 코드 비공개
>
> 이 모듈의 실행 코드는 공개 저장소에 포함하지 않는다. 분류 파이프라인과 물리기반 충돌확률(CP) 생성 코드(`CP_generation/`, `AVlib/`)가 연구실 자산이고, 센서 파라미터는 실차 캘리브레이션 정본이기 때문이다.
>
> 이 문서에는 **논문에 기술된 범위의 방법 설명과, 그 코드가 생성한 산출물**만 둔다.
> 분류 결과(`Output/`)는 포함되어 있어 논문 Table 1-1 / Table 3-6 / Figure 3-5의 수치를 직접 확인할 수 있다.
>
> **실차 식별자는 익명화되어 있다** — 산출물의 `FOT` 컬럼은 실제 취득 회차 대신 `FOT_A`~`FOT_E`로 치환했다. 5개 세션의 구분은 유지되므로 세션 간 비교 분석은 그대로 가능하다.

실도로(FOT) 평가에서 발생한 충돌 예측 오경보(False Positive)를 HARA/SOTIF 관점의 원인 5분류로 나누고, 보강 대상(2-1: 도로 기하 인지 불확실성)을 식별하는 파이프라인의 첫 모듈.

**파이프라인 위치**: **01: 오경보 원인 분류** → 02(도로 생성) · 03(거동 파라미터 추정)

**논문 대응**: 2.2절 분류 체계 (Figure 2-2, Table 2-4) · Table 1-1 (iter1~4 오경보 118/16/6/10) · Table 3-6 / Figure 3-5 (조건별 원인·도로유형 분해) · 최종 저감 10→3

> **범위 주의**: HARA/HMEA 분석은 **실도로(FOT) 데이터만** 대상으로 한다. 카탈로그(PSM) 계열은 선행연구 자산의 재현용으로 본 연구·논문에서는 다루지 않는다.

---

## 1. 방법

오경보 1건마다 두 단계 판정을 거쳐 원인 라벨을 붙인다.

**D1 — AI 컴포넌트 기인 여부.** 물리기반 위협지표(TM) 판정과 신경망(NN) 판정을 각각 High/Low로 이진화해 HH / HL / LH / LL로 분기한다. 둘 다 High(HH)인 경우는 결정트리 매칭 여부로 다시 나눈다.

**D2 — 인지 모델 기인 여부.** D1에서 남은 항목을 차선 신뢰도와 센서퓨전 품질로 분기해 2-1 / 2-2 / Others로 나눈다.

여기에 수동 주석된 도로유형 라벨(HW / URB / INT / RAB / OTHERS, multi-label)을 결합하면 **원인 × 도로유형** 분해가 나온다. 논문의 핵심 논거인 "잔존 오경보가 회전교차로(RAB)에 집중된다"가 이 표에서 나온다.

| 논문 표기 | 산출물 라벨 | 의미 |
|:---:|:---:|------|
| 1-1 | `1_1` | AI 컴포넌트 기인 — 결정트리 매칭 |
| 1-2 | `1_2` | AI 컴포넌트 기인 — 미매칭 |
| 2-1 | `2_1` | **인지 모델 기인 — 도로 기하 인지 불확실성 (본 연구의 보강 대상)** |
| 2-2 | `3_1` | 인지 모델 기인 — 그 외 |
| 3 | `4` | Others |

> **라벨 번호가 어긋난다.** 논문 2-2가 코드 `3_1`, 논문 3(Others)이 코드 `4`다. 코드 내부 카테고리 번호가 논문 최종 표기 확정 전에 굳어진 이력 때문이며, 산출물 파일명과 `summary_*.csv`의 라벨은 전부 코드 표기를 따른다.

### 실험 조건 8종

같은 분류 절차를 서로 다른 학습 조건의 추론 결과에 적용해, 조건별로 오경보가 얼마나 줄었는지 비교한다.

| 조건 | 내용 | 출력 위치 | 논문 대응 |
|------|------|-----------|-----------|
| iter1~4 | ACL 반복 학습 1~4회차 | `results/fp_classification/Baseline/iter{1..4}/` | Table 1-1 |
| PCGFOT_EIG | **제안 기법** (PCG-FOT + EIG 선별) | `results/fp_classification/PCGFOT_EIG/PCGFOT_EIG/` | 최종 10→3 · Table 3-6 |
| CMO_All | CMO 증강 전량 비교군 | `Output/CMO_All/CMO_All/` | Table 3-6 |
| Remix_EIG_K500 | Remix + EIG 선별 비교군 | `Output/Remix_EIG_K500/Remix_EIG_K500/` | Table 3-6 |
| realFOT_4500 | 실도로 FOT 전량 비교군 | `Output/realFOT_4500/realFOT_4500/` | Table 3-6 |

조건 간에 달라지는 것은 읽어들이는 추론 결과 디렉토리 하나뿐이고, 분류 절차 자체는 동일하다.

## 2. 산출물 (저장소 포함)

조건 디렉토리마다 동일한 형식의 산출물이 있다. 총 CSV 48개 + PNG 18개.

| 파일 | 내용 |
|------|------|
| `summary_{조건}.csv` | 원인별·도로유형별 건수 요약 — **논문 Table 1-1 / Table 3-6의 직접 근거** |
| `FP_HMEA_{조건}_{라벨}.csv` | 원인별 오경보 목록 (라벨 = `1_1`, `1_2`, `2_1`, `3_1`, `4`) |
| `{조건}_hazard_mode.png` | 원인 분포 플롯 |
| `{조건}_road_geometry.png` | 도로유형 분포 플롯 |
| `comparison/compare_road_geometry.png` | **논문 Figure 3-5** — 5개 조건 × 도로유형 잔존 오경보 |
| `comparison/compare_hazard_mode.png` | Table 3-6 시각화 — 5개 조건 × 원인 분해 |

### 2.1 `summary_*.csv` 스키마

```
classifier,iter,HMEA_1_1,HMEA_1_2,HMEA_2_1,HMEA_3_1,HMEA_4,total,rg_HW,rg_URB,rg_INT,rg_RAB,rg_OTHERS
Baseline,iter1,10,3,31,49,25,118,1,15,3,12,5
```

| 컬럼 | 의미 |
|------|------|
| `classifier`, `iter` | 실험 조건 식별 |
| `HMEA_*` | 원인 라벨별 오경보 건수 |
| `total` | 총 오경보 건수 |
| `rg_*` | 도로유형별 건수 (HW 고속도로 / URB 도심 / INT 교차로 / **RAB 회전교차로** / OTHERS) |

### 2.2 `FP_HMEA_*.csv` 스키마

오경보 1건이 1행이다.

```
FOT,logicalScenario,dataIndex,startFrameIndex,endFrameIndex,collisionModeGT,impactSample,roadGeometry
FOT_C,,134,1201,1600,0,0,URB
```

| 컬럼 | 의미 |
|------|------|
| `FOT` | **익명화된 취득 세션 ID** (`FOT_A`~`FOT_E`, 5종) |
| `logicalScenario` | 논리 시나리오명 (FOT 계열은 비어 있음) |
| `dataIndex` | 세션 내 데이터 번호 |
| `startFrameIndex`, `endFrameIndex` | 오경보 발생 구간 |
| `collisionModeGT` | 실제 충돌 모드 (0 = 미충돌 → 오경보 확정) |
| `impactSample` | 충돌 시점 (0 = 미충돌) |
| `roadGeometry` | 도로유형 라벨. multi-label은 `;`로 구분 (예: `INT;URB`) |

## 3. 핵심 수치 재현 위치

| 논문 수치 | 파일 |
|-----------|------|
| iter1~4 총 오경보 118 / 16 / 6 / 10 | `results/fp_classification/Baseline/iter{1..4}/summary_*.csv` 의 `total` |
| 표적 회전교차로 오경보 3건 | `results/fp_classification/Baseline/iter4/FP_HMEA_iter4_2_1.csv` 의 `roadGeometry=RAB` 행 |
| 최종 3건 · RAB 0건 | `results/fp_classification/PCGFOT_EIG/PCGFOT_EIG/summary_PCGFOT_EIG.csv` |
| Figure 3-5 | `results/fp_classification/comparison/compare_road_geometry.png` |

표적 회전교차로 3건이 **02(도로 생성)와 03(파라미터 추정)의 출발점**이다. 이 3건이 어떤 회전교차로에서 발생했는지가 절차적 도로 생성의 설계 근거가 된다.

## 4. I/O 계약

**상류에서 받는 것** — 저장소에 포함되지 않은 외부 입력이다.

| 입력 | 내용 | 생성 주체 |
|------|------|----------|
| `CP_Result_FOT/` | 물리기반 충돌확률(CP) 판정 캐시 + 시나리오별 시계열 | 이 모듈의 `CP_generation/` (비공개) |
| `Inference_Result/` | CP-CNN 추론 결과 (조건별) | 07_ACL |
| `Query_Output/` | 복잡도 측정값 | 05_MapBuilder |
| `Check_road_geometry_annotation/` | 도로유형 수동 주석 | 수동 작업 |
| `FOT_source/` | 실차 센서퓨전 원본 | 실차 로깅 후처리 (proprietary) |

`Data/input/`은 저장소에 빈 폴더로 존재한다. 정본은 연구실 NAS에 있다.

**하류에 넘기는 것**

| 대상 | 내용 |
|------|------|
| 02_JunctionArt | 표적 회전교차로 식별 — 절차적 도로 생성의 설계 근거 |
| 03_SelectionOfParamSpace | 오경보 구간의 거동 파라미터 추정 대상 |

## 5. 재현

| 단계 | 저장소만으로 | 필요한 것 |
|------|:---:|------|
| CP 생성 | ✕ | CP 생성 코드 + 실차 센서퓨전 원본 |
| 분류 실행 | ✕ | 분류 코드 + 위 5종 입력 |
| **결과 확인** | **○** | `Output/`의 CSV·PNG로 논문 수치를 직접 대조 가능 |

**논문만으로 재구현하려면** — 2.2절의 분류 체계(Figure 2-2, Table 2-4)에 D1/D2 판정 기준이 기술되어 있다. 다만 판정에 쓰이는 위협지표 임계값과 센서퓨전 품질 지표는 실차 파라미터에 의존하므로, 재구현 결과가 논문 수치와 동일하지는 않다.

## 6. Notes

- **`HARA_FP_meta_*.mat` 8개는 저장소에 없다.** 오경보 메타 전체를 담은 파일이었으나 익명화 가능 여부를 확인할 수 없어 제외했다. 같은 내용의 요약은 `summary_*.csv`와 `FP_HMEA_*.csv`에 있다.
- **익명화 매핑은 저장소에 없다.** `FOT_A`~`FOT_E`가 어느 취득 회차인지는 공개하지 않는다.
- **`FP_HMEA_*.csv` 중 일부는 비어 있다** (헤더만). 해당 조건에서 그 원인 라벨의 오경보가 0건이라는 뜻이며, 결측이 아니다.
