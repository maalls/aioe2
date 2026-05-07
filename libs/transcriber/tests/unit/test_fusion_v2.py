from transcriber.fusion_v2 import merge_words


class TestMergeWords:
    def test_groups_words_by_speaker_overlap(self):
        diarization_segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
            {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_01"},
        ]
        words = [
            {"start": 0.1, "end": 0.4, "text": "bonjour"},
            {"start": 0.5, "end": 0.8, "text": "a"},
            {"start": 2.2, "end": 2.6, "text": "tous"},
        ]

        result = merge_words(diarization_segments, words)

        assert result == [
            {"start": 0.1, "end": 0.8, "speaker": "SPEAKER_00", "text": "bonjour a"},
            {"start": 2.2, "end": 2.6, "speaker": "SPEAKER_01", "text": "tous"},
        ]

    def test_falls_back_to_nearest_speaker_when_word_is_in_gap(self):
        diarization_segments = [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 4.0, "speaker": "SPEAKER_01"},
        ]
        words = [
            {"start": 1.4, "end": 1.6, "text": "mot"},
        ]

        result = merge_words(diarization_segments, words)

        assert result == [
            {"start": 1.4, "end": 1.6, "speaker": "SPEAKER_00", "text": "mot"},
        ]

    def test_attaches_punctuation_without_extra_space(self):
        diarization_segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        ]
        words = [
            {"start": 0.1, "end": 0.3, "text": "Bonjour"},
            {"start": 0.31, "end": 0.35, "text": ","},
            {"start": 0.4, "end": 0.6, "text": "Malo"},
        ]

        result = merge_words(diarization_segments, words)

        assert result == [
            {"start": 0.1, "end": 0.6, "speaker": "SPEAKER_00", "text": "Bonjour, Malo"},
        ]
