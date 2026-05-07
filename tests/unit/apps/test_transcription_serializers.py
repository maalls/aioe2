from apps.transcriptions.models import TranscriptionResult
from apps.transcriptions.serializers import TranscriptionResultSerializer


def test_transcription_result_serializer_keeps_speaker_id_and_adds_label():
    result = TranscriptionResult(
        segments=[
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00", "text": "Bonjour"},
            {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_99", "text": "Test"},
        ],
        speaker_map={"SPEAKER_00": "Alison"},
        speakers_found=2,
        audio_duration_s=2.0,
        timings={"total_s": 1.2},
        export_txt="",
        export_srt="",
    )

    payload = TranscriptionResultSerializer(result).data

    assert payload["segments"][0]["speaker"] == "SPEAKER_00"
    assert payload["segments"][0]["speaker_label"] == "Alison"
    assert payload["segments"][1]["speaker"] == "SPEAKER_99"
    assert payload["segments"][1]["speaker_label"] == "SPEAKER_99"
    assert payload["speaker_map"] == {"SPEAKER_00": "Alison"}
