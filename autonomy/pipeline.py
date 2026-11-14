"""Bounded, resumable production orchestration. No remote inference or uploads by default."""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import datetime
from pathlib import Path
from .contracts import ROOT,digest,file_digest,write_json
from .compiler import compile_plan
from .director import LocalModel
from .store import Memory


def benchmark(out):
    records=json.loads((out/'frame_timings.json').read_text())
    records=sorted(records,key=lambda r:r['index'])
    warm=[r['seconds'] for r in records[1:]]
    values=sorted(warm or [records[0]['seconds']])
    meta=json.loads((out/'render_metadata.json').read_text())
    report={'measured':True,'engine':meta['engine'],'resolution':meta['resolution'],'samples':meta['samples'],
        'rendered_frames':len(records),'cold_first_frame_seconds':records[0]['seconds'],
        'warm_median_seconds':statistics.median(values),'warm_p95_seconds':values[min(int(.95*len(values)),len(values)-1)],
        'total_frame_render_seconds':sum(r['seconds'] for r in records),
        'estimated_1080_frame_seconds_at_same_settings':1080*statistics.mean(values),
        'estimate_caveat':'Linear extrapolation at preview settings; not a measured 24 FPS/full-quality render'}
    write_json(out/'benchmark.json',report)
    return report


def verify_outputs(out,c,ffmpeg):
    scene=json.loads((out/'scene_validation.json').read_text())
    video=json.loads((out/'video_validation.json').read_text())
    audio=json.loads((out/'audio/audio_manifest.json').read_text())
    if not scene.get('passed') or not video.get('full_decode_passed'):
        raise ValueError('Scene or video verification did not pass')
    if scene.get('score_hash')!=digest(c):
        raise ValueError('Saved master does not match the compiled story score')
    if len(audio['narration'])!=len(c['narration']) or any(line['status']!='synthesized' for line in audio['narration']):
        raise ValueError('Narration missing; continuity will not advance')
    if audio['duration']!=c['duration'] or audio['peak']>.95:
        raise ValueError('Invalid sound mix')
    path=out/f'episode_{c["episode"]:03d}_preview.mp4'
    # Read the actual output again at the commit boundary; reports alone are insufficient.
    from tools.media import probe
    info=probe(path)
    stream=next(s for s in info['tracks'] if s['type']=='vide')
    if [stream['width'],stream['height']]!=c['preview']['resolution'] or abs(stream['duration']-c['duration'])>.01:
        raise ValueError('Output geometry/duration changed after encoding')
    if not any(s['type']=='soun' for s in info['tracks']):
        raise ValueError('Missing audio stream')
    result=subprocess.run([ffmpeg,'-v','error','-i',str(path),'-f','null','-'],capture_output=True,text=True,timeout=180)
    if result.returncode or result.stderr.strip():
        raise ValueError('Final video decode failed')
    return {'passed':True,'scene_passed':True,'audio_passed':True,'video_sha256':file_digest(path),
            'video':path.relative_to(ROOT).as_posix(),'scene':(out/f'episode_{c["episode"]:03d}_master.blend').relative_to(ROOT).as_posix(),
            'score_hash':digest(c),'video_bytes':path.stat().st_size}


def produce(memory,row,settings,blender,ffmpeg,output_root=None):
    plan=json.loads(row['plan'])
    out=(Path(output_root) if output_root else ROOT/'artifacts/autonomy')/plan['uid']
    if row['status']=='verified':
        evidence=json.loads(row['evidence'])
        media=ROOT/evidence['video']
        if not media.exists():
            raise FileNotFoundError('Verified media is absent; restore its run artifact rather than creating a duplicate episode')
        if file_digest(media)!=evidence['video_sha256']:
            raise ValueError('Previously verified video has changed; restore the verified artifact')
        return evidence
    out.mkdir(parents=True,exist_ok=True)
    c=compile_plan(plan,settings)
    count=round(c['duration']*c['preview']['fps'])
    if count>settings['limits']['max_preview_frames']:
        raise ValueError('Preview exceeds frame budget')
    write_json(out/'story_plan.json',plan)
    config=out/'episode.json'
    if config.exists() and digest(json.loads(config.read_text()))!=digest(c) and any(out.glob('*.blend')):
        raise ValueError('Existing master has a different score; preserve it and use a new development run')
    write_json(config,c)
    master=out/f'episode_{c["episode"]:03d}_master.blend'
    env=os.environ.copy()
    env.update(EPISODE_CONFIG=str(config),EPISODE_OUTPUT=str(out),SCENE_BLEND=str(master),
               EPISODE_RENDER_MODE='preview',MAX_PREVIEW_FRAMES=str(settings['limits']['max_preview_frames']),
               RENDER_ENGINE=settings['render']['engine'])
    # Never let an inherited variable authorize replacing a master in this runner.
    env.pop('ALLOW_REBUILD',None)
    started=time.monotonic()

    def run(command,name,timeout=None):
        remaining=settings['limits']['max_total_seconds']-(time.monotonic()-started)
        if remaining<=0:
            raise TimeoutError('Production time budget exhausted')
        limit=min(timeout or settings['render']['timeout_seconds'],remaining)
        print(f'PRODUCTION STAGE: {name}; timeout={limit:.0f}s; log={out/(name+".log")}',flush=True)
        with (out/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=limit)
        print(f'PRODUCTION STAGE COMPLETE: {name}; exit={result.returncode}',flush=True)
        return result

    memory.mark(plan['uid'],'rendering')
    try:
        run([sys.executable,str(ROOT/'tools/prepare_audio.py'),'--config',str(config),'--out',str(out/'audio')],'audio').check_returncode()
        audio=json.loads((out/'audio/audio_manifest.json').read_text())
        if any(v['status']!='synthesized' for v in audio['narration']):
            raise RuntimeError('Offline narration unavailable; install espeak-ng or authorize Windows speech. Timing files were preserved.')
        command=[blender,'--background']
        if master.exists():
            command+=[str(master)]
        else:
            command+=['--factory-startup']
        command+=['--threads',str(settings['render']['threads']),'--python-exit-code','1']
        if not master.exists():
            command+=['--python',str(ROOT/'story_scene.py')]
        command+=['--python',str(ROOT/'tools/validate_score.py')]
        run(command,'build_validate').check_returncode()
        scene=json.loads((out/'scene_validation.json').read_text())
        if scene.get('score_hash')!=digest(c):
            raise ValueError('Existing master differs from story instructions')
        for attempt in range(1,settings['render']['attempts']+1):
            result=run([blender,'--background',str(master),'--threads',str(settings['render']['threads']),
                '--python-exit-code','1','--python',str(ROOT/'tools/render_episode.py')],f'render_attempt_{attempt}')
            if result.returncode==0:
                break
            if attempt==settings['render']['attempts']:
                result.check_returncode()
        run([sys.executable,str(ROOT/'tools/encode_episode.py'),'--config',str(config),'--out',str(out),'--ffmpeg',ffmpeg],'encode',180).check_returncode()
        evidence=verify_outputs(out,c,ffmpeg)
        report=benchmark(out)
        write_json(out/'production_receipt.json',evidence)
        from .youtube import prepare_upload
        prepare_upload(out,evidence,plan)
        memory.commit_verified(plan['uid'],evidence)
        return evidence
    except Exception as ex:
        memory.mark(plan['uid'],'failed',type(ex).__name__+': '+str(ex)[:500])
        write_json(out/'production_error.json',{'error':type(ex).__name__,'detail':str(ex)[:500],'canon_advanced':False})
        raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['bootstrap','plan','produce','status'])
    p.add_argument('--state',default='state/story.sqlite3')
    p.add_argument('--settings',default='config/autonomy.json')
    p.add_argument('--run-key',default='manual-preview')
    p.add_argument('--blender',default=shutil.which('blender'))
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--trusted-seed',action='store_true',help='Bootstrap from checked-in verified provenance when local seed media is absent')
    p.add_argument('--output-root',default='artifacts/autonomy',help='Separate test media from existing completed masters')
    a=p.parse_args()
    settings=json.loads((ROOT/a.settings).read_text())
    if settings['paid_services_enabled'] or settings['limits']['episodes_per_run']!=1:
        p.error('This version permits one bounded episode per run and no paid service provider')
    memory=Memory(ROOT/a.state)
    try:
        if a.command=='bootstrap':
            memory.bootstrap(verify_local=not a.trusted_seed)
            result={'bootstrapped':True}
        elif a.command=='status':
            result={'episodes':[dict(r) for r in memory.db.execute('SELECT uid,status,error FROM episodes ORDER BY number')]}
        else:
            provider=settings['director']['provider']
            if provider not in ['offline','ollama']:
                p.error('Only offline grammar or a loopback local model is supported')
            model=LocalModel(settings['director']['model']) if provider=='ollama' else None
            row=memory.reserve(a.run_key,model)
            plan=json.loads(row['plan'])
            out=ROOT/'artifacts/autonomy'/plan['uid']
            if a.command=='plan':
                write_json(out/'story_plan.json',plan)
                write_json(out/'episode.json',compile_plan(plan,settings))
                result={'planned':plan['uid'],'source':plan['source'],'series':plan['series_title']}
            else:
                if not a.blender or not a.ffmpeg:
                    p.error('Supply Blender and FFmpeg executable paths')
                result=produce(memory,row,settings,a.blender,a.ffmpeg,ROOT/a.output_root)
        print(json.dumps(result,indent=2))
    finally:
        memory.export(memory.path.with_name(memory.path.stem+'_memory.json'))
        backup=ROOT/'artifacts/autonomy/state_snapshots'/(datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.sqlite3')
        backup.parent.mkdir(parents=True,exist_ok=True)
        memory.backup(backup)
        memory.close()


if __name__=='__main__':
    main()
