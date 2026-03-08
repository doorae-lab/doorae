# tests/test_project_setup.py

def test_project_structure() -> None:
    """Core package imports stay available for both names."""
    import doorae
    import thetable

    assert hasattr(doorae, "__version__")
    assert hasattr(thetable, "__version__")
    assert doorae.__version__ == thetable.__version__
    assert doorae.PROJECT_ROOT == thetable.PROJECT_ROOT
