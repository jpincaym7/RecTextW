"""Extracción profesional de audio con FFmpeg para Whisper."""
import json
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import AUDIO_CODEC, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS
from app.utils.ffmpeg_check import find_ffmpeg, find_ffprobe, validate_ffmpeg
from app.utils.logger import get_logger
from app.utils.subprocess_helper import run_hidden, popen_hidden

logger = get_logger()


class FFmpegNotFoundError(Exception):
    pass


class AudioExtractionError(Exception):
    pass


@dataclass
class VideoInfo:
    duration_seconds: float
    width: int
    height: int
    fps: float
    codec_video: str
    codec_audio: str
    sample_rate_original: int
    has_audio: bool
    file_size_bytes: int


class AudioExtractor:
    """Extrae el stream de audio de un video y lo convierte al formato óptimo para Whisper."""

    def __init__(self, ffmpeg_path: Path | None = None) -> None:
        self._ffmpeg = ffmpeg_path or find_ffmpeg()
        self._ffprobe = find_ffprobe()
        if self._ffmpeg is None:
            raise FFmpegNotFoundError(
                "FFmpeg no encontrado. Instale FFmpeg y verifique que esté en el PATH "
                "o en el directorio de la aplicación."
            )
        if not validate_ffmpeg(self._ffmpeg):
            raise FFmpegNotFoundError(f"FFmpeg en {self._ffmpeg} no es válido.")
        logger.debug("AudioExtractor inicializado con FFmpeg: %s", self._ffmpeg)

    def validate_ffmpeg(self) -> bool:
        """Verifica que FFmpeg es accesible."""
        return self._ffmpeg is not None and validate_ffmpeg(self._ffmpeg)

    def get_video_info(self, video_path: Path) -> VideoInfo:
        """Extrae metadatos del video usando ffprobe."""
        if self._ffprobe is None:
            raise FFmpegNotFoundError("ffprobe no encontrado.")

        cmd = [
            str(self._ffprobe),
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(video_path),
        ]
        try:
            result = run_hidden(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
        except Exception as exc:
            raise AudioExtractionError(f"Error obteniendo metadatos del video: {exc}") from exc

        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        fps = 0.0
        fps_str = video_stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 0.0

        duration = float(fmt.get("duration", 0) or video_stream.get("duration", 0) or 0)

        return VideoInfo(
            duration_seconds=duration,
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            fps=fps,
            codec_video=video_stream.get("codec_name", ""),
            codec_audio=audio_stream.get("codec_name", "") if audio_stream else "",
            sample_rate_original=int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
            has_audio=audio_stream is not None,
            file_size_bytes=int(fmt.get("size", 0)),
        )

    def extract_audio(
        self,
        video_path: Path,
        output_path: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Extrae y convierte el audio al formato óptimo para Whisper."""
        info = self.get_video_info(video_path)
        if not info.has_audio:
            raise AudioExtractionError(f"El video '{video_path.name}' no contiene stream de audio.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self._ffmpeg),
            "-y",
            "-i", str(video_path),
            "-vn",
            "-ar", str(AUDIO_SAMPLE_RATE),
            "-ac", str(AUDIO_CHANNELS),
            "-c:a", AUDIO_CODEC,
            str(output_path),
        ]

        try:
            process = popen_hidden(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self._monitor_progress(process, info.duration_seconds, progress_callback)
            process.wait()
            if process.returncode != 0:
                raise AudioExtractionError(
                    f"FFmpeg falló con código {process.returncode} al procesar '{video_path.name}'."
                )
            logger.info("Audio extraído exitosamente: %s", output_path)
            return output_path
        except AudioExtractionError:
            raise
        except Exception as exc:
            raise AudioExtractionError(f"Error inesperado durante extracción: {exc}") from exc
        finally:
            if output_path.exists() and output_path.stat().st_size == 0:
                output_path.unlink(missing_ok=True)

    def _monitor_progress(
        self,
        process: subprocess.Popen,
        total_duration: float,
        progress_callback: Callable[[float], None] | None,
    ) -> None:
        """Lee stderr de FFmpeg en tiempo real para calcular progreso."""
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
        for line in process.stderr:
            match = time_pattern.search(line)
            if match and total_duration > 0 and progress_callback:
                h, m, s, cs = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                elapsed = h * 3600 + m * 60 + s + cs / 100
                progress = min(elapsed / total_duration, 1.0)
                progress_callback(progress)
