import json
import mimetypes
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import generics

from .edits import (
    append_edit_history,
    apply_edit_segment_text,
    apply_rename_speaker,
    apply_rename_subtopic,
    apply_rename_topic,
    build_edited_state,
    read_edited_state,
    write_edited_state,
)
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


@ensure_csrf_cookie
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


@ensure_csrf_cookie
def transcription_preview(request):
    selected_folder = request.GET.get("folder", "")
    if not selected_folder:
        raise Http404("Missing folder")

    folders = _list_output_folders()
    folder_data = _load_folder_data(selected_folder)
    response = render(
        request,
        "transcriptions/_viewer_panel.html",
        {
            "folders": folders,
            "selected_folder": selected_folder,
            "folder_data": folder_data,
        },
    )
    query = urlencode({"folder": selected_folder})
    response["HX-Push-Url"] = f"{reverse('transcription-browser')}?{query}"
    return response


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


@require_POST
def transcription_bookmark_toggle(request, folder: str):
    output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
    available_folders = {item["name"] for item in _list_output_folders()}
    if folder not in available_folders:
        raise Http404("Unknown output folder")

    folder_path = output_root / folder
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload"}, status=400)

    segment_key = str(payload.get("segment_key", "")).strip()
    if not segment_key:
        return JsonResponse({"ok": False, "error": "Missing segment_key"}, status=400)

    bookmarked = bool(payload.get("bookmarked", False))
    bookmarks = _read_segment_bookmarks(folder_path)
    if bookmarked:
        bookmarks.add(segment_key)
    else:
        bookmarks.discard(segment_key)

    _write_segment_bookmarks(folder_path, bookmarks)
    return JsonResponse({"ok": True, "segment_key": segment_key, "bookmarked": bookmarked})


@require_POST
def transcription_edit_segment_text(request, folder: str, segment_key: str):
    folder_path = _resolve_folder_path(folder)
    payload = _read_request_json(request)

    text = str(payload.get("text", "")).strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Missing text"}, status=400)

    state = _load_or_init_edited_state(folder_path)
    try:
        updated = apply_edit_segment_text(state, segment_key, text)
    except KeyError:
        return JsonResponse({"ok": False, "error": "Unknown segment_key"}, status=404)

    write_edited_state(folder_path, updated)
    append_edit_history(
        folder_path,
        {
            "id": f"op_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "type": "edit_segment_text",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "before": {"segment_key": segment_key},
            "after": {"segment_key": segment_key, "text": text},
        },
    )
    return JsonResponse({"ok": True})


@require_POST
def transcription_edit_speaker_rename(request, folder: str, speaker_id: str):
    folder_path = _resolve_folder_path(folder)
    payload = _read_request_json(request)

    label = str(payload.get("label", "")).strip()
    if not label:
        return JsonResponse({"ok": False, "error": "Missing label"}, status=400)

    state = _load_or_init_edited_state(folder_path)
    try:
        updated = apply_rename_speaker(state, speaker_id, label)
    except KeyError:
        return JsonResponse({"ok": False, "error": "Unknown speaker_id"}, status=404)

    write_edited_state(folder_path, updated)
    append_edit_history(
        folder_path,
        {
            "id": f"op_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "type": "rename_speaker",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "before": {"speaker_id": speaker_id},
            "after": {"speaker_id": speaker_id, "label": label},
        },
    )
    return JsonResponse({"ok": True})


@require_POST
def transcription_edit_topic_rename(request, folder: str, topic_id: int):
    folder_path = _resolve_folder_path(folder)
    payload = _read_request_json(request)

    title = str(payload.get("title", "")).strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Missing title"}, status=400)

    state = _load_or_init_edited_state(folder_path)
    try:
        updated = apply_rename_topic(state, topic_id, title)
    except IndexError:
        return JsonResponse({"ok": False, "error": "Unknown topic_id"}, status=404)

    write_edited_state(folder_path, updated)
    append_edit_history(
        folder_path,
        {
            "id": f"op_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "type": "rename_topic",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "before": {"topic_id": topic_id},
            "after": {"topic_id": topic_id, "title": title},
        },
    )
    return JsonResponse({"ok": True})


@require_POST
def transcription_edit_subtopic_rename(request, folder: str, subtopic_id: str):
    folder_path = _resolve_folder_path(folder)
    payload = _read_request_json(request)

    title = str(payload.get("title", "")).strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Missing title"}, status=400)

    try:
        topic_raw, subtopic_raw = subtopic_id.split(".", 1)
        topic_index = int(topic_raw)
        subtopic_index = int(subtopic_raw)
    except (ValueError, AttributeError):
        return JsonResponse({"ok": False, "error": "Invalid subtopic_id"}, status=400)

    state = _load_or_init_edited_state(folder_path)
    try:
        updated = apply_rename_subtopic(state, topic_index, subtopic_index, title)
    except IndexError:
        return JsonResponse({"ok": False, "error": "Unknown subtopic_id"}, status=404)

    write_edited_state(folder_path, updated)
    append_edit_history(
        folder_path,
        {
            "id": f"op_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "type": "rename_subtopic",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "before": {"subtopic_id": subtopic_id},
            "after": {"subtopic_id": subtopic_id, "title": title},
        },
    )
    return JsonResponse({"ok": True})


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
    report_path = folder_path / "run_report.json"

    # Ensure edited.json exists and use it as the single source of truth for segments/speakers.
    payload = _load_or_init_edited_state(folder_path)
    timeline_path, timeline_data = _load_timeline_report(folder_path)
    bookmarked_keys = _read_segment_bookmarks(folder_path)

    report = _read_json(report_path) if report_path.exists() else {}
    segments = payload.get("segments", [])
    # Add formatted timestamps to each segment
    for segment in segments:
        segment_key = _segment_key(segment)
        segment["segment_key"] = segment_key
        segment["is_bookmarked"] = segment_key in bookmarked_keys
        if "start" in segment:
            segment["start_pretty"] = _format_timestamp(segment["start"])
        if "end" in segment:
            segment["end_pretty"] = _format_timestamp(segment["end"])
    speaker_map = payload.get("speaker_map", {})
    for segment in segments:
        speaker_id = segment.get("speaker", "")
        segment["speaker_label"] = speaker_map.get(speaker_id, speaker_id)

    timeline_groups = _build_timeline_groups(segments, timeline_data)

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
        "timeline_file": timeline_path.name if timeline_path else "",
        "timeline_groups": timeline_groups,
        "txt_file": txt_files[0].name if txt_files else "",
        "srt_file": srt_files[0].name if srt_files else "",
        "preview_audio_file": preview_audio_file,
        "preview_video_file": preview_video_file,
        "preview_vtt_file": preview_vtt_file,
        "segment_count": len(segments),
    }


def _load_timeline_report(folder_path: Path) -> tuple[Path | None, dict]:
    candidates = [
        folder_path / "edited.json",
        *sorted(folder_path.glob("*.timeline.deep.json")),
        *sorted(folder_path.glob("*.timeline.json")),
    ]
    for path in candidates:
        data = _read_json(path)
        if isinstance(data, dict) and isinstance(data.get("chapters"), list):
            return path, data
    return None, {}


def _build_timeline_groups(segments: list[dict], timeline_data: dict) -> list[dict]:
    chapters = timeline_data.get("chapters") if isinstance(timeline_data, dict) else None
    if not isinstance(chapters, list) or not chapters:
        return []

    groups: list[dict] = []
    assigned_to_topic_ids: set[int] = set()
    for index, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            continue

        chapter_start = float(chapter.get("start", 0.0) or 0.0)
        chapter_end = float(chapter.get("end", chapter_start) or chapter_start)
        if chapter_end <= chapter_start:
            continue

        chapter_segments = [
            segment
            for segment in segments
            if _overlap(
                float(segment.get("start", 0.0) or 0.0),
                float(segment.get("end", 0.0) or 0.0),
                chapter_start,
                chapter_end,
            )
        ]
        for segment in chapter_segments:
            assigned_to_topic_ids.add(id(segment))

        analysis = chapter.get("analysis") if isinstance(chapter.get("analysis"), dict) else {}
        raw_sub_topics = analysis.get("sub_topics") if isinstance(analysis, dict) else []
        sub_topics: list[dict] = []
        assigned_ids: set[int] = set()

        for sub_index, sub_topic in enumerate(raw_sub_topics or [], start=1):
            if not isinstance(sub_topic, dict):
                continue

            rel_start = float(sub_topic.get("start", 0.0) or 0.0)
            rel_end = float(sub_topic.get("end", rel_start) or rel_start)
            if rel_end <= rel_start:
                continue

            # Accept either absolute timestamps or chapter-relative timestamps.
            chapter_duration = chapter_end - chapter_start
            if rel_end <= chapter_duration + 1.0:
                sub_start = chapter_start + rel_start
                sub_end = chapter_start + rel_end
            else:
                sub_start = rel_start
                sub_end = rel_end

            if sub_end <= sub_start:
                continue

            sub_segments = [
                segment
                for segment in chapter_segments
                if _overlap(
                    float(segment.get("start", 0.0) or 0.0),
                    float(segment.get("end", 0.0) or 0.0),
                    sub_start,
                    sub_end,
                )
            ]
            for segment in sub_segments:
                assigned_ids.add(id(segment))

            sub_topics.append(
                {
                    "index": sub_index,
                    "title": str(sub_topic.get("title", "Sous-topic")).strip() or "Sous-topic",
                    "summary": str(sub_topic.get("summary", "")).strip(),
                    "start": sub_start,
                    "end": sub_end,
                    "range_pretty": f"{_format_timestamp(sub_start)} - {_format_timestamp(sub_end)}",
                    "segments": sub_segments,
                }
            )

        other_segments = [segment for segment in chapter_segments if id(segment) not in assigned_ids]

        if sub_topics and other_segments:
            sub_topics.sort(key=lambda item: item["start"])
            for segment in other_segments:
                seg_start = float(segment.get("start", 0.0) or 0.0)
                seg_end = float(segment.get("end", seg_start) or seg_start)
                seg_mid = (seg_start + seg_end) / 2.0

                target_sub_topic = sub_topics[0]
                for sub_topic in sub_topics:
                    if seg_mid >= sub_topic["start"]:
                        target_sub_topic = sub_topic
                    else:
                        break

                segment["out_of_topic"] = True
                target_sub_topic["segments"].append(segment)

            other_segments = []

        for sub_topic in sub_topics:
            sub_topic["segments"].sort(key=lambda item: float(item.get("start", 0.0) or 0.0))
        other_segments.sort(key=lambda item: float(item.get("start", 0.0) or 0.0))

        groups.append(
            {
                "index": index,
                "title": str(chapter.get("title", "Topic")).strip() or "Topic",
                "summary": str(chapter.get("summary", "")).strip(),
                "start": chapter_start,
                "end": chapter_end,
                "range_pretty": f"{_format_timestamp(chapter_start)} - {_format_timestamp(chapter_end)}",
                "sub_topics": sub_topics,
                "other_segments": other_segments,
                "segment_count": len(chapter_segments),
            }
        )

    # Ensure no segment is lost in grouped display.
    # Any segment outside all topic ranges is appended to the chronologically current topic.
    if groups:
        for segment in segments:
            if id(segment) in assigned_to_topic_ids:
                continue

            seg_start = float(segment.get("start", 0.0) or 0.0)
            target_group = groups[0]
            for group in groups:
                if seg_start >= group["start"]:
                    target_group = group
                else:
                    break

            segment["out_of_topic"] = True
            target_group["other_segments"].append(segment)
            target_group["segment_count"] += 1

    for segment in segments:
        if "out_of_topic" not in segment:
            segment["out_of_topic"] = False

    return groups


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    return end_a > start_b and start_a < end_b


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
        "timeline_file": "",
        "timeline_groups": [],
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


def _segment_key(segment: dict) -> str:
    raw = "|".join(
        [
            str(segment.get("start", "")),
            str(segment.get("end", "")),
            str(segment.get("speaker", "")),
            str(segment.get("text", "")),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _bookmarks_file_path(folder_path: Path) -> Path:
    return folder_path / "segment_bookmarks.json"


def _read_segment_bookmarks(folder_path: Path) -> set[str]:
    path = _bookmarks_file_path(folder_path)
    data = _read_json(path)
    if not isinstance(data, dict):
        return set()
    values = data.get("bookmarked_segment_keys")
    if not isinstance(values, list):
        return set()
    return {str(item).strip() for item in values if str(item).strip()}


def _write_segment_bookmarks(folder_path: Path, bookmarks: set[str]) -> None:
    path = _bookmarks_file_path(folder_path)
    payload = {"bookmarked_segment_keys": sorted(bookmarks)}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _resolve_folder_path(folder: str) -> Path:
    output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
    available_folders = {item["name"] for item in _list_output_folders()}
    if folder not in available_folders:
        raise Http404("Unknown output folder")
    return output_root / folder


def _read_request_json(request) -> dict:
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_source_payload(folder_path: Path) -> dict:
    json_files = sorted(
        [
            file
            for file in folder_path.glob("*.json")
            if file.name not in {"run_report.json", "edited.json", "segment_edits_history.json"}
            and ".timeline" not in file.name
            and "_bookmarks" not in file.name
        ]
    )
    return _read_json(json_files[0]) if json_files else {}


def _load_or_init_edited_state(folder_path: Path) -> dict:
    existing = read_edited_state(folder_path)
    if existing is not None:
        return existing

    segments_payload = _load_source_payload(folder_path)
    _, timeline_data = _load_timeline_report(folder_path)
    state = build_edited_state(segments_payload, timeline_data)
    write_edited_state(folder_path, state)
    return state
