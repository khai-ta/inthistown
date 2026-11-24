# In This Town

A local production pipeline for original vertical block-character stories. The pilot, **Mom’s Yellow Doors**, introduces a strange town rule, shows it in action, and ends on a reversal. Blender renders the same cast across shots. ElevenLabs can speak the lines with word timings, and FFmpeg adds captions and assembles the MP4. A macOS narration option is available for previews.

## Render the pilot

On macOS, install Blender 5.3, Python 3.6 or later, and FFmpeg with libass. Homebrew's Blender cask and FFmpeg formula provide the tools used for the pilot.

```sh
brew install --cask blender
brew install ffmpeg
python3 make_video.py episodes/doors.json -o output/moms-yellow-doors.mp4
```

The standard render is 540 × 960 at 24 fps. Preview timing with `--width 180 --fps 12`, or use `--width 1080` for a larger export. Blender uses Eevee by default. Pass `--engine cycles` for CPU rendering if Eevee is unavailable. The run prints each shot as it starts. The final MP4 appears after all shots finish.

### Narration

Set `ELEVENLABS_API_KEY` in your local shell or save it as the password of a generic macOS Keychain item named `inthistown-elevenlabs`. Run with `--provider elevenlabs` to require ElevenLabs. The default is George with Multilingual v2. Set `--voice YOUR_VOICE_ID` to use a different ElevenLabs voice or `--model YOUR_MODEL_ID` to change models. This submits the episode lines to ElevenLabs and uses account credits. Captions follow the returned speech timings.

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
python3 -m unittest discover -s tests
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,duration output/moms-yellow-doors.mp4
```
