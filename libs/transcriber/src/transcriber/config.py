"""Runtime configuration: device detection, model selection, paths."""

import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class ModelSize(str, Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large-v3"


def get_device() -> str:
    """
    Detect the best available compute device.
    Priority: CUDA > MPS (Apple Silicon) > CPU.
    Can be overridden via the TRANSCRIBER_DEVICE env variable.
    """
    override = os.getenv("TRANSCRIBER_DEVICE")
    if override:
        return override

    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass

    return "cpu"


def get_hf_token() -> str:
    """Return the HuggingFace token required by pyannote.audio."""
    token = os.getenv("HF_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "HF_TOKEN is not set. "
            "Create a token at https://huggingface.co/settings/tokens "
            "and set it in your .env file or environment."
        )
    return token


# Default paths
VAR_DIR = Path(__file__).parents[2] / "var"
AUDIO_DIR = VAR_DIR / "audio"
OUTPUT_DIR = VAR_DIR / "output"

# Default model
DEFAULT_MODEL_SIZE = ModelSize.SMALL
