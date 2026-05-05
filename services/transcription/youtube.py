"""YouTube audio download adapter for transcription pipeline."""

from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yt_dlp


def download_youtube_audio(youtube_url: str, output_dir: Path = Path("var/audio")) -> Path:
    """
    Download audio from a YouTube URL and save as MP4.
    
    Args:
        youtube_url: Full YouTube URL (e.g., https://youtube.com/watch?v=...)
        output_dir: Directory to save downloaded audio file
        
    Returns:
        Path to the downloaded audio file (MP4 format)
        
    Raises:
        ValueError: If URL is invalid or download fails
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract video ID for filename
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        video_id = "youtube_video"
    
    output_template = str(output_dir / f"{video_id}.%(ext)s")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_template,
        "quiet": False,
        "no_warnings": False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        # Find the downloaded file
        audio_file = output_dir / f"{video_id}.m4a"
        if audio_file.exists():
            return audio_file
        
        # Fallback: check for .mp4 if m4a conversion didn't happen
        mp4_file = output_dir / f"{video_id}.mp4"
        if mp4_file.exists():
            return mp4_file
        
        raise ValueError("Download completed but audio file not found")
    except Exception as e:
        raise ValueError(f"Failed to download YouTube audio: {str(e)}") from e


def _extract_video_id(youtube_url: str) -> str:
    """Extract video ID from YouTube URL."""
    parsed = urlparse(youtube_url)
    
    # Handle youtube.com and youtu.be URLs
    if parsed.hostname in ("youtube.com", "www.youtube.com"):
        query = parse_qs(parsed.query)
        return query.get("v", [""])[0]
    elif parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/")
    
    return ""
