# 회전교차로 충돌 예측 — 절차적 도로 생성 및 데이터 선별

> **본 저장소는 석사 학위연구의 방법론과 본인 기여분을 소개하는 쇼케이스입니다.**
> 실도로 FOT 데이터를 비롯한 모든 데이터는 산학과제 계약 대상이라 비공개이며,
> 연구실 소유 코드와 상용 시뮬레이터 자산도 포함하지 않았습니다.
> 해당 부분은 **인터페이스 명세와 데이터 스키마**로 대체했습니다.
>
> **코드는 대부분 실행되지 않습니다** — 입력 데이터가 없기 때문입니다.
> 결과는 [`results/`](results/)의 산출물로 확인해 주십시오.

---

## 목적

자율주행 충돌 예측기가 **회전교차로에서 유독 오경보를 많이 낸다**는 문제에서 출발했다.
실도로 주행 평가에서 남은 오경보를 원인별로 분류해보니, 잔존 오경보가 회전교차로에 집중되어 있었고
원인은 도로 기하에 대한 인지 불확실성이었다. 그런데 회전교차로는 실도로 데이터 수집 자체가 어렵고,
수집해도 형상 다양성이 부족해 학습으로 보강하기 어렵다.

그래서 **회전교차로를 절차적으로 생성해 학습 데이터를 만들고, 그중 정보량이 큰 것만 골라 쓰는** 접근을 택했다.
핵심은 "많이 넣기"가 아니라 "**골라 넣기**"다 — 실제로 생성 데이터 4,500장을 전량 투입하면
오탐률이 3.65%에서 8.12%로 **악화**되지만, 같은 원천에서 139장만 선별하면 **2.31%로 개선**된다.
선별 기준이 성능을 좌우한다는 것이 이 연구의 결론이다.

## 결과

| 지표 | 기준 | 제안 기법 |
|---|---:|---:|
| 오탐률 (FPR) | 3.65% | **2.31%** |
| 정확도 | 97.0% | **97.6%** |
| 잔존 오경보 | 10건 | **3건** |
| 회전교차로 오경보 | 3건 | **0건** |
| 투입 데이터 | — | **139장** (전량 4,500 대비 3%) |

무작위로 같은 139장을 뽑으면 FPR 5.25%로, 선별 기준 자체의 기여가 드러난다.
전체 10개 조건 비교는 [`docs/thesis_link.md`](docs/thesis_link.md#4장--실험-결과) 참조.

## 파이프라인

<!-- docs/pipeline_overview.png — 공개/비공개 경계 다이어그램 -->

```
① 오경보 원인 분류 ──┬──→ ② 회전교차로 절차적 생성 ──┐
     [비공개]        │         [공개]                │
                     └──→ ③ 거동 파라미터 추정 ───────┴──→ ④ 시뮬레이션 ──→ ⑤ 복잡도·DSM
                              [공개]                          [비공개]         [비공개]
                                                                                   │
        ①로 회귀 (오경보 재측정) ←── ⑦ 커리큘럼 학습·평가 ←── ⑥ EIG 데이터 선별 ←┘
                                          [비공개]                [공개]
```

| 단계 | 코드 | 결과 |
|---|---|---|
| ① 오경보 원인 분류 | 비공개 | [`results/fp_classification/`](results/fp_classification/) |
| ② 회전교차로 생성 | **[`src/road_generation/`](src/road_generation/)** | 재생성 가능 |
| ③ 파라미터 추정·샘플링 | **[`src/param_space/`](src/param_space/)** | [`results/param_space/`](results/param_space/) |
| ④ CarMaker 시뮬레이션 | 비공개 (상용 라이선스) | — |
| ⑤ 복잡도·큐레이션·DSM | 비공개 | — |
| ⑥ **EIG 데이터 선별** | **[`src/data_selection/`](src/data_selection/)** | [`results/eig_selection/`](results/eig_selection/) |
| ⑦ 커리큘럼 학습·평가 | 비공개 | [`results/acl_training/`](results/acl_training/) |

비공개 단계와의 입출력 계약: [`docs/interface_spec.md`](docs/interface_spec.md)

---

## 본인 기여

### 1. 회전교차로 절차적 생성 — `src/road_generation/`

**무엇** — 반경·진입로 수·형상 왜곡을 파라미터로 받아 OpenDRIVE 도로망을 생성한다.
1,000개 도로망을 생성해 학습 데이터의 형상 다양성을 확보했다.

**왜 이렇게** — 실측 회전교차로는 2개뿐이었다. 이걸로는 CNN이 도로 기하를 일반화하지 못한다.
Perlin noise 기반 형상 왜곡을 넣어 **실측 도로가 생성 분포 안에 들어가도록**(inside the cloud) 설계했다 —
너무 다양하면 비현실적이고, 너무 좁으면 다양성이 없다. 이 균형을 ERA(Expressive Range Analysis)로 검증했다.
실측 2개가 생성 분포의 p4~p98 구간에 위치함을 확인했다(논문 Figure 2-5).

**입출력** — 파라미터(seed, nway, radius, distortion) → `.xodr` 도로망
**외부 입력이 없어 이 저장소에서 바로 실행된다.**

```powershell
python src/road_generation/run_modeE_roundabout.py --seed 0 --nway 4 --radius 11.2 --output out.xodr
```

> 도로망 생성 엔진으로 [JunctionArt](https://github.com/Adhocmaster/junction-art)(MPL-2.0)를 사용했다.
> 회전교차로 특화 생성 로직·파라미터 설계·검증 지표가 본인 기여분이다.
> 경계: [`src/road_generation/THIRD_PARTY_NOTICE.md`](src/road_generation/THIRD_PARTY_NOTICE.md)

### 2. 거동 파라미터 분포 추정·샘플링 — `src/param_space/`

**무엇** — 실도로에서 관측된 오경보 구간의 차량 거동(자차 속도, 타겟 속도·감속도)에서
분포를 추정하고, 생성 도로 1,000개에 결합할 파라미터 1,000행을 만든다.

**왜 이렇게** — GMM으로 분포를 적합해 샘플링하는 방법을 먼저 시도했으나,
파라미터 간 상관 구조가 깨져 물리적으로 불가능한 조합(타겟이 자차보다 빠른데 충돌)이 나왔다.
그래서 **행 단위 복원추출**로 바꿨다 — 관측된 조합을 통째로 뽑으므로 상관 구조가 보존된다.
GMM은 샘플링이 아니라 다봉 구조 확인용으로만 남겼다.

**검증** — 원 분포와 샘플 분포의 Hellinger distance 0.36 / 0.33 / 0.14로 재현도를 정량화했다.

**입출력** — 프레임별 관측 로그 → 시나리오 파라미터 1,000행 CSV
형식: [`docs/interface_spec.md` §2](docs/interface_spec.md#2-경계--3-파라미터--4-시뮬레이션)

### 3. EIG 기반 데이터 선별 — `src/data_selection/` ★ 핵심

**무엇** — 생성 데이터 4,500장 중 학습에 실제로 도움이 되는 139장을 고른다.
CNN 임베딩(40,000차원) → PCA(2,000차원) → k-means(K=500) → per-class EIG로 클러스터를 누적 선택한다.

**왜 이렇게** — 생성 데이터를 전량 투입하면 오히려 성능이 나빠진다(FPR 3.65% → 8.12%).
편향된 데이터가 많이 들어가면 분포가 왜곡되기 때문이다. 그래서
**"이 데이터를 추가하면 기존 학습셋의 정보량이 얼마나 늘어나는가"**를
EIG(Expected Information Gain)로 정량화해, 목표치(5.5)에 도달할 때까지만 누적하도록 설계했다.
클러스터 단위로 뽑는 이유는 개별 이미지 단위 탐욕 선택이 계산량이 크고 중복에 취약하기 때문이다.

**결과** — 139장(전량의 3%)으로 FPR 2.31%. 같은 수를 무작위로 뽑으면 5.25%.

**입출력** — DSM 이미지 세트 + CNN 가중치 → 선별 목록 CSV
결과: [`results/eig_selection/PCG/`](results/eig_selection/PCG/)

> EIG 산출식은 Dai, Ma et al., *"Trade-Offs Between Richness and Bias of Augmented Data in
> Long-Tailed Recognition"*, Entropy 27(2):201, 2025에서 가져왔고 **구현은 직접 작성**했다.
> 원 논문은 공개 구현체를 제공하지 않는다.

---

## 환경 및 실행

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.9+ (3.11 검증). MATLAB R2022b+는 일부 스크립트에만 필요하다.

**이 저장소만으로 실행 가능한 것**

| 대상 | 명령 |
|---|---|
| 회전교차로 생성 | `python src/road_generation/run_modeE_roundabout.py …` |
| 생성 단계 시각화 (논문 Figure 2-4) | `python src/road_generation/run_modeE_stages.py …` |
| 형상 다양성 그림 (논문 Figure 2-5) | `python src/data_selection/analysis/scripts/run_analysis1_figs.py` |

나머지 11종은 입력 데이터가 비공개라 실행되지 않는다.
스크립트별 판정: [`src/README.md`](src/README.md#1-실행-가능-여부--스크립트별)

## 데이터

**포함하지 않는다.** 스키마·수집 맥락·제외 사유는 [`data/README.md`](data/README.md)에 정리했다.

실차 취득 세션 구분자는 `FOT_A`~`FOT_E`로 익명화했고, NAS 경로는
`<DATA_NAS>`·`<PROJECT_NAS>` 등 플레이스홀더로 치환했다.

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/`](docs/) | 단계별 방법·산출물 스키마·재현 가능성 |
| [`docs/interface_spec.md`](docs/interface_spec.md) | 비공개 단계와의 입출력 계약 |
| [`docs/thesis_link.md`](docs/thesis_link.md) | 논문 서지 · 표/그림 ↔ 산출물 대응 |
| [`data/README.md`](data/README.md) | 데이터 스키마 및 비공개 사유 |
| [`src/README.md`](src/README.md) | 코드 구성 및 실행 가능 범위 |

## 논문

[`[학위논문]회전교차로 충돌 예측의 성능 개선을 위한 절차적 도로 생성 및 데이터 선별 연구.pdf`](./)

공개 링크는 학위수여 후 [`docs/thesis_link.md`](docs/thesis_link.md)에 기재한다.
