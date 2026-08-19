# docs — 모듈 문서

학위논문 *회전교차로 충돌 예측의 성능 개선을 위한 절차적 도로 생성 및 데이터 선별 연구*의
코드 저장소(01~07) 문서 모음. 각 md는 **논문 표·그림 ↔ 산출물 대응, 모듈 간 I/O 계약, 재현 가능성**을 담는다.

---

## 공개 범위

이 저장소는 **논문에 기술된 범위**만 공개한다. 아래 세 가지는 포함하지 않는다.

| 제외 대상 | 사유 |
|-----------|------|
| **실차 취득 데이터(FOT) 및 직접 파생물** | 산학과제 계약 대상 |
| **연구실 비공개 저장소 코드** | [Vehicle Intelligence and Control Lab](https://github.com/Vehicle-Intelligence-and-Control-Lab) 자산 |
| **IPG CarMaker 배포 자산** | 제3자 상용 라이선스 |

**실차 식별자는 익명화되어 있다.** 산출물에 남은 취득 세션 구분은 `FOT_A`~`FOT_E`로 치환했으며,
세션 간 비교 분석은 그대로 가능하다. 실제 회차와의 매핑은 공개하지 않는다.

**NAS 경로는 플레이스홀더로 치환되어 있다** — `<DATA_NAS>`, `<PROJECT_NAS>`, `<SCENARIO_NAS>`, `<FOT_NAS>`, `<NAS_HOST>`.

---

## ⚠ 코드는 대부분 실행되지 않는다

**입력 데이터가 전부 비공개 대상이기 때문이다.** 실도로 FOT 로그, CarMaker 시뮬레이션 출력,
DSM 이미지, 학습 가중치가 모두 제외되어 있으므로, 이 저장소를 내려받아
**코드를 돌려 결과를 재현하는 것은 불가능**하다.

**결과는 [`../results/`](../results/)의 산출물로 확인해야 한다.**
논문에 실린 표·그림의 근거가 그대로 들어 있다.

예외는 **회전교차로 도로 생성**이다. 외부 입력이 필요 없어 완전히 실행되며,
새 도로망을 직접 생성해볼 수 있다 ([`../src/road_generation/`](../src/road_generation/)).
스크립트별 실행 가능 여부는 [`../src/README.md`](../src/README.md) 1절에 정리했다.

코드를 공개하는 목적은 실행이 아니라 **방법과 구현을 읽을 수 있게 하는 것**이다.

---

## 문서 목록

파이프라인 7단계를 단계별로 기술한 문서다. 저장소가 단계 순서가 아니라 **기여 성격별**로
배치되어 있으므로(`src` / `results` / `data`), 아래 표의 "코드"·"결과" 열에서 각 단계의 실물 위치를 확인한다.

| 문서 | 단계 | 코드 | 결과 |
|------|------|------|------|
| [01_classification_of_fp.md](modules/01_classification_of_fp.md) | 오경보 원인 분류 | 비공개 | [`results/fp_classification/`](../results/fp_classification/) |
| [02_junction_art.md](modules/02_junction_art.md) | 회전교차로 절차적 생성 | [`src/road_generation/`](../src/road_generation/) | (도로망은 재생성) |
| [03_selection_of_param_space.md](modules/03_selection_of_param_space.md) | 거동 파라미터 추정·샘플링 | [`src/param_space/`](../src/param_space/) | [`results/param_space/`](../results/param_space/) |
| [04_carmaker_sim.md](modules/04_carmaker_sim.md) | concrete 시나리오 시뮬레이션 | 비공개 (IPG 라이선스) | — |
| [05_map_builder.md](modules/05_map_builder.md) | 복잡도·큐레이션·DSM 생성 | 비공개 | — |
| [06_eig.md](modules/06_eig.md) | 임베딩·k-means·EIG 선별 | [`src/data_selection/`](../src/data_selection/) | [`results/eig_selection/`](../results/eig_selection/) |
| [07_acl.md](modules/07_acl.md) | 커리큘럼 학습·추론·평가 | 비공개 | [`results/acl_training/`](../results/acl_training/) |

**코드가 비공개인 단계(01·04·05·07)의 문서**는 방법 설명 · 산출물 스키마 · I/O 계약 · 재현 경로를 담는다.
코드 없이도 결과를 해독하고, 논문 수치를 대조하고, 필요하면 재구현할 수 있게 하는 것이 목적이다.

> 각 문서는 재구성 이전(모듈 디렉토리 `01_…`~`07_…`) 기준으로 작성되어,
> 본문에서 옛 경로를 언급하는 곳이 있다. 실물 위치는 위 표를 기준으로 한다.

---

## 파이프라인

```
01 오경보 분류 ─┬─→ 02 도로 생성 ─┐
                └─→ 03 파라미터 ──┴─→ 04 시뮬레이션 ─→ 05 복잡도·DSM ─┬─→ 06 EIG 선별 ─→ 07 커리큘럼 학습
                                                                      └────────────────────↗
```

01이 실도로 오경보의 원인을 분류해 **회전교차로 기하 인지 불확실성**을 보강 대상으로 지목하고,
02·03이 그 조건을 재현하는 도로망과 거동 파라미터를 만들고, 04가 시뮬레이션으로 데이터를 생성하고,
05·06이 복잡도와 EIG 기준으로 학습 데이터를 선별하고, 07이 커리큘럼 학습으로 모델을 개선한다.
개선 결과는 다시 01로 돌아가 오경보 저감(10 → 3건)으로 확인된다.

---

## 재현 가능한 것

저장소만으로 확인·실행할 수 있는 범위다.

| 항목 | 위치 |
|------|------|
| 논문 Table 1-1 (오경보 118/16/6/10) · Table 3-6 · Figure 3-5 | [`results/fp_classification/`](../results/fp_classification/) |
| 논문 4장 10케이스 성능 비교 (FN/FP 근거 mat) | [`results/acl_training/`](../results/acl_training/) |
| 논문 Figure 3-2 (EIG 수렴) · 선별 139장 목록 | [`results/eig_selection/PCG/`](../results/eig_selection/PCG/) |
| 논문 Figure 2-5 (도로 형상 다양성) | [`results/eig_selection/analysis1/`](../results/eig_selection/analysis1/) |
| 논문 Figure 3-3 (ΔmTTCP 분포) | [`results/eig_selection/analysis2/`](../results/eig_selection/analysis2/) |
| 논문 Figure 2-7 (파라미터 분포 재현도, Hellinger 0.36/0.33/0.14) | [`results/param_space/figures/`](../results/param_space/figures/) |
| 회전교차로 도로망 **생성 코드** (재실행 가능) | [`src/road_generation/`](../src/road_generation/) |
| EIG 선별 **파이프라인 코드** | [`src/data_selection/`](../src/data_selection/) |
| 분포 재현도 진단 **코드** | [`src/param_space/hellinger_compare.py`](../src/param_space/hellinger_compare.py) |

**재현할 수 없는 것**: 데이터가 필요한 모든 단계. 이 저장소에는 데이터가 포함되지 않는다
([`data/README.md`](../data/README.md) 참조). 구체적으로는 01의 CP 생성, 03의 파라미터 추출,
04 전체(CarMaker 라이선스), 05 전체, 07의 학습·추론, 그리고 실도로(realroad-FOT) 계열 실험(논문 Case 4·8).

단, **`src/road_generation/`은 외부 입력 없이 단독 실행**되어 회전교차로 도로망을 새로 생성할 수 있다.

---

## 관련 문서

- [`../data/README.md`](../data/README.md) — 제외된 데이터의 스키마·수집 맥락·비공개 사유
- [`../src/road_generation/THIRD_PARTY_NOTICE.md`](../src/road_generation/THIRD_PARTY_NOTICE.md) — 외부 오픈소스 고지 (JunctionArt, MPL-2.0)
- `../[학위논문]회전교차로 충돌 예측의 성능 개선을 위한 절차적 도로 생성 및 데이터 선별 연구.pdf` — 출판본
- `../requirements.txt` — Python 의존성 (`pip install -r requirements.txt`)
