"""Tests for the database persistence layer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Patch get_db_path before importing db module
_temp_dir = tempfile.mkdtemp()


@pytest.fixture(autouse=True)
def patch_db_path(monkeypatch):
    """Use a temporary directory for the database during tests."""
    def mock_get_db_path() -> Path:
        return Path(_temp_dir) / "test_runs.db"

    monkeypatch.setattr("ssr_service.db.get_db_path", mock_get_db_path)
    # Reset the module-level state so init_db uses the new path
    import ssr_service.db as db_module
    db_module._engine = None
    db_module._Session = None
    yield
    # Cleanup: remove the test database
    test_db = Path(_temp_dir) / "test_runs.db"
    if test_db.exists():
        test_db.unlink()


def test_save_and_get_run():
    from ssr_service.db import get_run, init_db, save_run

    init_db()

    request_data = {"concept": {"title": "Test Product"}}
    response_data = {"aggregate": {"mean": 3.5}}

    run_id = save_run(
        request_data=request_data,
        response_data=response_data,
        label="Test Run",
    )

    assert run_id is not None
    assert len(run_id) == 36  # UUID format

    result = get_run(run_id)
    assert result is not None
    assert result["id"] == run_id
    assert result["label"] == "Test Run"
    assert result["request"]["concept"]["title"] == "Test Product"
    assert result["response"]["aggregate"]["mean"] == 3.5


def test_list_runs():
    from ssr_service.db import init_db, list_runs, save_run

    init_db()

    # Save a few runs
    for i in range(3):
        save_run(
            request_data={"index": i},
            response_data={"index": i},
            label=f"Run {i}",
        )

    runs = list_runs(limit=10)
    assert len(runs) >= 3
    # Check they are ordered by created_at desc (most recent first)
    labels = [r["label"] for r in runs[:3]]
    assert "Run 2" in labels


def test_delete_run():
    from ssr_service.db import delete_run, get_run, init_db, save_run

    init_db()

    run_id = save_run(
        request_data={"test": True},
        response_data={"test": True},
    )

    assert get_run(run_id) is not None

    deleted = delete_run(run_id)
    assert deleted is True

    assert get_run(run_id) is None

    # Deleting again should return False
    deleted_again = delete_run(run_id)
    assert deleted_again is False


def test_get_run_not_found():
    from ssr_service.db import get_run, init_db

    init_db()

    result = get_run("nonexistent-uuid")
    assert result is None
