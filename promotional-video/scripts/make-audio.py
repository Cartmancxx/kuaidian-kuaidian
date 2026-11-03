"""Original deterministic 120 BPM soundtrack and sound effects. No sampled assets."""
from pathlib import Path
import json, wave
import numpy as np
SR=48000
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'public'/'audio'
OUT.mkdir(parents=True,exist_ok=True)
(ROOT/'out').mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(110326)
def write(name,a,peak=.78):
    a=np.asarray(a,dtype=float)
    a=a/max(1e-9,float(np.max(np.abs(a))))*peak
    with wave.open(str(OUT/name),'wb') as w:
        w.setparams((1,2,SR,len(a),'NONE','not compressed'))
        w.writeframes((np.clip(a,-1,1)*32767).astype('<i2').tobytes())
def timeline(sec):return np.arange(round(sec*SR))/SR
def smoothnoise(n,width=7):return np.convolve(rng.uniform(-1,1,n),np.ones(width)/width,mode='same')
def add(dst,src,time,gain=1):
    k=round(time*SR);end=min(len(dst),k+len(src));dst[k:end]+=src[:end-k]*gain
music=np.zeros(SR*32)
t=timeline(.43)
kick=(np.sin(2*np.pi*(48*t+105*.035*(1-np.exp(-t/.035))))*np.exp(-t*12)+smoothnoise(len(t),3)*np.exp(-t*150)*.18)
t=timeline(.22);snare=smoothnoise(len(t),3)*np.exp(-t*22)+.18*np.sin(2*np.pi*170*t)*np.exp(-t*35)
t=timeline(.075);noise=rng.uniform(-1,1,len(t));hat=np.diff(noise,prepend=noise[0])*np.exp(-t*75)
roots=[73.4162,65.4064,58.2705,65.4064]
for beat in range(64):
    time=beat*.5
    section=.55 if beat<10 else .82 if beat<44 else .57 if beat<52 else 1.
    add(music,kick,time,.8*section)
    if beat%2:add(music,snare,time,.22*section)
    if beat>=8:
        add(music,hat,time+.25,.06*section)
        if beat%4==3:add(music,hat,time+.375,.025*section)
    t=timeline(.36)
    freq=roots[(beat//8)%4]
    bass=(np.sin(2*np.pi*freq*t)+.22*np.sin(2*np.pi*freq*2*t)+.07*np.sin(2*np.pi*freq*3*t))*np.minimum(1,t/.012)*np.exp(-t*8)
    add(music,bass,time+.125,.24*section)
# Warm restrained chord bed, side-chained against the kick; no game-like melody.
for bar in range(8):
    t=timeline(4);base=roots[(bar)%4]*2
    chord=sum(np.sin(2*np.pi*base*ratio*t)+.13*np.sin(2*np.pi*base*ratio*2*t) for ratio in [1,2**(3/12),2**(7/12),2])
    env=np.minimum(1,t/.18)*np.minimum(1,(4-t)/.3)
    side=.35+.65*np.minimum(1,((t%0.5)/.13))
    add(music,chord*env*side,bar*4,.027)
music*=np.minimum(1,np.arange(len(music))/SR/.12)
music*=np.minimum(1,(len(music)-np.arange(len(music)))/SR/.65)
write('bgm.wav',np.tanh(music*1.05),.82)
t=timeline(1.15);env=np.sin(np.pi*t/1.15)**2
write('whoosh.wav',smoothnoise(len(t),10)*env,.7)
t=timeline(.16);tap=smoothnoise(len(t),3)*np.exp(-t*80)+.4*np.sin(2*np.pi*930*t)*np.exp(-t*110)
write('tap.wav',tap,.72)
t=timeline(2);impact=np.sin(2*np.pi*(38*t+20*.15*(1-np.exp(-t/.15))))*np.exp(-t*4)+smoothnoise(len(t),25)*np.exp(-t*9)*.7
write('impact.wav',impact,.78)
t=timeline(1.4);riser=smoothnoise(len(t),7)*(t/1.4)**1.8+np.sin(2*np.pi*(75*t+65*t*t))*.16*(t/1.4)**3
write('riser.wav',riser,.68)
t=timeline(1.7);spark=sum(np.sin(2*np.pi*freq*t)*np.exp(-t*(4+i)) for i,freq in enumerate([1851,2753,4327]))*.18
spark+=smoothnoise(len(t),2)*np.exp(-t*5)*.1
write('sparkle.wav',spark,.6)
(OUT/'README.md').write_text('# Original audio\n\nAll WAV files are original deterministic synthesis from scripts/make-audio.py.\nNo third-party samples. 120 BPM, 48 kHz mono. MIT project license.\nRegeneration requires NumPy; no network access is used by the generator.\n',encoding='utf-8')
(ROOT/'out'/'audio-design.json').write_text(json.dumps({'bpm':120,'beatFrames':15,'durationFrames':960,'seed':110326,'sceneBeats':[0,10,22,32,44,52],'sampleRate':SR,'source':'original synthesis'},indent=2),encoding='utf-8')
print('Original soundtrack and five effects generated.')
