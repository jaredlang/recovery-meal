import sys
from pathlib import Path

# Ensure the backend package root is importable when running pytest from the repo root.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
