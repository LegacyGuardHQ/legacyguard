import os
import sys
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault(
    "JWT_SECRET",
    "legacyguard-test-jwt-secret-at-least-32-bytes",
)

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
