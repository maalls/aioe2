from services.transcription_quality.service import TranscriptQualityService


class FakeLLMClient:
    def chat(self, messages: list) -> str:
        return '{"is_suspicious": false, "risk_score": 0.2, "reason": "Test verdict", "evidence": "Test evidence", "confidence": 0.8}'


def test_empty_segment_is_flagged_high_risk():
    transcript_json = {
        "language": "fr",
        "segments": [
            {"start": 0.0, "end": 1.0, "speaker": "S1", "text": "Bonjour a tous"},
            {"start": 1.0, "end": 2.0, "speaker": "S2", "text": ""},
            {"start": 2.0, "end": 3.0, "speaker": "S1", "text": "Merci"},
        ],
    }

    service = TranscriptQualityService(llm_client=FakeLLMClient(), context_window=1)
    report = service.run_from_json(transcript_json)

    assert report.stats.total_segments == 3
    assert report.stats.flagged_segments >= 1
    assert any(flag.segment_id == 1 and flag.severity == "high" for flag in report.flags)


def test_report_contains_consistent_stats():
    transcript_json = {
        "language": "fr",
        "segments": [
            {"start": 0.0, "end": 1.0, "speaker": "S1", "text": "On commence la reunion"},
            {"start": 1.0, "end": 2.0, "speaker": "S2", "text": "Sujet totalement hors contexte"},
            {"start": 2.0, "end": 3.0, "speaker": "S1", "text": "On continue l ordre du jour"},
        ],
    }

    service = TranscriptQualityService(llm_client=FakeLLMClient(), context_window=1)
    report = service.run_from_json(transcript_json)

    assert 0.0 <= report.global_score <= 1.0
    assert report.stats.total_segments == 3
    assert report.stats.high_risk_segments <= report.stats.flagged_segments
