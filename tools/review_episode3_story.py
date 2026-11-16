"""Build the isolated complete story revision and still probes, not a full film."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.checkpoint import unpack
from autonomy.compiler import compile_plan
from production.story_revision import return_to_sender
from production.directing import assess_coverage
from soundstage.pipeline import prepare
from soundstage.captions import chunks,ass
from soundstage.media import read,SR


def engine_captions(manifest):
    output=[]
    for cue in manifest['captions']:
        selected=[w for w in manifest['words'] if cue['start']-.001<=(w['start']+w['end'])/2<=cue['end']+.001]
        # Unlike optional ASR, an ambiguous synthesis map must fail this build.
        values=chunks(cue,selected)
        for v in values: v['timing_method']='synthesis_phoneme_duration'
        output.extend(values)
    for i,value in enumerate(output):
        limit=output[i+1]['start']-.025 if i+1<len(output) else 44.95
        value['end']=min(limit,max(value['end'],value['start']+len(value['text'])/20))
        value['reading_hold_seconds']=max(0,value['end']-max(w['end'] for w in manifest['words']
            if value['start']-.01<=(w['start']+w['end'])/2<=value['end']))
    # Let the final short line remain readable through the deliberate black hold.
    output[-1]['end']=44.95
    output[-1]['reading_hold_seconds']=max(0,44.95-manifest['words'][-1]['end'])
    assert all(a['end']<=b['start'] for a,b in zip(output,output[1:])), 'Caption overlap'
    assert ' '.join(v['text'] for v in output)==' '.join(v['text'] for v in manifest['captions'])
    assert all(v['end']-v['start']>=.16 for v in output), 'Unreadably short caption'
    return {'captions':output,'fallback_phrases':[],
            'all_words_verified':True,'method':'exact synthesis phoneme durations; not ASR',
            'audio_mix_sha256':manifest['mix_sha256'],
            'requires_human_timing_review':True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blender',required=True);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--out',type=Path,default=ROOT/'artifacts/story_review/episode3_v4_reviewed')
    a=p.parse_args();out=a.out.resolve()
    if not out.is_relative_to((ROOT/'artifacts/story_review').resolve()): raise ValueError('Isolated story-review output required')
    out.mkdir(parents=True,exist_ok=True)
    config=out/'episode.json';source=out/'episode3_story_v4.blend'
    if config.exists() or source.exists(): raise FileExistsError('Preserve previous revision; use a fresh --out')
    seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
    plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
    original=compile_plan(plan,json.loads((ROOT/'config/cloud_preview.json').read_text()))
    c=return_to_sender(original)
    direction=json.loads((ROOT/'config/episode3_director_v4.json').read_text())
    c['narration']=direction['narration'];c['title']=direction['title']
    settings=json.loads((ROOT/'config/narrator_candidate.json').read_text());settings['phoneme_alignment']=True
    print('STORY REVIEW: original dialogue and exact engine alignment',flush=True)
    mix=prepare(c,out/'audio',settings,a.ffmpeg,direction)
    for line in mix['narration']:
        spoken=[w for w in mix['words'] if line['start']<=(w['start']+w['end'])/2<=line['actual_end']]
        assert spoken and max(w['end'] for w in spoken)<=line['end'], ('Spoken word exceeds cue',line['text'])
    assert all(a['actual_end']<=b['start'] for a,b in zip(mix['narration'],mix['narration'][1:])), 'Dialogue takes overlap'
    alignment=engine_captions(mix)
    (out/'alignment.json').write_text(json.dumps(alignment,indent=2))
    (out/'captions.ass').write_text(ass(alignment['captions']),encoding='utf-8-sig')
    c['captions']=alignment['captions']
    voice=read(out/'audio/narration_stem.wav',a.ffmpeg)
    envelope=[]
    courier_windows=[(n['start'],n['actual_end']) for n in mix['narration'] if n['speaker']=='courier']
    for i in range(45*24+1):
        t=i/24;block=voice[max(0,int(t*SR)):min(len(voice),int((t+1/24)*SR))]
        value=min(1,float(np.sqrt(np.mean(block*block)))*7) if len(block) and any(x<=t<y for x,y in courier_windows) else 0
        envelope.append([t,value])
    c['directing']['mouth_envelope']=envelope
    assert c['production']==original['production']
    config.write_text(json.dumps(c,indent=2))
    (out/'coverage.json').write_text(json.dumps(assess_coverage(c),indent=2))
    env=os.environ.copy();env.update(EPISODE_CONFIG=str(config),EPISODE_OUTPUT=str(out),SCENE_BLEND=str(source),ENABLE_REFLECTIONS='0')
    env.pop('ALLOW_REBUILD',None)
    with (out/'build_validate.log').open('w',encoding='utf-8') as log:
        subprocess.run([a.blender,'--background','--factory-startup','--threads','4','--python-exit-code','1',
            '--python',str(ROOT/'story_scene.py'),'--python',str(ROOT/'tools/validate_score.py'),
            '--python',str(ROOT/'tools/validate_story_performance.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    # One representative view per shot, with the control press shown at contact.
    parts=[]
    for shot in c['shots']:
        t=20.95 if shot['id']=='listening_reaction' else (shot['start']+shot['end'])/2
        f=round(t*24)+1
        parts.append({'frames':[f],'start':(f-1)/24,'end':f/24,'fps':24,'output_frames':1,'shot':shot['id']})
    for f in [421,468]:
        parts.append({'frames':[f],'start':(f-1)/24,'end':f/24,'fps':24,'output_frames':1,'shot':'countdown_pressure'})
    job={'out':str(out/'probes'),'profile':'balanced','samples':16,'resolution':[720,1280],
         'segments':parts,'external_captions':True,'max_seconds':180}
    (out/'probe_job.json').write_text(json.dumps(job,indent=2));env['QUALITY_JOB']=str(out/'probe_job.json')
    with (out/'probes.log').open('w',encoding='utf-8') as log:
        subprocess.run([a.blender,'--background','--factory-startup',str(source),'--threads','4','--python-exit-code','1',
                        '--python',str(ROOT/'tools/render_quality.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    print(json.dumps({'scene_passed':True,'probes':len(parts),'caption_fallbacks':0,
                      'canon_unchanged':True,'full_film_rendered':False,'readiness':'NOT_READY'},indent=2))


if __name__=='__main__': main()
