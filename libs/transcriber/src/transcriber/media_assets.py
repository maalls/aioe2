"""Generate browser-friendly media assets for transcription outputs."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aac", ".webm", ".mp4", ".ogg")


def generate_preview_assets(
    *,
    output_dir: Path,
    stem: str,
    input_audio_path: Path,
    srt_path: Path,
) -> dict:
    """Generate mp3 audio and black-background subtitle video assets.

    Returns a dict with generated file names. Missing entries mean generation failed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    assets: dict[str, str] = {}
    if not _has_ffmpeg():
        logger.warning("ffmpeg not found; skipping media asset generation")
        return assets

    if not input_audio_path.exists() or not srt_path.exists():
        logger.warning(
            "Missing media inputs for preview generation (audio=%s, srt=%s)",
            input_audio_path,
            srt_path,
        )
        return assets

    preview_audio = output_dir / f"{stem}.preview.mp3"
    preview_video = output_dir / f"{stem}.preview.mp4"
    preview_vtt = output_dir / f"{stem}.vtt"

    if _build_preview_audio(input_audio_path=input_audio_path, output_path=preview_audio):
        assets["preview_audio"] = preview_audio.name

    if _build_webvtt(srt_path=srt_path, output_path=preview_vtt):
        assets["preview_vtt"] = preview_vtt.name

    if _build_preview_video(
        input_audio_path=input_audio_path,
        srt_path=srt_path,
        output_path=preview_video,
    ):
        assets["preview_video"] = preview_video.name

    return assets


def find_audio_source_for_folder(output_dir: Path, stem: str) -> Path | None:
    """Find the most likely audio source to generate media preview assets."""
    preferred = output_dir / f"{stem}.wav"
    if preferred.exists():
        return preferred

    for ext in AUDIO_EXTENSIONS:
        candidate = output_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate

    for file in sorted(output_dir.iterdir()):
        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS:
            return file

    return None


def _build_preview_audio(*, input_audio_path: Path, output_path: Path) -> bool:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_audio_path),
        "-vn",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "3",
        str(output_path),
    ]
    return _run_ffmpeg(cmd, output_path)


def _build_preview_video(*, input_audio_path: Path, srt_path: Path, output_path: Path) -> bool:
    subtitles_arg = _escape_subtitles_path(srt_path)
    burn_in_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1280x720:r=30",
        "-i",
        str(input_audio_path),
        "-vf",
        f"subtitles={subtitles_arg}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        str(output_path),
    ]
    if _run_ffmpeg(burn_in_cmd, output_path):
        return True

    # Fallback when subtitles filter is unavailable: mux SRT as mov_text subtitle track.
    mux_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1280x720:r=30",
        "-i",
        str(input_audio_path),
        "-i",
        str(srt_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-map",
        "2:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=fra",
        "-shortest",
        str(output_path),
    ]
    return _run_ffmpeg(mux_cmd, output_path)


def _build_webvtt(*, srt_path: Path, output_path: Path) -> bool:
    try:
        srt_text = srt_path.read_text(encoding="utf-8")
    except OSError:
        return False

    lines = []
    for line in srt_text.splitlines():
        if "-->" in line:
            lines.append(line.replace(",", "."))
        else:
            lines.append(line)

    output_path.write_text("WEBVTT\n\n" + "\n".join(lines), encoding="utf-8")
    return output_path.exists()


def _escape_subtitles_path(path: Path) -> str:
    value = str(path.resolve())
    value = value.replace("\\", "\\\\")
    value = value.replace(":", "\\:")
    value = value.replace("'", "\\'")
    return value


def _run_ffmpeg(cmd: list[str], output_path: Path) -> bool:
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning("ffmpeg command failed: %s", exc)
        return False
    return output_path.exists()


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True
