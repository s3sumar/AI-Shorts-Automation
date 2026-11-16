"""Publication readiness is separate from successful rendering/story verification."""
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def evaluate(facts,standards,review=None):
    failures=[]
    def check(ok,reason):
        if not ok: failures.append(reason)
    v=facts.get('video',{}); a=facts.get('audio',{})
    width,height=v.get('width',0),v.get('height',0)
    check(width>=standards['minimum_resolution'][0] and height>=standards['minimum_resolution'][1] and width*16==height*9,'resolution_below_publication_standard')
    check(v.get('fps') in standards['allowed_fps'],'animation_frame_rate')
    check(v.get('constant_frame_rate') is True,'constant_frame_cadence_not_verified')
    check(abs(v.get('frames',0)-v.get('duration',0)*v.get('fps',0))<.01,'missing_output_frames')
    check(v.get('duration',0)>=standards['minimum_episode_seconds'],'development_clip_only')
    check(facts.get('full_decode_passed') is True,'media_decode_not_verified')
    evidence=facts.get('render_evidence',{})
    if standards['native_frame_evidence_required']:
        check(evidence.get('native') is True and evidence.get('source_frames')==v.get('frames') and evidence.get('contiguous') is True,'native_animation_not_proven')
        check(evidence.get('duplicate_moving_frames')==0,'duplicate_moving_frames_not_verified')
        source_size=evidence.get('source_resolution',[0,0])
        check(source_size[0]>=standards['minimum_resolution'][0] and source_size[1]>=standards['minimum_resolution'][1],'native_render_resolution_not_proven')
    check(a.get('channels')==standards['audio_channels'] and a.get('sample_rate')==standards['sample_rate'],'audio_format')
    check(math.isfinite(a.get('integrated_lufs',float('nan'))) and abs(a.get('integrated_lufs',0)-standards['integrated_lufs'])<=standards['loudness_tolerance_lu'],'integrated_loudness')
    check(math.isfinite(a.get('true_peak_dbtp',float('nan'))) and a.get('true_peak_dbtp',0)<=standards['true_peak_ceiling_dbtp'],'true_peak')
    check(a.get('speech_over_bed_db',0)>=standards['minimum_speech_over_bed_db'],'speech_masking_not_verified')
    check(a.get('clipped_samples',1)==0 and a.get('nonfinite_samples',1)==0,'clipped_or_invalid_audio')
    check(a.get('unexpected_silence') is False,'unintended_silence_not_verified')
    narration=facts.get('narration',[])
    check(bool(narration) and all(r.get('status')=='synthesized' and r.get('overrun_seconds',1)<=.15 and
          0<=r.get('start',-1)<r.get('actual_end',-1)<=v.get('duration',0)+.02 for r in narration),'narration_presence_or_sync')
    check(facts.get('voice_identity_approved') is True,'voice_identity_not_approved')
    captions=facts.get('captions',[])
    check(bool(captions) and all(0<=c['start']<c['end']<=v.get('duration',0)+.02 and
          len(c['text'].replace('\n',''))/max(c['end']-c['start'],.01)<=22 and
          max(map(len,c['text'].split('\n')))<=36 for c in captions),'caption_timing_or_readability')
    check(facts.get('scene_continuity_passed') is True,'scene_continuity_not_verified')
    check(facts.get('assets_passed') is True,'assets_not_verified')
    pending=[]
    for name in standards['required_human_reviews']:
        if not review or review.get('media_sha256')!=facts.get('media_sha256') or not review.get('reviewed_by') or review.get('checks',{}).get(name)!='approved':
            pending.append(name)
    ready=not failures and not pending
    return {'schema':1,'status':'READY' if ready else 'NOT_READY','technical_failures':failures,
            'pending_human_reviews':pending,'media_sha256':facts.get('media_sha256'),
            'public_publishing_allowed':ready and standards['public_publishing_enabled'],
            'note':'Render verification advances technical story evidence only; it is never publication approval.'}


def collect(video,ffmpeg,audio_manifest,render_evidence=None,captions=None,scene_passed=False,assets_passed=False,voice_approved=False):
    from tools.media import probe
    from soundstage.media import read,measure,SR
    import numpy as np
    path=Path(video); info=probe(path)
    v=next(t for t in info['tracks'] if t['type']=='vide')
    audio_stream=next((t for t in info['tracks'] if t['type']=='soun'),{})
    result=subprocess.run([ffmpeg,'-v','error','-i',str(path),'-f','null','-'],capture_output=True,text=True,timeout=180)
    loudness=measure(path,ffmpeg)
    audio=read(path,ffmpeg)
    windows=np.sqrt(np.mean(audio[:len(audio)//2400*2400].reshape(-1,2400,2)**2,axis=(1,2)))
    # Long silences are reported for review unless the mix explicitly authors them.
    silence=windows<.0003
    longest=run=0
    for quiet in silence:
        run=run+1 if quiet else 0; longest=max(longest,run)
    return {'video':{'width':v['width'],'height':v['height'],'frames':v['samples'],'fps':v['fps'],'duration':v['duration'],
                     'constant_frame_rate':v.get('constant_frame_rate',False)},
        'audio':{'channels':audio_stream.get('channels'),'sample_rate':audio_stream.get('sample_rate'),
                 'integrated_lufs':loudness['input_i'],'true_peak_dbtp':loudness['input_tp'],
                 'speech_over_bed_db':audio_manifest.get('speech_over_bed_db',0),
                 'clipped_samples':int((np.abs(audio)>=1).sum()),'nonfinite_samples':int((~np.isfinite(audio)).sum()),
                 'unexpected_silence':longest*.05>1.5,'longest_near_silence_seconds':longest*.05},
        'full_decode_passed':result.returncode==0 and not result.stderr.strip(),'render_evidence':render_evidence or {},
        'narration':audio_manifest.get('narration',[]),'captions':captions or [],'voice_identity_approved':voice_approved,
        'scene_continuity_passed':scene_passed,'assets_passed':assets_passed,
        'media_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def save_report(out,facts,review=None):
    standards=json.loads((ROOT/'config/production_standards.json').read_text())
    report=evaluate(facts,standards,review)
    Path(out).write_text(json.dumps({'gate':report,'facts':facts},indent=2))
    return report
