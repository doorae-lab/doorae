"""안건(Agenda) 관련 유틸리티"""
import yaml


def load_agendas(yaml_path: str) -> list[dict]:
    """YAML 파일에서 안건 목록 로드"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if data is None:
        return []
    return data.get('agendas', [])
