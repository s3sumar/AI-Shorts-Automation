"""Original Episode 3 directing experiment. Never loads reference media as an asset."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.compiler import compile_plan
from autonomy.checkpoint import unpack
from production.directing import lift_director_pass,assess_coverage
from soundstage.pipeline import prepare


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--blender',required=True)
    p.add_argument('--out',type=Path,default=ROOT/'artifacts/reference_director/episode3_v3')
    a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if not out.is_relative_to((ROOT/'artifacts/reference_director').resolve()):
        raise ValueError('Use an isolated directing experiment directory')
    if (out/'director_source.blend').exists() or (out/'episode.json').exists():
        raise FileExistsError('Preserve completed directing experiments; choose a fresh --out directory')
    seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
    plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
    original=compile_plan(plan,json.loads((ROOT/'config/cloud_preview.json').read_text()))
    c=lift_director_pass(original)
    direction=json.loads((ROOT/'config/episode3_director_v3.json').read_text())
    c['narration']=direction['narration']
    settings=json.loads((ROOT/'config/narrator_candidate.json').read_text())
    print('DIRECTOR STAGE: original narration and sound',flush=True)
    mix=prepare(c,out/'audio',settings,a.ffmpeg,direction)
    c['captions']=mix['captions']
    config=out/'episode.json';config.write_text(json.dumps(c,indent=2))
    (out/'coverage.json').write_text(json.dumps(assess_coverage(c),indent=2))
    source=out/'director_source.blend'
    env=os.environ.copy()
    env.update(EPISODE_CONFIG=str(config),EPISODE_OUTPUT=str(out),SCENE_BLEND=str(source),ENABLE_REFLECTIONS='0')
    env.pop('ALLOW_REBUILD',None)
    if not source.exists():
        with (out/'build_validate.log').open('w') as log:
            subprocess.run([a.blender,'--background','--factory-startup','--threads','4','--python-exit-code','1',
                '--python',str(ROOT/'story_scene.py'),'--python',str(ROOT/'tools/validate_score.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    print('DIRECTOR STAGE: coverage and continuity validated',flush=True)
    frames=[23,373,499,841,1009]
    parts=[{'frames':[f],'start':(f-1)/24,'end':f/24,'fps':24,'output_frames':1,
            'shot':next(s['id'] for s in c['shots'] if s['start']<=(f-1)/24<s['end'])} for f in frames]
    probes=out/'probes'
    job={'out':str(probes),'profile':'balanced','samples':16,'resolution':[720,1280],
         'segments':parts,'external_captions':True,'max_seconds':120}
    job_path=out/'probe_job.json';job_path.write_text(json.dumps(job,indent=2));env['QUALITY_JOB']=str(job_path)
    with (out/'probes.log').open('w') as log:
        subprocess.run([a.blender,'--background','--factory-startup',str(source),'--threads','4',
            '--python-exit-code','1','--python',str(ROOT/'tools/render_quality.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    print(json.dumps({'coverage':assess_coverage(c),'scene_validation':json.loads((out/'scene_validation.json').read_text())['passed'],
                      'narration_lines':len(mix['narration']),'narration_overruns':[r['overrun_seconds'] for r in mix['narration']],
                      'original_story_state_preserved':c['production']==original['production'],
                      'reference_media_used_in_render':False,'checkpoint_written':False,'readiness':'NOT_READY'},indent=2))


if __name__=='__main__':
    main()
