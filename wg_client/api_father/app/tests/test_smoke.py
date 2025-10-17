from fastapi.testclient import TestClient
import os
import importlib.util

_app_dir = os.path.dirname(os.path.dirname(__file__))
_main_py = os.path.join(_app_dir, "main.py")
_spec = importlib.util.spec_from_file_location("apifather_app_main", _main_py)
_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_mod)
app = getattr(_mod, "app")


def test_health():
    client = TestClient(app)
    r = client.get("/internal/health")
    assert r.status_code == 200


