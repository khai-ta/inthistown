"""Read the shared episode format used by the renderer and video pipeline."""

import json
from pathlib import Path

MARKET_ACTIONS = {"market_hook", "market_street", "market_win", "market_ticket", "market_friend",
                  "market_mayor", "market_count", "market_trade", "market_blackout", "market_end"}
PARTY_ACTIONS = {"party_street", "party_bedroom", "party_knock", "party_invite",
                 "party_power", "party_beat", "party_lantern", "party_end"}
RECRUIT_ACTIONS = {
    'recruit_city',
    'recruit_desk',
    'recruit_profile',
    'recruit_resume',
    'recruit_submit',
    'recruit_reject',
    'recruit_next',
    'recruit_grind',
    'recruit_failed',
    'recruit_accepted',
    'recruit_calendar',
    'recruit_prep',
    'recruit_mirror_first',
    'recruit_mirror_second',
    'recruit_mirror_third',
    'recruit_waiting',
    'recruit_night',
    'recruit_walk',
    'recruit_reflect',
    'recruit_uncertain',
    'recruit_montage',
    'recruit_morning',
    'recruit_ending',
}
ACTIONS = {"town", "lie", "appear", "knock", "open", "twist", "clock", "twin", "key", "escape", "dusk", "streetdoor"} | MARKET_ACTIONS | PARTY_ACTIONS | RECRUIT_ACTIONS


def read_episode(path):
    episode = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(episode, dict):
        raise ValueError("Episode must be an object")
    if episode.get("avatar") not in (None, "roblox-r15"):
        raise ValueError("Unsupported avatar type")
    if episode.get("style") not in (None, "shorts"):
        raise ValueError("Unsupported edit style")
    title = episode.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Episode needs a title")
    shots = episode.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("Episode needs at least one shot")
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            raise ValueError(f"Shot {index} must be an object")
        action = shot.get("action")
        if not isinstance(action, str) or action not in ACTIONS:
            raise ValueError(f"Shot {index} needs a supported action")
        line = shot.get("line")
        if not isinstance(line, str) or not line.strip():
            raise ValueError(f"Shot {index} needs a narration line")
        if len(line.split()) > 35:
            raise ValueError(f"Shot {index} needs at most 35 spoken words")
    return episode
