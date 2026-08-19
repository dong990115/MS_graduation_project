> **Vendoring notice** — 이 디렉토리는 [junction-art](https://github.com/Adhocmaster/junction-art) (MPL-2.0, [LICENSE](junctionart/LICENSE) 동봉)의 벤더링 사본이다.
> 본 연구 추가분: `run_modeE_roundabout.py` / `run_modeE_stages.py` / `run_modeE_eval.py`, `analysis/metrics/roundabout/` 3종. 회전교차로 파이프라인이 사용하지 않는 상류 교차로 생성 모듈 12종은 제거됨 (2026-07-25, import 도달성 분석).
> 벤더링 시점의 상류 commit SHA는 기록되지 않았다 (2023~2025년경 스냅샷).

# Junction Art

## 이 저장소에서의 실행 (Quick start)

> 아래 "Installation" 이하는 **상류 원본 프로젝트의 문서**다. 이 저장소에서는 다음 두 줄이면 충분하다.

```powershell
pip install -r requirements.txt      # 저장소 루트에서 1회
cd test_layer/scripts/PCG_dataSelection/02_JunctionArt
python run_modeE_roundabout.py --seed 0 --nway 4 --radius 11.2
```

- `config.yaml` 과 `output/` 은 **첫 실행 때 자동 생성**된다 (수동 복사 불필요).
- **esmini 는 필요 없다.** 진입 스크립트 3종(`run_modeE_*.py`)은 esmini 를 호출하지 않으며,
  생성된 `.xodr` 을 3D 로 볼 때만 별도로 `odrviewer.exe` 를 실행하면 된다.
- 졸업연구용 1,000개 일괄 생성 명령은 아래 [Usage](#usage) 절 참고.

---

Procedural Generation of Intersections for HD Maps for Autonomous Vehicle Development and Test. It's built using [pyodrx](https://github.com/pyoscx/pyodrx) library. It generates road networks in [Open drive](https://www.asam.net/standards/detail/opendrive/) format. Detailed documentation with architecture can be found in the **docs* folder of the repository.

**The documentation moved to [https://junctionart.readthedocs.io/](https://junctionart.readthedocs.io/)**

## Citations

We have two peer-review papers and one preprint in this project. Please, cite the one that's most relevant to your research.

### 1. HD Road Generation - complete city like maps
[Paper](https://www.researchgate.net/publication/360840690_Procedural_Generation_of_High-Definition_Road_Networks_for_Autonomous_Vehicle_Testing_and_Traffic_Simulations)
```
@article{Muktadir2022ProceduralGO,
    author = {Muktadir, Golam Md and Jawad, Abdul and Paranjape, Ishaan and Whitehead, Jim and Shepelev, Aleksey},
    year = {2022},
    month = {05},
    pages = {22},
    title = {Procedural Generation of High-Definition Road Networks for Autonomous Vehicle Testing and Traffic Simulations},
    volume = {6},
    journal = {SAE International Journal of Connected and Automated Vehicles},
    doi = {10.4271/12-06-01-0007}
}
```

### 2. Roundabout Generation - classic and turbo roundabouts
[Paper](https://www.researchgate.net/publication/372708949_Procedural_Generation_of_Complex_Roundabouts_for_Autonomous_Vehicle_Testing)
```
@INPROCEEDINGS{10186533,
    author={Ikram, Zarif and Muktadir, Golam Md and Whitehead, Jim},
    booktitle={2023 IEEE Intelligent Vehicles Symposium (IV)}, 
    title={Procedural Generation of Complex Roundabouts for Autonomous Vehicle Testing}, 
    year={2023},
    volume={},
    number={},
    pages={1-6},
    doi={10.1109/IV55152.2023.10186533}
}
```


### 3. Intersection Generation - most expressive intersection generator today
[Paper](https://www.researchgate.net/publication/360354961_P_r_e_-P_r_i_n_t_Realistic_Road_Generation_Intersections)

```
@unknown{Muktadir2022Intersections,
    author = {Muktadir, Golam Md and Jawad, Abdul and Shepelev, Aleksey and Paranjape, Ishaan and Whitehead, Jim},
    year = {2022},
    month = {05},
    pages = {},
    title = {P r e -P r i n t Realistic Road Generation: Intersections},
    doi = {10.13140/RG.2.2.30541.51683}
}
```

## Entry Points (Mode E)

| Script | Description | Output |
|--------|-------------|--------|
| `run_modeE_roundabout.py` | 단일 라운드어바웃 .xodr 생성 | `output/modeE_inner_roundabout.xodr` (or `--output` path) |
| `run_modeE_eval.py` | ERA (Expressive Range Analysis) 평가 | `output/eval/{mode}/era_*.png` |
| `run_modeE_stages.py` | 생성 과정 단계별 시각화 (논문 Figure용) | `output/stages/seed{N}_{M}way_stage{1-4}_*.png` |

### run_modeE_roundabout.py
```bash
# 단일 생성
python run_modeE_roundabout.py --seed 0 --nway 4 --radius 11.2 --output output/my_roundabout.xodr

# 졸업연구용 1000개 배치 생성
for ($i=0; $i -lt 1000; $i++) {
  python run_modeE_roundabout.py --seed $i --radius 11.2 --noiseSeed $i --distortionAmplitude 0.25 --noiseFrequency 4 --output output/roundabout_PCG_$i.xodr
}
```
- **Input**: 없음 (파라미터로 생성)
- **Output**: `output/roundabout_PCG_0.xodr` ~ `roundabout_PCG_999.xodr` (OpenDRIVE, CarMaker/esmini 호환)

### run_modeE_eval.py
```bash
python run_modeE_eval.py --mode full --nways 3 4 5 --trials 20
```
- **Input**: 없음 (내부적으로 라운드어바웃 대량 생성 후 평가)
- **Output**: `output/eval/{mode}/` 에 ERA 플롯 (radii, dradii, superimposed, bivariate .png)

### run_modeE_stages.py
```bash
python run_modeE_stages.py --seed 0 --nway 4 --output-dir output/stages
```
- **Input**: 없음 (파라미터로 생성)
- **Output**: 4단계 시각화 PNG (circle → distorted → approach → complete)

# Installation

**Steps**:
1. install dependencies
2. create config.yaml (instructions below)
3. create output folder (a folder called "output" in the root directory)

## Dependencies:

Python 3.7+

1. pyodrx (included with the project. No need to install)
2. dill
3. pyyaml
4. scipy, numpy, matplotlib, pytest, unittest
5. methodtools.
6. flask and jinja2 (for web-ui)
7. scikit-spatial
8. z3
9. seaborn
10. shapely, (requres installation of [osgeo](https://stackoverflow.com/questions/12578471/oserror-geos-c-could-not-be-found-when-installing-shapely/50623996#50623996)
11. pandas
12. tqdm
13. sympy
14. geos

### Conda commands:

1. conda install dill
2. conda install -c anaconda pyyaml 
3. conda install -c anaconda scipy
4. conda install -c conda-forge matplotlib
5. conda install -c anaconda unittest2
6. conda install -c conda-forge scikit-spatial
7. conda install -c asmeurer z3 (optional for road generation)
8. conda install -c anaconda seaborn (for analysis)
9. conda install -c conda-forge shapely 
10. conda install -c conda-forge pandas 
11. conda install tqdm 
12. conda install -c conda-forge shapely 
13. conda install -c conda-forge geos


## Configuration - create config.yaml
copy the contents of config-sample.yaml file and create a new file "config.yaml" in the root directory of the project. Now change these configurations:


1. esminipath - the folder containing the bin folder of esmini
2. rootPath - the path to the root folder of this project.


# Conventions:

1. successor is connected to one's end.
2. predecessor is connected to one's start.


# Immutable objects: (recreate instead of edits because they are shared amount different users)
1. raw geometries in planview (Line, Arc, Spiral, ParamPoly, etc.)
2. any lane
3. any link

# API

## Road Generators:
Documentation: [Road Generators](https://github.com/AugmentedDesignLab/junction-art/wiki/Road-Generators)

## SequentialJunctionBuilder

Detailed documentation: [docs/Sequential-RoadBuilder.md](https://github.com/Adhocmaster/junction-art)

## JunctionHarvester
This is the class that harvests junctions. 

## Common use-cases:

### 2 roads 2 lanes: harvest2ways2Lanes

### 3 roads from 2 roads: harvest3WayJunctionsFrom2Ways





