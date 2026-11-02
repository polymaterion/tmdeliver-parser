import json
import shutil
from datetime import datetime, timezone

import pytest

from app.filter.engine import FilterEngine

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def engine():
    return FilterEngine.from_dir("rules")


@pytest.fixture
def now():
    return NOW
