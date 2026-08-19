import os
import shutil

import yaml
from .DotDict import DotDict


class Configuration:

    def __init__(self):
        self.load()

    pass

    @staticmethod
    def _module_root():
        """02_JunctionArt 모듈 루트 (이 파일 기준 3단계 상위: library/junctionart/<root>)."""
        return os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        )

    @classmethod
    def resolve_config_path(cls):
        """설정 파일 경로를 결정한다.

        1) 현재 작업 디렉터리의 config.yaml (사용자가 직접 둔 것 우선)
        2) 모듈 루트의 config.yaml
        3) 없으면 모듈 루트의 config-sample.yaml 을 config.yaml 로 복사해 사용
           (저장소를 받은 직후 별도 준비 없이 실행되도록 하기 위함)

        config.yaml 은 esminipath 같은 로컬 경로를 담아 git 에 추적하지 않으므로,
        clone/zip 직후에는 존재하지 않는 것이 정상이다.
        """
        cwd_config = os.path.abspath(os.path.join(os.getcwd(), 'config.yaml'))
        if os.path.isfile(cwd_config):
            return cwd_config

        root = cls._module_root()
        root_config = os.path.join(root, 'config.yaml')
        if os.path.isfile(root_config):
            return root_config

        sample = os.path.join(root, 'config-sample.yaml')
        if os.path.isfile(sample):
            shutil.copyfile(sample, root_config)
            print(f'[Configuration] config.yaml 이 없어 config-sample.yaml 로 생성했습니다: {root_config}\n'
                  f'                esmini 시각화를 쓰려면 esminipath 를 실제 설치 경로로 수정하세요.')
            return root_config

        raise FileNotFoundError(
            f'설정 파일을 찾을 수 없습니다.\n'
            f'  확인한 경로: {cwd_config}\n'
            f'              {root_config}\n'
            f'              {sample} (샘플)\n'
            f'config-sample.yaml 을 config.yaml 로 복사한 뒤 다시 실행하세요.'
        )

    def load(self):
        path = self.resolve_config_path()
        with open(path, 'r', encoding='utf-8') as stream:
            self.dic = DotDict(yaml.safe_load(stream))

    def get(self, key):

        return self.dic.dot_get(key)
        # raise KeyError(f"{key} not found in configuration")
