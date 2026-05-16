import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
SCRIPTS = ROOT / 'scripts'

for p in (str(ARTIFACTS), str(SCRIPTS), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
