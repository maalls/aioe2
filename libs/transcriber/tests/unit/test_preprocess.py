"""Unit tests for preprocess module."""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestConvertToWav:
    def test_output_path_is_returned(self, tmp_path):
        input_file = tmp_path / "audio.mp3"
        input_file.touch()
        output_file = tmp_path / "audio.wav"

        with patch("transcriber.preprocess.ffmpeg") as mock_ffmpeg:
            mock_ffmpeg.input.return_value.output.return_value.overwrite_output.return_value.run = MagicMock()
            from transcriber.preprocess import convert_to_wav
            result = convert_to_wav(input_file, output_file)

        assert result == output_file

    def test_output_directory_is_created(self, tmp_path):
        input_file = tmp_path / "audio.mp3"
        input_file.touch()
        output_file = tmp_path / "subdir" / "audio.wav"

        with patch("transcriber.preprocess.ffmpeg") as mock_ffmpeg:
            mock_ffmpeg.input.return_value.output.return_value.overwrite_output.return_value.run = MagicMock()
            from transcriber.preprocess import convert_to_wav
            convert_to_wav(input_file, output_file)

        assert output_file.parent.exists()
