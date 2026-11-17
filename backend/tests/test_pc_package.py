import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def package():
    spec = importlib.util.spec_from_file_location(
        'package', Path(__file__).resolve().parents[2] / 'scripts/build_pc_package.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', [
    'runtime/taxi.sqlite3', 'runtime/provisioning/private.json', '.env',
    'backend/taxi/__pycache__/api.pyc', 'backend/taxi/perception/model.pth',
    'backend/vendor/YOLOX/model.py', 'firmware/arduino/src/secrets.h',
    'deploy/private.key', 'backend/taxi/.env', '../outside.py', '/tmp/private.py',
])
def test_private_and_unneeded_files_are_excluded(package, name):
    assert not package.permitted(name)


def test_source_and_public_assets_are_included(package):
    for name in ['pyproject.toml', 'scripts/setup_pc_server.ps1', 'backend/taxi/api.py',
                 'frontend/public/shared.css', 'backend/taxi/docs_assets/LICENSE', 'backend/api.py']:
        assert package.permitted(name)
