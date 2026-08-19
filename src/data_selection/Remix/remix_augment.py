"""
Remix (Rebalanced Mixup) — SBEV 이미지 증강 (도로유형 기준)
Chou et al., "Remix: Rebalanced Mixup", ECCV 2020 Workshops

클래스 정의: 도로유형 5개 (HW, INT, URB, RAB, Others)
라벨: 두 도로유형 중 샘플 수가 적은 쪽 (minority-biased)

사용법:
  python remix_augment.py --tail RAB
  python remix_augment.py --tail RAB Others
  python remix_augment.py --tail RAB --n_aug 5000
"""

import os
import csv
import random
import argparse
import numpy as np
from PIL import Image
from collections import defaultdict
import time

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(_SCRIPT_DIR)

# ━━ Defaults ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LABEL_CSV = os.path.join(MODULE_ROOT, 'Output', 'common', 'training_road_type_label.csv')
CURRICULA_DIR = (
    r"<PROJECT_NAS>\Collision Mode\Training\Result"
    r"\ACLpp_iter4_1_0s_051625_SIM3_spl10_wCB_mFtv2\Curricula"
)
OUTPUT_ROOT = os.path.join(MODULE_ROOT, 'Output', 'Remix')
SBEV_CLASS_DIR = "LK_CIR_MER_RAB_FOT"  # 07 학습 클래스 폴더 규약명 (아래 NOTE 참조 — 시나리오 생성물 아님)

ROAD_TYPES = ["HW", "INT", "URB", "RAB", "Others"]

CM_CODE_TO_DIR = {
    "0": "Not_Crash",
    "11": "Collision_Mode_11", "12": "Collision_Mode_12", "13": "Collision_Mode_13",
    "21": "Collision_Mode_21", "23": "Collision_Mode_23",
    "31": "Collision_Mode_31", "33": "Collision_Mode_33",
    "41": "Collision_Mode_41", "43": "Collision_Mode_43",
    "51": "Collision_Mode_51", "52": "Collision_Mode_52", "53": "Collision_Mode_53",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Remix augmentation (road type)")
    parser.add_argument("--tail", nargs="+", default=["RAB"],
                        choices=ROAD_TYPES,
                        help="Tail 클래스 목록 (예: --tail RAB 또는 --tail RAB Others)")
    parser.add_argument("--n_aug", type=int, default=4500,
                        help="생성할 증강 이미지 수 (default: 4500)")
    parser.add_argument("--alpha", type=float, default=1.0,
                        help="Beta(alpha, alpha) 분포 파라미터")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_training_data_by_road_type(csv_path, curricula_dir):
    road_type_images = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rt = row["road_type"]
            cm_dir = row["collision_mode_dir"]
            path = os.path.join(
                curricula_dir, row["level"], cm_dir, row["filename"]
            )
            road_type_images[rt].append({"path": path, "cm_dir": cm_dir})
    return road_type_images


def remix_blend(img_a, img_b, lam):
    arr_a = np.array(img_a, dtype=np.float32)
    arr_b = np.array(img_b, dtype=np.float32)
    mixed = lam * arr_a + (1 - lam) * arr_b
    return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8))


def cm_code_from_dir(cm_dir):
    if cm_dir in ("Not Crash", "Not_Crash"):
        return "0"
    return cm_dir.replace("Collision Mode ", "").replace("Collision_Mode_", "")


def main():
    args = parse_args()
    tail_rts = args.tail

    random.seed(args.seed)
    np.random.seed(args.seed)

    tail_tag = "_".join(sorted(tail_rts))
    output_dir = os.path.join(OUTPUT_ROOT, f"tail_{tail_tag}")
    # NOTE: "LK_CIR_MER_RAB_FOT"는 07 학습 로더의 클래스 폴더 "규약명"이다.
    #       CMO/Remix는 시뮬레이션 시나리오 생성이 아니라 기존 학습 SBEV의 이미지
    #       합성/재조합이며, 전방 합류(LK) 클래스 슬롯으로 학습에 투입하기 위해
    #       이 폴더명을 사용할 뿐이다 (파일명 Image_*_{CMO|Remix}_*.png 로 구분).
    sbev_out = os.path.join(output_dir, SBEV_CLASS_DIR)
    mode_out = os.path.join(output_dir, "mode_classification")
    os.makedirs(sbev_out, exist_ok=True)

    print("[안내] 출력 폴더명 LK_CIR_MER_RAB_FOT는 07 학습 클래스 규약명입니다 — %s는 이미지 합성이며 시나리오 생성이 아닙니다." % "Remix")

    print(f"=== Remix Augmentation (Road Type) ===\n")

    # 1. 데이터 로드 (도로유형 기준)
    print("[1/3] 학습 데이터 로드...")
    rt_images = load_training_data_by_road_type(LABEL_CSV, CURRICULA_DIR)
    rt_counts = {rt: len(imgs) for rt, imgs in rt_images.items()}
    rt_counts = dict(sorted(rt_counts.items(), key=lambda x: -x[1]))
    total = sum(rt_counts.values())

    print(f"  총 {total:,d}장, {len(rt_counts)} 도로유형")
    print(f"  Tail 지정: {tail_rts}")
    for rt, cnt in rt_counts.items():
        tag = " ← tail" if rt in tail_rts else ""
        print(f"    {rt}: {cnt:,d}{tag}")

    all_rts = list(rt_images.keys())

    # 2. Remix 증강
    print(f"\n[2/3] Remix 증강 ({args.n_aug:,d}장, tail={tail_rts})...")
    t0 = time.time()
    generated = 0
    class_gen_counts = defaultdict(int)

    head_rts = [rt for rt in all_rts if rt not in tail_rts]

    for i in range(args.n_aug):
        tail_rt = random.choice(tail_rts)
        head_rt = random.choice(head_rts)
        tail_entry = random.choice(rt_images[tail_rt])
        head_entry = random.choice(rt_images[head_rt])

        lam = np.random.beta(args.alpha, args.alpha)

        assigned_rt = tail_rt
        assigned_entry = tail_entry

        try:
            img_tail = Image.open(tail_entry["path"]).convert("RGB")
            img_head = Image.open(head_entry["path"]).convert("RGB")

            if img_tail.size != img_head.size:
                img_head = img_head.resize(img_tail.size, Image.BILINEAR)

            mixed = remix_blend(img_tail, img_head, lam)

            cm_code = cm_code_from_dir(assigned_entry["cm_dir"])
            fname = f"Image_{cm_code}_REMIX_{i+1:05d}.png"

            mixed.save(os.path.join(sbev_out, fname))

            mode_dir_name = CM_CODE_TO_DIR.get(cm_code, "Not_Crash")
            mode_sub = os.path.join(mode_out, mode_dir_name)
            os.makedirs(mode_sub, exist_ok=True)
            mixed.save(os.path.join(mode_sub, fname))

            generated += 1
            class_gen_counts[assigned_rt] += 1

        except Exception as e:
            print(f"  WARNING: {i+1} — {e}")
            continue

        if (i + 1) % 500 == 0 or (i + 1) == args.n_aug:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 1
            eta = (args.n_aug - i - 1) / rate if rate > 0 else 0
            print(f"  {i+1:,d}/{args.n_aug:,d}  ({elapsed:.0f}s, ~{eta:.0f}s remaining)")

    # 3. 결과
    print(f"\n[3/3] 완료: {generated:,d}장 생성")
    print(f"  출력: {output_dir}")
    print(f"\n  도로유형별 분포:")
    for rt in sorted(class_gen_counts.keys()):
        print(f"    {rt}: {class_gen_counts[rt]}")

    print(f"\n=== 완료 ({time.time()-t0:.0f}s) ===")


if __name__ == "__main__":
    main()
