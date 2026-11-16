"""Fair level-matched Episode 3 before/after preview from existing native frames."""
import argparse
import hashlib
import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from soundstage.media import normalize
from quality.production_gate import collect,save_report


def stamp(t):
    ms=round(t*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--revision',type=Path,default=ROOT/'artifacts/production_upgrade/episode3_v1')
    p.add_argument('--take',default='comparison')
    args=p.parse_args()
    args.revision=args.revision.resolve()
    if not args.take.replace('_','').isalnum(): p.error('Use a simple take name')
    out=args.revision.resolve()/args.take
    out.mkdir(parents=True,exist_ok=True)
    after=out/'episode3_upgraded_6s_720p24.mp4'
    if after.exists(): raise FileExistsError('Comparison exists; preserve it and create a new revision')
    source=ROOT/'artifacts/quality/native_final_720p24'
    job=json.loads((source/'job.json').read_text())
    assert job['resolution']==[720,1280] and job['external_captions']
    start,duration=29,6
    frame_paths=[]
    for i,part in enumerate(job['segments']):
        for index,f in enumerate(part['frames'],1):
            if 697<=f<=840: frame_paths.append((f,source/f'part_{i:03d}/frame_{index:04d}.png'))
    assert [f for f,path in frame_paths]==list(range(697,841))
    hashes=[hashlib.sha256(path.read_bytes()).hexdigest() for f,path in frame_paths]
    assert len(set(hashes))==144,'Unexpected repeated moving frames'
    started=time.monotonic()
    def run(command,name):
        result=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=180)
        (out/(name+'.log')).write_text(result.stderr,encoding='utf-8')
        result.check_returncode()
    for i,(directory,count) in enumerate([('part_001',120),('part_002',24)]):
        run([args.ffmpeg,'-v','error','-y','-framerate','24','-i',str(source/directory/'frame_%04d.png'),
             '-frames:v',str(count),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',f'picture_{i}.mp4'],f'picture_{i}')
    (out/'pictures.txt').write_text("file 'picture_0.mp4'\nfile 'picture_1.mp4'\n")
    manifest=json.loads((args.revision/'audio/audio_manifest.json').read_text())
    cues=[]
    for cue in manifest['captions']:
        a,b=max(start,cue['start']),min(start+duration,cue['end'])
        if b>a:
            cues.append({'start':a-start,'end':b-start,'text':'\n'.join(textwrap.wrap(cue['text'],30))})
    (out/'captions.srt').write_text('\n'.join(f'{i}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}\n' for i,c in enumerate(cues,1)),encoding='utf-8')
    run([args.ffmpeg,'-v','error','-y','-ss',str(start),'-i',str(args.revision/'audio/episode_mix.wav'),
         '-t',str(duration),'-c:a','pcm_s24le','candidate_clip.wav'],'clip_audio')
    normalize(out/'candidate_clip.wav',out/'candidate_matched.wav',args.ffmpeg)
    run([args.ffmpeg,'-v','error','-y','-f','concat','-safe','0','-i','pictures.txt','-i','candidate_matched.wav',
         '-map','0:v:0','-map','1:a:0','-vf',"hqdn3d=1.5:1.0:0:0,subtitles=captions.srt:force_style='FontName=Arial,FontSize=12,Outline=1,MarginV=40,MarginL=24,MarginR=36'",
         '-t','6','-r','24','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(after)],'compose_after')
    old=source/'quality_native_720p24.mp4'
    run([args.ffmpeg,'-v','error','-y','-ss','3','-i',str(old),'-t','6','-vn','-ac','2','-ar','48000','old_clip.wav'],'old_audio')
    normalize(out/'old_clip.wav',out/'old_matched.wav',args.ffmpeg)
    before=out/'episode3_original_levelmatched.mp4'
    run([args.ffmpeg,'-v','error','-y','-ss','3','-i',str(old),'-i','old_matched.wav','-map','0:v:0','-map','1:a:0',
         '-t','6','-r','24','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',str(before)],'compose_before')
    (out/'comparison.txt').write_text(f"file '{before.name}'\nfile '{after.name}'\n")
    run([args.ffmpeg,'-v','error','-y','-f','concat','-safe','0','-i','comparison.txt','-c','copy','episode3_before_after_12s.mp4'],'comparison')
    clipped=dict(manifest)
    clipped['narration']=[dict(v,start=max(0,v['start']-start),end=min(duration,v['end']-start),
                             actual_end=min(duration,v['actual_end']-start)) for v in manifest['narration'] if start<v['actual_end'] and v['start']<start+duration]
    visual=json.loads((source/'visual_validation.json').read_text())
    facts=collect(after,args.ffmpeg,clipped,{'native':True,'source_frames':144,'contiguous':True,'unique_pngs':144,'duplicate_moving_frames':0,'source_resolution':[720,1280]},cues,
        scene_passed=visual['passed'] and all(v['passed'] for v in visual['continuity_checks']),
        assets_passed=all(path.exists() for f,path in frame_paths),voice_approved=False)
    gate=save_report(out/'production_quality_gate.json',facts)
    (out/'render_provenance.json').write_text(json.dumps({'source_job_sha256':hashlib.sha256((source/'job.json').read_bytes()).hexdigest(),
        'master_frames':[f for f,path in frame_paths],'png_sha256':hashes,'native':True,'no_upscaling':True,'source_resolution':[720,1280]},indent=2))
    print(json.dumps({'after':str(after),'comparison':str(out/'episode3_before_after_12s.mp4'),
                      'audio':facts['audio'],'gate':gate,'composition_seconds':time.monotonic()-started,'checkpoint_written':False},indent=2))


if __name__=='__main__':
    main()
