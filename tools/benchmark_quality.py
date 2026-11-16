"""Bounded quality experiments using a fixed Episode 3 plan, never story memory.

Output is isolated under artifacts/quality. No GitHub calls, uploads, checkpoint
writes or automatic follow-on episodes are implemented here.
"""
import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import platform
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.compiler import compile_plan
from autonomy.checkpoint import unpack
from quality.plan import segments,interpolation_filter
from tools.media import probe


def timestamp(t):
    ms=round(t*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blender',default=shutil.which('blender'))
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--source',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=['native','hybrid','baseline','probe'],default='native')
    p.add_argument('--profile',choices=['original','balanced'],default='balanced')
    p.add_argument('--samples',type=int,default=16)
    p.add_argument('--width',type=int,choices=[720,1080],default=720)
    p.add_argument('--start',type=float,default=26)
    p.add_argument('--duration',type=float,default=10)
    p.add_argument('--max-seconds',type=int,default=1800)
    a=p.parse_args()
    if not a.blender or not a.ffmpeg or not 1<=a.samples<=64 or not 1<=a.max_seconds<=3600:
        p.error('Executable paths and bounded render settings required')
    out=a.out.resolve()
    if not out.is_relative_to((ROOT/'artifacts/quality').resolve()):
        p.error('Benchmark output must stay under artifacts/quality')
    out.mkdir(parents=True,exist_ok=True)
    seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
    plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
    c=compile_plan(plan,json.loads((ROOT/'config/cloud_preview.json').read_text()))
    parts=segments(c,a.start,a.duration,'native' if a.mode=='probe' else a.mode)
    if a.mode=='probe':
        parts=[{'start':(f-1)/24,'end':f/24,'frames':[f],'fps':24,'output_frames':1,
                'shot':next(s['id'] for s in c['shots'] if s['start']<=(f-1)/24<s['end'])}
               for f in [25,649,745,829,937]]
    resolution=[180,320] if a.mode=='baseline' else [a.width,a.width*16//9]
    config=out/'episode.json'
    config.write_text(json.dumps(c,indent=2))
    source=a.source.resolve() if a.source else out/'source.blend'
    env=os.environ.copy()
    env.update(ENABLE_REFLECTIONS='0',EPISODE_CONFIG=str(config),EPISODE_OUTPUT=str(out),SCENE_BLEND=str(source))
    env.pop('ALLOW_REBUILD',None)
    def run(command,name,timeout):
        print('BENCHMARK STAGE '+name,flush=True)
        t=time.monotonic()
        with (out/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        result.check_returncode()
        return time.monotonic()-t
    if not source.exists():
        if a.source:
            raise FileNotFoundError(source)
        run([sys.executable,str(ROOT/'tools/prepare_audio.py'),'--config',str(config),'--out',str(out/'audio')],'audio',120)
        run([a.blender,'--background','--factory-startup','--threads','4','--python-exit-code','1',
             '--python',str(ROOT/'story_scene.py'),'--python',str(ROOT/'tools/validate_score.py')],'build',180)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    job={'out':str(out),'profile':a.profile,'samples':a.samples,'resolution':resolution,
         'segments':parts,'max_seconds':a.max_seconds,'source_sha256':source_hash,'external_captions':True,
         'renderer_sha256':hashlib.sha256((ROOT/'tools/render_quality.py').read_bytes()).hexdigest(),
         'profile_sha256':hashlib.sha256((ROOT/'quality/profile.py').read_bytes()).hexdigest()}
    job_path=out/'job.json'
    if job_path.exists() and json.loads(job_path.read_text())!=job:
        raise FileExistsError('Output already belongs to another benchmark; choose a fresh directory')
    job_path.write_text(json.dumps(job,indent=2))
    env['QUALITY_JOB']=str(job_path)
    elapsed=run([a.blender,'--background','--factory-startup',str(source),'--threads','4',
                 '--python-exit-code','1','--python',str(ROOT/'tools/render_quality.py')],'render',a.max_seconds+120)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'Source master changed'
    visual=json.loads((out/'visual_validation.json').read_text())
    times=[r['seconds'] for r in json.loads((out/'timings.json').read_text()) if r['seconds'] is not None]
    report={'mode':a.mode,'profile':a.profile,'resolution':resolution,'samples':a.samples,
            'rendered_frames':len(times),'render_process_seconds':elapsed,'render_seconds':sum(times),
            'first_frame_seconds':times[0] if times else None,'warm_median_seconds':statistics.median(times[1:]) if len(times)>1 else None,
            'source_sha256':source_hash,'story_state_written':False,'visual_checks_passed':visual['passed'],
            'execution_environment':'github_actions' if os.environ.get('GITHUB_ACTIONS')=='true' else 'local',
            'platform':platform.platform(),'timing_scope':'Accumulated actual frame timings; process time is this invocation only'}
    if a.mode!='probe':
        paths=[]
        composition_started=time.monotonic()
        for i,part in enumerate(parts):
            target=f'part_{i:03d}.mp4'
            vf=f'fps=24,trim=end_frame={part["output_frames"]},setpts=PTS-STARTPTS' if a.mode=='baseline' else interpolation_filter(part['fps'],part['output_frames'])
            if part.get('reusable_plate'):
                vf=f'tpad=stop_mode=clone:stop_duration={part["output_frames"]/24},fps=24,trim=end_frame={part["output_frames"]},setpts=PTS-STARTPTS'
            run([a.ffmpeg,'-hide_banner','-y','-framerate',str(part['fps']),'-i',f'part_{i:03d}/frame_%04d.png',
                 '-vf',vf,'-an','-c:v','libx264','-crf','17','-preset','fast','-pix_fmt','yuv420p',target],f'encode_part_{i:03d}',300)
            paths.append("file '"+target+"'")
        (out/'concat.txt').write_text('\n'.join(paths)+'\n')
        captions=[]
        for cue in c['captions']:
            start,end=max(a.start,cue['start']),min(a.start+a.duration,cue['end'])
            if start<end:
                captions.append(f'{len(captions)+1}\n{timestamp(start-a.start)} --> {timestamp(end-a.start)}\n{cue["text"]}\n')
        (out/'captions.srt').write_text('\n'.join(captions),encoding='utf-8')
        video=out/f'quality_{a.mode}_{resolution[0]}p24.mp4' if a.mode!='baseline' else out/'baseline_180p24_container.mp4'
        filters="subtitles=captions.srt:force_style='FontName=Arial,FontSize=12,Outline=1,MarginV=40,MarginL=24,MarginR=36'"
        if a.profile=='balanced':
            filters='hqdn3d=1.5:1.0:0:0,'+filters
        run([a.ffmpeg,'-hide_banner','-y','-f','concat','-safe','0','-i','concat.txt','-ss',str(a.start),'-i','audio.wav',
             '-map','0:v:0','-map','1:a:0','-vf',filters,
             '-t',str(a.duration),'-r','24','-c:v','libx264','-crf','17','-preset','fast','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','128k','-movflags','+faststart',str(video)],'compose',300)
        run([a.ffmpeg,'-v','error','-i',str(video),'-f','null','-'],'decode',120)
        if (out/'decode.log').read_text().strip():
            raise ValueError('Video decoder reported errors')
        info=probe(video)
        v=next(t for t in info['tracks'] if t['type']=='vide')
        assert [v['width'],v['height']]==resolution and v['samples']==round(a.duration*24) and v['fps']==24
        assert abs(v['duration']-a.duration)<.01 and any(t['type']=='soun' for t in info['tracks'])
        report.update(video=str(video),video_info=info,decode_passed=True,composition_seconds=time.monotonic()-composition_started,
                      sha256=hashlib.sha256(video.read_bytes()).hexdigest(),limitation='Hybrid is optical-flow reconstruction, not native animation; inspect edges and occlusions' if a.mode=='hybrid' else None)
    (out/'benchmark.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
