from pathlib import Path

from fastapi.testclient import TestClient

from taxi.render_service import create_render_app
from taxi.manage import create_admin


def test_render_same_origin_frontend_and_api(tmp_path, monkeypatch):
    for key, value in {
        'RENDER_EXTERNAL_HOSTNAME': 'probix-test.onrender.com',
        'TAXI_ALLOWED_HOSTS': 'probix-test.onrender.com',
        'TAXI_DEPLOYMENT': 'production',
        'TAXI_SECURE_COOKIES': '1',
        'TAXI_ALLOW_LEGACY_TOKEN': '0',
        'TAXI_MODE': 'simulation',
        'TAXI_DATA_DIR': str(tmp_path),
        'TAXI_FRONTEND_ROOT': str(Path('frontend/public').resolve()),
    }.items():
        monkeypatch.setenv(key, value)
    create_admin(tmp_path / 'taxi.sqlite3', 'testadmin', 'test-only-password-123')
    with TestClient(create_render_app(), base_url='https://probix-test.onrender.com') as client:
        for page in ('/', '/operator', '/passenger', '/admin', '/account', '/diagnostics'):
            assert client.get(page).status_code == 200
            assert client.get(page, params={'filename': '../../pyproject.toml'}).text == client.get(page).text
        assert client.get('/static/shared.css').status_code == 200
        assert client.get('/api/health').json()['ok']
        assert client.get('/backend/taxi/auth.py').status_code == 404
        assert client.get('/api/health', headers={'Host': 'evil.example'}).status_code == 400
        assert client.get('http://probix-test.onrender.com/account').status_code == 403
