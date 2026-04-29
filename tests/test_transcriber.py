"""Tests del módulo de transcripción (con mocks de whisper/torch)."""
import pytest
from unittest.mock import MagicMock, patch

from app.core.transcriber import Transcriber, TranscriptionResult, Segment, Word, ModelNotFoundError


def test_is_model_available_false():
    with patch("app.core.transcriber.is_model_available", return_value=False):
        t = Transcriber()
        assert t.is_model_available() is False


def test_is_model_available_true():
    with patch("app.core.transcriber.is_model_available", return_value=True):
        t = Transcriber()
        assert t.is_model_available() is True


def test_load_model_raises_when_not_available():
    with patch("app.core.transcriber.is_model_available", return_value=False):
        t = Transcriber()
        with pytest.raises(ModelNotFoundError):
            t.load_model()


def test_transcription_result_to_timestamped():
    words = [Word(0.0, 1.0, "hola", 0.9)]
    segs = [
        Segment(0, 0.0, 5.0, "Hola mundo", words),
        Segment(1, 3600.0, 3605.0, "Una hora después", []),
    ]
    tr = TranscriptionResult(
        full_text="Hola mundo",
        segments=segs,
        words=words,
        language_detected="es",
        duration_seconds=10.0,
    )
    text = tr.to_timestamped_text()
    assert "[00:00:00]" in text
    assert "[01:00:00]" in text


def test_get_word_confidence_avg_empty():
    tr = TranscriptionResult("", [], [], "es", 0.0)
    assert tr.get_word_confidence_avg() == 0.0


def test_get_key_timestamps_empty():
    tr = TranscriptionResult("", [], [], "es", 0.0)
    assert tr.get_key_timestamps() == []
