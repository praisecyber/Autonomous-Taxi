"""Build a source-only Windows-PC handoff ZIP; never include private runtime data."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT_FILES = {'README.md', 'AGENTS.md', 'pyproject.toml', 'backend/api.py', '.gitignore', '.dockerignore', '.env.example'}
PREFIXES = ('backend/taxi/', 'backend/tests/', 'frontend/', 'scripts/', 'deploy/', 'docs/')
EXCLUDED_PARTS = {'__pycache__', 'node_modules', '.venv', 'runtime', 'vendor', 'firmware'}
EXCLUDED_SUFFIXES = {'.pyc', '.pth', '.pt', '.onnx', '.sqlite3', '.db', '.pem', '.key', '.env'}


def permitted(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or EXCLUDED_PARTS.intersection(path.parts):
        return False
    if path.name == '.env' or (path.name.startswith('.env.') and name != '.env.example'):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return name in ROOT_FILES or name.startswith(PREFIXES)


def build(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Package output exists; choose a new filename')
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    files = {}
    for name in sorted(filter(permitted, filter(None, names))):
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('Package entry must be a regular tracked file')
        files[name] = path.read_bytes()
    required = {'pyproject.toml', 'scripts/setup_pc_server.ps1', 'scripts/start_pc_server.py',
                'backend/taxi/api.py', 'frontend/public/index.html', 'deploy/Caddyfile.pc'}
    if not required.issubset(files):
        raise ValueError('Required PC deployment files are missing or untracked')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    manifest = {'revision': revision, 'scope': 'software source only; no private data or model weights',
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation; no existing package is overwritten.
    with output.open('xb') as target, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr('Autonomous-Taxi/' + name, data)
        archive.writestr('Autonomous-Taxi/PACKAGE-MANIFEST.json', json.dumps(manifest, indent=2))
    # Read the finished deliverable back and verify every member against its receipt.
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(archive.read('Autonomous-Taxi/' + name)).hexdigest() != expected:
                raise ValueError('Package member hash mismatch')
    return len(files), hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    count, digest = build(Path(__file__).resolve().parents[1], args.output)
    print(json.dumps({'files': count, 'sha256': digest, 'output': str(Path(args.output).resolve())}))
