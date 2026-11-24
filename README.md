# In This Town

A local production pipeline for original vertical block-character stories. The pilot, **The Door That Knocked Back**, introduces a strange town rule, shows it in action, and ends on a reversal. Blender renders the same cast across shots. macOS speaks the lines, and FFmpeg adds timed captions and assembles the MP4.

## Render the pilot

On macOS, install Blender 5.3, Python 3.6 or later, and FFmpeg with libass. Homebrew's Blender cask and FFmpeg formula provide the tools used for the pilot.

```sh
brew install --cask blender
brew install ffmpeg
python3 make_video.py episodes/doors.json -o output/the-door-that-knocked-back.mp4
```

The standard render is 540 × 960 at 24 fps. Preview timing with `--width 180 --fps 12`, or use `--width 1080` for a larger export. Blender uses Eevee by default. Pass `--engine cycles` for CPU rendering if Eevee is unavailable. The run prints each shot as it starts. The final MP4 appears after all shots finish.

Run `say -v '?'` to list voices installed on the Mac. Choose one with `--voice Daniel` or change the delivery speed with `--rate 175`. If Blender is installed outside your PATH, pass `--blender /Applications/Blender.app/Contents/MacOS/Blender`.

## Make another short

Copy `episodes/doors.json` to a new episode file. Give each shot one action and one short line of narration. Use the existing shots for another story set in this town, or add a new scene and action in `render.py` and `episode.py` for a different visual premise.

| Action | What happens on screen |
| --- | --- |
| `town` | The narrator walks down the town's main street. |
| `lie` | The narrator talks to Mom in the hallway. |
| `appear` | A yellow door grows out of the wall. |
| `knock` | The camera pushes in as the door shakes three times. |
| `open` | A double steps out of the doorway holding a clock. |
| `twist` | The hallway walls turn yellow. |

For a new premise, ask Codex from this checkout to write the original episode, add the visual actions it needs, and render a preview MP4. For example, “Make a 25-second episode where every apology swaps two people's voices. Show the first swap, then end with a visual twist.” The local CLI takes the authored JSON as input. It handles production after the story and scene actions are in place.

Captions are timed from the duration of each spoken line, with reading groups estimated by word count. Any foreground sound effects are synthesized locally. The render uses original procedural assets and requires no paid video credits or network calls once the tools and voice are installed.

## Verify

```sh
python3 -m unittest discover -s tests
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,duration output/the-door-that-knocked-back.mp4
```
