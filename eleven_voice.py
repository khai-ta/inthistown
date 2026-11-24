"""ElevenLabs speech and word timings, using the official Python SDK."""

import base64
import re

from elevenlabs import ElevenLabs
from elevenlabs.core.api_error import ApiError

ADAM_VOICE = "pNInz6obpgDQGcFmaJgB"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # George
DEFAULT_MODEL = "eleven_multilingual_v2"


def speak(key, voice, model, line, previous, following):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", voice):
        raise ValueError("ElevenLabs voice ID contains unsupported characters")
    client = ElevenLabs(api_key=key, timeout=90)
    try:
        result = client.text_to_speech.convert_with_timestamps(
            voice_id=voice,
            output_format="mp3_44100_128",
            text=line,
            model_id=model,
            previous_text=previous,
            next_text=following,
        )
    except ApiError as error:
        raise RuntimeError(f"ElevenLabs returned HTTP {error.status_code}. Check your API key, voice ID, and credits.") from error
    try:
        audio = base64.b64decode(result.audio_base_64, validate=True)
    except (TypeError, ValueError) as error:
        raise RuntimeError("ElevenLabs returned invalid audio") from error
    if not audio:
        raise RuntimeError("ElevenLabs returned empty audio")
    alignment = result.normalized_alignment or result.alignment
    return audio, word_timings(alignment.model_dump() if alignment else None)


def word_timings(alignment):
    if not alignment:
        return None
    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    if not chars or len(chars) != len(starts) or len(chars) != len(ends):
        return None
    return [(match.group(), starts[match.start()], ends[match.end() - 1])
            for match in re.finditer(r"\S+", "".join(chars))] or None
