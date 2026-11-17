import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3

import pytest

from taxi.storage import Store


@pytest.fixture
def checkpoint_module():
    spec = importlib.util.spec_from_file_location(
        'checkpoint', Path(__file__).resolve().parents[2] / 'scripts/backup_checkpoint.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(os.name == 'nt', reason='Windows ACL integration requires native Windows validation')
def test_checkpoints_preserve_previous_copies_and_verify_receipts(checkpoint_module, tmp_path):
    source = tmp_path / 'source.sqlite3'
    store = Store(str(source))
    store.event('checkpoint-test', {'fixture': True})
    store.close()
    directory = tmp_path / 'backups'
    first = checkpoint_module.checkpoint(source, directory)
    first_bytes = first.read_bytes()
    second = checkpoint_module.checkpoint(source, directory)
    assert first != second and first.read_bytes() == first_bytes
    for backup in (first, second):
        receipt = json.loads(backup.with_suffix('.json').read_text())
        assert receipt['sha256'] == hashlib.sha256(backup.read_bytes()).hexdigest()
        assert receipt['bytes'] == backup.stat().st_size
        assert not receipt['off_machine_copy_verified'] and not receipt['restore_drill_completed']
        assert backup.stat().st_mode & 0o777 == 0o600
        with sqlite3.connect(backup) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert db.execute("SELECT count(*) FROM events WHERE kind='checkpoint-test'").fetchone()[0] == 1


@pytest.mark.skipif(os.name == 'nt', reason='POSIX directory-mode restriction')
def test_checkpoint_rejects_exposed_directory_without_writing(checkpoint_module, tmp_path):
    directory = tmp_path / 'public'
    directory.mkdir(mode=0o755)
    directory.chmod(0o755)
    with pytest.raises(ValueError, match='owner-only'):
        checkpoint_module.checkpoint(tmp_path / 'missing.sqlite3', directory)
    assert list(directory.iterdir()) == []


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows ACL validation')
def test_windows_acl_rejects_broad_read_access(checkpoint_module, tmp_path):
    import subprocess
    directory = tmp_path / 'private'
    directory.mkdir()
    environment = {**os.environ, 'TAXI_ACL_TEST_DIRECTORY': str(directory)}
    private_acl = r"""
$ErrorActionPreference = 'Stop'
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = [System.Security.AccessControl.DirectorySecurity]::new()
$acl.SetOwner($sid)
$acl.SetAccessRuleProtection($true, $false)
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $env:TAXI_ACL_TEST_DIRECTORY -AclObject $acl
"""
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', private_acl],
                   env=environment, check=True, capture_output=True)
    checkpoint_module.require_private_directory(directory)
    broad_acl = r"""
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:TAXI_ACL_TEST_DIRECTORY
$everyone = [System.Security.Principal.SecurityIdentifier]::new('S-1-1-0')
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new($everyone, 'Read', 'Allow')
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $env:TAXI_ACL_TEST_DIRECTORY -AclObject $acl
"""
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', broad_acl],
                   env=environment, check=True, capture_output=True)
    with pytest.raises(ValueError, match='ACL'):
        checkpoint_module.require_private_directory(directory)
