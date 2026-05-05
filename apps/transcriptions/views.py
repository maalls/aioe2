import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import generics

from .models import TranscriptionJob
from .serializers import TranscriptionJobCreateSerializer, TranscriptionJobDetailSerializer
from .tasks import run_transcription_task


class TranscriptionJobListCreateView(generics.ListCreateAPIView):
    queryset = TranscriptionJob.objects.select_related("project", "created_by").prefetch_related("result")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TranscriptionJobCreateSerializer
        return TranscriptionJobDetailSerializer

    def perform_create(self, serializer) -> None:
        user = self.request.user if self.request.user.is_authenticated else None
        job = serializer.save(created_by=user)
        run_transcription_task.delay(str(job.id))


class TranscriptionJobDetailView(generics.RetrieveAPIView):
    queryset = TranscriptionJob.objects.select_related("project", "created_by").prefetch_related("result")
    serializer_class = TranscriptionJobDetailSerializer


def transcription_browser(request):
    folders = _list_output_folders()
    selected_folder = request.GET.get("folder") or (folders[0]["name"] if folders else "")
    folder_data = _load_folder_data(selected_folder) if selected_folder else _empty_folder_data("")

    return render(
        request,
        "transcriptions/browser.html",
        {
            "folders": folders,
            "selected_folder": selected_folder,
            "folder_data": folder_data,
        },
    )


def transcription_preview(request):
    selected_folder = request.GET.get("folder", "")
    if not selected_folder:
        raise Http404("Missing folder")

    folder_data = _load_folder_data(selected_folder)
    return render(
        request,
        "transcriptions/_viewer_panel.html",
        {
            "selected_folder": selected_folder,
            "folder_data": folder_data,
        },
    )


def transcription_asset(request, folder: str, filename: str):
    folder_data = _load_folder_data(folder)
    allowed_files = {
        folder_data.get("txt_file", ""),
        folder_data.get("srt_file", ""),
        folder_data.get("preview_audio_file", ""),
        folder_data.get("preview_video_file", ""),
        folder_data.get("preview_vtt_file", ""),
    }

    if filename not in allowed_files:
        raise Http404("Unknown asset")

    asset_path = Path(settings.TRANSCRIPTION_OUTPUT_ROOT) / folder / filename
    if not asset_path.exists() or not asset_path.is_file():
        raise Http404("Asset not found")

    range_header = request.headers.get("Range")
    content_type, _ = mimetypes.guess_type(str(asset_path))
    if range_header:
        return _range_response(asset_path=asset_path, content_type=content_type, range_header=range_header)

    response = FileResponse(asset_path.open("rb"), content_type=content_type)
    response["Accept-Ranges"] = "bytes"
    return response


def _range_response(*, asset_path: Path, content_type: str | None, range_header: str) -> HttpResponse:
    file_size = asset_path.stat().st_size
    start, end = _parse_range_header(range_header=range_header, file_size=file_size)
    length = end - start + 1

    with asset_path.open("rb") as f:
        f.seek(start)
        data = f.read(length)

    response = HttpResponse(data, status=206, content_type=content_type)
    response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = str(length)
    return response


def _parse_range_header(*, range_header: str, file_size: int) -> tuple[int, int]:
    if not range_header.startswith("bytes="):
        raise Http404("Invalid range unit")

    range_value = range_header.split("=", 1)[1].strip()
    if "," in range_value:
        raise Http404("Multiple ranges are not supported")

    start_raw, end_raw = range_value.split("-", 1)
    try:
        if not start_raw:
            # bytes=-N -> last N bytes
            length = int(end_raw)
            start = max(file_size - length, 0)
            end = file_size - 1
            return start, end

        start = int(start_raw)
        end = int(end_raw) if end_raw else file_size - 1
    except ValueError as exc:
        raise Http404("Malformed range header") from exc

    if start >= file_size:
        raise Http404("Range start out of bounds")
    end = min(end, file_size - 1)
    if end < start:
        raise Http404("Invalid range interval")
    return start, end


def _list_output_folders() -> list[dict]:
    output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
    if not output_root.exists():
        return []

    folders = [
        {
            "name": folder.name,
            "modified_ts": folder.stat().st_mtime,
        }
        for folder in output_root.iterdir()
        if folder.is_dir()
    ]
    folders.sort(key=lambda item: item["modified_ts"], reverse=True)
    return folders


def _load_folder_data(folder_name: str) -> dict:
    output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
    available_folders = {item["name"] for item in _list_output_folders()}
    if folder_name not in available_folders:
        raise Http404("Unknown output folder")

    folder_path = output_root / folder_name
    json_files = sorted(
        [file for file in folder_path.glob("*.json") if file.name != "run_report.json"]
    )
    report_path = folder_path / "run_report.json"

    payload = {}
    if json_files:
        payload = _read_json(json_files[0])

    report = _read_json(report_path) if report_path.exists() else {}
    segments = payload.get("segments", [])
    # Add formatted timestamps to each segment
    for segment in segments:
        if "start" in segment:
            segment["start_pretty"] = _format_timestamp(segment["start"])
        if "end" in segment:
            segment["end_pretty"] = _format_timestamp(segment["end"])
    speaker_map = payload.get("speaker_map", {})

    txt_files = sorted(folder_path.glob("*.txt"))
    srt_files = sorted(folder_path.glob("*.srt"))
    preview_audio_files = sorted(folder_path.glob("*.preview.mp3"))
    preview_video_files = sorted(folder_path.glob("*.preview.mp4"))
    preview_vtt_files = sorted(folder_path.glob("*.vtt"))

    media_assets = report.get("media_assets", {}) if isinstance(report, dict) else {}

    preview_audio_file = media_assets.get("preview_audio") if isinstance(media_assets, dict) else ""
    preview_video_file = media_assets.get("preview_video") if isinstance(media_assets, dict) else ""
    preview_vtt_file = media_assets.get("preview_vtt") if isinstance(media_assets, dict) else ""

    if not preview_audio_file and preview_audio_files:
        preview_audio_file = preview_audio_files[0].name
    if not preview_video_file and preview_video_files:
        preview_video_file = preview_video_files[0].name
    if not preview_vtt_file and preview_vtt_files:
        preview_vtt_file = preview_vtt_files[0].name

    return {
        "folder_name": folder_name,
        "segments": segments,
        "speaker_map": speaker_map,
        "speakers_found": payload.get("speakers_found", 0),
        "audio_duration_s": payload.get("audio_duration_s", 0),
        "audio_duration_pretty": _pretty_duration(payload.get("audio_duration_s", 0)),
        "timings": report.get("timings", {}),
        "txt_file": txt_files[0].name if txt_files else "",
        "srt_file": srt_files[0].name if srt_files else "",
        "preview_audio_file": preview_audio_file,
        "preview_video_file": preview_video_file,
        "preview_vtt_file": preview_vtt_file,
        "segment_count": len(segments),
    }


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or H:MM:SS format."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def _pretty_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {sec:02d}s"
    if m:
        return f"{m}m {sec:02d}s"
    return f"{sec}s"


def _empty_folder_data(folder_name: str) -> dict:
    return {
        "folder_name": folder_name,
        "segments": [],
        "speaker_map": {},
        "speakers_found": 0,
        "audio_duration_s": 0,
        "audio_duration_pretty": "0s",
        "timings": {},
        "txt_file": "",
        "srt_file": "",
        "preview_audio_file": "",
        "preview_video_file": "",
        "preview_vtt_file": "",
        "segment_count": 0,
    }


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
