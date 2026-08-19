# 03_SelectionOfParamSpace — 거동 파라미터 분포 추정 · 샘플링

> ### 일부 코드 비공개
>
> 이 모듈은 **코드가 부분적으로 포함**되어 있다.
>
> - **포함** — 샘플링 스크립트와 분포 진단 스크립트. 논문 출판본 2.5절에 맞춰 새로 작성한 것들이다.
> - **미포함** — 실차 센서퓨전 원본에서 프레임별 파라미터를 추출하는 코드(`parameterDistribution_FOT.py`)와 도로 배정 스크립트(`assignRoadToParamSpace.m`). 연구실 비공개 저장소
>   [VICL/SelectionofParameterSpace](https://github.com/Vehicle-Intelligence-and-Control-Lab/SelectionofParameterSpace) 자산이다.
>
> 추출 단계의 산출물인 프레임 단위 실차 로그(`data/processed/ScenarioParameters/`)도 실차 취득 데이터라 제외했다.
> 그 다음 단계인 **샘플링 결과부터는 저장소에 포함**되어 있어, 04로 넘어가는 파라미터 표를 그대로 확인할 수 있다.

01이 식별한 회전교차로 오경보 3건의 실도로 거동(v_ego, v_target, a_target)에서 파라미터 분포를 추정하고, 02가 만든 1,000개 도로망에 1:1 배정할 파라미터 표를 생성하는 모듈.

**파이프라인 위치**: 01(오경보 메타) → **03: 거동 파라미터** ← 02(도로망) → 04(concrete 시나리오)

**논문 대응**: 2.5절 파라미터 분포 추정 (식 2.6-2.7, Figure 2-7) · 153프레임(LK) + 1프레임(drivingAlone) · "1,000개의 회전교차로-파라미터 쌍" · Hellinger distance 0.36 / 0.33 / 0.14

---

## 1. 방법

| 단계 | 하는 일 | 코드 | 산출물 |
|------|---------|:---:|--------|
| ① 파라미터 추출 | 01이 지목한 오경보 구간의 실차 센서퓨전 로그에서 프레임별 거동(v_ego, v_target, a_target)을 뽑는다 | 미포함 | 미포함 (실차 로그) |
| ② 분포 추정 · 샘플링 | ①의 관측 분포에서 1,000행을 추출한다 | **포함** | **포함** |
| ③ 도로 배정 | 샘플링된 1,000행에 02의 도로 1,000개를 1:1 배정한다 | 미포함 | **포함** (결과가 CSV에 반영됨) |
| ④ 분포 진단 | 원 분포와 샘플 분포의 Hellinger distance를 계산해 재현도를 확인한다 | **포함** | **포함** |

### 샘플링 방법 (② — 논문 2.5절)

제약 조건을 만족하는 관측 프레임의 **경험분포에서 행 단위 복원추출** 1,000행을 뽑는다 (`rng(42)`).

- 제약: `v_target ≥ 10 km/h`, `v_ego > v_target`
- 행 단위이므로 (v_ego, v_target, a_target)의 상관 구조가 보존된다
- 관측값 집합에서 뽑으므로 결과의 고유 조합 수는 관측 조합 수를 넘지 않는다 (LK ≤ 107개)

**GMM은 샘플링이 아니라 진단용**이다. 파라미터별 1-D GMM(K = 4/4/2)은 분포의 다봉 구조 확인과 Figure 2-7 작성에 쓰였다. `estimationDistributionAndSampling_FOT_GMM.m`은 joint GMM으로 실제 샘플링하는 별도 참고 구현이며 **논문에는 쓰이지 않았다**. 출력이 `_GMM` 접미사로 분리되어 논문 데이터를 덮어쓰지 않는다.

## 2. 저장소에 포함된 코드

```powershell
cd 03_SelectionOfParamSpace

# ④ 분포 재현도 진단 — 저장소만으로 실행 가능
python hellinger_compare.py            # 3×3 비교 + HD 수치
python hellinger_compare_overlay.py    # 원본 + GMM PDF + 샘플 오버레이 (Figure 2-7 형식)
```

```matlab
cd 03_SelectionOfParamSpace/ExampleFor_generationSingleParameterDistribution
run('estimationDistributionAndSampling_FOT.m')       % ②: 논문 데이터 생성판
run('estimationDistributionAndSampling_FOT_GMM.m')   % 참고: joint GMM 교정판 (논문 미사용)
```

| 파일 | 역할 |
|------|------|
| `estimationDistributionAndSampling_FOT.m` | ② 복원추출 샘플링 — 논문 2.5절 정합판 |
| `estimationDistributionAndSampling_FOT_GMM.m` | ② 대안 구현 — joint GMM 샘플링 (논문 미사용) |
| `hellinger_compare.py` | ④ 3×3 분포 비교 + HD 수치 |
| `hellinger_compare_overlay.py` | ④ 오버레이 플롯 — Figure 2-7 형식 |

**요건**: Python 3.9+ (루트 `requirements.txt`), MATLAB R2022b+ + Statistics and Machine Learning Toolbox (`fitgmdist`).

> ①의 산출물이 저장소에 없으므로 **②는 그대로 재실행되지 않는다.** 입력 CSV를 직접 준비해야 한다 (3.1 스키마 참조). ④는 포함된 CSV만으로 실행된다.

## 3. 산출물 (저장소 포함)

| 파일 | 위치 | 내용 |
|------|------|------|
| `hellinger_comparison.png` | [`results/param_space/figures/`](../../results/param_space/figures/) | HD 0.3585 / 0.3327 / 0.1419 → 출판본 0.36 / 0.33 / 0.14와 정합 |
| `hellinger_overlay.png` | 〃 | **논문 Figure 2-7 형식의 정본 소재** |
| `*_param_space.csv` (1,000행) | **제외됨** | ②③ 최종 출력 — 04 단계의 입력. 스키마는 3.1절 |
| `*_SPD_SPS.csv` (1,000행) | **제외됨** | ② 출력 — 도로 배정 전 보존본 |

파라미터 표는 실차 FOT 분포에서 샘플링한 값이라 제외했다. 사유는 [`data/README.md`](../../data/README.md) 참조.

### 3.1 `*_param_space.csv` 스키마

```
Variation,road,v_ego,v_target,a_target
1,roundabout_PCG_821.rd5,21.5,10.34,-0.150221
```

| 컬럼 | 단위 | 의미 |
|------|------|------|
| `Variation` | — | 1..1000 |
| `road` | — | ③에서 배정된 도로 파일명 |
| `v_ego` | **km/h** | 자차 주행 속도 |
| `v_target` | **km/h** | 타겟 차량 초기 속도 |
| `a_target` | **m/s²** | 타겟 차량 감속도 — **LK_CIR_MER 에만 존재** |

`*_SPD_SPS.csv`는 `road` 컬럼이 없는 형태다(③ 이전 상태).

**`drivingAlone_RVL`에 `a_target`이 없는 것은 결함이 아니다.** (v_ego, v_target) 2-D 설계이며, 논문이 공시한 한계(단일 파라미터 고정)와 정합한다.

### 3.2 ①의 출력 형식 (재현용 참고)

②를 직접 재실행하려면 아래 형식의 입력이 필요하다. 실차 로그이므로 저장소에는 없다.

| 컬럼 | 의미 |
|------|------|
| `frame` | 프레임 번호 |
| `v_ego_kmh`, `v_target_kmh`, `a_target_ms2` | 거동 파라미터 (km/h, m/s²) |
| `v_ego_ms`, `v_target_ms` | 동일 값의 m/s 환산 |
| `rel_vel_x`, `rel_vel_y`, `rel_acc_x` | 상대 속도·가속도 |
| `heading_angle_rad` | 상대 헤딩각 |
| `entry_index` | 회전교차로 진입로 인덱스 |
| `rg_label` | 도로유형 라벨 (`RAB`) |

논문의 153프레임은 LK 계열 entry 0(62프레임) + entry 1(91프레임)이고, drivingAlone은 1프레임이다.

## 4. I/O 계약

| 방향 | 대상 | 내용 |
|------|------|------|
| 상류 | 01_ClassificationOfFP | 표적 회전교차로 오경보 3건 — 어느 구간의 거동을 추출할지 |
| 상류 | 02_JunctionArt | 도로망 1,000개의 파일명 — ③ 배정 대상 |
| 하류 | 04_CarMakerSim | `*_param_space.csv` — `paramSpace/`로 복사되어 시뮬레이션 입력이 된다 |

## 5. 재현

| 단계 | 저장소만으로 | 필요한 것 |
|------|:---:|------|
| ① 추출 | ✕ | 추출 코드 + 실차 센서퓨전 원본 |
| ② 샘플링 | △ | **코드는 포함**. ① 출력이 필요 (3.2 스키마로 대체 입력 구성 가능) |
| ③ 도로 배정 | ✕ | 배정 코드 |
| ④ 진단 | △ | **코드는 포함**. 입력 CSV가 제외되어 그대로는 실행되지 않음 |

**논문만으로 재구현하려면** — ②의 방법(제약 조건 + 복원추출 + `rng(42)`)이 위에 전부 기술되어 있고, ③은 단순 1:1 배정이다. 실질적인 장벽은 ①의 실차 로그뿐이다. 자체 주행 데이터가 있다면 3.2 스키마에 맞춰 구성해 ②부터 그대로 재현할 수 있다.

## 6. Notes

- **Hellinger 정본 조건**: LK 기준(entry 0+1 + LK param_space), `N_BINS=30` → 출판본 0.36 / 0.33 / 0.14와 정합. 컬럼 부재 시 스킵 가드가 있어 drivingAlone 진단으로 바꿔도 동작한다.
- **`parameterDistribution_FOT_README.md`는 남아 있다.** 미포함 코드인 ①의 상세 설명 문서로, 입력 형식 파악에 참고할 수 있다.
- 원 저장소의 보조 추출판 2종(`_raw` / `_SF_PP`)은 논문에 쓰이지 않아 처음부터 포함하지 않았다.
