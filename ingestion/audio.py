import time
from pathlib import Path

from utils.config import WHISPER_MODEL_SIZE, SUPPORTED_AUDIO_FORMATS, UPLOAD_DIR


def transcribe(audio_path: str | Path, language: str | None = None) -> dict:
    if isinstance(audio_path, str):
        audio_path = Path(audio_path)

    if audio_path.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {audio_path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
        )

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is not installed. "
            "Install it with: pip install faster-whisper"
        )

    dest = UPLOAD_DIR / audio_path.name
    if dest.exists():
        pass
    else:
        import shutil
        shutil.copy2(str(audio_path), str(dest))

    start = time.time()
    model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        num_workers=2,
    )
    segments, info = model.transcribe(str(audio_path), language=language, beam_size=3)

    segments_list = []
    full_text_parts = []
    for seg in segments:
        segments_list.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        full_text_parts.append(seg.text.strip())

    elapsed = time.time() - start
    transcript = " ".join(full_text_parts)

    return {
        "transcript": transcript,
        "segments": segments_list,
        "language": info.language if info else "unknown",
        "duration": round(info.duration, 2) if info else 0,
        "processing_time": round(elapsed, 2),
        "model": WHISPER_MODEL_SIZE,
    }
