import json
from pathlib import Path
import tempfile
import unittest

from episode import read_episode
from make_video import caption_time, captions, sound_effect


class EpisodeTests(unittest.TestCase):
    def test_pilot_uses_six_valid_shots(self):
        path = Path(__file__).resolve().parents[1] / "episodes" / "doors.json"
        episode = read_episode(path)
        self.assertEqual(len(episode["shots"]), 6)

    def test_market_episode_opens_with_the_town_rule(self):
        path = Path(__file__).resolve().parents[1] / "episodes" / "kalshi-town.json"
        shots = read_episode(path)["shots"]
        self.assertTrue(shots[0]["line"].startswith("In this town,"))
        self.assertEqual(shots[0]["action"], "market_street")
        self.assertEqual(len(shots), len({shot["action"] for shot in shots}))

    def test_unknown_actions_fail_before_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({"title": "One door", "shots": [
                {"action": "unknown", "line": "Watch the door."}
            ]}))
            with self.assertRaisesRegex(ValueError, "Shot 1"):
                read_episode(path)

    def test_captions_start_after_lead_in_and_end_with_voice(self):
        events = captions("A yellow door popped up right behind her.", 2.4, 5)
        self.assertIn(",0:00:05.14,", events[0])
        self.assertIn(",0:00:07.54,", events[-1])
        self.assertEqual(caption_time(59.999), "0:01:00.00")

    def test_effects_have_the_same_sample_count_as_the_shot(self):
        import wave

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "effects.wav"
            self.assertTrue(sound_effect(path, "knock", 1.5))
            with wave.open(str(path), "rb") as file:
                self.assertEqual(file.getnframes(), 72000)
            self.assertFalse(sound_effect(path, "town", 1.5))


if __name__ == "__main__":
    unittest.main()
