# 외부 오픈소스 고지 — `junctionart/`

이 디렉토리의 `junctionart/` 하위는 **본인 작성 코드가 아니라 외부 오픈소스를 가져온 것**이다.

| 항목 | 내용 |
|------|------|
| 프로젝트명 | **JunctionArt** — Procedural HD Map and Intersection Generator |
| 버전 | 0.1.2 |
| 원저작자 | Adhocmaster |
| 라이선스 | **Mozilla Public License 2.0 (MPL-2.0)** |
| 원문 라이선스 | [`junctionart/LICENSE`](junctionart/LICENSE) |

MPL-2.0은 재배포를 허용하되 **파일 단위 카피레프트**를 적용한다.
`junctionart/` 안의 파일을 수정해 배포할 경우, 수정된 **그 파일들**은 MPL-2.0으로 공개해야 한다.
반면 이 저장소의 다른 코드(`src/road_generation/` 루트, `src/param_space/`, `src/data_selection/`)는
별도 저작물로 취급되어 MPL-2.0의 적용을 받지 않는다.

## 본인 기여와의 경계

| 경로 | 작성 주체 |
|------|----------|
| `junctionart/` | **외부 (JunctionArt, MPL-2.0)** |
| `run_modeE_roundabout.py` | 본인 — 회전교차로 생성 진입점 |
| `run_modeE_stages.py` | 본인 — 단계별 생성 실행 |
| `run_modeE_eval.py` | 본인 — 생성 결과 평가 |
| `analysis/` | 본인 — 형상 다양성·현실성 지표 |
| `config-sample.yaml` | 본인 — 생성 파라미터 설정 예시 |

즉 **JunctionArt는 도로망 생성 엔진으로 사용한 라이브러리**이고,
회전교차로 특화 생성 로직·파라미터 설계·생성 결과 검증이 본인 기여분이다.

## 원 저장소

**https://github.com/Adhocmaster/junction-art**

벤더링 시점의 상류 commit SHA는 기록되지 않았다 (2023~2025년경 스냅샷).
회전교차로 파이프라인이 사용하지 않는 상류 교차로 생성 모듈 12종은 제거한 상태다
(2026-07-25, import 도달성 분석 기준).

## 참고 — EIG는 성격이 다르다

[`../data_selection/`](../data_selection/)의 EIG 선별 알고리즘은 **코드를 가져온 것이 아니라
참고 논문의 수식만 참조해 직접 구현**한 것이다.

| 대상 | 가져온 것 | 의무 |
|---|---|---|
| `junctionart/` | **코드 자체** | MPL-2.0 준수 (이 문서) |
| EIG 선별 | **수식만** (식 3.1~3.6) | 학술적 인용 |

EIG 참고 논문은 Dai, Ma et al., *"Trade-Offs Between Richness and Bias of Augmented Data in
Long-Tailed Recognition"*, Entropy 27(2):201, 2025이며, 공개 구현체를 제공하지 않는다.
