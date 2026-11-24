"""Add a local soundtrack under the narration without re-rendering the picture."""
import argparse
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from make_video import ffmpeg


def mix(video, music, output, start, gain):
    if output.resolve() in {video.resolve(), music.resolve()}:
        raise ValueError("Choose a separate output file")
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output needs an .mp4 extension")
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=duration", "-of", "csv=p=0", str(video),
    ]))
    fade = min(.6, duration / 2)
    filters = (
        "[0:a]aformat=channel_layouts=stereo[voice];"
        f"[1:a]aformat=channel_layouts=stereo,volume={gain},apad,"
        f"afade=t=in:d={fade},afade=t=out:st={duration-fade}:d={fade}[music];"
        "[voice][music]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95:level=0:latency=1[audio]"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".music-", dir=output.parent) as work:
        temporary = Path(work) / "mix.mp4"
        ffmpeg("-i", str(video), "-ss", str(start), "-i", str(music),
               "-filter_complex", filters, "-map", "0:v:0", "-map", "[audio]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", str(temporary))
        temporary.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("music", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--music-start", type=float, default=0, help="Starting offset in seconds")
    parser.add_argument("--music-gain", type=float, default=.16, help="Linear soundtrack gain")
    args = parser.parse_args()
    if not math.isfinite(args.music_start) or args.music_start < 0:
        parser.error("Music start must be a non-negative time")
    if not 0 <= args.music_gain <= 1:
        parser.error("Music gain must be between 0 and 1")
    try:
        mix(args.video, args.music, args.output, args.music_start, args.music_gain)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Mix failed: {error}\n")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
