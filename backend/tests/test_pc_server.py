import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def launcher():
    path = Path(__file__).resolve().parents[2] / 'scripts/start_pc_server.py'
    spec = importlib.util.spec_from_file_location('pc_launcher', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('address', ['0.0.0.0', '127.0.0.1', '8.8.8.8', '::1', '224.0.0.1'])
def test_lan_listener_rejects_nonprivate_addresses(launcher, address):
    args = launcher.parser().parse_args(['--lan-address', address])
    with pytest.raises(ValueError, match='private IPv4'):
        launcher.configuration(args)


def test_pc_configuration_is_single_host_and_private_backend(launcher, tmp_path):
    (tmp_path / 'taxi.sqlite3').touch()
    caddy = tmp_path / 'caddy'
    caddy.touch()
    args = launcher.parser().parse_args([
        '--lan-address', '192.168.1.20', '--data-dir', str(tmp_path), '--caddy', str(caddy),
    ])
    env, _, _, hostname, bind = launcher.configuration(args)
    assert hostname == bind == env['TAXI_ALLOWED_HOSTS'] == '192.168.1.20'
    assert env['TAXI_API_UPSTREAM'] == '127.0.0.1:8000'
    assert env['TAXI_SECURE_COOKIES'] == '1' and env['TAXI_ALLOW_LEGACY_TOKEN'] == '0'
    args.lan_address = None
    env, _, _, hostname, bind = launcher.configuration(args)
    assert hostname == 'probix.localhost' and bind == '127.0.0.1'
    args.https_port = args.backend_port
    with pytest.raises(ValueError, match='different'):
        launcher.configuration(args)
