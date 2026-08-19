# 07_ACL — Active Curriculum Learning 충돌 예측 학습·평가

> ### 공개 범위
>
> **코드는 공개, 데이터·가중치는 비공개.** 학습·추론·평가 스크립트와 파라미터 정의는 그대로 있지만,
> 아래는 포함하지 않는다.
>
> | 제외 | 사유 |
> |------|------|
> | `AVlib/` (전처리 → 예측 → 위협지표 → DSM 충돌확률 체인) | 연구실 비공개 저장소 자산 |
> | `Result/Training/` (10케이스 학습 가중치) | 실차 데이터로 학습된 모델 |
> | `Data/BenchTest/{FOT,SIM}/` (미니 벤치셋 470MB) | 실차 FOT 원본 + AV 스택 신호 덤프 |
> | `Data/Concrete_Set_Script/`, `Data/ComplexityMeasure/…EXP_RG3…` | 실도로 시나리오 카탈로그 |
> | `Parameter/Genesis/` | 실차 센서 캘리브레이션 정본 |
>
> **결과적으로 이 모듈은 그대로 실행되지 않는다.** 아래 3절 참조.
> 다만 **평가 결과 mat은 전부 포함**되어 있어 논문 표의 수치를 직접 검증할 수 있다.
>
> NAS 경로는 `<PROJECT_NAS>` 등 플레이스홀더로 치환되어 있다.

05/06에서 만든 증강 데이터를 기존 커리큘럼 학습 데이터에 더해 CP-CNN 충돌 예측기를 재학습하고,
동일 테스트셋(가상 SIM + 실도로 FOT)으로 평가하는 모듈. 논문의 **10케이스 비교 실험**이 전부 여기서 실행된다.

**파이프라인 위치**: 05(DSM)·06(EIG 선별) → **07: 학습 → 추론 → 평가** → 01(오경보 분류 입력)

**논문 대응**: 3.4절 학습 구성 · 4장 Table(10케이스 성능 비교)

---

## 1. 10케이스 대조표

아래 FN/FP 건수는 **저장소에 포함된 평가 mat**(`results/acl_training/…/Test_Result-ScenarioBasedCollisionDetection-*.mat`)에서 직접 추출한 값이다. 코드나 가중치 없이도 이 수치는 확인할 수 있다.

| C# | 실행 스크립트 | Train_Params | 추가 학습 데이터 | Acc% | FNR%(FN) | FPR%(FP) |
|----|--------------|--------------|------------------|------|----------|----------|
| C1 베이스 | `ActiveCurriculumLearning_Case01.m` | `_iter4_origin` | (없음 — 기존 커리큘럼만) | 97.0 | 1.66(43) | 3.65(204) |
| C2 CMO 전량 | `RunCase02_CMO_4500.m` | `_v13aug_CMO_4500_260609` | 06 CMO tail_RAB 4,500 | 97.3 | 2.62(68) | 2.69(150) |
| C3 Remix 전량 | `RunCase03_Remix_4500.m` | `_v13aug_Remix_4500_260609` | 06 Remix tail_RAB 4,500 | 97.3 | 1.70(44) | 3.23(181) |
| C4 실도로 전량 | `RunCase04_realFOT_4500.m` | `_v13aug_realFOT_4500_260618` | 05 realRAB DSM 4,500 | 97.1 | 2.19(57) | 3.30(184) |
| C5 PCG 전량 | `RunCase05_PCG_4500.m` | `_v13aug_PCG_4500_260609` | 05 RAB DSM 4,500 | 93.9 | 1.86(48) | 8.12(455) |
| C6 CMO EIG | `RunCase06_CMO_EIG_K500.m` | `_v13aug_CMO_EIG_K500_260609` | 06 CMO 선별 227 | 96.1 | 1.97(51) | 4.74(265) |
| C7 Remix EIG | `RunCase07_Remix_EIG_K500.m` | `_v13aug_Remix_EIG_K500_260609` | 06 Remix 선별 164 | 97.4 | 2.08(54) | 2.90(162) |
| C8 실도로 EIG | `RunCase08_realFOT_EIG_K500.m` | `_v13aug_realFOT_K500_260618` | 06 realroad 선별 203 | 96.9 | 2.05(53) | 3.61(202) |
| C9 PCG random | `RunCase09_PCG_random_139.m` | `_v13aug_RAB139` | 05 RAB DSM 무작위 139 | 95.8 | 1.82(47) | 5.25(296) |
| **C10 PCG EIG (제안)** | `RunCase10_PCG_EIG_K500.m` | `_v13aug_PCG_EIG_K500_260609` | 06 PCG 선별 139 (LK 130 + DA 9) | **97.6** | 2.62(68) | **2.31(129)** |

- 실행 스크립트는 `07_ACL/논문/`에 있다. 같은 케이스의 벤치판 `BenchCase##_*.m`은 모듈 루트에 있다.
- `Train_Params` 접두 `ACL_Training_Params` 생략.
- C2·C3·C6·C7 데이터의 하위 폴더명 `LK_CIR_MER_RAB_FOT`는 **학습 클래스 규약명일 뿐**이다 — CMO/Remix는 시나리오 생성이 아니라 이미지 합성/재조합이다 (06 문서 참조).
- 케이스별 원 런 이름(`acl_name`)은 각 RunCase 스크립트 주석에 있다.

**논문의 핵심 결론**이 이 표에 있다. PCG 전량(C5, FPR 8.12%)은 오히려 성능을 악화시키지만, 같은 원천에서 EIG로 139장만 선별한 C10은 FPR 2.31%로 전체 최고다. 무작위 139장(C9, 5.25%)과 비교하면 **선별 기준 자체의 기여**가 드러난다.

## 2. 산출물 (저장소 포함)

| 경로 | 내용 |
|------|------|
| `results/acl_training/<케이스>/Test_Result-ScenarioBasedCollisionDetection-*.mat` | **1절 표의 FN/FP 근거** — 시나리오 단위 충돌 검출 |
| `results/acl_training/<케이스>/Test_Result-ScenarioBasedCollisionModeClassification-*.mat` | 충돌 모드 분류 결과 |
| `results/acl_training/<케이스>/Test_Result-SampleBased-*.mat` | 샘플 단위 결과 |
| `Data/SIMGT/*_GT.mat` (24) | SIM 시나리오 24종의 GT |
| `Data/BenchTest/CarMakerData/{Road,TestRun}` | 벤치 시나리오의 CarMaker 텍스트 자산 |
| `Data/ComplexityMeasure/complexityMeasures_Catalog_103123.mat` | 커리큘럼 난이도 산정용 복잡도 (선행연구 계열) |

`.fig` 파일은 디스크에는 있으나 공개 대상에서 제외된다 — MATLAB `.fig`는 플롯 뒤에 원 데이터 배열이 통째로 직렬화되어 들어가기 때문이다. 같은 내용은 `.mat`에 있다.

## 3. 재현

| 단계 | 저장소만으로 | 막히는 지점 |
|------|:---:|------|
| **평가 수치 확인** | **○** | `results/acl_training/**/*.mat` 로드 → 1절 표 대조 |
| 벤치 추론 (오프라인) | ✕ | `Data/BenchTest/{FOT,SIM}` 미포함 |
| 논문 재현 추론 | ✕ | 가중치 + 전체 테스트셋 + `AVlib` 필요 |
| 학습 재현 | ✕ | 위 + 베이스 커리큘럼 이미지 47,470장 (proprietary) |

**코드는 읽을 수 있다.** 학습 스케줄러, 커리큘럼 난이도 분할, 평가 지표 산출 로직은 `Training/`·`Inference/`에 그대로 있다. 재현이 막히는 것은 데이터와 가중치이지 알고리즘이 아니다.

**논문만으로 재구현하려면** — 3.4절의 학습 구성(커리큘럼 스케줄, 증강 데이터 투입 비율)과 4장의 평가 프로토콜이 필요하다. CP-CNN 구조와 DSM 입력 형식은 05 문서 1절에 있다.

## 4. 구조·경로 규약

- 진입점 20종 (`BenchCase01~10` + `논문/RunCase02~10`·`Case01`)
- `Training/Train_Params` 11종 + `Inference/Test_Params` 5종 + `Test_Utils` 13종
- 모든 param은 `MODULE_ROOT` 앵커 기반 상대경로 + `if ~isfolder(...)` NAS 폴백. 절대경로 없음
- 기본 토글은 추론만 (`RUN_TRAINING=0, RUN_SCORING=0, RUN_EVALUATION=1`)

`Data_Type` 식별자 `EXP_RG3`는 코드 분기에 쓰이므로 그대로 두었다. 해당 데이터는 포함되지 않으므로 이 분기는 실행되지 않는다.

## 5. 상류·하류 연결

| 방향 | 모듈 | 데이터 |
|------|------|--------|
| ← 05_MapBuilder | DSM 이미지(전량 케이스), 복잡도 지표(커리큘럼 난이도) |
| ← 06_EIG | `selected_v13` 선별 이미지(EIG 케이스) |
| → 01_ClassificationOfFP | C10 평가 결과가 오경보 분류의 입력 (FN 68 · FP 129) |

C10의 평가 결과가 01로 돌아가 **오경보 10건 → 3건, 회전교차로 3건 → 0건**으로 확인되는 것이 논문의 최종 논거다.
