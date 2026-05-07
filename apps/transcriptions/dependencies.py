from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string

from services.transcription.service import TranscriptionService
from services.transcription2.service import Transcription2Service


@lru_cache(maxsize=1)
def get_transcription_service() -> TranscriptionService:
    pipeline_fn = import_string(settings.TRANSCRIPTION_PIPELINE_FN)
    output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
    return TranscriptionService(pipeline_fn=pipeline_fn, output_root=output_root)


@lru_cache(maxsize=1)
def get_transcription2_service() -> Transcription2Service:
    pipeline_fn = import_string(settings.TRANSCRIPTION2_PIPELINE_FN)
    output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
    return Transcription2Service(pipeline_fn=pipeline_fn, output_root=output_root)
