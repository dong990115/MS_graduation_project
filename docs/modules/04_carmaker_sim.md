# 04_CarMakerSim — Concrete 시나리오 시뮬레이션

> ### 코드 비공개
>
> 이 모듈의 실행 코드는 공개 저장소에 포함하지 않는다. 두 가지 이유다.
>
> 1. **제3자 상용 라이선스** — 이 디렉토리는 IPG CarMaker 13 프로젝트다. Simulink 소스(`src_cm4sl/`), 차량 모델, 프로젝트 설정은 IPG Automotive 배포 자산이라 재배포할 수 없다.
> 2. **데이터 생성 코드** — 시나리오 생성·시뮬레이션 실행 스크립트는 연구실 자산이다.
>
> **산출물도 포함하지 않는다.** 도로망 1,000개(`.rd5`)와 파라미터 표는 과제 라이선스 도구(CarMaker)를
> 거친 산출물이라 제외했다. 사유와 스키마는 [`data/README.md`](../../data/README.md) 참조.
>
> 이 문서에는 **논문에 기술된 범위의 방법 설명과 데이터 스키마**를 둔다.
> 도로망은 [`src/road_generation/`](../../src/road_generation/)의 코드로 재생성할 수 있다.

02의 도로망 1,000개와 03의 파라미터 1,000행을 결합한 **2,000개 concrete 시나리오**(LK_CIR_MER 전방충돌오인 + drivingAlone_RVL 후방추돌오인)를 IPG CarMaker로 실행하고, 프리크래시 구간 시계열과 충돌 GT를 산출하는 모듈.

**파이프라인 위치**: 02(xodr) + 03(param_space) → **04: 시뮬레이션** → 05(DSM 생성) · 06(임베딩)

**논문 대응**: 2.5절 후단 — "두 종류의 논리 시나리오 각각에 대해 1,000개의 회전교차로-파라미터 쌍을 결합하여 총 2,000개의 concrete 시나리오를 생성하고, 이를 CarMaker 시뮬레이터로 실행" (출판본 p.36)

---

## 1. 방법

5단계다. 굵게 표시한 산출물이 이 저장소에 포함되어 있다.

| 단계 | 하는 일 | 입력 → 출력 | 저장소 |
|------|---------|------------|--------|
| ① 도로 변환 | 02가 생성한 OpenDRIVE 도로망을 CarMaker 도로 포맷으로 일괄 변환. CarMaker GUI의 ScriptControl에서 변환 스크립트를 돌린다 (GUI 라이선스 필요) | `roundabout_PCG_*.xodr` 1,000 → **`roundabout_PCG_*.rd5` 1,000** | **포함** |
| ② Route 생성 | 변환된 각 도로에 주행 경로 3종을 내장한다 — `EgoRing`(자차 환상교차로 순환), `TargetApproach`(타겟 진입), `TargetDA`(drivingAlone용). 기존 Route를 제거한 뒤 회전교차로 기하에서 경로를 재생성한다 | `*.rd5` → 같은 파일에 Route 3종 내장 | **포함** (rd5에 반영됨) |
| ③ 파라미터 확장 | 03의 파라미터 표에 각 행이 사용할 Route ObjId를 붙여 실행용 표로 만든다 | `*_param_space.csv` → **`*_param_space_extended.csv`** | **포함** |
| ④ 시뮬레이션 + GT | 도로×파라미터 조합마다 TestRun을 구성해 CarMaker/Simulink로 실행하고, 결과를 mat으로 변환한 뒤 충돌 GT(impact 시점·모드)를 산출한다 | `*_extended.csv` + `*.rd5` → `SimOutput/{erg,mat}/` | 미포함 (3절 참조) |
| ⑤ 변수명 정규화 | 시뮬 출력의 신호 변수명을 하류가 기대하는 규약(64종)으로 변환한다 | `*_data_N.mat` (in-place) | 미포함 |

**논리 시나리오 2종**의 정의는 `Data/TestRun/`에 남아 있다.

| TestRun | 시나리오 | 타겟 행동 | 오경보 유형 |
|---------|----------|-----------|------------|
| `LK_CIR_MER_RAB_FOT` | Lane Keeping + 합류 | 접근로 → Ring 진입 → 퇴출 | **전방 충돌 오인** |
| `drivingAlone_RVL_RAB_FOT` | Driving Alone + 선행 | Ring 내부 주행 → 퇴출 | **후방 추돌 오인** |

각 논리 시나리오가 1,000개 도로 × 1,000행 파라미터와 1:1로 결합되어 concrete 시나리오 1,000개씩, 합계 2,000개가 된다.

## 2. 산출물 (제외됨 — 스키마만 기록)

아래는 이 단계가 생성했던 산출물이다. **저장소에는 포함하지 않는다.**

| 경로 (당시) | 내용 | 규모 |
|------|------|------|
| `Data/Road/roundabout_PCG_{0..999}.rd5` | Route 3종이 내장된 CarMaker 도로 1,000개 | 58.8 MB |
| `paramSpace/*_param_space.csv` | 03에서 넘어온 파라미터 표 (도로 배정 완료) | 각 1,000행 |
| `paramSpace/*_param_space_extended.csv` | ③ 출력 — Route ObjId 컬럼이 추가된 실행용 표 | 각 1,000행 |
| `paramSpace/*_SPD_SPS.csv` | 도로 배정 전 파라미터 원표 | 각 1,000행 |
| `Data/TestRun/*_RAB_FOT` | 논리 시나리오 정의 (CarMaker TestRun) | 2개 |

### 2.1 `.rd5` 형식

IPG CarMaker의 도로 정의 포맷이며 **UTF-8 텍스트**다. CarMaker 없이도 열어서 구조를 확인할 수 있다.

```
#INFOFILE1.1 (UTF-8) - Do not remove this line!
FileIdent = IPGRoad 13.0
FileCreator = roadutil 13.1.3
Description:
        Converted OpenDRIVE File (Revision 1.4)
        Original File: .../roundabout_PCG_0.xodr
LibVersion = 13.1.3
Country = DEU
nLinks = 8            # 도로 링크 수
nJunctions = 4        # 접속부 수 (회전교차로 진입/진출)
nObjects = 1164       # 도로 객체 수
```

`Route` 블록에 ② 단계에서 생성한 주행 경로 3종이 들어 있고, ③이 붙이는 ObjId가 이 Route를 가리킨다. 도로 기하 자체는 02가 만든 `.xodr`에서 변환된 것이므로 **원 정의는 02 모듈이 정본**이다.

### 2.2 `paramSpace/*.csv` 스키마

```
Variation,road,v_ego,v_target,a_target
1,roundabout_PCG_821.rd5,21.5,10.34,-0.150221
```

| 컬럼 | 단위 | 의미 | TestRun 매핑 |
|------|------|------|-------------|
| `Variation` | — | 1..1000, concrete 시나리오 일련번호 | — |
| `road` | — | 결합된 도로 파일명 | `Road.FName` |
| `v_ego` | **km/h** | 자차 주행 속도 | DrivMan 속도 |
| `v_target` | **km/h** | 타겟 차량 초기 속도 | `Traffic.0` 속도 |
| `a_target` | **m/s²** | 타겟 차량 감속도 — **LK_CIR_MER 에만 존재** | `Traffic.0` 감속도 |
| `ego_route` | — | 자차 Route ObjId (`_extended` 에만) | `Vehicle.Routing.ObjId` |
| `target_route` | — | 타겟 Route ObjId (`_extended` 에만) | `Traffic.0.Routing.ObjId` |

`drivingAlone_RVL`은 (v_ego, v_target) 2-D 설계라 `a_target`이 없다. 이는 결함이 아니라 논문이 공시한 설계 한계다 (03 문서 참조).

**TestRun 매핑** 열은 각 파라미터가 CarMaker TestRun의 어느 필드로 주입되는지를 나타낸다. ④ 단계에서 도로×파라미터 조합마다 이 필드들을 채워 TestRun을 구성한다.

## 3. I/O 계약

**상류에서 받는 것**

| 출처 | 형식 |
|------|------|
| 02_JunctionArt | `roundabout_PCG_{0..999}.xodr` — OpenDRIVE 1.4 |
| 03_SelectionOfParamSpace | `*_param_space.csv` — 위 2.2 스키마 |

**하류에 넘기는 것** — `SimOutput/mat/{시나리오}/` 아래 2종이며, 시뮬레이션을 실행해야 생성된다.

| 파일 | 내용 |
|------|------|
| `{시나리오}_data_{N}.mat` | Variation N의 프리크래시 구간 시계열. 05의 복잡도 계산·DSM 렌더링 입력 |
| `{시나리오}_GT.mat` | 충돌 GT (impact 시점·충돌 모드). 05의 큐레이션 입력 |

저장소의 `SimOutput/`은 **비어 있다**(`.gitkeep`만). 논문 실행분 2,000개는 연구실 NAS에 아카이브되어 있고, 05·06은 로컬이 비어 있으면 그쪽으로 폴백하도록 작성되어 있다.

## 4. 재현

| 단계 | 저장소만으로 | 필요한 것 |
|------|:---:|------|
| ① 도로 변환 | ✕ | CarMaker GUI 라이선스 + 변환 스크립트 |
| ② Route 생성 | ✕ | 생성 스크립트 |
| ③ 파라미터 확장 | ✕ | 확장 스크립트 |
| ④ 시뮬레이션 | ✕ | CarMaker 13.1.3 + MATLAB/Simulink + 실행 스크립트 |
| ⑤ 변수명 정규화 | ✕ | 변환 스크립트 |

**논문만으로 재구현하려면** — 입력이 되는 OpenDRIVE 도로망은 [`src/road_generation/`](../../src/road_generation/)으로 새로 생성할 수 있고, 파라미터 표 형식은 2.2 스키마에 있다. 이 둘이 있으면 임의의 시뮬레이터에서 ④를 직접 구성할 수 있다. 추가로 필요한 정보는 논문 2.5절의 논리 시나리오 2종 정의와 프리크래시 구간 절단 규칙이다.

**코드 열람**은 별도 문의가 필요하다. 단, IPG CarMaker 자산은 어떤 경우에도 재배포할 수 없으므로 라이선스를 보유한 환경에서 CarMaker 프로젝트를 새로 구성해야 한다.

## 5. Notes

- **`src_cm4sl/`, `Data/Vehicle/`, `Data/Config/`, `Data/Road/example/` 는 저장소에 없다.** 각각 CarMaker Simulink 소스, IPG 배포 차량 모델, CarMaker 프로젝트 설정, 실측 도로 데이터다.
- **실도로(realFOT) 계열 시나리오는 제외했다.** 논문 Case 4·8에 해당하는 실도로 기반 concrete 시나리오는 실차 취득 데이터에서 유래하므로 정의 파일·도로·궤적을 모두 제외했다.
- **`.rd5` 안의 `Original File:` 줄**에는 도로 변환 당시의 로컬 작업 경로가 남아 있다. 기능에는 영향이 없다.
- **버전 의존**: 산출물은 CarMaker 13.1.3 / MATLAB R2022b 기준이다. `.rd5`의 `LibVersion` 값으로 확인할 수 있다.
