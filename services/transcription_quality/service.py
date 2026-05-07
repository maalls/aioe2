import json
import logging
import re
from pathlib import Path
from typing import Any

from services.transcription_quality.schemas import (
    QualityFlag,
    QualityStats,
    TranscriptQualityReport,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


class TranscriptQualityService:
    def __init__(self, llm_client: Any | None = None, context_window: int = 2):
        self.llm_client = llm_client
        self.context_window = max(context_window, 1)

    def run_from_path(
        self,
        transcript_path: Path,
        expected_language: str = "",
        max_segments: int | None = None,
        intermediates_dir: Path | None = None,
    ) -> TranscriptQualityReport:
        transcript_path = Path(transcript_path)
        payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        return self.run_from_json(
            payload,
            expected_language=expected_language,
            max_segments=max_segments,
            intermediates_dir=intermediates_dir,
        )

    def run_from_json(
        self,
        transcript_json: dict[str, Any],
        expected_language: str = "",
        max_segments: int | None = None,
        intermediates_dir: Path | None = None,
    ) -> TranscriptQualityReport:
        segments = self._extract_segments(transcript_json, max_segments=max_segments)
        if not segments:
            return TranscriptQualityReport(
                global_score=0.0,
                summary="No segment found in transcript.",
                stats=QualityStats(total_segments=0, flagged_segments=0, high_risk_segments=0),
                flags=[],
            )

        inferred_language = expected_language or str(transcript_json.get("language", "")).strip()

        cache_dir: Path | None = None
        if intermediates_dir is not None:
            cache_dir = Path(intermediates_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)

        flags: list[QualityFlag] = []
        segment_risks: list[float] = []
        for segment in segments:
            risk, reason, evidence = self._score_segment(
                segment=segment,
                segments=segments,
                expected_language=inferred_language,
                cache_dir=cache_dir,
            )
            segment_risks.append(risk)
            if risk >= 0.4:
                context_indices = self._context_indices(segment.index, len(segments))
                flags.append(
                    QualityFlag(
                        segment_id=segment.index,
                        risk_score=round(risk, 3),
                        severity=self._severity(risk),
                        reason=reason,
                        evidence=evidence,
                        context_window=context_indices,
                    )
                )

        high_count = sum(1 for flag in flags if flag.severity == "high")
        global_score = self._compute_global_score(segment_risks, flags)

        stats = QualityStats(
            total_segments=len(segments),
            flagged_segments=len(flags),
            high_risk_segments=high_count,
        )
        summary = (
            f"{len(flags)} segments suspects sur {len(segments)}. "
            f"{high_count} segments a risque eleve."
        )

        return TranscriptQualityReport(
            global_score=round(global_score, 3),
            summary=summary,
            stats=stats,
            flags=sorted(flags, key=lambda item: item.risk_score, reverse=True),
        )

    def _extract_segments(
        self,
        transcript_json: dict[str, Any],
        max_segments: int | None = None,
    ) -> list[TranscriptSegment]:
        raw_segments = transcript_json.get("segments", [])
        if not isinstance(raw_segments, list):
            return []

        cleaned: list[TranscriptSegment] = []
        for idx, raw in enumerate(raw_segments):
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("text", "")).strip()
            cleaned.append(
                TranscriptSegment(
                    index=idx,
                    start=float(raw.get("start", 0.0) or 0.0),
                    end=float(raw.get("end", 0.0) or 0.0),
                    speaker=str(raw.get("speaker", "")).strip(),
                    text=text,
                )
            )

        if max_segments is not None and max_segments > 0:
            return cleaned[:max_segments]
        return cleaned

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_path(self, cache_dir: Path, index: int) -> Path:
        return cache_dir / f"segment_{index:06d}.json"

    def _load_cached(self, cache_dir: Path, index: int) -> dict[str, Any] | None:
        path = self._cache_path(cache_dir, index)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _save_cached(self, cache_dir: Path, index: int, data: dict[str, Any]) -> None:
        path = self._cache_path(cache_dir, index)
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            logger.warning("Could not write segment cache %s: %s", path, exc)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_segment(
        self,
        segment: TranscriptSegment,
        segments: list[TranscriptSegment],
        expected_language: str,
        cache_dir: Path | None = None,
    ) -> tuple[float, str, str]:
        # 1 — Check cache first
        if cache_dir is not None:
            cached = self._load_cached(cache_dir, segment.index)
            if cached is not None:
                logger.debug("segment %d: loaded from cache", segment.index)
                return (
                    float(cached.get("risk_score", 0.0)),
                    str(cached.get("reason", "")),
                    str(cached.get("evidence", "")),
                )

        # 2 — Empty segment shortcut (no LLM needed)
        if not segment.text:
            result = (0.95, "Segment vide", "Aucun contenu textuel sur ce segment.")
            if cache_dir is not None:
                self._save_cached(cache_dir, segment.index, {
                    "index": segment.index,
                    "start": segment.start,
                    "end": segment.end,
                    "speaker": segment.speaker,
                    "text": segment.text,
                    "risk_score": result[0],
                    "reason": result[1],
                    "evidence": result[2],
                })
            return result

        llm_risk = 0.35
        reason = "Evaluation heuristique"
        evidence = "Score calcule via signaux locaux"

        if self.llm_client is not None:
            window_segments, target_pos = self._build_context_window(segment.index, segments)
            try:
                llm_result = self._call_llm(
                    window_segments=window_segments,
                    target_pos=target_pos,
                    expected_language=expected_language,
                )
                llm_risk = float(llm_result.get("risk_score", llm_risk))
                reason = str(llm_result.get("reason", reason))
                evidence = str(llm_result.get("evidence", evidence))
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                reason = "Fallback heuristique"
                evidence = f"LLM indisponible: {exc}"

        lang_anomaly = self._language_anomaly_score(segment.text, expected_language)
        local_break = self._local_break_score(segment.index, segments)

        risk_score = min(max((0.6 * llm_risk) + (0.2 * lang_anomaly) + (0.2 * local_break), 0.0), 1.0)

        # 3 — Persist to cache
        if cache_dir is not None:
            self._save_cached(cache_dir, segment.index, {
                "index": segment.index,
                "start": segment.start,
                "end": segment.end,
                "speaker": segment.speaker,
                "text": segment.text,
                "risk_score": risk_score,
                "reason": reason,
                "evidence": evidence,
            })

        return risk_score, reason, evidence

    def _call_llm(
        self,
        window_segments: list[TranscriptSegment],
        target_pos: int,
        expected_language: str,
    ) -> dict[str, Any]:
        context_payload = [
            {
                "index": item.index,
                "speaker": item.speaker,
                "start": item.start,
                "end": item.end,
                "text": item.text,
            }
            for item in window_segments
        ]
        prompt = self._build_prompt(context_payload, target_pos, expected_language)
        raw = self.llm_client.chat([{"role": "user", "content": prompt}])
        return self._parse_llm_response(raw)

    def _build_prompt(
        self,
        context_segments: list[dict[str, Any]],
        target_index_in_context: int,
        expected_language: str,
    ) -> str:
        segments_payload = json.dumps(context_segments, ensure_ascii=False)
        expected_lang_text = expected_language or "unknown"
        return (
            "Tu es un auditeur de qualite de transcription."
            " Evalue UNIQUEMENT la coherence conversationnelle du segment cible"
            " dans son contexte local.\n"
            "Rends STRICTEMENT un JSON valide, sans texte additionnel,"
            " avec ce schema exact:\n"
            '{"is_suspicious": bool, "risk_score": float, "reason": str, '
            '"evidence": str, "confidence": float}\n'
            "Contraintes:\n"
            "- risk_score et confidence entre 0.0 et 1.0\n"
            "- reason court et explicite\n"
            "- evidence ancree dans le contexte fourni\n"
            f"- Langue attendue: {expected_lang_text}\n\n"
            f"Index du segment cible dans la fenetre: {target_index_in_context}\n"
            f"Segments de contexte: {segments_payload}\n"
        )

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        if not content:
            raise ValueError("Empty LLM response")
        parsed: dict[str, Any] | None = None
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("Invalid JSON payload from LLM")
        risk_score = float(parsed.get("risk_score", 0.0))
        confidence = float(parsed.get("confidence", 0.0))
        return {
            "is_suspicious": bool(parsed.get("is_suspicious", False)),
            "risk_score": min(max(risk_score, 0.0), 1.0),
            "reason": str(parsed.get("reason", "No reason provided")),
            "evidence": str(parsed.get("evidence", "No evidence provided")),
            "confidence": min(max(confidence, 0.0), 1.0),
        }

    def _build_context_window(
        self,
        index: int,
        segments: list[TranscriptSegment],
    ) -> tuple[list[TranscriptSegment], int]:
        start = max(index - self.context_window, 0)
        end = min(index + self.context_window + 1, len(segments))
        window = segments[start:end]
        target_position = index - start
        return window, target_position

    def _context_indices(self, index: int, total: int) -> list[int]:
        start = max(index - self.context_window, 0)
        end = min(index + self.context_window + 1, total)
        return list(range(start, end))

    def _language_anomaly_score(self, text: str, expected_language: str) -> float:
        if not text:
            return 1.0
        if expected_language.lower() != "fr":
            return 0.0

        normalized = f" {re.sub(r'\s+', ' ', text.lower())} "
        common_markers = [
            " le ",
            " la ",
            " les ",
            " de ",
            " des ",
            " et ",
            " je ",
            " vous ",
            " nous ",
            " est ",
            " pas ",
            " pour ",
        ]
        letter_count = sum(1 for char in normalized if char.isalpha())
        has_marker = any(marker in normalized for marker in common_markers)

        if letter_count < 10:
            return 0.1
        if has_marker:
            return 0.0
        return 0.35

    def _local_break_score(self, index: int, segments: list[TranscriptSegment]) -> float:
        text = segments[index].text
        if not text:
            return 1.0

        current_tokens = self._token_set(text)
        if not current_tokens:
            return 0.8

        similarities: list[float] = []
        neighbors = []
        if index - 1 >= 0:
            neighbors.append(segments[index - 1].text)
        if index + 1 < len(segments):
            neighbors.append(segments[index + 1].text)

        for neighbor_text in neighbors:
            neighbor_tokens = self._token_set(neighbor_text)
            similarities.append(self._jaccard(current_tokens, neighbor_tokens))

        if not similarities:
            return 0.0

        max_similarity = max(similarities)
        return 1.0 - max_similarity

    def _token_set(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text.lower())
        return set(tokens)

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def _severity(self, score: float) -> str:
        if score >= 0.7:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"

    def _compute_global_score(self, risks: list[float], flags: list[QualityFlag]) -> float:
        if not risks:
            return 0.0
        mean_risk = sum(risks) / len(risks)
        high_risk_bonus = sum(0.02 for item in flags if item.severity == "high")
        return min(mean_risk + high_risk_bonus, 1.0)


def run_quality_check(
    transcript_path: Path,
    llm_client: Any | None = None,
    context_window: int = 2,
    expected_language: str = "",
    max_segments: int | None = None,
    intermediates_dir: Path | None = None,
) -> TranscriptQualityReport:
    service = TranscriptQualityService(llm_client=llm_client, context_window=context_window)
    return service.run_from_path(
        transcript_path=transcript_path,
        expected_language=expected_language,
        max_segments=max_segments,
        intermediates_dir=intermediates_dir,
    )
