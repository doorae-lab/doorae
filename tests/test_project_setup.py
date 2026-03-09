# tests/test_project_setup.py
def test_project_structure():
    """프로젝트 기본 구조 확인"""
    import doorae

    assert hasattr(doorae, "__version__")
