"""Original deterministic synthesized effects, local/offline TTS and timed captions.

Requires NumPy. No downloaded recordings. Run before scene construction.
Windows uses installed SAPI; Linux optionally uses espeak-ng. Missing TTS is explicit.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SR=24000


def read_wav(path):
    with wave.open(str(path),'rb') as w:
        assert w.getsampwidth()==2, 'TTS must produce PCM16'
        data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)/32768
        data=data.reshape(-1,w.getnchannels()).mean(axis=1)
        rate=w.getframerate()
    if rate!=SR:
        data=np.interp(np.arange(round(len(data)*SR/rate))*rate/SR,np.arange(len(data)),data)
    return data


def write_wav(path,data):
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,SR,0,'NONE','not compressed'))
        w.writeframes((np.clip(data,-.98,.98)*32767).astype('<i2').tobytes())


def timestamp(t,sep=','):
    ms=round(t*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}{sep}{ms%1000:03d}'


def prepare(config,out):
    c=json.loads(config.read_text(encoding='utf-8'))
    out.mkdir(parents=True,exist_ok=True)
    voices=out/'voice'
    voices.mkdir(exist_ok=True)
    source='unavailable; narration timing and captions prepared'
    error=None
    cache=voices/'voice_plan.json'
    texts=[line['text'] for line in c['narration']]
    cached=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
    existing=all((voices/f'voice_{i:02d}.wav').exists() and (voices/f'voice_{i:02d}.wav').stat().st_size>100
                 for i in range(len(c['narration'])))
    valid=existing and cached.get('texts')==texts
    if valid:
        source=cached['source']
    elif os.name=='nt':
        try:
            result=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/narrate_windows.ps1'),
                '-Config',str(config),'-Output',str(voices)],check=True,capture_output=True,text=True)
            source=result.stdout.strip()
            valid=True
        except subprocess.CalledProcessError as ex:
            error=ex.stderr.strip()
    elif shutil.which('espeak-ng'):
        for i,line in enumerate(c['narration']):
            subprocess.run(['espeak-ng','-s','155','-v','en-us','-w',str(voices/f'voice_{i:02d}.wav'),line['text']],check=True)
        source='espeak-ng local synthesized English voice'
        valid=True
    if valid:
        cache.write_text(json.dumps({'texts':texts,'source':source},indent=2),encoding='utf-8')
    rng=np.random.default_rng(13001)
    mix=np.zeros(round(c['duration']*SR),dtype=np.float64)
    manifest=[]
    cues=list(c['audio_cues'])
    cues.extend({'type':'beep','start':t,'end':t+.15,'gain':.11} for t,v in c['floor_events'] if v and '?' not in v and v!='--')
    for cue in cues:
        n=round((cue['end']-cue['start'])*SR)
        t=np.arange(n)/SR
        noise=rng.normal(0,1,n)
        kind=cue['type']
        if kind=='hum':
            x=.6*np.sin(math.tau*55*t)+.25*np.sin(math.tau*110*t)+noise*.025
        elif kind=='beep':
            x=np.sin(math.tau*880*t)*np.exp(-t*24)
        elif kind=='radio':
            x=noise*.4*(.5+.5*np.sin(math.tau*7*t))
        elif kind=='rumble':
            x=(np.sin(math.tau*(32*t+1.5*t*t))+.3*np.sin(math.tau*71*t))*np.minimum(t/8,1)*.65
        elif kind=='flicker':
            x=noise*.3*(np.sin(t*math.tau*6)> .91)
        elif kind in ('impact','step','knock'):
            decay=7 if kind=='impact' else 14
            x=(np.sin(math.tau*48*t)+noise*.4)*np.exp(-t*decay)
            if kind=='knock':
                for delay in [.23,.46]:
                    offset=round(delay*SR)
                    x[offset:]+=np.sin(math.tau*100*t[:-offset])*np.exp(-t[:-offset]*25)*.7
        elif kind=='doors':
            x=.35*noise+.4*np.sin(math.tau*135*t)
        elif kind=='drone':
            x=.5*np.sin(math.tau*43*t)+.3*np.sin(math.tau*45.2*t)+.2*np.sin(math.tau*87*t)
        elif kind=='sting':
            x=(np.sin(math.tau*(90*t+120*t*t))+.5*np.sin(math.tau*47*t)+noise*.4)*np.exp(-t*1.6)
        else:
            raise ValueError('Unknown audio cue '+kind)
        fade=np.minimum(np.arange(n)/max(SR*.015,1),1)*np.minimum(np.arange(n)[::-1]/max(SR*.04,1),1)
        x=x*fade*cue['gain']
        start=round(cue['start']*SR)
        mix[start:min(start+n,len(mix))]+=x[:min(n,len(mix)-start)]
        manifest.append(cue)
    voice_report=[]
    for i,line in enumerate(c['narration']):
        path=voices/f'voice_{i:02d}.wav'
        if not valid or not path.exists() or path.stat().st_size<=100:
            voice_report.append(dict(line,status='missing'))
            continue
        x=read_wav(path)
        original_duration=len(x)/SR
        available=line['end']-line['start']
        # Fit radio lines inside the authored caption window without truncating words.
        if original_duration>available:
            x=np.interp(np.linspace(0,len(x)-1,round(available*SR)),np.arange(len(x)),x)
        # Radio coloration: gently differentiated signal, soft saturation, tiny echo.
        x=.75*x+.25*np.concatenate(([0],np.diff(x)))
        x=np.tanh(x*2.4)*.30
        start=round(line['start']*SR)
        mix[start:start+len(x)]+=x
        delay=round(.09*SR)
        n=min(len(x),len(mix)-start-delay)
        mix[start+delay:start+delay+n]+=x[:n]*.12
        voice_report.append(dict(line,status='synthesized',source_duration=round(original_duration,3),output_duration=round(len(x)/SR,3)))
    peak=float(np.max(np.abs(mix)))
    if peak>.93:
        mix*=.93/peak
    write_wav(out/'episode_mix.wav',mix)
    captions=[]
    for i,caption in enumerate(c['captions'],1):
        captions.append(f'{i}\n{timestamp(caption["start"])} --> {timestamp(caption["end"])}\n{caption["text"]}\n')
    (out.parent/'captions.srt').write_text('\n'.join(captions),encoding='utf-8')
    (out.parent/'narration.md').write_text('# Radio transmission\n\n'+'\n\n'.join(
        f'{timestamp(v["start"],".")} - {timestamp(v["end"],".")} | {v["text"]}' for v in c['narration']),encoding='utf-8')
    report={'sample_rate':SR,'duration':len(mix)/SR,'effects_source':'Original procedural synthesis, no third-party recordings; project-generated effects may be reused',
        'voice_source':source,'tts_error':error,'narration':voice_report,'cues':manifest,'peak':float(np.max(np.abs(mix)))}
    (out/'audio_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['duration','voice_source','tts_error','peak']}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='episodes/episode_001.json')
    p.add_argument('--out',default='artifacts/episode_001/audio')
    a=p.parse_args()
    prepare((ROOT/a.config).resolve(),(ROOT/a.out).resolve())
