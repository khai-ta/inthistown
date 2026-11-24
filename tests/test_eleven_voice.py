import base64
from io import BytesIO
import json
import unittest
from unittest.mock import patch

from eleven_voice import DEFAULT_MODEL, DEFAULT_VOICE, speak
from make_video import captions, cut_effects


class ElevenVoiceTests(unittest.TestCase):
    @patch("eleven_voice.urlopen")
    def test_speech_request_and_caption_timing(self, urlopen):
        urlopen.return_value = BytesIO(json.dumps({
            "audio_base64": base64.b64encode(b"audio").decode(),
            "alignment": {
                "characters": list("Hi. Run."),
                "character_start_times_seconds": [.3, .4, .5, .6, 1.1, 1.2, 1.3, 1.4],
                "character_end_times_seconds": [.4, .5, .6, .7, 1.2, 1.3, 1.4, 1.5],
            },
        }).encode())
        audio, words = speak("example-key", DEFAULT_VOICE, DEFAULT_MODEL, "Hi. Run.", "Before.", "After.")
        request = urlopen.call_args[0][0]
        self.assertIn("/with-timestamps", request.full_url)
        self.assertEqual(json.loads(request.data)["previous_text"], "Before.")
        self.assertEqual(json.loads(request.data)["next_text"], "After.")
        self.assertEqual(audio, b"audio")
        events = captions("Hi. Run.", 2, 0, words)
        self.assertIn("0:00:00.44", events[0])
        self.assertIn("0:00:01.24", events[1])

    def test_flash_starts_at_impact_keyframe(self):
        self.assertIn("eq(n,119)", cut_effects("appear", 100, 60, 24)[0])
