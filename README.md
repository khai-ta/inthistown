# In This Town

A local production pipeline for original vertical block-character stories. The pilot, **Mom’s Yellow Doors**, introduces a strange town rule, shows it in action, and ends on a reversal. Blender renders the same cast across shots. ElevenLabs can speak the lines with word timings, and FFmpeg adds captions and assembles the MP4. A macOS narration option is available for previews.

## Render the pilot

On macOS, install Blender 5.3, Python 3.10 or later, and FFmpeg with libass. Homebrew's Blender cask and FFmpeg formula provide the tools used for the pilot.

```sh
brew install --cask blender
brew install ffmpeg
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python make_video.py episodes/doors.json -o output/moms-yellow-doors.mp4
```

The standard render is 540 × 960 at 24 fps. Preview timing with `--width 180 --fps 12`, or use `--width 1080` for a larger export. Blender uses Eevee by default. Pass `--engine cycles` for CPU rendering if Eevee is unavailable. The run prints each shot as it starts. The final MP4 appears after all shots finish.

### Narration

Run `npx -y @elevenlabs/cli@latest onboard init` for browser-based setup. The renderer reads `ELEVENLABS_API_KEY` from the gitignored `.env.local` file. You can also set it in your shell or save it as the password of a generic macOS Keychain item named `inthistown-elevenlabs`. Run with `--provider elevenlabs` to require ElevenLabs. The default is George with Multilingual v2. Set `--voice YOUR_VOICE_ID` to use a different ElevenLabs voice or `--model YOUR_MODEL_ID` to change models. This submits the episode lines to ElevenLabs and uses account credits. Captions follow the returned speech timings.

If your narration comes from ElevenLabs MCP, generate each shot's `line` separately. Save the audio as `shot-01.mp3`, `shot-02.mp3`, and so on in one folder. Run `.venv/bin/python make_video.py episodes/doors.json --narration-dir path/to/voiceover -o output/moms-yellow-doors.mp4`. WAV and M4A files also work. Imported audio uses estimated caption timings unless you render directly through the timestamp API.

For offline previews, pass `--provider local`. Run `say -v '?'` to list voices installed on the Mac. Try `--voice Daniel --rate 175` to change the local narrator. Blender installed outside your PATH can be selected with `--blender /Applications/Blender.app/Contents/MacOS/Blender`.

## Make another short

Copy `episodes/doors.json` to a new episode file. Give each shot one action and one short line of narration. Use the existing shots for another story set in this town, or add a new scene and action in `render.py` and `episode.py` for a different visual premise.

| Action | What happens on screen |
| --- | --- |
| `town` | The narrator walks down the town's main street. |
| `lie` | The narrator talks to Mom in the hallway. |
| `appear` | A yellow door grows out of the wall. |
| `knock` | The camera pushes in as the door shakes three times. |
| `open` | A double steps out of the doorway holding the hidden hammer. |
| `twist` | The other doors turn yellow and knock. |

For a new premise, ask Codex from this checkout to write the original episode, add the visual actions it needs, and render a preview MP4. For example, “Make a 25-second episode where every apology swaps two people's voices. Show the first swap, then end with a visual twist.” The local CLI takes the authored JSON as input. It handles production after the story and scene actions are in place.

Local narration captions estimate word timings from line durations. Foreground sound effects and all 3D assets are generated locally.

## Verify

```sh
.venv/bin/python -m unittest discover -s tests
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,duration output/moms-yellow-doors.mp4
```

## Render The Door With My Name

This longer episode uses Roblox's [official Blocky R15 reference avatar](https://create.roblox.com/docs/avatar/resources) for the cast, with custom colors and face details. Download the FBX once, then generate Adam narration at 1.35×. FFmpeg preserves the pitch and scales the ElevenLabs word timings to match.

```sh
.venv/bin/python fetch_avatar.py
.venv/bin/python make_video.py episodes/yellow-doors.json --provider elevenlabs --voice Adam --tempo 1.35 --width 540 -o output/the-door-with-my-name.mp4
```

To mix a local copy of “Numbers” by TEMPOREX under the narration, run the following. Adjust `--music-start` in seconds or `--music-gain` as needed. The soundtrack is a separate input and the picture is copied at its original quality.

```sh
.venv/bin/python mix_music.py output/the-door-with-my-name.mp4 "/path/to/Numbers.mp3" output/the-door-with-my-name-numbers.mp4
```

## Render Everybody Bet Yes

The Kalshi-town episode uses three [official Roblox avatar bodies](https://create.roblox.com/docs/avatar/resources) with different silhouettes and rigs. Its edit uses moving cameras, bent-joint animation, phone and fountain inserts, animated captions and original sound effects.

```sh
.venv/bin/python fetch_avatar.py --market
.venv/bin/python make_video.py episodes/kalshi-town.json --provider elevenlabs --voice Adam --tempo 1.4 -o output/everybody-bet-yes-voice.mp4
.venv/bin/python mix_music.py output/everybody-bet-yes-voice.mp4 "/path/to/TempoRex Instrumental.mp3" output/everybody-bet-yes.mp4 --music-gain .30
```

### Use avatars from a Studio project

The renderer can work from official reference bodies without a live Studio session. To direct a cast inside Studio, install and open Roblox Studio and enable **Assistant → Manage MCP Servers → Enable Studio as MCP server**. Choose Codex CLI under **Quick connect** or use [Roblox's official Codex integration](https://github.com/Roblox/roblox-studio-agent-plugin). Restart the client and look for Studio's green connection indicator. In a connected place, Roblox Studio can insert a default R6 or R15 rig, your own avatar, or an avatar specified by username or user ID through Rig Builder. See [Studio MCP setup](https://create.roblox.com/docs/studio/mcp) and [Rig Builder](https://create.roblox.com/docs/studio/rig-builder).
