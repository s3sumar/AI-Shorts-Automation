"""Real, isolated creative episode -> voice/captions -> Blender -> MP4.

Development previews only. Media verification does not grant public readiness.
No production database, network inference or uploading is performed here.
"""
import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import time
import math
from pathlib import Path
from .contracts import ROOT,digest,file_digest,write_json
from .creative_contract import validate_episode
from .creative_compile import compile_creative,require_renderable


def fit_dialogue(score,library,out,ffmpeg,reuse_sources=()):
    from soundstage.casting import VoiceCast,resolve_delivery
    from soundstage.take_cache import seed_takes
    (out/'timing_probe').mkdir(parents=True,exist_ok=True)
    score=copy.deepcopy(score);cast=VoiceCast(library,score,ffmpeg,out/'timing_probe');sources=[];changes=[]
    for i,line in enumerate(score['narration']):
        authored_end=line['end']
        seed_takes([line],library,out/'timing_probe'/f'line_{i:02d}',reuse_sources)
        pace=resolve_delivery(library,line)[2]['pace']
        for attempt in range(3):
            folder=out/'timing_probe'/f'line_{i:02d}'/f'voice/take_{attempt:02d}'
            take=cast.render_line(line,folder)
            spoken=max(w['end'] for w in take['words']);available=line['end']-line['start']
            total=take['duration']
            # Respect both the authored cue and the next line; never cut samples.
            next_start=score['narration'][i+1]['start'] if i+1<len(score['narration']) else 45
            permitted=min(available,next_start-line['start']-.03)
            tail_limit=min(available+library['timing']['max_tail_overrun_seconds'],next_start-line['start']-.03)
            if spoken<=permitted and total<=tail_limit:
                sources.append(folder.parent.parent);break
            revised=round(max(.75,pace*min(permitted/max(spoken,.01),
                tail_limit/max(total,.01))*.97),4)
            if revised>=pace or attempt==2:
                treatment=score.get('narrative_treatment',{})
                beat_id=treatment.get('cue_links',{}).get(line['id'],{}).get('beat')
                beat=next((b for b in treatment.get('beats',[]) if b['id']==beat_id),None)
                ceiling=min(authored_end+.25,next_start-.03,beat['end']-.02 if beat else authored_end)
                needed=line['start']+max(spoken,total-library['timing']['max_tail_overrun_seconds'])+.02
                if beat and needed<=ceiling and total<=next_start-line['start']-.03:
                    line['end']=math.ceil(needed*1000)/1000
                    changes.append({'cue':line['id'],'from_end':authored_end,'to_end':line['end'],
                        'reason':'measured platform variation; borrow <=250ms of existing silence inside the same beat'})
                    sources.append(folder.parent.parent);break
                raise ValueError('Dialogue needs a writing revision; cannot fit cue '+line['id'])
            changes.append({'cue':line['id'],'from_pace':pace,'to_pace':revised,'reason':'measured engine speech overrun'})
            pace=revised;line['pace']=pace
        else:raise ValueError('Unresolved dialogue timing')
    seed_takes(score['narration'],library,out/'audio',sources)
    write_json(out/'timing_adjustments.json',changes)
    return score


def produce(bible,episode,memory,out,blender,ffmpeg,resolution=(180,320),fps=2,max_seconds=1200,reuse_audio=None):
    out=Path(out).resolve()
    if not out.is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Use isolated artifacts media output')
    if out.exists():raise FileExistsError('Preserve completed/partial media; choose a fresh output')
    if fps not in [2,6,12,24] or len(resolution)!=2 or any(type(n)!=int or n<64 or n>1920 or n%2 for n in resolution):raise ValueError('Invalid preview settings')
    if max_seconds>2400 or max_seconds<30:raise ValueError('Invalid media runtime budget')
    validate_episode(episode,bible,memory)
    compiled=compile_creative(episode,bible,memory);require_renderable(compiled['blender_storyboard'])
    out.mkdir(parents=True);started=time.monotonic();stages=[]
    for name,data in [('episode.json',episode),('series_bible.json',bible),('input_memory.json',memory),
                      ('blender_storyboard.json',compiled['blender_storyboard'])]:write_json(out/name,data)
    def run(command,name,cwd=ROOT):
        remaining=max_seconds-(time.monotonic()-started)
        if remaining<=0:raise TimeoutError('Creative media time budget exhausted')
        print('CREATIVE MEDIA STAGE: '+name,flush=True);t=time.monotonic()
        with (out/(name+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=remaining,check=True)
        stages.append({'stage':name,'seconds':time.monotonic()-t})
    env=dict(os.environ);env.update(FFMPEG_BIN=ffmpeg,EPISODE_OUTPUT=str(out),
        EPISODE_RENDER_MODE='preview',MAX_PREVIEW_FRAMES=str(45*fps))
    try:
        library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
        score=compiled['audio_score']
        reuse_sources=[]
        if reuse_audio:
            previous=Path(reuse_audio).resolve().parent
            if digest(json.loads((previous/'episode.json').read_text()))!=digest(episode):raise ValueError('Reused audio belongs to another screenplay')
            if (previous/'audio_score.json').exists():score=json.loads((previous/'audio_score.json').read_text())
            else:
                for i,line in enumerate(score['narration']):
                    receipts=sorted((previous/'timing_probe'/f'line_{i:02d}').glob('voice/take_*/delivery.json'))
                    if receipts:line['pace']=json.loads(receipts[-1].read_text())['delivery_controls']['pace']
            reuse_sources=[reuse_audio]+list((previous/'timing_probe').glob('line_*'))
        score=fit_dialogue(score,library,out,ffmpeg,reuse_sources)
        performance_episode=copy.deepcopy(episode);performance_episode['narration']=copy.deepcopy(score['narration'])
        validate_episode(performance_episode,bible,memory)
        write_json(out/'performance_episode.json',performance_episode)
        write_json(out/'audio_score.json',score)
        from soundstage.pipeline import prepare
        audio=prepare(score,out/'audio',library,ffmpeg)
        if max(len(c['text'])/(c['end']-c['start']) for c in audio['captions'])>22:
            raise ValueError('Caption reading speed requires a timing/writing revision')
        write_json(out/'audio_score.json',score)
        render_config={'schema_version':2,'episode':episode['episode'],'duration':45,'fps':24,
            'resolution':[720,1280],'preview':{'fps':fps,'resolution':list(resolution),'samples':8}}
        write_json(out/'render_config.json',render_config)
        run([blender,'--background','--factory-startup','--threads','4','--python-exit-code','1',
            '--python',str(ROOT/'production/creative_scene.py'),'--',str(out)],'build')
        run([blender,'--background',str(out/'creative_master.blend'),'--threads','4',
            '--python-exit-code','1','--python',str(ROOT/'tools/render_episode.py')],'render')
        from tools.media import validate_png,probe
        files=sorted((out/'preview_frames').glob('frame_*.png'))
        if len(files)!=45*fps:raise ValueError('Incomplete creative frame sequence')
        for i,path in enumerate(files,1):
            if path.name!=f'frame_{i:04d}.png':raise ValueError('Creative frame gap')
            validate_png(path,list(resolution))
        video=out/'creative_episode_preview.mp4'
        run([ffmpeg,'-v','error','-framerate',str(fps),'-i','preview_frames/frame_%04d.png',
             '-i','audio/episode_mix.wav','-vf','ass=audio/captions.ass','-map','0:v:0','-map','1:a:0',
             '-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t','45',
             '-movflags','+faststart',str(video)],'encode',out)
        run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],'full_decode')
        info=probe(video);stream=next(t for t in info['tracks'] if t['type']=='vide')
        if abs(stream['duration']-45)>.01 or [stream['width'],stream['height']]!=list(resolution) or stream['samples']!=45*fps:
            raise ValueError('Creative video duration/geometry/frame count mismatch')
        if not any(t['type']=='soun' for t in info['tracks']):raise ValueError('Missing creative audio track')
        scene=json.loads((out/'scene_validation.json').read_text())
        report={'passed':True,'duration':45,'resolution':list(resolution),'fps':fps,'frames':len(files),
            'video':str(video.relative_to(ROOT)),'video_sha256':file_digest(video),
            'master':str((out/'creative_master.blend').relative_to(ROOT)),'script_sha256':digest(episode),
            'input_memory_sha256':digest(memory),'scene_passed':scene['passed'],'audio_passed':True,
            'full_decode_passed':True,'caption_fallbacks':audio['caption_fallbacks'],
            'seconds':time.monotonic()-started,'stages':stages,'quality_status':'NOT_READY',
            'development_preview':True,'checkpoint_written':False,'uploaded':False,
            'limitations':scene['limitations']+['Sampled low-resolution preview; not native full-quality motion']}
        write_json(out/'media_validation.json',report)
        # A private upload job is prepared only; no network operation occurs.
        job={'episode_uid':bible['id']+f'_e{episode["episode"]:03d}','video':report['video'],
            'video_sha256':report['video_sha256'],'production_readiness':'NOT_READY','approved':False,
            'metadata':{'snippet':{'title':(bible['title']+' | '+episode['title'])[:100],
                'description':episode['synopsis'],'categoryId':'24'},
                'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}}}
        write_json(out/'youtube_private_upload.json',job)
        return report
    except Exception as error:
        write_json(out/'media_error.json',{'error':type(error).__name__,'detail':str(error)[:800],
            'checkpoint_written':False,'uploaded':False,'stages':stages})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bible',type=Path,required=True);p.add_argument('--episode',type=Path,required=True)
    p.add_argument('--memory',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--blender',required=True);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--fps',type=int,default=2);p.add_argument('--width',type=int,default=180);p.add_argument('--height',type=int,default=320)
    p.add_argument('--reuse-audio',type=Path)
    a=p.parse_args();r=produce(*[json.loads(q.read_text()) for q in [a.bible,a.episode,a.memory]],a.out,a.blender,a.ffmpeg,(a.width,a.height),a.fps,reuse_audio=a.reuse_audio)
    print(json.dumps(r,indent=2))
