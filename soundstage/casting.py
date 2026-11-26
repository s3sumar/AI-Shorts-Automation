"""Reusable identity-locked casting, bounded delivery controls and aligned line takes."""
import hashlib
import json
import math
import subprocess
from pathlib import Path
import numpy as np
from .narration import Narrator,ROOT
from .media import SR,read,write
from .voice_contract import freeze_cast,validate_cast_lock,voice_fingerprint,digest


def resolve_delivery(library,line):
    role=line.get('role',line['speaker'])
    if role not in library['roles']: raise ValueError('Uncast role: '+role)
    emotion=line.get('emotion',library['default_emotions'].get(role,'uneasy'))
    if emotion not in library['delivery_profiles']: raise ValueError('Unsupported delivery emotion: '+emotion)
    delivery=dict(library['delivery_profiles'][emotion])
    if 'pace' in line: delivery['pace']=line['pace']
    bounds={'pace':(.75,1.35),'pitch_semitones':(-3,3),'gain_db':(-6,3),
            'tremor_depth':(0,.05),'echo_ms':(0,100),'echo_gain':(0,.12),'lowpass_hz':(2500,12000),
            'noise_scale':(.1,.9),'noise_w_scale':(.1,.9)}
    if set(delivery)-set(bounds): raise ValueError('Unknown delivery control')
    for key,value in delivery.items():
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not bounds[key][0]<=value<=bounds[key][1]:
            raise ValueError('Unsafe delivery value: '+key)
    return role,emotion,delivery


def apply_delivery(audio,delivery,ffmpeg,out):
    """Pitch processing retains time; expressive pacing is synthesized by the engine."""
    audio=np.array(audio,copy=True)
    if abs(delivery.get('pitch_semitones',0))>.001:
        write(out/'pitch_input.wav',audio)
        pitch=2**(delivery['pitch_semitones']/12)
        result=subprocess.run([ffmpeg,'-v','error','-y','-i',str(out/'pitch_input.wav'),'-af',
            f'rubberband=tempo=1:pitch={pitch}:formant=preserved:pitchq=quality',
            '-ar',str(SR),'-ac','2','-c:a','pcm_s24le',str(out/'pitch_output.wav')],capture_output=True,text=True,timeout=90)
        (out/'pitch.log').write_text(result.stderr);result.check_returncode()
        processed=read(out/'pitch_output.wav',ffmpeg)
        delta=len(processed)-len(audio)
        if abs(delta)>.025*SR: raise ValueError('Pitch processor changed dialogue duration')
        if delta>0 and np.max(np.abs(processed[-delta:]))>.01: raise ValueError('Pitch correction would truncate audible speech')
        audio=processed[:len(audio)] if delta>=0 else np.pad(processed,((0,-delta),(0,0)))
    if delivery.get('lowpass_hz'):
        spectrum=np.fft.rfft(audio,axis=0)
        freq=np.fft.rfftfreq(len(audio),1/SR)
        spectrum*= (1/(1+(freq/delivery['lowpass_hz'])**6))[:,None]
        audio=np.fft.irfft(spectrum,n=len(audio),axis=0)
    tremor=delivery.get('tremor_depth',0)
    if tremor:
        t=np.arange(len(audio))/SR
        envelope=1-tremor*(.5+.5*np.sin(2*np.pi*4.3*t))
        audio*=envelope[:,None]
    if delivery.get('echo_ms'):
        delay=round(delivery['echo_ms']/1000*SR)
        if 0<delay<len(audio): audio[delay:]+=audio[:-delay].copy()*delivery.get('echo_gain',0)
    audio*=10**(delivery.get('gain_db',0)/20)
    if not np.isfinite(audio).all(): raise ValueError('Non-finite delivered line')
    # Preserve transient shape with linear headroom, never a hard clip.
    peak=float(np.max(np.abs(audio)))
    if peak>.98: audio*=.98/peak
    return audio


class VoiceCast:
    def __init__(self,library,score,ffmpeg,out):
        self.library=library;self.ffmpeg=ffmpeg;self.out=Path(out)
        self.series_id=score.get('production',{}).get('series_id',score.get('series_id','standalone'))
        self.lock=freeze_cast(library,self.series_id)
        expected=score.get('audio_production',{}).get('cast_lock')
        registry=ROOT/'config/series_voice_casts.json'
        established=json.loads(registry.read_text()).get('series',{}).get(self.series_id) if registry.exists() else None
        if established is not None: validate_cast_lock(established,library,self.series_id)
        if expected is not None: validate_cast_lock(expected,library,self.series_id)
        lock_path=self.out/'voice_cast_lock.json'
        if lock_path.exists() and json.loads(lock_path.read_text())!=self.lock: raise ValueError('Output cast lock changed')
        lock_path.write_text(json.dumps(self.lock,indent=2))
        self.engines={}

    def render_line(self,line,out):
        role,emotion,delivery=resolve_delivery(self.library,line)
        voice_id=self.library['roles'][role]
        voice=self.library['voices'][voice_id]
        if voice_id not in self.engines: self.engines[voice_id]=Narrator(voice,self.ffmpeg)
        engine=self.engines[voice_id]
        out=Path(out);out.mkdir(parents=True,exist_ok=True)
        phrases=line.get('phrases',[{'text':line['text'],'pause_after':.08}])
        take=engine.synthesize(phrases,out,delivery.get('pace',1),delivery=delivery)
        target=out/'delivered.wav';receipt_path=out/'delivery.json'
        signature=digest({'take':take['sha256'],'delivery':delivery,'processing_version':2})
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            if receipt['signature']!=signature or hashlib.sha256(target.read_bytes()).hexdigest()!=receipt['sha256']:
                raise ValueError('Cached delivered line changed; use a new revision')
        else:
            audio=read(out/'voice.wav',self.ffmpeg)
            rms=float(np.sqrt(np.mean(audio*audio)))
            if rms<1e-6: raise ValueError('Silent voice take')
            audio*=min(.105/rms,3)
            processed=apply_delivery(audio,delivery,self.ffmpeg,out)
            write(target,processed)
            receipt={'signature':signature,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                     'samples':len(processed),'delivery_controls':delivery,
                     'timing_method':'engine_phoneme_durations_with_time_preserving_delivery'}
            receipt_path.write_text(json.dumps(receipt,indent=2))
        return dict(take,delivered_path=str(target),voice_id=voice_id,role=role,emotion=emotion,
                    delivery_controls=delivery,voice_fingerprint=voice_fingerprint(voice),
                    delivered_sha256=receipt['sha256'],timing_method=receipt['timing_method'])
