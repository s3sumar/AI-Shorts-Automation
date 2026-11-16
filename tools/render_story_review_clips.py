"""Three fixed review windows only; verified frame reuse, no story-memory writes."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quality.plan import segments
from soundstage.captions import ass
from tools.media import probe,validate_png

WINDOWS=[('beginning',0,5),('middle',17.5,5),('ending',38,7)]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def check_completed_preview(prior,video,scene,audio,caption_sha):
    expected={'sha256':sha(video),'source_scene_sha256':sha(scene),
              'source_audio_sha256':sha(audio),'source_caption_sha256':caption_sha}
    if any(prior.get(k)!=value for k,value in expected.items()):
        raise ValueError('Completed preview has changed inputs or incomplete provenance; preserve it and use a fresh revision directory')


def verify_reuse(source,old):
    from PIL import Image,ImageChops
    current=json.loads((source/'episode.json').read_text())
    previous=json.loads((old.parent/'episode.json').read_text())
    for key in ['floor_events','lighting','effects']:
        assert current[key]==previous[key],('Cache visual setting changed',key)
    a=next(s for s in current['shots'] if s['id']=='countdown_pressure')
    b=next(s for s in previous['shots'] if s['id']=='countdown_pressure')
    assert a==b,'Cache camera changed'
    evidence=[]
    for part,index in [(5,31),(15,1),(16,48)]:
        new=source/f'probes/part_{part:03d}/frame_0001.png'
        cached=old/f'part_001/frame_{index:04d}.png'
        validate_png(new,[720,1280]);validate_png(cached,[720,1280])
        assert ImageChops.difference(Image.open(new).convert('RGB'),Image.open(cached).convert('RGB')).getbbox() is None, 'Cache probe pixels changed'
        evidence.append({'master_frame':420+index,'new_probe':str(new),'cached_frame':str(cached),'pixel_identical':True})
    return evidence


def optional_reuse_evidence(source,old):
    return verify_reuse(source,old) if old.is_dir() else []


def render(source,old,blender,ffmpeg):
    from PIL import Image
    c=json.loads((source/'episode.json').read_text())
    scene=source/'episode3_story_v4.blend'
    alignment=json.loads((source/'alignment.json').read_text())
    audio=source/'audio/episode_mix.wav'
    assert alignment['audio_mix_sha256']==sha(audio), 'Stale caption/audio binding'
    assert not alignment['fallback_phrases']
    # A clean checkout does not contain the optional older render cache.
    cache_proof=optional_reuse_evidence(source,old)
    probe_parts=json.loads((source/'probe_job.json').read_text())['segments']
    probes={p['frames'][0]:source/f'probes/part_{i:03d}/frame_0001.png' for i,p in enumerate(probe_parts)}
    black=source/'probes/part_014/frame_0001.png'
    # Blender's output dither may produce a one-code-value black floor.
    assert all(0<=lo<=hi<=1 for lo,hi in Image.open(black).convert('RGB').getextrema()),'Black plate not black'
    results=[]
    for name,start,duration in WINDOWS:
        out=source/'previews'/name;out.mkdir(parents=True,exist_ok=True)
        video=out/f'episode3_v4_{name}_720p24.mp4'
        clipped=[dict(v,start=max(0,v['start']-start),end=min(duration,v['end']-start))
                 for v in alignment['captions'] if v['start']<start+duration and v['end']>start]
        caption_text=ass(clipped)
        caption_sha=hashlib.sha256(caption_text.encode('utf-8')).hexdigest()
        if video.exists():
            prior=json.loads((out/'validation.json').read_text())
            check_completed_preview(prior,video,scene,audio,caption_sha)
            results.append(prior);continue
        parts=segments(c,start,duration,'native')
        job={'out':str(out),'profile':'balanced','samples':16,'resolution':[720,1280],
             'segments':parts,'external_captions':True,'max_seconds':900,'source_scene_sha256':sha(scene),
             'renderer_sha256':sha(ROOT/'tools/render_quality.py'),'profile_sha256':sha(ROOT/'quality/profile.py')}
        job_path=out/'job.json'
        if job_path.exists(): assert json.loads(job_path.read_text())==job,'Stale partial render job'
        job_path.write_text(json.dumps(job,indent=2))
        reuse=[]
        for i,part in enumerate(parts):
            directory=out/f'part_{i:03d}';directory.mkdir(exist_ok=True)
            for index,f in enumerate(part['frames'],1):
                origin=None;reason=None
                if cache_proof and part['shot']=='countdown_pressure' and 421<=f<=468:
                    origin=old/f'part_001/frame_{f-420:04d}.png';reason='previous render; matching camera/settings plus three pixel-identical probes'
                elif part['shot']=='black': origin=black;reason='intentional validated black hold'
                elif f in probes: origin=probes[f];reason='current revision representative render'
                if origin:
                    target=directory/f'frame_{index:04d}.png'
                    if not target.exists(): shutil.copy2(origin,target)
                    assert sha(target)==sha(origin),'Cached frame changed'
                    reuse.append({'master_frame':f,'source':str(origin),'reason':reason})
        (out/'reuse.json').write_text(json.dumps(reuse,indent=2))
        env=os.environ.copy();env['QUALITY_JOB']=str(job_path)
        print(f'REVIEW RENDER: {name}; {duration}s; preseeded {len(reuse)} frames',flush=True)
        with (out/'render.log').open('w',encoding='utf-8') as log:
            subprocess.run([blender,'--background','--factory-startup',str(scene),'--threads','4','--python-exit-code','1',
                            '--python',str(ROOT/'tools/render_quality.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1020)
        def run(command,label):
            result=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=180)
            (out/(label+'.log')).write_text(result.stderr,encoding='utf-8');result.check_returncode()
        for i,part in enumerate(parts):
            run([ffmpeg,'-v','error','-y','-framerate','24','-i',f'part_{i:03d}/frame_%04d.png','-frames:v',str(part['output_frames']),
                '-c:v','libx264','-crf','17','-preset','fast','-pix_fmt','yuv420p',f'part_{i:03d}.mp4'],f'encode_{i}')
        (out/'concat.txt').write_text('\n'.join(f"file 'part_{i:03d}.mp4'" for i in range(len(parts)))+'\n')
        (out/'captions.ass').write_text(caption_text,encoding='utf-8-sig')
        run([ffmpeg,'-v','error','-y','-ss',str(start),'-i',str(audio),'-t',str(duration),'-c:a','pcm_s24le','clip.wav'],'audio_clip')
        run([ffmpeg,'-v','error','-y','-f','concat','-safe','0','-i','concat.txt','-i','clip.wav','-map','0:v:0','-map','1:a:0',
             '-vf','hqdn3d=1.5:1.0:0:0,ass=captions.ass','-t',str(duration),'-r','24','-c:v','libx264','-crf','17','-preset','fast',
             '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(video)],'compose')
        run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],'decode')
        info=probe(video);v=next(t for t in info['tracks'] if t['type']=='vide');a=next(t for t in info['tracks'] if t['type']=='soun')
        assert v['constant_frame_rate'] and v['fps']==24 and v['samples']==round(duration*24)
        assert [v['width'],v['height']]==[720,1280] and abs(v['duration']-duration)<.01
        assert a['channels']==2 and a['sample_rate']==48000 and abs(a['duration']-duration)<.05
        timings=json.loads((out/'timings.json').read_text())
        result={'passed':True,'name':name,'start':start,'duration':duration,'video':str(video),'sha256':sha(video),
                'media':info,'source_scene_sha256':sha(scene),'source_audio_sha256':sha(audio),'source_caption_sha256':caption_sha,
                'frames_reused':sum(t['reused'] for t in timings),'fresh_frames':sum(not t['reused'] for t in timings),
                'fresh_render_seconds':sum(t['seconds'] or 0 for t in timings if not t['reused']),
                'caption_fallbacks':0,'full_film_rendered':False,'readiness':'NOT_READY'}
        (out/'validation.json').write_text(json.dumps(result,indent=2));results.append(result)
        print(f'REVIEW COMPLETE: {video}',flush=True)
    (source/'preview_summary.json').write_text(json.dumps({'passed':True,'clips':results,'cache_proof':cache_proof,
        'checkpoint_written':False,'full_film_rendered':False},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source-dir',type=Path,default=ROOT/'artifacts/story_review/episode3_v4_reviewed')
    p.add_argument('--old-preview',type=Path,default=ROOT/'artifacts/reference_director/episode3_v3/preview')
    p.add_argument('--blender',required=True);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();source=a.source_dir.resolve()
    if not source.is_relative_to((ROOT/'artifacts/story_review').resolve()): raise ValueError('Use an isolated story-review directory')
    render(source,a.old_preview.resolve(),a.blender,a.ffmpeg)
