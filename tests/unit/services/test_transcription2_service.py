import json
from pathlib import Path

from services.transcription.schemas import TranscriptionRequest
from services.transcription2.service import Transcription2Service


def test_transcription2_service_reads_pipeline_outputs(tmp_path: Path):
    def fake_pipeline(**kwargs):
        output_dir = kwargs["output_dir"]
        (output_dir / "meeting.txt").write_text("bonjour", encoding="utf-8")
        (output_dir / "meeting.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nbonjour\n", encoding="utf-8")
        (output_dir / "run_report.json").write_text(
            json.dumps({"timings": {"total_s": 1.23}}),
            encoding="utf-8",
        )
        return {
            "segments": [{"start": 0.0, "end": 1.0, "speaker": "Malo", "text": "bonjour"}],
            "speaker_map": {"SPEAKER_00": "Malo"},
            "speakers_found": 1,
            "audio_duration_s": 42.0,
        }

    service = Transcription2Service(pipeline_fn=fake_pipeline, output_root=tmp_path / "out")
    request = TranscriptionRequest(audio_path=tmp_path / "meeting.wav")
    request.audio_path.write_bytes(b"fake")

    result = service.run(request)

    assert result.speakers_found == 1
    assert result.audio_duration_s == 42.0
    assert result.timings == {"total_s": 1.23}
    assert result.export_txt == "bonjour"
    assert "bonjour" in result.export_srt
