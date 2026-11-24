"""Assemble a 105-second recruiting cut from timed speech and rendered shots."""

import argparse
from array import array
import json
import math
from pathlib import Path
import random
import sys
from tempfile import TemporaryDirectory
import wave

from episode import read_episode
from make_video import CAPTION_HEADER, SAMPLE_RATE, assemble_video, caption_time, captions, ffmpeg

FPS = 24


def write_wave(path, samples):
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(path), "wb") as sound:
        sound.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        sound.writeframes(samples.tobytes())


def foley(path, offsets, durations):
    """Build the hard opening sound cut and the desk and interview cues."""
    samples = array("h", [0]) * round(sum(durations) * SAMPLE_RATE)
    noise = random.Random(19)
    for i in range(round(durations[0] * SAMPLE_RATE)):
        t = i / SAMPLE_RATE
        tick = t % .46875
        kick = .39 * math.sin(math.tau * (67*tick - 35*tick*tick)) * math.exp(-tick*19)
        bass = .14 * math.sin(math.tau * 55*t) * math.exp(-tick*6)
        chatter = .040 * noise.uniform(-1, 1)
        samples[i] = round(32767 * (kick + bass + chatter))
    for index in (1, 2, 3, 4, 6, 7, 8, 9, 19, 20):
        clicks = (.19,.24,.34,.46,.54) if index in {3,4,7,8,20} else (.32,.59)
        for beat in clicks:
            at = round((offsets[index]+beat*durations[index])*SAMPLE_RATE)
            for j in range(min(680,len(samples)-at)):
                samples[at+j] += round(32767*.095*noise.uniform(-1,1)*math.exp(-j/135))
    for second in range(50, 69):
        start = round(second*SAMPLE_RATE)
        for i in range(700):
            samples[start+i] += round(32767*.06*math.sin(math.tau*1550*i/SAMPLE_RATE)*math.exp(-i/144))
    for index, pitch in ((5,223),(9,698),(10,540),(22,600)):
        start = round((offsets[index]+.10)*SAMPLE_RATE)
        for j in range(3900):
            samples[start+j] += round(32767*.12*math.sin(math.tau*pitch*j/SAMPLE_RATE)*math.exp(-j/950))
    write_wave(path, samples)


def assemble(work, episode, music, output):
    shots = read_episode(episode)["shots"]
    frames = json.loads((work/"frames.json").read_text())
    if len(shots) != len(frames) or sum(frames) != 105*FPS:
        raise ValueError("The recruiting edit requires the timed 105-second timeline")
    for index, length in enumerate(frames):
        if not (work/f"shot-{index:03d}-0001-{length:04d}.mp4").is_file():
            raise ValueError(f"Missing rendered shot {index + 1}")
    offset = 0
    events = []
    durations = [length/FPS for length in frames]
    offsets = []
    with wave.open(str(work/"narration.wav"), "wb") as narration:
        narration.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        for index, (shot, duration) in enumerate(zip(shots, durations)):
            cache = work/f"speech-{index:02d}"
            speech, words = json.loads((cache/"timing.json").read_text())
            lead = .94 if index == len(shots)-1 else .10
            speed = max(1, speech/max(.25, duration-lead-.18))
            spoken = speech/speed
            rendered = cache/"padded.wav"
            ffmpeg("-i",str(cache/"speech.wav"),"-af",
                   f"atempo={speed},adelay={round(lead*1000)},apad",
                   "-t",str(duration),"-ac","1","-ar",str(SAMPLE_RATE),
                   "-c:a","pcm_s16le",str(rendered))
            with wave.open(str(rendered), "rb") as wav:
                count = round(duration*SAMPLE_RATE)
                narration.writeframes(wav.readframes(count).ljust(count*2,b"\0"))
            adjusted = [(word,start/speed,end/speed) for word,start,end in words] if words else None
            events.extend(captions(shot["line"],spoken,offset+lead-.14,adjusted,True,208))
            offsets.append(offset)
            offset += duration
    (work/"clips.txt").write_text("".join(
        f"file 'shot-{index:03d}-0001-{length:04d}.mp4'\n" for index,length in enumerate(frames)))
    title_start=103.30
    header=CAPTION_HEADER.replace("\n[Events]", """
Style: Title,Arial,48,&H00F9F9FF,&H000000FF,&H00101923,&H80000000,-1,0,0,0,100,100,2,0,1,1,0,5,32,32,12,1

[Events]""")
    events.append(f"Dialogue: 1,{caption_time(title_start)},0:01:45.00,Title,,0,0,0,,RECRUITING SEASON.")
    (work/"captions.ass").write_text(header+"\n".join(events)+"\n")
    assemble_video(work,[f"fade=t=out:st={title_start-.31}:d=.30"],FPS,"picture.mp4")
    foley(work/"foley.wav",offsets,durations)

    # The opening club track stops with the first desk cut. Music returns for
    # the application montage, slows in the reflection, then cuts for the tag.
    ending = offsets[-1]
    filters = (
        "[3:a]asplit=2[up][slow];"
        "[up]atrim=duration=58,asetpts=PTS-STARTPTS,atempo=1.06,apad,atrim=duration=58,"
        "afade=t=in:d=.25,afade=t=out:st=57.60:d=.40,volume=.20,adelay=12000[m1];"
        f"[slow]atrim=start=28,asetpts=PTS-STARTPTS,atempo=.84,atrim=duration={ending-70},"
        f"afade=t=in:d=.50,afade=t=out:st={ending-70-.20}:d=.20,volume=.23,adelay=70000[m2];"
        "[1:a][2:a][m1][m2]amix=inputs=4:duration=first:normalize=0,"
        "alimiter=limit=.94:level=0:latency=1[mix]"
    )
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix=".recruiting-",dir=output.parent) as temporary:
        result=Path(temporary)/"export.mp4"
        ffmpeg("-i",str(work/"picture.mp4"),"-i",str(work/"narration.wav"),
               "-i",str(work/"foley.wav"),"-i",str(music),"-filter_complex",filters,
               "-map","0:v:0","-map","[mix]","-c:v","copy","-c:a","aac","-b:a","192k",
               "-t","105","-movflags","+faststart",str(result))
        result.replace(output)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("work","episode","music","output"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    assemble(args.work.resolve(),args.episode.resolve(),args.music.resolve(),args.output.resolve())
