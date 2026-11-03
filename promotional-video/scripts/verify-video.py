"""Decode exports and check specifications, perceptual alignment and audio peaks.

Independent H.264 encodes need not decode to bit-identical pixels. The two
compositions share the same visual/SFX graph; optional lossless still pairs
provide a stricter source-render check, while decoded SSIM checks all frames.
"""
from pathlib import Path
import json, subprocess, hashlib, re
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'out'
(OUT/'qa').mkdir(parents=True,exist_ok=True)
def run(args):return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
report={'renders':{},'cutBeatCheck':[]}
hashes=[]
for stem in ['kuaidian-kuaidian-launch','kuaidian-kuaidian-launch-sfx']:
    file=OUT/(stem+'.mp4');meta=probe(file)
    video=next(s for s in meta['streams'] if s['codec_type']=='video')
    assert video['width']==1920 and video['height']==1080 and video['nb_frames']=='960'
    assert video['avg_frame_rate']=='30/1'
    assert abs(float(meta['format']['duration'])-32)<.1
    framemd5=run(['ffmpeg','-v','error','-i',str(file),'-map','0:v:0','-f','framemd5','-']).decode()
    imagehash=[line.split(',')[-1].strip() for line in framemd5.splitlines() if line and not line.startswith('#')]
    assert len(imagehash)==960;hashes.append(imagehash)
    (OUT/'qa'/(stem+'.framemd5')).write_text(framemd5,encoding='utf-8')
    wav=run(['ffmpeg','-v','error','-i',str(file),'-vn','-ac','1','-ar','48000','-f','f32le','-'])
    a=np.frombuffer(wav,dtype='<f4');peak=float(np.max(np.abs(a)))
    assert peak<.99,peak
    streamhash=run(['ffmpeg','-v','error','-i',str(file),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip().split('=')[-1]
    report['renders'][stem]={'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'videoStreamSha256':streamhash,'frames':len(imagehash),'duration':meta['format']['duration'],'videoCodec':video['codec_name'],'pixelFormat':video['pix_fmt'],'peakDbFS':round(20*np.log10(peak),2)}
    audiohash=run(['ffmpeg','-v','error','-i',str(file),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip().split('=')[-1]
    quiet=a[round(18.5*48000):round(21.5*48000)]
    report['renders'][stem].update({'audioStreamSha256':audiohash,'decodedAudioRms':round(float(np.sqrt(np.mean(a*a))),9),'noSfxWindow18_5to21_5sPeak':float(np.max(np.abs(quiet)))})
    if stem.endswith('-sfx'): assert np.max(np.abs(quiet))<.00001, 'Unexpected audio in no-SFX interval'
    else: assert np.max(np.abs(quiet))>.01, 'Music missing in BGM interval'
    if stem=='kuaidian-kuaidian-launch':
        # Quantify decoded low-frequency kick energy within +-3 frames of each cut.
        n=len(a);fft=np.fft.rfft(a);freq=np.fft.rfftfreq(n,1/48000);fft[(freq<30)|(freq>120)]=0;low=np.fft.irfft(fft,n)
        for frame in [150,330,480,660,780]:
            expected=frame/30;lo=round((expected-.22)*48000);hi=round((expected+.22)*48000)
            energy=np.convolve(low[lo:hi]**2,np.ones(480)/480,mode='same')
            observed=(lo+int(np.argmax(energy)))/48000
            error=(observed-expected)*30
            report['cutBeatCheck'].append({'cutFrame':frame,'nearestBeatFrame':round(frame/15)*15,'gridErrorFrames':frame-round(frame/15)*15,'decodedBassPeakErrorFrames':round(error,3)})
report['visualFramesIdentical']=hashes[0]==hashes[1]
report['differentDecodedFrameCount']=sum(a!=b for a,b in zip(*hashes))
comparison=subprocess.run(['ffmpeg','-hide_banner','-i',str(OUT/'kuaidian-kuaidian-launch.mp4'),'-i',str(OUT/'kuaidian-kuaidian-launch-sfx.mp4'),'-lavfi','ssim','-f','null','-'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
matched=re.search(r'SSIM Y:.*?All:([0-9.]+)',comparison.stderr.decode(errors='replace'))
assert matched, 'No decoded SSIM result'
report['decodedVideoSsim']=float(matched.group(1))
assert report['decodedVideoSsim']>.999,report['decodedVideoSsim']
stills=[OUT/'qa'/f'determinism-{variant}.png' for variant in ['bgm','sfx']]
if all(p.exists() for p in stills):
    report['losslessSourceStillAtFrame750Identical']=stills[0].read_bytes()==stills[1].read_bytes()
    assert report['losslessSourceStillAtFrame750Identical']
report['videoStreamsIdentical']=len({v['videoStreamSha256'] for v in report['renders'].values()})==1
report['audioStreamsDifferent']=len({v['audioStreamSha256'] for v in report['renders'].values()})==2
assert report['audioStreamsDifferent'], 'BGM and SFX audio should differ'
report['visualComparisonNote']=('All 960 decoded frames and compressed video streams are identical. SFX audio was rendered using bgm=false on the same timeline, then losslessly paired with the main video stream.' if report['videoStreamsIdentical'] else 'Same visual/SFX timeline; independent H.264 encodes can show small pixel-level differences. SSIM is checked across all 960 frames; no claim of decoded pixel identity.')
assert all(abs(c['decodedBassPeakErrorFrames'])<=3 for c in report['cutBeatCheck'])
(OUT/'qa'/'technical-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
