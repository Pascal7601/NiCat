
"""Shared pytest fixtures for NiCat backend tests."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolate_throttle_cache():
    """
    Reset the test cache before and after each test.

    This prevents authentication throttling requests from
    affecting unrelated tests.

    Production rate limiting is not affected.
    """
    cache.clear()

    yield

    cache.clear()
