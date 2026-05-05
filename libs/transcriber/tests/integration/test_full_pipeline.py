"""
Integration test: full pipeline on the 45-min reference audio.

Requires:
- var/audio/test/meeting_4speakers_45min.m4a to exist
- HF_TOKEN set in environment or .env
- Models downloaded (first run will download them)

Run with:
    pytest tests/integration/ -v -s --timeout=1800
"""

import json
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
AUDIO_FILE = PACKAGE_ROOT / "var" / "audio" / "test" / "meeting_4speakers_45min.m4a"
OUTPUT_DIR = PACKAGE_ROOT / "var" / "output" / "test_integration"
SPEAKER_NAMES = ["Alison", "Gabrielle", "Malo", "Lamya"]
NUM_SPEAKERS = 4
LANG = "fr"


@pytest.fixture(scope="module")
def pipeline_result():
    """Run the full pipeline once for all tests in this module."""
    from transcriber.pipeline import run_pipeline

    return run_pipeline(
        input_path=AUDIO_FILE,
        output_dir=OUTPUT_DIR,
        lang=LANG,
        num_speakers=NUM_SPEAKERS,
        speaker_names=SPEAKER_NAMES,
        model_size="medium",
        save_intermediates=True,
        verbose=True,
    )


@pytest.mark.skipif(not AUDIO_FILE.exists(), reason="Reference audio file not found.")
class TestFullPipeline:
    def test_no_exception(self, pipeline_result):
        assert pipeline_result is not None

    def test_result_json_exists(self):
        assert (OUTPUT_DIR / "meeting_4speakers_45min.json").exists()

    def test_txt_export_exists(self):
        assert (OUTPUT_DIR / "meeting_4speakers_45min.txt").exists()

    def test_srt_export_exists(self):
        assert (OUTPUT_DIR / "meeting_4speakers_45min.srt").exists()

    def test_run_report_exists(self):
        assert (OUTPUT_DIR / "run_report.json").exists()

    def test_correct_number_of_speakers(self, pipeline_result):
        assert pipeline_result["speakers_found"] == NUM_SPEAKERS

    def test_all_names_in_speaker_map(self, pipeline_result):
        mapped_names = set(pipeline_result["speaker_map"].values())
        for name in SPEAKER_NAMES:
            assert name in mapped_names

    def test_all_segments_have_text_field(self, pipeline_result):
        for seg in pipeline_result["segments"]:
            assert "text" in seg
            assert seg["text"] is not None

    def test_audio_coverage(self, pipeline_result):
        """Pipeline segments should cover at least 80% of the audio duration."""
        total_audio = pipeline_result["audio_duration_s"]
        total_covered = sum(
            s["end"] - s["start"] for s in pipeline_result["segments"]
        )
        assert total_covered / total_audio >= 0.80

    def test_timings_logged(self):
        report = json.loads((OUTPUT_DIR / "run_report.json").read_text())
        assert "timings" in report
        assert report["timings"]["total_s"] > 0
