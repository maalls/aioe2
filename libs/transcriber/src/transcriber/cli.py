"""CLI entry point: `transcriber run`."""

from pathlib import Path
from typing import Optional

import typer

from .pipeline import run_pipeline

app = typer.Typer(help="Local audio transcription with speaker diarization.")


@app.command()
def run(
    input: Path = typer.Option(..., "--input", "-i", help="Path to the audio file."),
    output: Path = typer.Option(..., "--output", "-o", help="Output directory."),
    lang: str = typer.Option("fr", "--lang", "-l", help="Audio language (ISO 639-1 code, e.g. fr, en)."),
    num_speakers: Optional[int] = typer.Option(None, "--num-speakers", "-n", help="Number of speakers (recommended)."),
    speaker_names: Optional[str] = typer.Option(
        None, "--speaker-names",
        help='Comma-separated speaker names in expected order, e.g. "Alice,Bob,Chloe".',
    ),
    model_size: str = typer.Option("medium", "--model", "-m", help="Whisper model size: tiny, small, medium, large-v3."),
    save_intermediates: bool = typer.Option(False, "--save-intermediates", help="Save intermediate artefacts."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """Transcribe an audio file and produce a speaker-labelled output."""

    if not input.exists():
        typer.echo(f"Error: input file not found: {input}", err=True)
        raise typer.Exit(code=1)

    names = [n.strip() for n in speaker_names.split(",")] if speaker_names else []

    run_pipeline(
        input_path=input,
        output_dir=output,
        lang=lang,
        num_speakers=num_speakers,
        speaker_names=names,
        model_size=model_size,
        save_intermediates=save_intermediates,
        verbose=verbose,
    )
