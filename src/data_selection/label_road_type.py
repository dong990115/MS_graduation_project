"""
도로 유형 라벨링 파이프라인
━━━━━━━━━━━━━━━━━━━━━━━━━━
Input:
  - NAS Curricula SBEV 47,470장 (ACLpp iter4 최종 학습셋)
  - RG3 도로유형 annotation CSV (frame-level)
Output:
  - training_road_type_label.csv  (per-SBEV 도로유형)
  - road_type_distribution.png           (분포 bar chart)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from utils.parse_sbev import (
    parse_sbev_filename,
    road_type_from_psm,
    load_rg3_annotations,
    road_type_from_rg3,
    drive_road_type_summary,
)

# ━━ Relative path anchors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MONOREPO_ROOT = os.path.dirname(_SCRIPT_DIR)

# ━━ Paths ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRICULA_DIR = (  # NAS (proprietary data)
    r"<PROJECT_NAS>\Collision Mode\Training\Result"
    r"\ACLpp_iter4_1_0s_051625_SIM3_spl10_wCB_mFtv2\Curricula"
)
RG3_CSV_DIR = os.path.join(
    MONOREPO_ROOT, '01_ClassificationOfFP', 'Data', 'input',
    'Check_road_geometry_annotation', 'Test_Data_110424',
)
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, 'Output', 'common')

ROAD_TYPE_ORDER = ['HW', 'INT', 'URB', 'RAB', 'Others']
ROAD_COLORS = {
    'HW': '#4C72B0', 'INT': '#55A868', 'URB': '#C44E52',
    'RAB': '#8172B3', 'Others': '#CCB974', 'Unknown': '#999999',
}


def scan_curricula(curricula_dir, rg3_lookup):
    """Scan all SBEV PNGs in Curricula and assign road types."""
    records = []
    for level_name in sorted(os.listdir(curricula_dir)):
        level_path = os.path.join(curricula_dir, level_name)
        if not os.path.isdir(level_path):
            continue
        for cm_dir_name in sorted(os.listdir(level_path)):
            cm_path = os.path.join(level_path, cm_dir_name)
            if not os.path.isdir(cm_path):
                continue
            for fname in os.listdir(cm_path):
                if not fname.lower().endswith('.png'):
                    continue

                cm, scenario, data_index, frame_index = parse_sbev_filename(fname)

                if scenario.startswith('RG3_'):
                    source = 'RG3'
                    road_type = road_type_from_rg3(
                        scenario, data_index, frame_index, rg3_lookup
                    )
                else:
                    source = 'PSM'
                    road_type = road_type_from_psm(scenario)

                records.append({
                    'filename': fname,
                    'level': level_name,
                    'collision_mode': cm,
                    'collision_mode_dir': cm_dir_name,
                    'scenario': scenario,
                    'data_index': data_index,
                    'frame_index': frame_index,
                    'road_type': road_type,
                    'source': source,
                })

        print(f'  {level_name}: {sum(1 for r in records if r["level"] == level_name)} files')

    df = pd.DataFrame(records)

    # Add drive-level road type columns for RG3
    df['drive_dominant_type'] = ''
    df['drive_all_types'] = ''
    df['drive_segments'] = ''

    rg3_mask = df['source'] == 'RG3'
    if rg3_mask.any():
        rg3_df = df.loc[rg3_mask]
        max_frames = rg3_df.groupby(['scenario', 'data_index'])['frame_index'].max()

        for (scen, didx), max_f in max_frames.items():
            mask = rg3_mask & (df['scenario'] == scen) & (df['data_index'] == didx)
            dom, all_types, detail = drive_road_type_summary(
                scen, didx, rg3_lookup, max_frame=max_f
            )
            df.loc[mask, 'drive_dominant_type'] = dom
            df.loc[mask, 'drive_all_types'] = all_types
            df.loc[mask, 'drive_segments'] = detail

    # PSM: single road type per scenario
    psm_mask = df['source'] == 'PSM'
    df.loc[psm_mask, 'drive_dominant_type'] = df.loc[psm_mask, 'road_type']
    df.loc[psm_mask, 'drive_all_types'] = df.loc[psm_mask, 'road_type']

    return df


def save_csv(df, path):
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  CSV → {path}')


def print_summary(df):
    total = len(df)
    road_counts = df['road_type'].value_counts()

    print(f'\n{"Road Type":>10s}  {"Count":>7s}  {"Pct":>6s}  {"CumPct":>6s}  H/T')
    print('-' * 48)
    cumulative = 0
    for rt in ROAD_TYPE_ORDER:
        if rt not in road_counts.index:
            continue
        cnt = road_counts[rt]
        cumulative += cnt
        pct = cnt / total * 100
        cum_pct = cumulative / total * 100
        ht = 'head' if cum_pct <= 90 else 'tail'
        print(f'{rt:>10s}  {cnt:7,d}  {pct:5.1f}%  {cum_pct:5.1f}%  {ht}')

    # Unknown (if any)
    for rt in road_counts.index:
        if rt not in ROAD_TYPE_ORDER:
            cnt = road_counts[rt]
            cumulative += cnt
            print(f'{rt:>10s}  {cnt:7,d}  {cnt/total*100:5.1f}%  {cumulative/total*100:5.1f}%  -')

    print('-' * 48)
    print(f'{"Total":>10s}  {total:7,d}\n')

    psm_n = (df['source'] == 'PSM').sum()
    rg3_n = (df['source'] == 'RG3').sum()
    print(f'  PSM (Simulation): {psm_n:,d}')
    print(f'  RG3 (Real Drive): {rg3_n:,d}\n')

    print('[Road Type × Source]')
    ct = pd.crosstab(df['road_type'], df['source'], margins=True)
    print(ct.to_string())
    print()


def plot_distribution(df, output_dir):
    road_counts = df['road_type'].value_counts()
    order = [r for r in ROAD_TYPE_ORDER if r in road_counts.index]
    for r in road_counts.index:
        if r not in order:
            order.append(r)

    total = len(df)
    counts = [road_counts[r] for r in order]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ── Left: overall bar chart with head/tail line ──
    ax = axes[0]
    colors = [ROAD_COLORS.get(r, '#999999') for r in order]
    bars = ax.bar(order, counts, color=colors, edgecolor='white', linewidth=0.5)

    cumulative = 0
    for i, (rt, cnt) in enumerate(zip(order, counts)):
        cumulative += cnt
        if cumulative / total > 0.90:
            ax.axvline(x=i - 0.5, color='red', ls='--', lw=1.5,
                       label=f'Head/Tail 90% boundary')
            break

    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + total * 0.005,
                f'{cnt:,}', ha='center', va='bottom', fontsize=13)

    max_count = max(counts)
    ax.set_ylim(0, max_count + 2500)
    ax.set_xlabel('Road Type', fontsize=13)
    ax.set_ylabel('SBEV Count', fontsize=13)
    ax.set_title('')
    ax.tick_params(labelsize=13)
    ax.legend(fontsize=13)

    # ── Right: stacked bar (PSM / RG3) ──
    ax2 = axes[1]
    psm_counts = df[df['source'] == 'PSM']['road_type'].value_counts()
    rg3_counts = df[df['source'] == 'RG3']['road_type'].value_counts()

    x = np.arange(len(order))
    psm_vals = [psm_counts.get(r, 0) for r in order]
    rg3_vals = [rg3_counts.get(r, 0) for r in order]

    ax2.bar(x, psm_vals, 0.6, label='PSM (Simulation)', color='#4C72B0')
    ax2.bar(x, rg3_vals, 0.6, bottom=psm_vals, label='RG3 (Real)', color='#C44E52')

    for i, (pv, rv) in enumerate(zip(psm_vals, rg3_vals)):
        if rv > 0:
            ax2.text(i, pv + rv + total * 0.005,
                     f'{pv+rv:,}\n(RG3:{rv})', ha='center', va='bottom', fontsize=13)
        else:
            ax2.text(i, pv + total * 0.005, f'{pv:,}', ha='center', va='bottom', fontsize=13)

    max_count2 = max(p + r for p, r in zip(psm_vals, rg3_vals))
    ax2.set_ylim(0, max_count2 + 2500)
    ax2.set_xticks(x)
    ax2.set_xticklabels(order, fontsize=13)
    ax2.set_xlabel('Road Type', fontsize=13)
    ax2.set_ylabel('SBEV Count', fontsize=13)
    ax2.set_title('')
    ax2.tick_params(labelsize=13)
    ax2.legend(fontsize=13)

    plt.tight_layout()
    plot_path = os.path.join(output_dir, 'road_type_distribution.png')
    fig.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Plot → {plot_path}')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_path = os.path.join(OUTPUT_DIR, 'training_road_type_label.csv')
    if os.path.exists(csv_path):
        print('=== Phase 0: pre-computed output exists, skipping ===')
        print(f'  {csv_path}')
        print('  Delete the file and re-run to regenerate from NAS + RG3 CSV.')
        return

    print('=== Phase 0: Road Type Labeling ===\n')

    if not os.path.isdir(RG3_CSV_DIR):
        print(f'ERROR: RG3 CSV dir not found: {RG3_CSV_DIR}')
        print('  Requires original data in 01_ClassificationOfFP/Data/')
        return

    if not os.path.isdir(CURRICULA_DIR):
        print(f'ERROR: NAS Curricula dir not accessible: {CURRICULA_DIR}')
        print('  Requires NAS (<DATA_NAS>) connection.')
        return

    print('[1/5] RG3 annotation CSV 로드...')
    rg3_lookup = load_rg3_annotations(RG3_CSV_DIR)
    print(f'  {len(rg3_lookup)} (date, dataIndex) pairs loaded\n')

    print('[2/5] Curricula SBEV 스캔 + 도로유형 매핑...')
    df = scan_curricula(CURRICULA_DIR, rg3_lookup)
    print(f'  Total: {len(df):,d} SBEV\n')

    print('[3/5] 분포 요약')
    print_summary(df)

    print('[4/5] CSV 저장...')
    save_csv(df, os.path.join(OUTPUT_DIR, 'training_road_type_label.csv'))
    print()

    print('[5/5] 분포 플롯...')
    plot_distribution(df, OUTPUT_DIR)

    print('\n=== 완료 ===')


if __name__ == '__main__':
    main()
