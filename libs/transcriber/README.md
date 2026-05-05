# Transcriber

Local audio transcription with speaker diarization. No cloud, no data leaves your machine.

## Requirements

- Python 3.10+
- ffmpeg installed system-wide (`brew install ffmpeg`)
- A HuggingFace account with access to `pyannote/speaker-diarization-3.1`

## Installation

```bash
# 1. Clone and enter the project
cd transcriber

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install the package and dependencies
pip install -e ".[dev]"

# 4. Configure your HuggingFace token
cp .env.example .env
# Edit .env and replace hf_your_token_here with your real token
```

## Usage

```bash
transcriber run \
  --input var/audio/test/meeting_4speakers_45min.m4a \
  --output var/output/meeting \
  --lang fr \
  --num-speakers 4 \
  --speaker-names "Alice,Bob,Chloe,David" \
  --verbose
```

### Options

| Option | Default | Description |
|---|---|---|
| `--input` | required | Path to audio file (WAV, MP3, M4A, ...) |
| `--output` | required | Output directory |
| `--lang` | `fr` | Language code (fr, en, ...) |
| `--num-speakers` | auto | Number of speakers (strongly recommended) |
| `--speaker-names` | none | Comma-separated names |
| `--model` | `small` | Whisper model: tiny, small, medium, large-v3 |
| `--save-intermediates` | off | Save diarization/ASR intermediate files |
| `--verbose` | off | Print step-by-step progress |

### Override device

```bash
TRANSCRIBER_DEVICE=cpu transcriber run ...
```

## Output

```
var/output/meeting/
  meeting.json          # full result (source of truth)
  meeting.txt           # readable timestamped transcript
  meeting.srt           # subtitles
  run_report.json       # timing and speaker stats
  intermediates/        # only with --save-intermediates
    diarization.json
    asr_segments.json
    mapping.json
```

## Correcting speaker labels

Edit `speaker_map` in `result.json`, then re-export without re-running the pipeline (V1 feature — for now, edit the `.txt` directly or rerun with corrected `--speaker-names`).

## Running tests

```bash
# Unit tests only (fast, no models needed)
pytest tests/unit/ -v

# Functional tests (requires models downloaded)
pytest tests/functional/ -v

# Full integration test (long — runs on the 45-min reference file)
pytest tests/integration/ -v -s
```
