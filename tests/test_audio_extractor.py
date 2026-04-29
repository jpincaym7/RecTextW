"""Tests del extractor de audio con mocks de FFmpeg."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.audio_extractor import AudioExtractor, AudioExtractionError, FFmpegNotFoundError, VideoInfo


@pytest.fixture
def extractor():
    with patch("app.core.audio_extractor.find_ffmpeg", return_value=Path("ffmpeg")), \
         patch("app.core.audio_extractor.find_ffprobe", return_value=Path("ffprobe")), \
         patch("app.core.audio_extractor.validate_ffmpeg", return_value=True):
        return AudioExtractor()


def test_extractor_creates_with_valid_ffmpeg(extractor):
    assert extractor is not None


def test_extractor_raises_ffmpeg_not_found():
    with patch("app.core.audio_extractor.find_ffmpeg", return_value=None):
        with pytest.raises(FFmpegNotFoundError):
            AudioExtractor()


def _mock_ffprobe_output() -> str:
    return json.dumps({
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "120.0",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "44100",
            },
        ],
        "format": {
            "duration": "120.0",
            "size": "50000000",
        },
    })


def test_get_video_info(extractor, tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = _mock_ffprobe_output()

    with patch("subprocess.run", return_value=mock_result):
        info = extractor.get_video_info(tmp_path / "test.mp4")

    assert info.duration_seconds == 120.0
    assert info.width == 1920
    assert info.height == 1080
    assert info.has_audio is True
    assert info.codec_video == "h264"


def test_extract_audio_no_audio_stream(extractor, tmp_path):
    no_audio = json.dumps({
        "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720, "r_frame_rate": "30/1"}],
        "format": {"duration": "60.0", "size": "10000000"},
    })
    mock_result = MagicMock()
    mock_result.stdout = no_audio

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(AudioExtractionError, match="no contiene stream de audio"):
            extractor.extract_audio(tmp_path / "video.mp4", tmp_path / "audio.wav")
