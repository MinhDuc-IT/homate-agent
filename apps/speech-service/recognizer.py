"""Sherpa-ONNX-backed speech transcription for Vietnamese audio."""

from __future__ import annotations

import asyncio
import io
import logging
import math
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

MODEL_DIRECTORY = (
    Path(__file__).resolve().parent
    / "models"
    / "sherpa-onnx-zipformer-vi-30M-int8-2026-02-09"
)
LANGUAGE = "vi"
SAMPLE_RATE = 16_000
FEATURE_DIM = 80

logger = logging.getLogger("stt")
_decode_lock = threading.Lock()


class AudioDecodeError(ValueError):
    """Raised when an uploaded audio payload cannot be decoded."""


@lru_cache(maxsize=1)
def get_recognizer() -> Any:
    """Load the local Sherpa-ONNX recognizer once per process."""
    import sherpa_onnx

    model_files = {
        "encoder": MODEL_DIRECTORY / "encoder.int8.onnx",
        "decoder": MODEL_DIRECTORY / "decoder.onnx",
        "joiner": MODEL_DIRECTORY / "joiner.int8.onnx",
        "tokens": MODEL_DIRECTORY / "tokens.txt",
    }
    missing = [str(path) for path in model_files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Sherpa-ONNX model files are missing: {', '.join(missing)}")

    logger.info("Loading Sherpa-ONNX model from %s", MODEL_DIRECTORY)
    recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(model_files["encoder"]),
        decoder=str(model_files["decoder"]),
        joiner=str(model_files["joiner"]),
        tokens=str(model_files["tokens"]),
        num_threads=1,
        sample_rate=SAMPLE_RATE,
        feature_dim=FEATURE_DIM,
        decoding_method="greedy_search",
        provider="cpu",
    )
    logger.info("Sherpa-ONNX recognizer ready")
    return recognizer


def _decode_audio(raw: bytes) -> Any:
    """Decode audio bytes into a mono 16 kHz float32 waveform."""
    if not raw:
        raise AudioDecodeError("Audio upload is empty")

    try:
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample_poly

        samples, sample_rate = sf.read(
            io.BytesIO(raw),
            dtype="float32",
            always_2d=False,
        )
    except Exception as exc:
        raise AudioDecodeError("Audio upload could not be decoded") from exc

    if samples.size == 0 or sample_rate <= 0:
        raise AudioDecodeError("Audio upload contains no samples")

    if samples.ndim > 1:
        samples = np.mean(samples, axis=1, dtype=np.float32)

    if sample_rate != SAMPLE_RATE:
        divisor = math.gcd(int(sample_rate), SAMPLE_RATE)
        samples = resample_poly(
            samples,
            SAMPLE_RATE // divisor,
            int(sample_rate) // divisor,
        ).astype(np.float32)

    if len(samples) > SAMPLE_RATE * 61:
        raise AudioDecodeError("Audio must be at most 60 seconds")
    return samples


def _transcribe_sync(raw: bytes) -> dict[str, Any]:
    waveform = _decode_audio(raw)
    recognizer = get_recognizer()

    # The binding does not document concurrent decode calls on one recognizer.
    with _decode_lock:
        stream = recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, waveform)
        recognizer.decode_stream(stream)
        text = str(stream.result.text).strip()

    return {
        "text": text,
        "confidence": 0.0,
        "language": LANGUAGE,
    }


async def transcribe(raw: bytes) -> dict[str, Any]:
    """Transcribe audio without blocking FastAPI's event loop."""
    return await asyncio.to_thread(_transcribe_sync, raw)
