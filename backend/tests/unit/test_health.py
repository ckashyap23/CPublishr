from src.main import app


def test_health_route_exists() -> None:
    assert app is not None
