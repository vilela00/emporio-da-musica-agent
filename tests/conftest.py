import pytest

from emporio.catalog import get_store


@pytest.fixture(scope="session")
def store():
    return get_store()
