"""
CMO (Context-rich Minority Oversampling) — SBEV 이미지 증강 (도로유형 기준)
Park et al., "The Majority Can Help the Minority", CVPR 2022

클래스 정의: 도로유형 5개 (HW, INT, URB, RAB, Others)
Head/Tail: 사용자 지정 (--tail 옵션)
  --tail RAB          → Tail: RAB만
  --tail RAB Others   → Tail: RAB + Others

사용법:
  python cmo_augment.py --tail RAB
  python cmo_augment.py --tail RAB Others
  python cmo_augment.py --tail RAB --n_aug 5000
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
OUTPUT_ROOT = os.path.join(MODULE_ROOT, 'Output', 'CMO')
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
    parser = argparse.ArgumentParser(description="CMO augmentation (road type)")
    parser.add_argument("--tail", nargs="+", default=["RAB"],
                        choices=ROAD_TYPES,
                        help="Tail 클래스 목록 (예: --tail RAB 또는 --tail RAB Others)")
    parser.add_argument("--n_aug", type=int, default=4500,
                        help="생성할 증강 이미지 수 (default: 4500)")
    parser.add_argument("--patch_min", type=float, default=0.25)
    parser.add_argument("--patch_max", type=float, default=0.60)
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


def random_bbox(img_w, img_h, ratio):
    cut_area = img_w * img_h * ratio
    cut_w = int(np.sqrt(cut_area * img_w / img_h))
    cut_h = int(np.sqrt(cut_area * img_h / img_w))
    cut_w = min(cut_w, img_w)
    cut_h = min(cut_h, img_h)
    cx = random.randint(0, img_w - cut_w)
    cy = random.randint(0, img_h - cut_h)
    return cx, cy, cx + cut_w, cy + cut_h


def cmo_cutmix(bg_img, fg_img, bbox):
    result = bg_img.copy()
    x1, y1, x2, y2 = bbox
    patch = fg_img.crop((x1, y1, x2, y2))
    result.paste(patch, (x1, y1))
    return result


def cm_code_from_dir(cm_dir):
    if cm_dir in ("Not Crash", "Not_Crash"):
        return "0"
    return cm_dir.replace("Collision Mode ", "").replace("Collision_Mode_", "")


def main():
    args = parse_args()
    tail_rts = args.tail
    head_rts = [rt for rt in ROAD_TYPES if rt not in tail_rts]

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

    print("[안내] 출력 폴더명 LK_CIR_MER_RAB_FOT는 07 학습 클래스 규약명입니다 — %s는 이미지 합성이며 시나리오 생성이 아닙니다." % "CMO")

    print(f"=== CMO Augmentation (Road Type) ===\n")

    # 1. 데이터 로드
    print("[1/3] 학습 데이터 로드...")
    rt_images = load_training_data_by_road_type(LABEL_CSV, CURRICULA_DIR)

    total = sum(len(v) for v in rt_images.values())
    print(f"  총 {total:,d}장, {len(rt_images)} 도로유형")
    print(f"\n  HEAD ({len(head_rts)} 유형):")
    for rt in head_rts:
        print(f"    {rt}: {len(rt_images.get(rt, [])):,d}")
    print(f"\n  TAIL ({len(tail_rts)} 유형):")
    for rt in tail_rts:
        print(f"    {rt}: {len(rt_images.get(rt, [])):,d}")

    head_pool = []
    for rt in head_rts:
        head_pool.extend(rt_images.get(rt, []))

    if not head_pool:
        print("  ERROR: head 이미지 풀이 비어 있습니다.")
        return

    # 2. CMO 증강
    print(f"\n[2/3] CMO 증강 ({args.n_aug:,d}장, tail={tail_rts})...")
    t0 = time.time()
    generated = 0
    class_gen_counts = defaultdict(int)

    aug_per_tail = args.n_aug // len(tail_rts)
    remainder = args.n_aug % len(tail_rts)

    global_idx = 0
    for t_idx, tail_rt in enumerate(tail_rts):
        n_this = aug_per_tail + (1 if t_idx < remainder else 0)
        tail_pool = rt_images.get(tail_rt, [])
        if not tail_pool:
            print(f"  WARNING: {tail_rt} 이미지 없음, 건너뜀")
            continue

        for j in range(n_this):
            global_idx += 1
            fg_entry = random.choice(tail_pool)
            bg_entry = random.choice(head_pool)

            try:
                fg_img = Image.open(fg_entry["path"]).convert("RGB")
                bg_img = Image.open(bg_entry["path"]).convert("RGB")

                if bg_img.size != fg_img.size:
                    bg_img = bg_img.resize(fg_img.size, Image.BILINEAR)

                ratio = random.uniform(args.patch_min, args.patch_max)
                bbox = random_bbox(fg_img.width, fg_img.height, ratio)
                mixed = cmo_cutmix(bg_img, fg_img, bbox)

                cm_code = cm_code_from_dir(fg_entry["cm_dir"])
                fname = f"Image_{cm_code}_CMO_{global_idx:05d}.png"

                mixed.save(os.path.join(sbev_out, fname))

                mode_dir_name = CM_CODE_TO_DIR.get(cm_code, "Not_Crash")
                mode_sub = os.path.join(mode_out, mode_dir_name)
                os.makedirs(mode_sub, exist_ok=True)
                mixed.save(os.path.join(mode_sub, fname))

                generated += 1
                class_gen_counts[tail_rt] += 1

            except Exception as e:
                print(f"  WARNING: {global_idx} — {e}")
                continue

            if global_idx % 500 == 0 or global_idx == args.n_aug:
                elapsed = time.time() - t0
                rate = global_idx / elapsed if elapsed > 0 else 1
                eta = (args.n_aug - global_idx) / rate
                print(f"  {global_idx:,d}/{args.n_aug:,d}  ({elapsed:.0f}s, ~{eta:.0f}s remaining)")

    # 3. 결과
    print(f"\n[3/3] 완료: {generated:,d}장 생성")
    print(f"  출력: {output_dir}")
    print(f"\n  도로유형별 분포:")
    for rt in sorted(class_gen_counts.keys()):
        print(f"    {rt}: {class_gen_counts[rt]}")

    print(f"\n=== 완료 ({time.time()-t0:.0f}s) ===")


if __name__ == "__main__":
    main()
