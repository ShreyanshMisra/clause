"""Point persistence at a throwaway temp dir for the whole test session so
tests never touch the real data store."""
import tempfile
import pytest
import app.db as db


@pytest.fixture(scope="session", autouse=True)
def _temp_data_dir():
    tmp = tempfile.mkdtemp(prefix="clause-test-")
    db.init(tmp)
    yield
