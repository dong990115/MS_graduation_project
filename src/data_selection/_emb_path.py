"""임베딩(embeddings_pca_B.mat) 경로 결정 — 06_EIG 공통 헬퍼.

②run_kmeans · ③run_algorithm2_perclass · run_random_select · plot_tsne_clusters 가
모두 이 함수를 쓴다. 각자 분기를 두면 서로 어긋나므로 여기 한 곳에서만 정한다.

우선순위
    1) --emb <경로>   직접 지정
    2) --nas          NAS 정본 강제 (로컬이 있어도 무시) ← 논문 수치 재현용
    3) 로컬 Output/<case>/<run>/embeddings_pca_B.mat  (①의 출력)
    4) NAS 정본으로 폴백

논문 재현 시 반드시 --nas 를 쓸 것. ①(extract_and_pca)은 PCA randomized SVD 때문에
정본과 다른 임베딩을 만들며(README 참조), 로컬에 그 산출물이 있으면 3)이 선택되어
선별 결과가 논문과 달라진다(실측: 139장 → 158장).
"""

import argparse
import os

NAS_ROOT = r"<DATA_NAS>\EIG"
EMB_FILENAME = "embeddings_pca_B.mat"


def add_emb_args(parser):
    """임베딩 선택 인자를 파서에 추가."""
    g = parser.add_argument_group("임베딩 입력")
    g.add_argument("--nas", action="store_true",
                   help="NAS 정본 임베딩을 강제 사용 (로컬이 있어도 무시) — 논문 수치 재현용")
    g.add_argument("--emb", metavar="PATH", default=None,
                   help="임베딩 파일 경로 직접 지정")
    return parser


def parse_emb_args(argv=None):
    """스크립트가 자체 파서를 두지 않을 때 쓰는 간이 파서 (미지의 인자는 무시)."""
    ap = argparse.ArgumentParser(add_help=False)
    add_emb_args(ap)
    args, _ = ap.parse_known_args(argv)
    return args


def resolve_emb_path(case, run_name, module_root, args=None, verbose=True):
    """임베딩 경로를 결정해 반환한다.

    case      : 'PCG' | 'CMO' | 'realroad' | 'Remix'
    run_name  : 예) 'noLane_060126_sub4500'
    module_root: 06_EIG 디렉터리 절대경로
    args      : parse_emb_args() 결과 (None 이면 sys.argv 에서 파싱)
    """
    if args is None:
        args = parse_emb_args()

    local = os.path.join(module_root, "Output", case, run_name, EMB_FILENAME)
    nas = os.path.join(NAS_ROOT, case, run_name, EMB_FILENAME)

    if getattr(args, "emb", None):
        path, src = os.path.abspath(args.emb), "직접 지정(--emb)"
    elif getattr(args, "nas", False):
        path, src = nas, "NAS 정본(--nas)"
    elif os.path.isfile(local):
        path, src = local, "로컬(① 출력)"
    else:
        path, src = nas, "NAS 정본(로컬 없음 → 폴백)"

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"임베딩 파일을 찾을 수 없습니다 [{src}]\n"
            f"  대상: {path}\n"
            f"  로컬: {local} ({'있음' if os.path.isfile(local) else '없음'})\n"
            f"  NAS : {nas} ({'있음' if os.path.isfile(nas) else '없음(Z: 연결 확인)'})"
        )

    if verbose:
        # cp949 콘솔에서도 깨지지 않도록 ASCII 기호만 사용
        print(f"  [emb] path  : {path}")
        print(f"  [emb] source: {src}")
        if src.startswith("로컬"):
            print("  [emb] warn  : (1) 재실행본이면 논문 수치와 달라질 수 있습니다. "
                  "재현이 목적이면 --nas 를 쓰세요.")
    return path
