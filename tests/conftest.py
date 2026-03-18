import pytest

from tests.dummy_config import DummyConfig


@pytest.fixture
def dummy_config():
    """Return a fresh DummyConfig instance for tests to customize."""
    return DummyConfig()
