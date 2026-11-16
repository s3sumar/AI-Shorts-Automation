"""Deterministic voice identity and explicit phrase timing; no paid network calls."""
import hashlib
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path
from .media import SR,read,write
from .engine_alignment import phoneme_words
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


class Narrator:
    def __init__(self,settings,ffmpeg):
        self.settings=settings
        self.ffmpeg=ffmpeg
        self.voice=None
        self.identity=dict(settings)
        provider=settings['provider']
        if settings.get('phoneme_alignment') and provider!='piper':
            raise ValueError('Exact engine alignment currently requires the local Piper provider')
        if provider=='piper':
            # Explicitly installed, locally cached model only; never download during synthesis.
            try:
                from piper import PiperVoice
            except ImportError:
                sys.path.insert(0,str(ROOT/'artifacts/audio_tooling'))
                from piper import PiperVoice
            model=(ROOT/settings['model']).resolve()
            sha=hashlib.sha256(model.read_bytes()).hexdigest()
            if sha!=settings['model_sha256']:
                raise ValueError('Narrator model hash changed; identity review required')
            if settings.get('phoneme_alignment'):
                sys.path.insert(0,str(ROOT/'artifacts/alignment_tooling'))
            self.voice=PiperVoice.load(str(model),use_cuda=False,include_alignments=settings.get('phoneme_alignment',False))
            self.identity['model_sha256']=sha
        elif provider=='sapi':
            if os.name!='nt':
                raise RuntimeError('SAPI is Windows only; select a reviewed cross-platform neural voice')
        else:
            raise PermissionError('Only local piper/sapi providers are enabled. Paid providers require separate approval and implementation.')

    def synthesize(self,phrases,out,pace=1.0):
        out=Path(out)
        out.mkdir(parents=True,exist_ok=True)
        plan={'identity':self.identity,'phrases':phrases,'pace':pace}
        signature=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
        result=out/'voice.wav'
        receipt=out/'voice.json'
        if receipt.exists() and result.exists():
            previous=json.loads(receipt.read_text())
            if previous['signature']!=signature:
                raise FileExistsError('Refusing to reuse a different narration take')
            if hashlib.sha256(result.read_bytes()).hexdigest()!=previous['sha256']:
                raise ValueError('Cached narration changed')
            return previous
        started=time.monotonic()
        parts=[]
        timings=[]
        word_timings=[]
        cursor=0.0
        for i,phrase in enumerate(phrases):
            path=out/f'phrase_{i:02d}.wav'
            if self.settings['provider']=='piper':
                from piper import SynthesisConfig
                with wave.open(str(path),'wb') as stream:
                    alignment=self.voice.synthesize_wav(phrase['text'],stream,syn_config=SynthesisConfig(
                        length_scale=pace,noise_scale=.5,noise_w_scale=.65,normalize_audio=True),
                        include_alignments=self.settings.get('phoneme_alignment',False))
            else:
                request=out/f'phrase_{i:02d}.json'
                request.write_text(json.dumps({'text':phrase['text'],'voice':self.settings['voice'],
                    'directed':self.settings.get('directed',False),'rate_percent':round((1/pace-1)*100)}))
                subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/speak_directed.ps1'),
                    '-Request',str(request),'-Output',str(path)],capture_output=True,text=True,check=True)
            audio=read(path,self.ffmpeg)
            # Preserve pronunciation: trim only long leading/trailing near-silence.
            active=np.flatnonzero(np.max(np.abs(audio),axis=1)>.006)
            if not len(active):
                raise ValueError('Narrator produced silence')
            trim_start=max(0,active[0]-int(.035*SR))
            audio=audio[trim_start:min(len(audio),active[-1]+int(.09*SR))]
            if self.settings.get('phoneme_alignment'):
                if not alignment: raise ValueError('Engine did not return required phoneme timing; refusing fallback')
                words=phoneme_words(phrase['text'],[{'phoneme':p.phoneme,'num_samples':int(p.num_samples)} for p in alignment],self.voice.config.sample_rate)
                for w in words:
                    w['start']=cursor+max(0,w['start']-trim_start/SR)
                    w['end']=cursor+min(len(audio)/SR,w['end']-trim_start/SR)
                    if w['end']<=w['start']: raise ValueError('Trim removed a spoken word')
                word_timings.extend(words)
            timings.append({'text':phrase['text'],'start':cursor,'end':cursor+len(audio)/SR})
            parts.append(audio)
            pause=float(phrase.get('pause_after',0))
            if not 0<=pause<=2:
                raise ValueError('Invalid narration pause')
            parts.append(np.zeros((round(pause*SR),2)))
            cursor+=len(audio)/SR+pause
        combined=np.concatenate(parts)
        write(result,combined)
        value={'signature':signature,'identity':self.identity,'duration':len(combined)/SR,'phrases':timings,
               'words':word_timings,'alignment_method':'synthesis_phoneme_duration' if word_timings else None,
               'synthesis_seconds':time.monotonic()-started,'sha256':hashlib.sha256(result.read_bytes()).hexdigest(),
               'human_naturalness_review':'pending','paid_request':False}
        receipt.write_text(json.dumps(value,indent=2))
        return value
