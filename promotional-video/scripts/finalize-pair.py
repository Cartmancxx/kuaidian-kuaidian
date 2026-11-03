"""Pair the independently rendered SFX audio with an identical video bitstream.

First render both versions through the composition's bgm prop. This step does
not remove music from a mixed track: it keeps the already-rendered SFX track
and losslessly remuxes it with the main picture to eliminate codec variance.
"""
from pathlib import Path
import shutil, subprocess, argparse

OUT=Path(__file__).resolve().parent.parent/'out'
main=OUT/'kuaidian-kuaidian-launch.mp4'
sfx=OUT/'kuaidian-kuaidian-launch-sfx.mp4'
assert main.is_file() and sfx.is_file(), 'Render both versions first.'
parser=argparse.ArgumentParser()
parser.add_argument('--sfx-audio-source',type=Path,help='Optional independent bgm=false export; default is the current SFX export.')
args=parser.parse_args()
audio_source=args.sfx_audio_source or sfx
assert audio_source.is_file(), 'Missing SFX audio source.'
qa=OUT/'qa';qa.mkdir(parents=True,exist_ok=True)
backup=qa/'kuaidian-kuaidian-launch-sfx-independent-encode.mp4'
# Preserve the first independent export instead of overwriting the evidence.
if not backup.exists(): shutil.copy2(sfx,backup)
temp=OUT/'kuaidian-kuaidian-launch-sfx-mux.mp4'
subprocess.run(['ffmpeg','-hide_banner','-y','-i',str(main),'-i',str(audio_source),
    '-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(temp)],check=True)
temp.replace(sfx)
print('SFX audio preserved; both exports now use the same compressed video stream.')
