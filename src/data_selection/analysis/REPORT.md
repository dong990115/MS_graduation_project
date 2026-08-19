# 회전교차로 증강 데이터 분석 — 논문 그림 재현 리포트

> ### 산출물 위치와 실행 가능 범위
>
> 이 분석의 산출물은 [`results/eig_selection/analysis1/`](../../../results/eig_selection/analysis1/)과
> [`analysis2/`](../../../results/eig_selection/analysis2/)에 있다.
>
> **그림 생성 단계(`run_analysis1_figs.py`, `run_analysis2_frame_figs.py`)는 실행 가능하다** —
> 입력인 `shape_stats.csv`·`shape_pool.npz`·`frame_metrics.csv`가 포함되어 있기 때문이다.
> 반면 그 앞의 **집계 단계(`*_batch.py`)는 실행되지 않는다** — 원 도로망(`.xodr`)과
> DSM 이미지가 제외되었다. 사유: [`data/README.md`](../../../data/README.md)

> 기준: 학위논문 출판본. 이 폴더의 코드·산출물은 논문 **Figure 2-5**(형상 다양성·현실성)와
> **Figure 3-3**(ΔmTTCP 분포·FP 대역 농축)을 재현한다. 모든 수치는 도구로 직접 계산한 결과다.
> (2026-07-26: 논문 미사용 산출물·지표 계산 경로를 정리 — 코드가 논문 지표만 산출하도록 트림,
> 재실행 대조로 값 불변 확인.)

---

## 분석 1 — 생성 도로망의 형상 다양성·현실성 (논문 Figure 2-5, 2.4절)

**입력**: 절차 생성 회전교차로 `02_JunctionArt/output/roundabout_PCG_0~999.xodr` 1,000개 +
오경보 발생 실측 회전교차로 2개(`04_CarMakerSim/Data/Road/example/FOT_A_{087,090}.xodr`).
전처리: OpenDRIVE planView 파싱 → 순환 링 중심선 식별 → 호길이 Δs=0.5 m 등간격 샘플링
(PCG pooled N=140,410 / FP pooled N=337).

**지표** (논문 식 2.2·2.3 + 평균 반지름 정규화):

```
(c_x, c_y) = (1/N)·Σ(xₖ, yₖ),  rₖ = √((xₖ−c_x)²+(yₖ−c_y)²)      (식 2.2)
r̄ = (1/N)·Σ rₖ,   x̃ₖ = (rₖ−r̄)/r̄          — 정규화 반지름 편차 (0 = 완전한 원)
Δrₖ = rₖ − rₖ₋₁,  Δr̃ₖ = Δrₖ/r̄             (식 2.3) — 형상 거칠기
```

**그림 대응**:

| 산출물 | 논문 |
|---|---|
| `Fig1a_radius_dist` | Figure 2-5 (a) radius length distribution |
| `Fig1b_radius_change_dist` | Figure 2-5 (b) radius change distribution |
| `Fig1c_2d_shape` | Figure 2-5 (c) normalized 4-way roundabouts superimposed on a circle |

**결과 (Table1_shape_diversity.csv)**: 실측 FP 회전교차로의 형상 편차는 약 [−0.01, +0.01]~±9%
이내로, 생성 분포([−0.05, +0.03] 변화율 / 편차 [−41%, +44%])의 **안쪽 부분집합**
(x̃: [p4.2, p98.0], Δr̃: [p4.8, p98.9] — 전 샘플이 PCG CDF 내부). 즉 절차적 생성은 실패가 발생한
실측 형상을 포함하면서 그 주변·바깥 형상까지 연속 확장한다 (논문 p.33 서술의 근거 수치).

**한계 (논문 명기와 동일)**: ① 기준집합은 잔존 오경보 3건이 발생한 실측 회전교차로 2개소 —
필요조건 제시이며 실세계 형상 전체를 대표하지 않음. ② 정규화로 크기 축은 범위 밖.

---

## 분석 2 — EIG 선별 데이터의 프레임 단위 상호작용 (논문 Figure 3-3, 3.3절 식 3.7–3.8)

**분석 단위**: CNN 학습·EIG 선별 단위가 SBEV 이미지이므로, 지표는 시나리오 집계값이 아니라
각 이미지가 담은 프레임 k의 순간값 (논문 p.47 서술).

**지표** (논문 식 3.7–3.8):

```
mTTCPᵢᵖ(k) = dᵢᵖ(k) / vᵢ(k)                                  (식 3.7)
ΔmTTCP(k) = min over p∈CP | mTTCP_egoᵖ(k) − mTTCP_tgtᵖ(k) |   (식 3.8)
  CP = 두 차량의 실주행 경로가 공유하는 전방 충돌점 후보 (경로 근접 ≤1 m; 없으면 미정의)
```

**입력**: 생성 풀 SBEV 4,500장(`05_MapBuilder/Output/DSM/RAB_v13_Train_060126_noLane_sub4500`,
NAS 폴백 `augmented_dataset\PCG_4500`) + EIG 선별 139장(`06_EIG/Output/PCG/.../K_500/selected_scenarios.csv`)
+ baseline(Case 1) 평가의 FP 204건(PSM 194 + FOT 10)의 오판 프레임 517개
(`07_ACL/Result/Inference/ACLpp_iter4_origin/Test_Result-ScenarioBasedCollisionDetection-2026_06_05_12_57_06.mat`).

**그림 대응**:

| 산출물 | 논문 |
|---|---|
| `Fig2-mTTCP_frame_RAB` | Figure 3-3 (a) compared with RAB false positives |
| `Fig2-mTTCP_frame_allFP` | Figure 3-3 (b) compared with all false positives |

**결과 (논문 p.48–49 서술의 근거 수치)**:
- baseline 오경보 판단 프레임들의 ΔmTTCP: 정의 351/517, min 0.00 / p25 0.09 / **중앙값 0.29 s** —
  오경보는 두 차량이 충돌점에 거의 동시에 도달하는 near-critical 순간에 집중.
- **FP 중앙값 대역 [0, 0.29 s]의 프레임 비율: 풀 2.6% → EIG 선별 13.2% (약 ×5 농축)** —
  임베딩만으로 선별했음에도 FP 대역이 농축됨 (논문: "2.6%에서 13.2%로").
- RAB판(a)은 회전교차로 오판 프레임 2개의 참고선; 정량 서술은 allFP판(b)에 둠.
- 주장 강도: 농축 "경향" 서술이며 통계적 검정 주장이 아님 (논문 명기와 동일).

**정의율 참고** (2026-07-26 재실행 로그): 풀 4,500장 중 ΔmTTCP 정의 2,606(58%; LK 33%·DA 82%),
선별 139장 중 53(38%) — 경로 비교차·짧은 트랙은 미정의. FP는 351/517.

---

## 산출물 목록

| 파일 | 내용 |
|---|---|
| `output/analysis1/Fig1a·1b·1c.{png,pdf}` | 논문 Figure 2-5 (a)(b)(c) |
| `output/analysis1/Table1_shape_diversity.csv`, `shape_stats.csv`, `shape_pool.npz` | 본문 수치 근거·도로별 원자료 |
| `output/analysis2/Fig2-mTTCP_frame_{RAB,allFP}.{png,pdf}` | 논문 Figure 3-3 (a)(b) |
| `output/analysis2/frame_metrics.csv` (4,500행), `fp_frame_metrics.csv` (517행) | 그림·농축 수치의 원자료 (ΔmTTCP) |

## 재현 방법

```
cd <repo>/test_layer/scripts/PCG_dataSelection/06_EIG/analysis
python scripts/run_analysis1_batch.py        # 링 추출 + rₖ/Δrₖ (1,002 도로망, ~수 초)
python scripts/run_analysis1_figs.py         # Figure 2-5 3장 + Table 1
python scripts/run_analysis2_frame_batch.py  # 풀 4,500 + 선별 139 프레임 ΔmTTCP (~3분)
python scripts/run_analysis2_fp_frames.py    # baseline FP 517프레임 ΔmTTCP (~1분)
python scripts/run_analysis2_frame_figs.py   # Figure 3-3 2장 + 농축 수치
# 구현 검증(회귀): scripts/validation/ (test_metrics.py, validate_frame_mapping.py 등)
```

경로는 전부 레포 상대(`_MONO` 앵커) + NAS 폴백 — 2026-07-26 재실행으로 전 체인 에러 0,
기존 산출물과 값 완전 일치(ΔmTTCP 최대차 0, analysis1 CSV 바이트 동일) 확인.

## 한계·주의

1. rₖ·Δrₖ는 도로 참조선 기준 — 실측 087은 정션 입구 참조선 오프셋으로 링 커버리지 87%(마스킹).
2. 상호작용 지표는 차량 기준점 운동학(크기 보정 없음) — 절대값은 보수적, 집합 간 비교에는 동일 적용.
3. CMO/Remix는 이미지 합성이라 차량 궤적이 없어 분석 2 대상이 아님.
