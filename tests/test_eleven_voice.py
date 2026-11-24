import base64
import unittest
from unittest.mock import patch

from elevenlabs.types.audio_with_timestamps_response import AudioWithTimestampsResponse

from eleven_voice import DEFAULT_MODEL, DEFAULT_VOICE, speak
from make_video import captions, cut_effects


class ElevenVoiceTests(unittest.TestCase):
    @patch("eleven_voice.ElevenLabs")
    def test_speech_request_and_caption_timing(self, client):
        convert = client.return_value.text_to_speech.convert_with_timestamps
        convert.return_value = AudioWithTimestampsResponse.model_validate({
            "audio_base64": base64.b64encode(b"audio").decode(),
            "normalized_alignment": None,
            "alignment": {
                "characters": list("Hi. Run."),
                "character_start_times_seconds": [.3, .4, .5, .6, 1.1, 1.2, 1.3, 1.4],
                "character_end_times_seconds": [.4, .5, .6, .7, 1.2, 1.3, 1.4, 1.5],
            },
        })
        audio, words = speak("example-key", DEFAULT_VOICE, DEFAULT_MODEL, "Hi. Run.", "Before.", "After.")
        convert.assert_called_once_with(voice_id=DEFAULT_VOICE, output_format="mp3_44100_128",
                                        text="Hi. Run.", model_id=DEFAULT_MODEL,
                                        previous_text="Before.", next_text="After.")
        self.assertEqual(audio, b"audio")
        events = captions("Hi. Run.", 2, 0, words)
        self.assertIn("0:00:00.44", events[0])
        self.assertIn("0:00:01.24", events[1])

    def test_flash_starts_at_impact_keyframe(self):
        self.assertIn("eq(n,119)", cut_effects("appear", 100, 60, 24)[0])
