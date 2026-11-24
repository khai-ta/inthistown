"""Render an episode to a narrated vertical MP4 on macOS."""

import argparse
import math
import os
from pathlib import Path
import re
import sys
import shutil
import subprocess
import tempfile
import wave

from episode import read_episode

ROOT = Path(__file__).resolve().parent
SAMPLE_RATE = 48000
PAD_START = .14
PAD_END = .36
CAPTION_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 540
PlayResY: 960
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Story,Arial,43,&H00F9F9FF,&H000000FF,&H00101923,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,45,55,195,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def run(*command, cwd=None):
    subprocess.run(command, cwd=cwd, check=True)


def ffmpeg(*args, cwd=None):
    run("ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args, cwd=cwd)


def caption_time(seconds):
    ticks = round(seconds * 100)
    minutes, remainder = divmod(ticks, 6000)
    whole, fraction = divmod(remainder, 100)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{whole:02}.{fraction:02}"


def captions(line, seconds, offset):
    words = line.replace("{", "(").replace("}", ")").replace(chr(92), "/").split()
    groups = []
    current = []
    for word in words:
        if current and (len(current) >= 5 or len(" ".join(current + [word])) > 22):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    start = offset + PAD_START
    events = []
    for group in groups:
        end = start + seconds * len(group) / len(words)
        text = " ".join(group)
        events.append(f"Dialogue: 0,{caption_time(start)},{caption_time(end)},Story,,0,0,0,,{text}")
        start = end
    return events


def sound_effect(path, action, duration):
    if action == "knock":
        cues = [(duration * t, 115, .20, .16) for t in (.37, .53, .69)]
    elif action == "appear":
        cues = [(duration / 3, 528, .30, .09)]
    elif action == "open":
        cues = [(duration / 3, 180, .45, .065)]
    elif action == "twist":
        cues = [(duration * .66, 73, .64, .10)]
    else:
        return False
    from array import array

    samples = array("h", [0]) * round(duration * SAMPLE_RATE)
    for start, pitch, length, gain in cues:
        position = round(start * SAMPLE_RATE)
        for i in range(min(round(length * SAMPLE_RATE), len(samples) - position)):
            t = i / SAMPLE_RATE
            envelope = min(t * 700, 1) * math.exp(-5 * t / length)
            tone = math.sin((2 * math.pi) * pitch * t) + .23 * math.sin((2 * math.pi) * pitch * 2.7 * t)
            samples[position + i] += round(32767 * gain * envelope * tone)
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(path), "wb") as file:
        file.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        file.writeframes(samples.tobytes())
    return True


def render_episode(args):
    episode_path = args.episode.resolve()
    output = args.output.resolve()
    episode = read_episode(episode_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".episode-", dir=output.parent) as temp:
        work = Path(temp)
        events = []
        clips = []
        audio_files = []
        total_frames = 0
        for index, shot in enumerate(episode["shots"]):
            print(f"Shot {index + 1}/{len(episode['shots'])} · {shot['action']}", flush=True)
            # Read plain narration from a file. Escape the macOS speech command opener.
            text = re.sub(r"\[\[", "[ [", shot["line"])
            (work / "line.txt").write_text(text, encoding="utf-8")
            run("say", "-v", args.voice, "-r", str(args.rate), "-f", "line.txt", "-o", "speech.aiff", cwd=work)
            ffmpeg("-i", "speech.aiff", "-ar", str(SAMPLE_RATE), "-ac", "1", "speech.wav", cwd=work)
            with wave.open(str(work / "speech.wav"), "rb") as file:
                speech = file.getnframes() / file.getframerate()
            frames = max(12, math.ceil((speech + PAD_START + PAD_END) * args.fps))
            duration = frames / args.fps
            events.extend(captions(shot["line"], speech, total_frames / args.fps))
            stem = f"shot-{index:03d}-"
            with (work / "render.log").open("w") as log:
                result = subprocess.run([
                    args.blender, "-b", "-t", str(args.threads), "--python-exit-code", "1",
                    "--python", str(ROOT / "render.py"), "--", str(episode_path), str(index),
                    str(frames), str(args.width), str(args.fps),
                    "CYCLES" if args.engine == "cycles" else "BLENDER_EEVEE", str(work / stem)
                ], stdout=log, stderr=subprocess.STDOUT)
            raw = list(work.glob(f"{stem}*.mp4"))
            if result.returncode or len(raw) != 1:
                raise RuntimeError((work / "render.log").read_text()[-4000:])
            audio_name = f"voice-{index:03d}.wav"
            effects = sound_effect(work / "effects.wav", shot["action"], duration)
            inputs = ["-i", "effects.wav"] if effects else []
            audio = f"[0:a]adelay={round(PAD_START * 1000)},apad"
            if effects:
                audio += "[voice];[voice][1:a]amix=inputs=2:duration=first:normalize=0"
            ffmpeg("-i", "speech.wav", *inputs, "-filter_complex", audio + "[audio]",
                   "-map", "[audio]", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le",
                   "-t", str(duration), audio_name, cwd=work)
            clips.append(f"file '{raw[0].name}'")
            audio_files.append(work / audio_name)
            total_frames += frames
        with wave.open(str(work / "narration.wav"), "wb") as file:
            file.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
            for path in audio_files:
                with wave.open(str(path), "rb") as part:
                    file.writeframes(part.readframes(part.getnframes()))
        (work / "clips.txt").write_text("\n".join(clips) + "\n")
        (work / "captions.ass").write_text(CAPTION_HEADER + "\n".join(events) + "\n", encoding="utf-8")
        ffmpeg("-f", "concat", "-safe", "1", "-i", "clips.txt", "-i", "narration.wav",
               "-map", "0:v", "-map", "1:a", "-vf", "ass=captions.ass",
               "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-b:a", "160k", "-movflags", "+faststart", "final.mp4", cwd=work)
        (work / "final.mp4").replace(output)
    print(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "output" / "episode.mp4")
    parser.add_argument("--voice", default="Samantha")
    parser.add_argument("--rate", type=int, default=188, help="Words per minute")
    parser.add_argument("--width", type=int, choices=(180, 360, 540, 720, 1080), default=540)
    parser.add_argument("--fps", type=int, choices=(12, 24, 30), default=24)
    parser.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    parser.add_argument("--blender", default="blender")
    args = parser.parse_args()
    for program in (args.blender, "ffmpeg", "say"):
        if not shutil.which(program):
            parser.error(f"Missing executable: {program}")
    if args.rate < 1 or args.threads < 1:
        parser.error("Rate and thread count must be positive")
    if args.output.suffix.lower() != ".mp4":
        parser.error("Output needs an .mp4 extension")
    try:
        render_episode(args)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Render failed: {error}\n")


if __name__ == "__main__":
    main()
