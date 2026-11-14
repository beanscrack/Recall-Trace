"""Encode real browser screenshots plus narration into a 60-second submission video.

Run after browser_demo_check.py has captured .local/qa screenshots and narration.wav
has been supplied in that directory. Requires optional imageio-ffmpeg from requirements-dev.txt.
This edits presentation only; it never creates or alters decision/replay measurements.
"""
import argparse
import subprocess
import wave
from pathlib import Path
import imageio_ffmpeg

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', type=Path, default=root / '.local' / 'qa')
parser.add_argument('--output', type=Path, default=root / '.local' / 'RecallTrace-demo.mp4')
args = parser.parse_args()
directory = args.directory.resolve()
scenes = [('01-incident.png', 7), ('00-code.png', 10), ('02-unsafe-decision.png', 8),
          ('03-replay.png', 11), ('04-evidence-review.png', 9), ('05-before-after.png', 9),
          ('06-isolation.png', 6)]
for name, _ in scenes:
    if not (directory / name).is_file(): raise SystemExit('Missing captured scene: ' + name)
with wave.open(str(directory / 'narration.wav')) as audio:
    duration = audio.getnframes() / audio.getframerate()
if not 30 <= duration <= 120: raise SystemExit('Narration should be between 30 and 120 seconds')
playlist = directory / 'scenes.txt'
playlist.write_text(''.join(f"file '{name}'\nduration {seconds}\n" for name, seconds in scenes)
                    + f"file '{scenes[-1][0]}'\n")
args.output.parent.mkdir(parents=True, exist_ok=True)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
command = [ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', str(playlist), '-i', str(directory / 'narration.wav'),
           '-vf', 'fps=30,scale=1440:960,format=yuv420p', '-af', f'atempo={duration / 60},apad',
           '-t', '60', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
           '-movflags', '+faststart', str(args.output.resolve())]
subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
# Decode both streams to catch corrupt output, instead of merely checking file existence.
subprocess.run([ffmpeg, '-v', 'error', '-i', str(args.output.resolve()), '-f', 'null', '-'], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
print('PASS: 60-second video encoded and decoded with narration:', args.output.resolve())
