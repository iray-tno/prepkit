"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for tests."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture(scope="session")
def test_data_root():
    """Root directory for all test data."""
    return Path(__file__).parent / "cpp_test_cases"


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "build: marks tests that require compilation tools"
    )
    config.addinivalue_line(
        "markers", "snapshot: marks tests that use snapshot comparison"
    )