"""Create a source-only portfolio ZIP and hash manifest, excluding local credentials/data."""
import hashlib
import json
from pathlib import Path
import zipfile
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
ROOT_FILES = ['README.md', 'requirements.txt', 'manage.py', '.env.example', '.gitignore', '.dockerignore', 'Dockerfile', 'compose.yaml']
DIRECTORIES = ['config', 'risk', 'static', 'templates', 'docs', 'tools', '.github', 'evaluation']

def release_files():
    files = [ROOT / p for p in ROOT_FILES if (ROOT / p).is_file()]
    for directory in DIRECTORIES:
        for path in (ROOT / directory).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix in ['.pyc', '.sqlite3', '.log']:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith('evaluation/results'): continue
            files.append(path)
    return sorted(set(files))

def main():
    files = release_files()
    secrets = [v.encode() for k, v in dotenv_values(ROOT / '.env').items()
               if v and (k.endswith('_API_KEY') or k in ['WEBHOOK_SECRET', 'SECRET_KEY', 'DEMO_PASSWORD'])
               and len(v) >= 16]
    manifest = []
    for path in files:
        content = path.read_bytes()
        if any(secret in content for secret in secrets):
            raise RuntimeError('Credencial local encontrada no arquivo de publicação: ' + path.relative_to(ROOT).as_posix())
        manifest.append({'path': path.relative_to(ROOT).as_posix(), 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    destination = ROOT / 'artifacts'
    destination.mkdir(exist_ok=True)
    archive = destination / 'riskops-portfolio.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for path in files: output.write(path, 'riskops/' + path.relative_to(ROOT).as_posix())
    (destination / 'release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'files': len(files), 'bytes': archive.stat().st_size, 'credential_check': 'passed'}))

if __name__ == '__main__': main()
