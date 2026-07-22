import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Point every test at an isolated SQLite file *before* any test module can
# import backend.database/backend.models (which happens as early as pytest's
# collection phase, e.g. `from backend.analytics.reporting import ...` at a
# test module's top level). Setting this here - in conftest.py, which pytest
# always imports first - means no test file needs importlib.reload() tricks
# to get a clean database, regardless of import order.
_TMP_DB_DIR = tempfile.mkdtemp(prefix="skillsphere_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB_DIR}/test_skillsphere.db"
