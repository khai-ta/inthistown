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

from dotenv import dotenv_values

from episode import read_episode
from eleven_voice import ADAM_VOICE, DEFAULT_MODEL, DEFAULT_VOICE, speak
from fetch_avatar import TARGET as AVATAR_FILE

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


def captions(line, seconds, offset, words=None, single_word=False):
    if not words:
        tokens = line.split()
        step = seconds / len(tokens)
        words = [(token, i * step, (i + 1) * step) for i, token in enumerate(tokens)]
    groups = []
    current = []
    for word, start, end in words:
        word = word.replace("{", "(").replace("}", ")").replace(chr(92), "/")
        if current and (single_word or len(current) >= 5 or len(" ".join(item[0] for item in current) + " " + word) > 23):
            groups.append(current)
            current = []
        current.append((word, start, end))
        if word.endswith((".", "!", "?", "…")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    base = offset + PAD_START
    events = []
    for index, group in enumerate(groups):
        start = group[0][1]
        next_start = groups[index + 1][0][1] if index + 1 < len(groups) else seconds
        end = min(seconds, next_start, max(group[-1][2], start + .22) + .07)
        if end > start:
            text = " ".join(item[0] for item in group)
            events.append(f"Dialogue: 0,{caption_time(base + start)},{caption_time(base + end)},Story,,0,0,0,,{text}")
    return events


def imported_tracks(directory, count):
    tracks = []
    for index in range(1, count + 1):
        stem = f"shot-{index:02d}"
        matches = [directory / (stem + suffix) for suffix in (".mp3", ".wav", ".m4a")]
        files = [path for path in matches if path.is_file()]
        if len(files) != 1:
            raise ValueError(f"Expected one {stem}.mp3, .wav, or .m4a in {directory}")
        tracks.append(files[0])
    return tracks


def narration(args, shots, index, work, tracks):
    line = shots[index]["line"]
    if tracks:
        source = tracks[index]
        words = None
    elif args.provider == "elevenlabs":
        previous = shots[index - 1]["line"] if index else None
        following = shots[index + 1]["line"] if index + 1 < len(shots) else None
        audio, words = speak(args.api_key, args.voice or DEFAULT_VOICE, args.model, line, previous, following)
        source = work / "speech.mp3"
        source.write_bytes(audio)
    else:
        text = re.sub(r"\[\[", "[ [", line)
        (work / "line.txt").write_text(text, encoding="utf-8")
        source = work / "speech.aiff"
        run("say", "-v", args.voice or "Samantha", "-r", str(args.rate), "-f", "line.txt",
            "-o", source.name, cwd=work)
        words = None
    tempo_filter = ["-af", f"atempo={args.tempo}"] if args.tempo != 1 else []
    ffmpeg("-i", str(source), *tempo_filter, "-ar", str(SAMPLE_RATE), "-ac", "1", "speech.wav", cwd=work)
    if words and args.tempo != 1:
        words = [(word, start / args.tempo, end / args.tempo) for word, start, end in words]
    with wave.open(str(work / "speech.wav"), "rb") as file:
        seconds = file.getnframes() / file.getframerate()
    return seconds, words


def sound_effect(path, action, duration):
    if action == "lie":
        cues = [(.025, 91, .18, .10)]
    elif action == "knock":
        cues = [(duration * t, 115, .20, .16) for t in (.37, .53, .69)]
    elif action == "appear":
        cues = [(duration / 3, 88, .26, .16), (duration / 3, 528, .34, .07)]
    elif action == "open":
        cues = [(.02, 340, .13, .07), (duration / 3, 126, .43, .085)]
    elif action == "twist":
        cues = [(duration * t, pitch, .21, .18) for t, pitch in ((.69, 98), (.8, 136), (.87, 78))]
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
            pulse = samples[position + i] + round(32767 * gain * envelope * tone)
            samples[position + i] = max(-32768, min(32767, pulse))
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(path), "wb") as file:
        file.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        file.writeframes(samples.tobytes())
    return True


def cut_effects(action, first_frame, frames, fps):
    if action == "appear":
        impact = first_frame + max(2, frames // 3) - 1
        return [f"drawbox=c=white@.28:t=fill:enable='eq(n,{impact})'",
                f"drawbox=c=white@.11:t=fill:enable='eq(n,{impact+1})'"]
    if action == "twist":
        fade_frames = min(round(.25 * fps), frames - 1)
        end = first_frame + frames
        return [f"fade=t=out:s={end-fade_frames-1}:n={fade_frames}"]
    return []


def render_episode(args):
    episode_path = args.episode.resolve()
    output = args.output.resolve()
    episode = read_episode(episode_path)
    if episode.get("avatar") == "roblox-r15" and not AVATAR_FILE.is_file():
        raise ValueError("Run python fetch_avatar.py to download Roblox’s blocky R15 rig")
    shorts_style = episode.get("style") == "shorts"
    tracks = imported_tracks(args.narration_dir.resolve(), len(episode["shots"])) if args.narration_dir else []
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".episode-", dir=output.parent) as temp:
        work = Path(temp)
        events = []
        clips = []
        audio_files = []
        flashes = []
        total_frames = 0
        for index, shot in enumerate(episode["shots"]):
            print(f"Shot {index + 1}/{len(episode['shots'])} · {shot['action']}", flush=True)
            speech, words = narration(args, episode["shots"], index, work, tracks)
            frames = max(12, math.ceil((speech + PAD_START + PAD_END) * args.fps))
            duration = frames / args.fps
            events.extend(captions(shot["line"], speech, total_frames / args.fps, words, shorts_style))
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
            effects = cut_effects(shot["action"], total_frames, frames, args.fps)
            if shot["action"] != "twist" or index == len(episode["shots"]) - 1:
                flashes.extend(effects)
            total_frames += frames
        with wave.open(str(work / "narration.wav"), "wb") as file:
            file.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
            for path in audio_files:
                with wave.open(str(path), "rb") as part:
                    file.writeframes(part.readframes(part.getnframes()))
        (work / "clips.txt").write_text("\n".join(clips) + "\n")
        caption_header = CAPTION_HEADER
        if shorts_style:
            caption_header = caption_header.replace("Arial,43", "Arial,44").replace(",2,45,55,195,1", ",2,45,55,446,1")
        (work / "captions.ass").write_text(caption_header + "\n".join(events) + "\n", encoding="utf-8")
        ffmpeg("-f", "concat", "-safe", "1", "-i", "clips.txt", "-i", "narration.wav",
               "-map", "0:v", "-map", "1:a", "-vf", ",".join(flashes + ["ass=captions.ass"]),
               "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-b:a", "160k", "-movflags", "+faststart", "final.mp4", cwd=work)
        (work / "final.mp4").replace(output)
    print(output)


def elevenlabs_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        key = (dotenv_values(ROOT / ".env.local").get("ELEVENLABS_API_KEY") or "").strip()
    if key or sys.platform != "darwin":
        return key
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "inthistown-elevenlabs", "-w"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    return result.stdout.decode().strip() if result.returncode == 0 else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "output" / "episode.mp4")
    voice_source = parser.add_mutually_exclusive_group()
    voice_source.add_argument("--provider", choices=("local", "elevenlabs"))
    voice_source.add_argument("--narration-dir", type=Path, help="Import shot-01.mp3, shot-02.mp3, etc.")
    parser.add_argument("--tempo", type=float, default=1.0, help="Pitch-preserving narration speed multiplier")
    parser.add_argument("--voice", help="ElevenLabs voice ID or macOS voice name")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="ElevenLabs model ID")
    parser.add_argument("--rate", type=int, default=188, help="Words per minute")
    parser.add_argument("--width", type=int, choices=(180, 360, 540, 720, 1080), default=540)
    parser.add_argument("--fps", type=int, choices=(12, 24, 30), default=24)
    parser.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    parser.add_argument("--blender", default="blender")
    args = parser.parse_args()
    if args.voice and args.voice.lower() == "adam" and args.provider != "local":
        args.voice = ADAM_VOICE
    if not .5 <= args.tempo <= 2:
        parser.error("Tempo must be between 0.5 and 2")
    args.api_key = elevenlabs_key() if not args.narration_dir and args.provider != "local" else ""
    args.provider = args.provider or ("elevenlabs" if args.api_key else "local")
    if args.provider == "elevenlabs" and not args.api_key:
        parser.error("Set ELEVENLABS_API_KEY in .env.local, your shell, or the inthistown-elevenlabs Keychain entry")
    dependencies = [args.blender, "ffmpeg"]
    if args.provider == "local" and not args.narration_dir:
        dependencies.append("say")
    for program in dependencies:
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
