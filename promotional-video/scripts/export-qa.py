"""Extract evidence from the encoded MP4, never from preview-only stills."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'out';QA=OUT/'qa'/'final'
QA.mkdir(parents=True,exist_ok=True)
frames=[0,22,32,36,41,48,60,75,100,126,130,134,145,149,150,210,280,300,329,330,360,395,450,479,480,540,600,630,659,660,700,750,779,780,782,785,790,794,800,822,830,838,840,846,852,900,930,959]
select='+'.join(f'eq(n\\,{f})' for f in frames)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'kuaidian-kuaidian-launch.mp4'),'-vf',f'select={select}','-vsync','0',str(QA/'decode-%03d.png')],check=True)
for i,f in enumerate(frames,1):(QA/f'decode-{i:03d}.png').replace(QA/f'f{f}.png')
for name,fps,tile in [('contact-sheet.jpg','1/2','4x4'),('mobile-sheet.jpg','1/4','2x4')]:
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'kuaidian-kuaidian-launch.mp4'),'-vf',f'fps={fps},scale=480:-1,tile={tile}','-frames:v','1',str(QA/name)],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-ss','31','-i',str(OUT/'kuaidian-kuaidian-launch.mp4'),'-frames:v','1',str(OUT/'kuaidian-kuaidian-poster.png')],check=True)
print(f'Extracted {len(frames)} decoded final frames, two sheets, and the poster.')
