"""Short native-frame proof of our own directing pass; no reference assets or canon writes."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quality.plan import segments
from soundstage.captions import ass
from soundstage.media import normalize
from tools.media import probe


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--blender',required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--source-dir',type=Path,default=ROOT/'artifacts/reference_director/episode3_v3')
    a=p.parse_args()
    source=a.source_dir.resolve();out=source/'preview';out.mkdir(exist_ok=True)
    video=out/'original_director_v3_720p24.mp4'
    if video.exists(): raise FileExistsError('Preserve the completed director preview')
    c=json.loads((source/'episode.json').read_text())
    parts=segments(c,14.5,5,'native')
    job={'out':str(out),'profile':'balanced','samples':16,'resolution':[720,1280],
         'segments':parts,'external_captions':True,'max_seconds':600}
    job_path=out/'job.json';job_path.write_text(json.dumps(job,indent=2))
    env=os.environ.copy();env['QUALITY_JOB']=str(job_path)
    with (out/'render.log').open('w') as log:
        subprocess.run([a.blender,'--background','--factory-startup',str(source/'director_source.blend'),
            '--threads','4','--python-exit-code','1','--python',str(ROOT/'tools/render_quality.py')],
            env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=720)
    def run(command,name):
        result=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=180)
        (out/(name+'.log')).write_text(result.stderr,encoding='utf-8');result.check_returncode()
    for i,part in enumerate(parts):
        run([a.ffmpeg,'-v','error','-y','-framerate','24','-i',f'part_{i:03d}/frame_%04d.png','-frames:v',str(part['output_frames']),
            '-c:v','libx264','-crf','17','-preset','fast','-pix_fmt','yuv420p',f'part_{i:03d}.mp4'],f'encode_{i}')
    (out/'concat.txt').write_text('\n'.join(f"file 'part_{i:03d}.mp4'" for i in range(len(parts)))+'\n')
    aligned=json.loads((source/'alignment/word_alignment.json').read_text())
    clipped=[dict(v,start=max(0,v['start']-14.5),end=min(5,v['end']-14.5))
             for v in aligned['captions'] if v['start']<19.5 and v['end']>14.5]
    (out/'captions.ass').write_text(ass(clipped),encoding='utf-8-sig')
    run([a.ffmpeg,'-v','error','-y','-ss','14.5','-i',str(source/'audio/episode_mix.wav'),'-t','5','-c:a','pcm_s24le','clip.wav'],'audio_clip')
    normalize(out/'clip.wav',out/'matched.wav',a.ffmpeg)
    run([a.ffmpeg,'-v','error','-y','-f','concat','-safe','0','-i','concat.txt','-i','matched.wav','-map','0:v:0','-map','1:a:0',
        '-vf','hqdn3d=1.5:1.0:0:0,ass=captions.ass','-t','5','-r','24','-c:v','libx264','-crf','17','-preset','fast',
        '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(video)],'compose')
    run([a.ffmpeg,'-v','error','-i',str(video),'-f','null','-'],'decode')
    info=probe(video);v=next(t for t in info['tracks'] if t['type']=='vide')
    assert v['samples']==120 and v['fps']==24 and v['constant_frame_rate']
    assert [v['width'],v['height']]==[720,1280] and abs(v['duration']-5)<.01
    result={'passed':True,'video':str(video),'media':info,'native_source_frames':120,
            'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'reference_media_used':False,
            'caption_fallbacks_require_review':True,'checkpoint_written':False,'readiness':'NOT_READY'}
    (out/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
