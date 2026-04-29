"""Tests del repository pattern contra SQLite en memoria."""
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from app.db.models import ProcessingRecord
from app.db.repository import ProcessingRepository


@pytest.fixture
def repo(tmp_path):
    """Repository usando base de datos temporal."""
    db_file = tmp_path / "test.db"
    return ProcessingRepository(db_file)


def _make_record(**kwargs) -> ProcessingRecord:
    defaults = dict(
        video_path="/videos/test.mp4",
        video_name="test.mp4",
        output_dir="/output/test",
        status="completed",
        duration_seconds=120.0,
        language_detected="es",
        ai_provider="Groq",
        ai_model="llama-3.3-70b-versatile",
        transcription_confidence=0.92,
        created_at=datetime.now(),
    )
    defaults.update(kwargs)
    return ProcessingRecord(**defaults)


def test_insert_and_get_all(repo):
    r = _make_record()
    record_id = repo.insert(r)
    assert record_id is not None and record_id > 0

    records = repo.get_all()
    assert len(records) == 1
    assert records[0].video_name == "test.mp4"


def test_get_by_id(repo):
    r = _make_record(video_name="video_especial.mp4")
    record_id = repo.insert(r)

    found = repo.get_by_id(record_id)
    assert found is not None
    assert found.video_name == "video_especial.mp4"


def test_get_by_id_not_found(repo):
    result = repo.get_by_id(9999)
    assert result is None


def test_delete(repo):
    r = _make_record()
    record_id = repo.insert(r)
    assert len(repo.get_all()) == 1

    repo.delete(record_id)
    assert len(repo.get_all()) == 0


def test_update_status(repo):
    r = _make_record(status="completed")
    record_id = repo.insert(r)

    repo.update_status(record_id, "error", "Algo falló")
    updated = repo.get_by_id(record_id)
    assert updated.status == "error"
    assert updated.error_message == "Algo falló"


def test_multiple_inserts_limit(repo):
    for i in range(5):
        repo.insert(_make_record(video_name=f"video_{i}.mp4"))

    all_records = repo.get_all(limit=3)
    assert len(all_records) == 3


def test_delete_all(repo):
    for i in range(3):
        repo.insert(_make_record(video_name=f"video_{i}.mp4"))
    assert len(repo.get_all()) == 3

    repo.delete_all()
    assert len(repo.get_all()) == 0
