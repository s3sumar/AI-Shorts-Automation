"""Episode 3 audio audition and measured revision. Does not touch story storage."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from soundstage.narration import Narrator
from soundstage.media import normalize
from soundstage.pipeline import prepare
from autonomy.checkpoint import unpack
from autonomy.compiler import compile_plan


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'artifacts/production_upgrade/episode3_v1')
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to((ROOT/'artifacts/production_upgrade').resolve()):
        parser.error('Use an isolated production_upgrade directory')
    out.mkdir(parents=True,exist_ok=True)
    candidate=json.loads((ROOT/'config/narrator_candidate.json').read_text())
    texts=['The lift is empty.','So who said her name?','The doors are opening.','Someone is waiting.']
    approaches=[('A_plain_sapi',{'provider':'sapi','voice_id':'sapi_david_reference','voice':'Microsoft David Desktop','directed':False},0,1),
                ('B_directed_sapi',{'provider':'sapi','voice_id':'sapi_david_directed','voice':'Microsoft David Desktop','directed':True},.4,1.06),
                ('C_local_neural',candidate,.4,1.1)]
    samples=[]
    for name,settings,pause,pace in approaches:
        path=out/'samples'/name
        receipt=Narrator(settings,args.ffmpeg).synthesize([{'text':t,'pause_after':pause} for t in texts],path,pace)
        listen=out/'samples'/(name+'_listen.wav')
        loudness=normalize(path/'voice.wav',listen,args.ffmpeg)
        samples.append({'approach':name,'file':str(listen),'identity':receipt['identity'],
                        'duration':receipt['duration'],'loudness':loudness,'human_listening_review':'pending'})
    (out/'voice_comparison.json').write_text(json.dumps(samples,indent=2))
    seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
    plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
    c=compile_plan(plan,json.loads((ROOT/'config/cloud_preview.json').read_text()))
    direction=json.loads((ROOT/'config/episode_003_audio_direction.json').read_text())
    report=prepare(c,out/'audio',candidate,args.ffmpeg,direction)
    (out/'source_score.json').write_text(json.dumps(c,indent=2))
    (out/'direction.json').write_text(json.dumps(direction,indent=2))
    print(json.dumps({'samples':len(samples),'audio_loudness':report['loudness'],
                      'speech_over_bed_db':report['speech_over_bed_db'],'narration_overruns':[v['overrun_seconds'] for v in report['narration']],
                      'mix_seconds':report['elapsed_seconds'],'readiness':'NOT_READY','checkpoint_written':False},indent=2))


if __name__=='__main__':
    main()
