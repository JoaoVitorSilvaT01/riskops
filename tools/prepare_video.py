"""Serve a fresh, synthetic-only database for a portfolio recording on port 8001."""
import os
from pathlib import Path
import subprocess
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
database = ROOT / 'artifacts' / 'video-demo.sqlite3'
database.parent.mkdir(exist_ok=True)
environment = {**os.environ, 'DATABASE_PATH': str(database), 'PYTHONUNBUFFERED': '1'}
for command in ['migrate', 'seed_demo']:
    subprocess.run([sys.executable, 'manage.py', command], cwd=ROOT, env=environment, check=True)
print('Demonstração isolada em http://127.0.0.1:8001 — somente dados sintéticos preparados pelo seed.', flush=True)
subprocess.run([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8001', '--noreload'], cwd=ROOT, env=environment, check=True)
