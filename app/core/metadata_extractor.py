"""Extracción de metadatos del video (delega a AudioExtractor)."""
from pathlib import Path

from app.core.audio_extractor import AudioExtractor, VideoInfo


def extract_metadata(video_path: Path, extractor: AudioExtractor) -> VideoInfo:
    """Extrae metadatos del video usando ffprobe."""
    return extractor.get_video_info(video_path)
