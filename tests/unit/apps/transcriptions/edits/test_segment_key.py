from apps.transcriptions.edits import segment_key
from .conftest import SOURCE_SEGMENTS


def test_is_16_char_hex():
    seg = SOURCE_SEGMENTS["segments"][0]
    k = segment_key(seg)
    assert len(k) == 16
    assert all(c in "0123456789abcdef" for c in k)


def test_is_stable():
    seg = SOURCE_SEGMENTS["segments"][0]
    assert segment_key(seg) == segment_key(dict(seg))


def test_differs_across_segments():
    segs = SOURCE_SEGMENTS["segments"]
    keys = [segment_key(s) for s in segs]
    assert len(set(keys)) == len(keys), "Each segment must have a unique key"
