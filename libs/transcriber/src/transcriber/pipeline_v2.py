"""ASR-first pipeline: Whisper timeline, then diarization, then temporal merge."""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from . import export, identity
from .asr import transcribe_file_with_word_timestamps
from .diarization import diarize
from .fusion_v2 import merge_words
from .media_assets import generate_preview_assets
from .preprocess import convert_to_wav, get_duration

logger = logging.getLogger(__name__)


def run_pipeline_v2(
    input_path: Path,
    output_dir: Path,
    lang: str,
    num_speakers: Optional[int],
    speaker_names: list[str],
    model_size: str = "small",
    save_intermediates: bool = False,
    verbose: bool = False,
) -> dict:
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    intermediates_dir = output_dir / "intermediates"
    asr_words_path = intermediates_dir / "asr_words.json"
    diarization_path = intermediates_dir / "diarization.json"
    merged_path = intermediates_dir / "asr_diarized_segments.json"

    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    intermediates_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Step 1/5: pre-processing audio...")
    t0 = time.perf_counter()
    wav_path = output_dir / f"{stem}.wav"
    if wav_path.exists():
        logger.info("  using cached wav: %s", wav_path.name)
    else:
        convert_to_wav(input_path, wav_path)
    audio_duration = get_duration(wav_path)
    timings["preprocess_s"] = round(time.perf_counter() - t0, 2)
    logger.info("  duration: %.1fs", audio_duration)

    logger.info("Step 2/5: transcribing full audio with timestamps...")
    t0 = time.perf_counter()
    if asr_words_path.exists():
        asr_words = json.loads(asr_words_path.read_text(encoding="utf-8"))
        logger.info("  using cached ASR timeline: %s", asr_words_path.name)
    else:
        asr_words = transcribe_file_with_word_timestamps(wav_path, lang=lang, model_size=model_size)
        asr_words_path.write_text(json.dumps(asr_words, indent=2, ensure_ascii=False), encoding="utf-8")
    timings["asr_s"] = round(time.perf_counter() - t0, 2)
    logger.info("  %d ASR words found", len(asr_words))

    logger.info("Step 3/5: diarizing...")
    t0 = time.perf_counter()
    if diarization_path.exists():
        diarization_segments = json.loads(diarization_path.read_text(encoding="utf-8"))
        logger.info("  using cached diarization: %s", diarization_path.name)
    else:
        diarization_segments = diarize(wav_path, num_speakers=num_speakers)
        diarization_path.write_text(json.dumps(diarization_segments, indent=2), encoding="utf-8")
    timings["diarization_s"] = round(time.perf_counter() - t0, 2)
    logger.info("  %d raw diarization segments found", len(diarization_segments))

    logger.info("Step 4/5: merging ASR words with diarization...")
    t0 = time.perf_counter()
    merged_segments = merge_words(diarization_segments, asr_words)
    timings["fusion_s"] = round(time.perf_counter() - t0, 2)
    logger.info("  %d merged speaker segments", len(merged_segments))

    if save_intermediates:
        merged_path.write_text(json.dumps(merged_segments, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Step 5/5: mapping speakers to names...")
    t0 = time.perf_counter()
    speaker_map = identity.build_speaker_map(merged_segments, speaker_names)
    final_segments = [dict(segment) for segment in merged_segments]
    timings["identity_s"] = round(time.perf_counter() - t0, 2)
    timings["total_s"] = round(time.perf_counter() - total_start, 2)

    speakers_found = list(speaker_map.keys())
    talk_time = {
        spk: round(
            sum(s["end"] - s["start"] for s in merged_segments if s["speaker"] == spk), 2
        )
        for spk in speakers_found
    }

    result = {
        "audio_file": input_path.name,
        "audio_duration_s": round(audio_duration, 2),
        "language": lang,
        "model_size": model_size,
        "speakers_found": len(speakers_found),
        "speaker_map": speaker_map,
        "talk_time_s": talk_time,
        "segments": final_segments,
    }

    run_report = {**{k: v for k, v in result.items() if k != "segments"}, "timings": timings}

    json_output = output_dir / f"{stem}.json"
    txt_output = output_dir / f"{stem}.txt"
    srt_output = output_dir / f"{stem}.srt"

    export.to_json(result, json_output)
    export.to_txt(final_segments, txt_output)
    export.to_srt(final_segments, srt_output)

    media_assets = generate_preview_assets(
        output_dir=output_dir,
        stem=stem,
        input_audio_path=input_path,
        srt_path=srt_output,
    )
    if media_assets:
        result["media_assets"] = media_assets
        run_report["media_assets"] = media_assets

    export.to_json(run_report, output_dir / "run_report.json")

    logger.info("Done in %.1fs. Output: %s", timings["total_s"], output_dir)
    return result
