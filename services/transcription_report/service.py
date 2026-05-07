import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from infrastructure.llm.openai_compatible_client import OpenAICompatibleClient

from .schemas import ChapterAnalysis, Decision, MeetingTimelineReport, QAPair, SubTopic, TimelineChapter


class TranscriptionTimelineService:
    def __init__(
        self,
        llm_client: OpenAICompatibleClient,
        max_prompt_chars: int = 70000,
        max_chapter_prompt_chars: int = 20000,
    ):
        self.llm_client = llm_client
        self.max_prompt_chars = max_prompt_chars
        self.max_chapter_prompt_chars = max_chapter_prompt_chars

    def run(self, input_json_path: Path, output_json_path: Path | None = None) -> MeetingTimelineReport:
        """Generate a chapter-level timeline (topics only, no deep-dive).

        Output: <stem>.timeline.json
        """
        source_path = Path(input_json_path)
        report, _ = self._build_report(source_path)

        destination = output_json_path or source_path.with_name(f"{source_path.stem}.timeline.json")
        Path(destination).write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return report

    def run_deep(self, input_json_path: Path, output_json_path: Path | None = None) -> MeetingTimelineReport:
        """Generate a full deep-dive report: chapters + per-chapter sub-topics, Q&A, decisions.

        Output: <stem>.timeline.deep.json
        """
        source_path = Path(input_json_path)
        report, context = self._build_report(source_path)

        segments = context["segments"]
        speaker_map = context["speaker_map"]

        for chapter in report.chapters:
            chapter_segments = _segments_in_window(segments, chapter.start, chapter.end)
            if chapter_segments:
                chapter.analysis = self._analyse_chapter(chapter, chapter_segments, speaker_map)

        destination = output_json_path or source_path.with_name(f"{source_path.stem}.timeline.deep.json")
        Path(destination).write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return report

    def _build_report(
        self, source_path: Path
    ) -> tuple[MeetingTimelineReport, dict[str, Any]]:
        """Core logic: load JSON, call LLM for chapters, return report + raw context."""
        payload = json.loads(source_path.read_text(encoding="utf-8"))

        segments = payload.get("segments") or []
        if not segments:
            raise ValueError("Input transcription JSON has no segments")

        audio_duration_s = float(payload.get("audio_duration_s", 0.0) or 0.0)
        speaker_map: dict[str, str] = payload.get("speaker_map") or {}
        transcript_for_prompt = _render_segments_for_prompt(segments, self.max_prompt_chars, speaker_map=speaker_map)

        system_prompt = (
            "You are a meeting analyst. "
            "Your job is to segment a meeting timeline into major chapters. "
            "Return only valid JSON."
        )
        user_prompt = (
            "Given this diarized transcript, split the meeting into major topics. "
            "Keep topics count between 4 and 12 when possible. "
            "Use concise topic titles.\n\n"
            "Return JSON with this exact schema:\n"
            "{\n"
            "  \"chapters\": [\n"
            "    {\"title\": \"string\", \"start\": 0.0, \"end\": 10.0, \"summary\": \"string\"}\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- start and end are seconds (float)\n"
            "- topics must be ordered, non-overlapping\n"
            "- start of first topic should be near meeting start\n"
            "- end of last topic should be near meeting end\n"
            "- title in French\n"
            "- summary in French, one short sentence\n\n"
            f"Approximate meeting duration (s): {audio_duration_s:.2f}\n\n"
            "Transcript:\n"
            f"{transcript_for_prompt}"
        )

        llm_data = self.llm_client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        raw_chapters = llm_data.get("chapters")
        if not isinstance(raw_chapters, list):
            raise RuntimeError("LLM response is missing chapters list")

        chapters, warnings = _normalize_chapters(raw_chapters, segments, audio_duration_s)

        report = MeetingTimelineReport(
            source_json=str(source_path),
            generated_at=datetime.now(timezone.utc).isoformat(),
            chapter_count=len(chapters),
            chapters=chapters,
            warnings=warnings,
        )
        return report, {"segments": segments, "speaker_map": speaker_map}

    def _analyse_chapter(
        self,
        chapter: TimelineChapter,
        segments: list[dict[str, Any]],
        speaker_map: dict[str, str],
    ) -> ChapterAnalysis:
        transcript = _render_segments_for_prompt(segments, self.max_chapter_prompt_chars, speaker_map=speaker_map)

        system_prompt = (
            "You are a meeting analyst. Analyse a section of a meeting transcript. "
            "Return only valid JSON."
        )
        user_prompt = (
            f"Chapter: \"{chapter.title}\"\n"
            f"Duration: {_fmt_time(chapter.start)} – {_fmt_time(chapter.end)}\n\n"
            "Analyse this chapter and return JSON with this exact schema:\n"
            "{\n"
            "  \"sub_topics\": [\n"
            "    {\"title\": \"string\", \"summary\": \"string\", \"start\": 0.0, \"end\": 0.0}\n"
            "  ],\n"
            "  \"qa_pairs\": [\n"
            "    {\"question\": \"string\", \"answer\": \"string\", \"questioner\": \"string\", \"answerer\": \"string\"}\n"
            "  ],\n"
            "  \"decisions\": [\n"
            "    {\"decision\": \"string\", \"owner\": \"string\"}\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- sub_topics: major threads discussed in this chapter (1–5 items)\n"
            "- qa_pairs: explicit questions raised and their answers (may be empty)\n"
            "- decisions: concrete decisions or commitments made (may be empty)\n"
            "- All text in French\n"
            "- owner/answerer/questioner should be speaker names when identifiable, else empty string\n\n"
            "Transcript:\n"
            f"{transcript}"
        )

        try:
            data = self.llm_client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        except RuntimeError:
            return ChapterAnalysis()

        return _parse_chapter_analysis(data)


# ── helpers ───────────────────────────────────────────────────────────────────

def _render_segments_for_prompt(
    segments: list[dict[str, Any]],
    max_chars: int,
    speaker_map: dict[str, str] | None = None,
) -> str:
    lines: list[str] = []
    total = 0
    for seg in segments:
        start = float(seg.get("start", 0.0) or 0.0)
        end = float(seg.get("end", start) or start)
        raw_speaker = str(seg.get("speaker", "SPEAKER"))
        speaker = (speaker_map or {}).get(raw_speaker, raw_speaker)
        text = str(seg.get("text", "")).replace("\n", " ").strip()
        line = f"[{start:.1f}-{end:.1f}] {speaker}: {text}"

        if total + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total += len(line) + 1

    return "\n".join(lines)


def _segments_in_window(
    segments: list[dict[str, Any]], start: float, end: float
) -> list[dict[str, Any]]:
    return [
        s for s in segments
        if float(s.get("end", 0.0) or 0.0) > start and float(s.get("start", 0.0) or 0.0) < end
    ]


def _parse_chapter_analysis(data: dict[str, Any]) -> ChapterAnalysis:
    sub_topics: list[SubTopic] = []
    for item in data.get("sub_topics") or []:
        if not isinstance(item, dict):
            continue
        try:
            sub_topics.append(SubTopic(
                title=str(item.get("title", "")).strip() or "Sous-topic",
                summary=str(item.get("summary", "")).strip(),
                start=float(item.get("start", 0.0) or 0.0),
                end=float(item.get("end", 0.0) or 0.0),
            ))
        except Exception:  # noqa: BLE001
            continue

    qa_pairs: list[QAPair] = []
    for item in data.get("qa_pairs") or []:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        if q and a:
            qa_pairs.append(QAPair(
                question=q,
                answer=a,
                questioner=str(item.get("questioner", "")).strip(),
                answerer=str(item.get("answerer", "")).strip(),
            ))

    decisions: list[Decision] = []
    for item in data.get("decisions") or []:
        if not isinstance(item, dict):
            continue
        d = str(item.get("decision", "")).strip()
        if d:
            decisions.append(Decision(
                decision=d,
                owner=str(item.get("owner", "")).strip(),
            ))

    return ChapterAnalysis(sub_topics=sub_topics, qa_pairs=qa_pairs, decisions=decisions)


def _normalize_chapters(
    raw_chapters: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    audio_duration_s: float,
) -> tuple[list[TimelineChapter], list[str]]:
    warnings: list[str] = []
    normalized: list[TimelineChapter] = []

    for item in raw_chapters:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip() or "Chapitre"
        summary = str(item.get("summary", "")).strip()

        try:
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start))
        except (TypeError, ValueError):
            continue

        if end <= start:
            continue
        normalized.append(TimelineChapter(title=title, start=max(0.0, start), end=max(0.0, end), summary=summary))

    normalized.sort(key=lambda c: c.start)

    if not normalized:
        first_start = float(segments[0].get("start", 0.0) or 0.0)
        last_end = float(segments[-1].get("end", first_start) or first_start)
        warnings.append("No valid chapter from LLM; fallback to single chapter")
        return (
            [TimelineChapter(
                title="Reunion complete",
                start=first_start,
                end=max(last_end, first_start + 1.0),
                summary="Vue d'ensemble de la reunion.",
            )],
            warnings,
        )

    for idx in range(1, len(normalized)):
        prev = normalized[idx - 1]
        cur = normalized[idx]
        if cur.start < prev.end:
            cur.start = prev.end
            if cur.end <= cur.start:
                cur.end = cur.start + 1.0
                warnings.append(f"Chapter overlap adjusted at index {idx}")

    # Warn if LLM emitted chapter bounds outside real audio duration.
    if audio_duration_s > 0:
        out_of_bounds = [
            ch for ch in normalized
            if ch.start > audio_duration_s or ch.end > audio_duration_s
        ]
        if out_of_bounds:
            warnings.append(
                f"{len(out_of_bounds)} chapter(s) exceeded audio duration and were clamped"
            )

    # Clamp all boundaries to [0, audio_duration_s]
    if audio_duration_s > 0:
        for ch in normalized:
            ch.start = max(0.0, min(ch.start, audio_duration_s))
            ch.end = max(ch.start + 0.1, min(ch.end, audio_duration_s))
        normalized[-1].end = audio_duration_s

    if audio_duration_s > 0 and normalized[0].start > 0.0:
        warnings.append("First chapter does not start near 0s")

    return normalized, warnings


def _fmt_time(seconds: float) -> str:
    total = int(max(0, seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
