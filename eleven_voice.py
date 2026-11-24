"""ElevenLabs speech and word timings, with no third-party Python dependencies."""

import base64
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # George
DEFAULT_MODEL = "eleven_multilingual_v2"


def speak(key, voice, model, line, previous, following):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", voice):
        raise ValueError("ElevenLabs voice ID contains unsupported characters")
    body = {"text": line, "model_id": model}
    if previous:
        body["previous_text"] = previous
    if following:
        body["next_text"] = following
    request = Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=90) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"ElevenLabs returned HTTP {error.code}. Check your API key, voice ID, and credits.") from error
    try:
        audio = base64.b64decode(result["audio_base64"], validate=True)
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("ElevenLabs returned invalid audio") from error
    if not audio:
        raise RuntimeError("ElevenLabs returned empty audio")
    return audio, word_timings(result.get("normalized_alignment") or result.get("alignment"))


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
