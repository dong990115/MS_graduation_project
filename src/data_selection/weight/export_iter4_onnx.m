%% export_iter4_onnx.m
% iter4 학습 결과 MAT에서 trained network를 ONNX로 export
%
% Input:  iter4 Training_Result MAT 파일
% Output: ./cp_cnn_iter4.onnx (이 스크립트와 같은 폴더)

%% 경로
weight_dir = fileparts(mfilename('fullpath'));
mat_path = fullfile(weight_dir, 'iter4', ...
    'Training_Result_CatalogRG3_LaneOnlyCP_Time-2025-05-16-01-15-54.mat');
onnx_path = fullfile(weight_dir, 'cp_cnn_iter4.onnx');

%% MAT 로드
fprintf('Loading: %s\n', mat_path);
S = load(mat_path);

%% network 찾기
net = [];
var_names = fieldnames(S);
fprintf('Variables in MAT: %s\n', strjoin(var_names, ', '));

for i = 1:length(var_names)
    v = S.(var_names{i});
    if isa(v, 'SeriesNetwork') || isa(v, 'DAGNetwork') || isa(v, 'dlnetwork')
        net = v;
        fprintf('Found network in variable: %s (%s)\n', var_names{i}, class(v));
        break;
    end
    if isstruct(v) && isfield(v, 'network')
        candidate = v.network;
        if isa(candidate, 'SeriesNetwork') || isa(candidate, 'DAGNetwork') || isa(candidate, 'dlnetwork')
            net = candidate;
            fprintf('Found network in %s.network (%s)\n', var_names{i}, class(net));
            break;
        end
    end
end

if isempty(net)
    fprintf('\n=== network 자동 탐색 실패 ===\n');
    fprintf('수동 확인: whos -file 결과:\n');
    whos('-file', mat_path);
    fprintf('\nMAT 파일을 직접 로드해서 network 변수를 찾아주세요.\n');
    return;
end

%% 아키텍처 확인
fprintf('\n=== Network Layers ===\n');
disp(net.Layers);

%% ONNX export
fprintf('\nExporting to: %s\n', onnx_path);
exportONNXNetwork(net, onnx_path);
fprintf('=== 완료 ===\n');
