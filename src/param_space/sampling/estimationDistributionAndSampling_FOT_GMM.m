% estimationDistributionAndSampling_FOT_GMM — 수정본 (GMM 실사용 샘플링)
% 논문 데이터 생성에는 사용되지 않은 참고 구현이다.
%  - 논문(출판본 2.5절)·커밋된 param_space CSV = 관측 경험분포의 행 단위 복원추출.
%  - 본 수정본 = joint GMM을 적합해 random(gm,·)으로 실제 샘플링하는 교정판 (감사 N2의 (a)안).
%  - 출력 파일명에 _GMM 접미사를 붙여 논문 데이터(원본 CSV)를 덮어쓰지 않는다.

%% ============================================================
% estimationDistributionAndSampling_FOT.m
%
% FOT RAB 시나리오 SPD 파라미터 스페이스 생성
%   - LK_CIR_MER_RAB:      3D GMM [v_ego, v_target, a_target], v_ego > v_target
%   - drivingAlone_RVL_RAB: 2D GMM [v_ego, v_target],          v_ego < v_target
%
% Input:
%   data/processed/ScenarioParameters/distribution_RAB.csv
%     (analyze_scenario_distribution.py 출력, 프레임별 데이터)
%
% Output:
%   data/processed/SPD/SPS/<tag>_FOT_SPD_SPS.csv
%   data/processed/SPD/ParamSpace/<tag>_FOT_param_space.csv
% ============================================================
clear; clc; close all;

%% ============================================================
% 0) Project root & I/O paths
%% ============================================================
ROOT = local_project_root();
addpath(genpath(fullfile(ROOT)));

IN_CSV = fullfile(ROOT, 'data', 'processed', 'ScenarioParameters', 'distribution_RAB.csv');
if ~isfile(IN_CSV)
    error('Missing input: %s', IN_CSV);
end

OUT_SPS_DIR = fullfile(ROOT, 'data', 'processed', 'SPD', 'SPS');
if ~exist(OUT_SPS_DIR, 'dir'), mkdir(OUT_SPS_DIR); end

OUT_PARAMSPACE_DIR = fullfile(ROOT, 'data', 'processed', 'SPD', 'ParamSpace');
if ~exist(OUT_PARAMSPACE_DIR, 'dir'), mkdir(OUT_PARAMSPACE_DIR); end

%% ---------------- USER CONFIG ----------------
% entry → scenario mapping
ENTRY_MAP = containers.Map();
ENTRY_MAP('LK_CIR_MER_RAB')      = [0, 1];
ENTRY_MAP('drivingAlone_RVL_RAB') = [2];

% SPD config
bins_3d          = [30 30 30];
bins_2d          = [30 30];
export_rows      = 1000;
K_RANGE_GMM      = 1:5;
V_TARGET_MIN_KMH = 10.0;

% stability
MIN_ROWS_FOR_SPD = 20;
TOPUP_FACTOR     = 3;

rng(42);

%% ============================================================
% 1) Load CSV + scenario mapping
%% ============================================================
T = readtable(IN_CSV);
fprintf('Loaded %d rows from %s\n', height(T), IN_CSV);

% column name mapping
if ismember('v_ego_kmh', T.Properties.VariableNames)
    T.v_ego = T.v_ego_kmh;
end
if ismember('v_target_kmh', T.Properties.VariableNames)
    T.v_target = T.v_target_kmh;
end
if ismember('a_target_ms2', T.Properties.VariableNames)
    T.a_target = T.a_target_ms2;
end

tags = keys(ENTRY_MAP);
Variation = (1:export_rows).';

%% ============================================================
% 2) SPD generation per scenario
%% ============================================================
for t = 1:numel(tags)
    tag = tags{t};
    entry_indices = ENTRY_MAP(tag);

    rows = ismember(T.entry_index, entry_indices);
    Ts = T(rows, :);

    fprintf('\n=== %s (entries %s) : %d rows ===\n', tag, mat2str(entry_indices), height(Ts));

    if height(Ts) < MIN_ROWS_FOR_SPD
        fprintf('  Insufficient rows (N=%d < %d) → replicate mode\n', height(Ts), MIN_ROWS_FOR_SPD);
        replicate_rows(Ts, tag, export_rows, Variation, OUT_SPS_DIR, OUT_PARAMSPACE_DIR);
        continue;
    end

    switch tag
        case 'LK_CIR_MER_RAB'
            generate_spd_3d(Ts, tag, export_rows, bins_3d, K_RANGE_GMM, ...
                V_TARGET_MIN_KMH, true, TOPUP_FACTOR, MIN_ROWS_FOR_SPD, ...
                Variation, OUT_SPS_DIR, OUT_PARAMSPACE_DIR);

        case 'drivingAlone_RVL_RAB'
            generate_spd_2d(Ts, tag, export_rows, bins_2d, K_RANGE_GMM, ...
                V_TARGET_MIN_KMH, TOPUP_FACTOR, MIN_ROWS_FOR_SPD, ...
                Variation, OUT_SPS_DIR, OUT_PARAMSPACE_DIR);
    end
end

fprintf('\n[DONE] SPD generation completed.\n');
fprintf('  SPS dir:        %s\n', OUT_SPS_DIR);
fprintf('  ParamSpace dir: %s\n', OUT_PARAMSPACE_DIR);

%% ============================================================
% Replicate mode: 데이터 부족 시 단일(또는 소수) 행 복제
%% ============================================================
function replicate_rows(Ts, tag, export_rows, Variation, OUT_SPS_DIR, OUT_PARAMSPACE_DIR)
    param_cols = intersect({'v_ego','v_target','a_target', ...
                            'v_ego_kmh','v_target_kmh','a_target_ms2'}, ...
                           Ts.Properties.VariableNames, 'stable');

    % column name 통일
    if ismember('v_ego_kmh', Ts.Properties.VariableNames)
        Ts.v_ego = Ts.v_ego_kmh;
    end
    if ismember('v_target_kmh', Ts.Properties.VariableNames)
        Ts.v_target = Ts.v_target_kmh;
    end
    if ismember('a_target_ms2', Ts.Properties.VariableNames)
        Ts.a_target = Ts.a_target_ms2;
    end

    is_3d = strcmp(tag, 'LK_CIR_MER_RAB');
    N_src = height(Ts);

    % 복제 인덱스: 소스 행을 순환 반복
    rep_idx = mod((0:export_rows-1)', N_src) + 1;

    v_ego    = Ts.v_ego(rep_idx);
    v_target = Ts.v_target(rep_idx);

    if is_3d
        a_target = Ts.a_target(rep_idx);
        SPS = table(Variation, v_ego, v_target, a_target, ...
            'VariableNames', {'Variation','v_ego','v_target','a_target'});
    else
        SPS = table(Variation, v_ego, v_target, ...
            'VariableNames', {'Variation','v_ego','v_target'});
    end

    sps_csv = fullfile(OUT_SPS_DIR, [tag '_FOT_SPD_SPS_GMM.csv']);
    writetable(SPS, sps_csv);

    ps_csv = fullfile(OUT_PARAMSPACE_DIR, [tag '_FOT_param_space_GMM.csv']);
    writetable(SPS, ps_csv);

    fprintf('  Replicated %d source rows → %d rows\n', N_src, export_rows);
    fprintf('  SPS saved:        %s\n', sps_csv);
    fprintf('  ParamSpace saved: %s\n', ps_csv);
end

%% ============================================================
% LK_CIR_MER_RAB: 3D GMM [v_ego, v_target, a_target]
%% ============================================================
function generate_spd_3d(Ts, tag, export_rows, bins, K_RANGE, ...
    v_target_min, enforce_ego_gt, TOPUP_FACTOR, MIN_ROWS, ...
    Variation, OUT_SPS_DIR, OUT_PARAMSPACE_DIR)

    Xs = [Ts.v_ego, Ts.v_target, Ts.a_target];
    Xs = Xs(all(isfinite(Xs), 2), :);

    % v_target >= threshold
    Xs = Xs(Xs(:,2) >= v_target_min, :);

    % v_ego > v_target
    if enforce_ego_gt
        Xs = Xs(Xs(:,1) > Xs(:,2), :);
    end

    if size(Xs,1) < MIN_ROWS
        fprintf('  SKIP: insufficient rows after filter (N=%d)\n', size(Xs,1));
        return;
    end
    fprintf('  Data after filter: %d rows\n', size(Xs,1));

    % [수정본] joint 3-D GMM 적합 + 직접 샘플링 (감사 N2 (a)안)
    gm = fitGMM_multi(Xs, K_RANGE);
    fprintf('  3D GMM fitted (K=%d)\n', gm.NumComponents);
    X_final = random(gm, export_rows);
    % 시나리오 제약 재적용 + 부족분 GMM 재샘플
    X_final = X_final(X_final(:,2) >= v_target_min, :);
    if enforce_ego_gt, X_final = X_final(X_final(:,1) > X_final(:,2), :); end
    it = 0;
    while size(X_final,1) < export_rows && it < 50
        Xm = random(gm, max((export_rows - size(X_final,1))*TOPUP_FACTOR, 50));
        Xm = Xm(Xm(:,2) >= v_target_min, :);
        if enforce_ego_gt, Xm = Xm(Xm(:,1) > Xm(:,2), :); end
        X_final = [X_final; Xm]; it = it + 1; %#ok<AGROW>
    end
    X_final = X_final(1:export_rows, :);

    if size(X_final,1) < export_rows
        remain = export_rows - size(X_final,1);
        X_final = [X_final; X_final(randsample(size(X_final,1), remain, true), :)];
    end
    X_final = X_final(1:export_rows,:);

    v_ego    = X_final(:,1);
    v_target = X_final(:,2);
    a_target = X_final(:,3);

    % SPS
    SPS = table(Variation, v_ego, v_target, a_target, ...
        'VariableNames', {'Variation','v_ego','v_target','a_target'});
    sps_csv = fullfile(OUT_SPS_DIR, [tag '_FOT_SPD_SPS_GMM.csv']);
    writetable(SPS, sps_csv);

    % ParamSpace
    ParamSpace = table(Variation, v_ego, v_target, a_target, ...
        'VariableNames', {'Variation','v_ego','v_target','a_target'});
    ps_csv = fullfile(OUT_PARAMSPACE_DIR, [tag '_FOT_param_space_GMM.csv']);
    writetable(ParamSpace, ps_csv);

    fprintf('  SPS saved:        %s (%d rows)\n', sps_csv, export_rows);
    fprintf('  ParamSpace saved: %s (%d rows)\n', ps_csv, export_rows);
end

%% ============================================================
% drivingAlone_RVL_RAB: 2D GMM [v_ego, v_target]
%% ============================================================
function generate_spd_2d(Ts, tag, export_rows, bins, K_RANGE, ...
    v_target_min, TOPUP_FACTOR, MIN_ROWS, ...
    Variation, OUT_SPS_DIR, OUT_PARAMSPACE_DIR)

    Xs = [Ts.v_ego, Ts.v_target];
    Xs = Xs(all(isfinite(Xs), 2), :);

    % v_target >= threshold
    Xs = Xs(Xs(:,2) >= v_target_min, :);

    % v_ego < v_target (타겟이 뒤에서 접근, 더 빠름)
    Xs = Xs(Xs(:,1) < Xs(:,2), :);

    if size(Xs,1) < MIN_ROWS
        fprintf('  SKIP: insufficient rows after filter (N=%d)\n', size(Xs,1));
        return;
    end
    fprintf('  Data after filter: %d rows\n', size(Xs,1));

    % [수정본] joint 2-D GMM 적합 + 직접 샘플링
    gm = fitGMM_multi(Xs, K_RANGE);
    X_final = random(gm, export_rows);
    X_final = X_final(X_final(:,2) >= v_target_min & X_final(:,1) < X_final(:,2), :);
    it = 0;
    while size(X_final,1) < export_rows && it < 50
        Xm = random(gm, max((export_rows - size(X_final,1))*TOPUP_FACTOR, 50));
        Xm = Xm(Xm(:,2) >= v_target_min & Xm(:,1) < Xm(:,2), :);
        X_final = [X_final; Xm]; it = it + 1; %#ok<AGROW>
    end
    X_final = X_final(1:export_rows, :);

    if size(X_final,1) < export_rows
        remain = export_rows - size(X_final,1);
        X_final = [X_final; X_final(randsample(size(X_final,1), remain, true), :)];
    end
    X_final = X_final(1:export_rows,:);

    v_ego    = X_final(:,1);
    v_target = X_final(:,2);

    % SPS
    SPS = table(Variation, v_ego, v_target, ...
        'VariableNames', {'Variation','v_ego','v_target'});
    sps_csv = fullfile(OUT_SPS_DIR, [tag '_FOT_SPD_SPS_GMM.csv']);
    writetable(SPS, sps_csv);

    % ParamSpace
    ParamSpace = table(Variation, v_ego, v_target, ...
        'VariableNames', {'Variation','v_ego','v_target'});
    ps_csv = fullfile(OUT_PARAMSPACE_DIR, [tag '_FOT_param_space_GMM.csv']);
    writetable(ParamSpace, ps_csv);

    fprintf('  SPS saved:        %s (%d rows)\n', sps_csv, export_rows);
    fprintf('  ParamSpace saved: %s (%d rows)\n', ps_csv, export_rows);
end

%% ============================================================
% GMM fitting (N-dimensional, BIC selection)
%% ============================================================
function gm = fitGMM_multi(X, kRange)
    opts = statset('MaxIter', 2000, 'Display', 'off');
    bestBIC = inf; bestGM = [];
    for k = kRange
        try
            gm_k = fitgmdist(X, k, 'Options', opts, ...
                'RegularizationValue', 1e-6, 'Replicates', 5);
            if gm_k.BIC < bestBIC
                bestBIC = gm_k.BIC;
                bestGM = gm_k;
            end
        catch
        end
    end
    if isempty(bestGM)
        error('GMM fitting failed for %dD data.', size(X,2));
    end
    gm = bestGM;
end

%% ============================================================
% 3D helper functions (원본 유지)
%% ============================================================
function P = probgrid3(X, edges)
    C = count3d(X, edges);
    P = C / (sum(C(:)) + eps);
end

function C = count3d(X, edges)
    [i,j,k,valid] = bin_idx_3d(X, edges);
    i=i(valid); j=j(valid); k=k(valid);
    C = accumarray([i j k], 1, ...
        [numel(edges{1})-1, numel(edges{2})-1, numel(edges{3})-1], @sum, 0);
end

function [i,j,k,valid] = bin_idx_3d(X, edges)
    i = discretize(X(:,1), edges{1});
    j = discretize(X(:,2), edges{2});
    k = discretize(X(:,3), edges{3});
    valid = ~isnan(i) & ~isnan(j) & ~isnan(k);
end

function Xf = gap_fill_3d(Xs, gm, edges, P_ref)
    N = size(Xs,1);
    count_s = count3d(Xs, edges);
    P_ref = P_ref / (sum(P_ref(:)) + eps);
    target_count = P_ref * N;
    deficit = max(target_count - count_s, 0);
    need = round(sum(deficit(:)));
    if need <= 0, Xf = Xs; return; end

    X_new = random(gm, need);
    [i,j,k,valid] = bin_idx_3d(X_new, edges);
    X_new = X_new(valid,:); i=i(valid); j=j(valid); k=k(valid);
    lin = sub2ind(size(deficit), i, j, k);
    keep = false(size(X_new,1),1);
    [linS, ord] = sort(lin);
    ptr = 1;
    while ptr <= numel(linS)
        linv = linS(ptr); ptr2 = ptr;
        while ptr2 <= numel(linS) && linS(ptr2)==linv, ptr2 = ptr2+1; end
        cnt = ptr2 - ptr;
        [ii,jj,kk] = ind2sub(size(deficit), linv);
        take = min(cnt, floor(deficit(ii,jj,kk)));
        if take > 0
            keep(ord(ptr:ptr+take-1)) = true;
            deficit(ii,jj,kk) = deficit(ii,jj,kk) - take;
        end
        ptr = ptr2;
    end
    Xf = [Xs; X_new(keep,:)];
end

function X_final = resample_3d(X_pool, edges, P_ref, N)
    count_pool = count3d(X_pool, edges);
    P_ref = P_ref / (sum(P_ref(:)) + eps);
    target_count = P_ref * N;
    count_pool(count_pool < 1) = 1;
    wb = target_count ./ count_pool;
    wb = wb / (sum(wb(:)) + eps);
    [i,j,k,valid] = bin_idx_3d(X_pool, edges);
    W = zeros(size(X_pool,1),1);
    lin = sub2ind(size(wb), i(valid), j(valid), k(valid));
    W(valid) = wb(lin);
    W = W / (sum(W) + eps);
    idx = randsample(size(X_pool,1), N, true, W);
    X_final = X_pool(idx,:);
end

%% ============================================================
% 2D helper functions (신규)
%% ============================================================
function P = probgrid2(X, edges)
    C = count2d(X, edges);
    P = C / (sum(C(:)) + eps);
end

function C = count2d(X, edges)
    [i,j,valid] = bin_idx_2d(X, edges);
    i=i(valid); j=j(valid);
    C = accumarray([i j], 1, ...
        [numel(edges{1})-1, numel(edges{2})-1], @sum, 0);
end

function [i,j,valid] = bin_idx_2d(X, edges)
    i = discretize(X(:,1), edges{1});
    j = discretize(X(:,2), edges{2});
    valid = ~isnan(i) & ~isnan(j);
end

function Xf = gap_fill_2d(Xs, gm, edges, P_ref)
    N = size(Xs,1);
    count_s = count2d(Xs, edges);
    P_ref = P_ref / (sum(P_ref(:)) + eps);
    target_count = P_ref * N;
    deficit = max(target_count - count_s, 0);
    need = round(sum(deficit(:)));
    if need <= 0, Xf = Xs; return; end

    X_new = random(gm, need);
    [i,j,valid] = bin_idx_2d(X_new, edges);
    X_new = X_new(valid,:); i=i(valid); j=j(valid);
    lin = sub2ind(size(deficit), i, j);
    keep = false(size(X_new,1),1);
    [linS, ord] = sort(lin);
    ptr = 1;
    while ptr <= numel(linS)
        linv = linS(ptr); ptr2 = ptr;
        while ptr2 <= numel(linS) && linS(ptr2)==linv, ptr2 = ptr2+1; end
        cnt = ptr2 - ptr;
        [ii,jj] = ind2sub(size(deficit), linv);
        take = min(cnt, floor(deficit(ii,jj)));
        if take > 0
            keep(ord(ptr:ptr+take-1)) = true;
            deficit(ii,jj) = deficit(ii,jj) - take;
        end
        ptr = ptr2;
    end
    Xf = [Xs; X_new(keep,:)];
end

function X_final = resample_2d(X_pool, edges, P_ref, N)
    count_pool = count2d(X_pool, edges);
    P_ref = P_ref / (sum(P_ref(:)) + eps);
    target_count = P_ref * N;
    count_pool(count_pool < 1) = 1;
    wb = target_count ./ count_pool;
    wb = wb / (sum(wb(:)) + eps);
    [i,j,valid] = bin_idx_2d(X_pool, edges);
    W = zeros(size(X_pool,1),1);
    lin = sub2ind(size(wb), i(valid), j(valid));
    W(valid) = wb(lin);
    W = W / (sum(W) + eps);
    idx = randsample(size(X_pool,1), N, true, W);
    X_final = X_pool(idx,:);
end

%% ============================================================
% Project root resolver
%% ============================================================
function ROOT = local_project_root()
    thisFile = mfilename("fullpath");
    thisDir  = fileparts(thisFile);
    cand = fileparts(thisDir);
    if exist(fullfile(cand, "data"), "dir")
        ROOT = cand;
        return;
    end
    d = thisDir;
    for k = 1:8
        d = fileparts(d);
        if isempty(d), break; end
        if exist(fullfile(d, "data"), "dir")
            ROOT = d;
            return;
        end
    end
    error("프로젝트 루트 탐지 실패: data/ 폴더를 포함하는 상위 경로가 필요함.");
end
