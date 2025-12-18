"""
Pytest configuration for Playwright tests.

This file provides fixtures and configuration for running automated tests.
"""

import pytest
import os


def pytest_addoption(parser):
    """Add custom command line options (only those not provided by pytest-playwright)."""
    parser.addoption(
        "--test-username",
        action="store",
        default="admin1",
        help="Username for login",
    )
    parser.addoption(
        "--test-password",
        action="store",
        default="123456",
        help="Password for login",
    )


@pytest.fixture(scope="session")
def test_credentials(request):
    """Get test credentials from command line or environment."""
    return {
        "username": request.config.getoption("--test-username") or os.getenv("TEST_USERNAME", "admin"),
        "password": request.config.getoption("--test-password") or os.getenv("TEST_PASSWORD", "admin"),
    }


def pytest_configure(config):
    """Configure pytest."""
    # Create screenshots directory
    os.makedirs("tests/screenshots", exist_ok=True)
