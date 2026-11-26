"""Stereo stem mixing, speech ducking, measured two-pass loudness and provenance."""
import json
import math
import time
import hashlib
from pathlib import Path
import numpy as np
from .media import SR,read,write,normalize,measure
from .narration import Narrator
from .events import event_plan,sound,duck_envelope
from .voice_contract import validate_dialogue


def prepare(c,out,settings,ffmpeg,direction=None):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    audio_score={k:v for k,v in c.items() if k!='captions'}
    cast_mode='roles' in settings and 'voices' in settings
    inputs={'score':audio_score,'settings':settings,'direction':direction,'sound_design_version':2}
    if cast_mode: inputs.update(cast_delivery_revision=2,caption_alignment_revision=4)
    signature=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    if (out/'audio_manifest.json').exists():
        prior=json.loads((out/'audio_manifest.json').read_text())
        if prior.get('signature')==signature and hashlib.sha256((out/'episode_mix.wav').read_bytes()).hexdigest()==prior.get('mix_sha256'):
            if prior.get('voice_cast'):
                for line in prior['narration']:
                    path=out/line['line_audio_file']
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=line['line_audio_sha256']:
                        raise ValueError('Cached cast line is missing or changed; preserve this mix and use a new revision')
            return prior
        raise FileExistsError('Preserve completed sound mixes; use a new revision directory')
    started=time.monotonic()
    n=round(c['duration']*SR)
    dialogue=np.zeros((n,2)); ambience=np.zeros((n,2)); effects=np.zeros((n,2))
    lines=direction['narration'] if direction else c['narration']
    cast=None
    if cast_mode:
        from .casting import VoiceCast
        validate_dialogue(lines,c['duration'])
        cast=VoiceCast(settings,c,ffmpeg,out)
    else:
        narrator=Narrator(settings,ffmpeg)
    speaker_stems={}
    receipts=[]; windows=[]; captions=[]; words=[]
    for i,line in enumerate(lines):
        phrases=line.get('phrases',[{'text':line['text'],'pause_after':.08}])
        take=cast.render_line(line,out/'voice'/f'take_{i:02d}') if cast else narrator.synthesize(phrases,out/'voice'/f'take_{i:02d}',line.get('pace',1.0))
        words.extend(dict(w,start=line['start']+w['start'],end=line['start']+w['end'],speaker=line.get('speaker','narrator')) for w in take.get('words',[]))
        audio=read(take['delivered_path'] if cast else out/'voice'/f'take_{i:02d}'/'voice.wav',ffmpeg)
        if not cast:
            rms=float(np.sqrt(np.mean(audio*audio)))
            audio*=min(.105/max(rms,1e-6),3)
        a=round(line['start']*SR)
        b=min(n,a+len(audio))
        if a+len(audio)>n:
            raise ValueError('Narration exceeds scene; edit delivery rather than truncate words')
        dialogue[a:b]+=audio[:b-a]
        actual_end=b/SR
        if cast:
            word_end=line['start']+max(w['end'] for w in take['words'])
            next_start=lines[i+1]['start'] if i+1<len(lines) else c['duration']
            if word_end>line['end'] or actual_end>next_start or actual_end-line['end']>settings['timing']['max_tail_overrun_seconds']:
                raise ValueError(f'Dialogue does not fit cue {i}: spoken_end={word_end:.3f}, take_end={actual_end:.3f}, planned_end={line["end"]:.3f}; edit writing or pacing, never truncate speech')
            stem=speaker_stems.setdefault(take['voice_id'],np.zeros((n,2)))
            stem[a:b]+=audio[:b-a]
        windows.append((line['start'],actual_end))
        overrun=max(0,actual_end-line['end'])
        receipts.append(dict(line,status='synthesized',source_duration=len(audio)/SR,actual_end=actual_end,
                             overrun_seconds=overrun,identity=take['identity'],signature=take['signature']))
        if cast:
            receipts[-1].update(voice_id=take['voice_id'],voice_fingerprint=take['voice_fingerprint'],
                emotion=take['emotion'],role=take['role'],delivery_controls=take['delivery_controls'],
                line_audio_file=Path(take['delivered_path']).relative_to(out).as_posix(),line_audio_sha256=take['delivered_sha256'],
                word_timing_method=take['timing_method'],spoken_end=word_end)
        for phrase in take['phrases']:
            captions.append({'start':line['start']+phrase['start'],'end':line['start']+phrase['end'],
                             'text':phrase['text'],**({'speaker':line['speaker'],'role':take['role']} if cast else {})})
    if cast:
        from .aligned_captions import build,write_files
        phrase_cues=list(captions)
        captions=build(captions,words,c['duration'])
        write_files(out,captions)
    events=event_plan(c)
    for i,event in enumerate(events):
        a=round(event['start']*SR); b=min(n,round(event['end']*SR))
        if a<0 or b<=a: raise ValueError('Invalid sound cue bounds')
        mono=sound(event['category'],(b-a)/SR,seed=300+i)*event['gain']
        pan=event.get('pan',0)
        stereo=np.column_stack((mono*math.sqrt((1-pan)/2),mono*math.sqrt((1+pan)/2)))
        (ambience if event['category'] in ['environment','mechanical'] else effects)[a:b]+=stereo
    ambience*=duck_envelope(n,windows,12)[:,None]
    effects*=duck_envelope(n,windows,8)[:,None]
    active=np.max(np.abs(dialogue),axis=1)>.008
    voice_rms=float(np.sqrt(np.mean(dialogue[active]**2)))
    bed_rms=float(np.sqrt(np.mean((ambience+effects)[active]**2)))
    speech_margin=20*math.log10(max(voice_rms,1e-9)/max(bed_rms,1e-9))
    mixed=dialogue+ambience+effects
    # Avoid pre-normalization clipping while retaining float stem balance.
    scale=min(1,.90/max(float(np.max(np.abs(mixed))),1e-6))
    for name,data in [('narration',dialogue),('ambience',ambience),('effects',effects)]:
        write(out/(name+'_stem.wav'),data*scale)
    for voice_id,data in speaker_stems.items(): write(out/('speaker_'+voice_id+'.wav'),data*scale)
    write(out/'premix.wav',mixed*scale)
    loudness=normalize(out/'premix.wav',out/'episode_mix.wav',ffmpeg)
    final=read(out/'episode_mix.wav',ffmpeg)
    mono=final.mean(axis=1)
    mono_delta=20*math.log10(max(np.sqrt(np.mean(mono**2)),1e-9)/max(np.sqrt(np.mean(final**2)),1e-9))
    # Simulated phone bandwidth and mono are a review artifact, not a device listening test.
    import subprocess
    subprocess.run([ffmpeg,'-v','error','-y','-i',str(out/'episode_mix.wav'),'-af','highpass=f=150,lowpass=f=7000',
                    '-ac','1',str(out/'phone_simulation.wav')],check=True)
    report={'schema':2,'sample_rate':SR,'channels':2,'duration':len(final)/SR,'peak':float(np.max(np.abs(final))),
            'loudness':loudness,'speech_over_bed_db':speech_margin,'mono_rms_delta_db':mono_delta,
            'narration':receipts,'cues':events,'captions':captions,'words':words,'voice_source':settings['voice_id'],
            'effects_source':'Original project procedural synthesis; no recordings or copyrighted music',
            'phone_listening':'pending; bandwidth simulation provided','headphone_listening':'pending',
            'elapsed_seconds':time.monotonic()-started,'readiness':'NOT_READY','signature':signature,
            'mix_sha256':hashlib.sha256((out/'episode_mix.wav').read_bytes()).hexdigest()}
    if cast:
        report.update(voice_cast=cast.lock,caption_fallbacks=0,phrase_cues=phrase_cues,caption_alignment_revision=4,
            speech_timing='engine phoneme boundaries; time-preserving delivery; human pronunciation/listening review pending',
            speaker_stems={key:'speaker_'+key+'.wav' for key in speaker_stems},
            per_line_audio_files=len(receipts),paid_request=False)
    (out/'audio_manifest.json').write_text(json.dumps(report,indent=2))
    return report
