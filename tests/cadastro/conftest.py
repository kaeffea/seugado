"""Fixtures for tests."""

import os

import psycopg
import pytest


@pytest.fixture
def db_conn():
    """Database connection for tests."""
    url = os.environ.get("SEUGADO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("SEUGADO_TEST_DATABASE_URL not set; skipping live DB test")
    conn = psycopg.connect(url, autocommit=False)
    yield conn
    conn.rollback()
    conn.close()
