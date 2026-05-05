"""Map internal speaker IDs to user-provided names."""


def build_speaker_map(
    segments: list[dict],
    speaker_names: list[str],
) -> dict[str, str]:
    """
    Build a mapping from SPEAKER_XX ids to human names.

    Strategy:
    - Rank speakers by total talk time (descending).
    - Assign names in the order provided by the user.
    - If fewer names than speakers, remaining ones stay as SPEAKER_XX.
    """
    talk_time: dict[str, float] = {}
    for seg in segments:
        spk = seg["speaker"]
        talk_time[spk] = talk_time.get(spk, 0.0) + (seg["end"] - seg["start"])

    ranked = sorted(talk_time, key=lambda s: talk_time[s], reverse=True)

    speaker_map: dict[str, str] = {}
    for i, spk in enumerate(ranked):
        if i < len(speaker_names):
            speaker_map[spk] = speaker_names[i]
        else:
            speaker_map[spk] = spk

    return speaker_map


def apply_speaker_map(segments: list[dict], speaker_map: dict[str, str]) -> list[dict]:
    """Replace speaker IDs with mapped names in all segments."""
    return [
        {**seg, "speaker": speaker_map.get(seg["speaker"], seg["speaker"])}
        for seg in segments
    ]
