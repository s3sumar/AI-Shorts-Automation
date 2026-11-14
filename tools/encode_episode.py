"""Verify PNG completeness, encode H.264/AAC and decode the entire video to test it."""
import argparse
import json
import shutil
import subprocess
import datetime
from pathlib import Path
from media import probe,validate_png

ROOT=Path(__file__).resolve().parents[1]


def encode(config,out,ffmpeg):
    cfg=json.loads(config.read_text(encoding='utf-8'))
    metadata_path=out/'render_metadata.json'
    if cfg.get('schema_version')==2:
        meta=json.loads(metadata_path.read_text())
    else:
        meta={'fps':12,'resolution':[432,768],'frames':96,'duration':8,'mode':'preview'}
    directory=out/(meta['mode']+'_frames')
    files=sorted(directory.glob('frame_*.png'))
    expected=[directory/f'frame_{i:04d}.png' for i in range(1,meta['frames']+1)]
    if files!=expected or any(p.stat().st_size<100 for p in files):
        raise RuntimeError(f'Incomplete PNG sequence: expected {len(expected)}, found {len(files)}')
    for p in files:
        validate_png(p,meta['resolution'])
    video=out/f'episode_{cfg["episode"]:03d}_preview.mp4'
    if video.exists():
        revisions=out/'revisions'
        revisions.mkdir(exist_ok=True)
        prior=revisions/(video.stem+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.mp4')
        shutil.copy2(video,prior)
    command=[ffmpeg,'-hide_banner','-y','-framerate',str(meta['fps']),'-start_number','1','-i',str(directory/'frame_%04d.png')]
    audio=out/'audio'/'episode_mix.wav'
    if audio.exists():
        command+=['-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','128k']
    command+=['-c:v','libx264','-crf','20','-preset','medium','-pix_fmt','yuv420p',
              '-t',str(meta['duration']),'-movflags','+faststart',str(video)]
    result=subprocess.run(command,capture_output=True,text=True)
    (out/'ffmpeg_encode.log').write_text(result.stderr,encoding='utf-8')
    result.check_returncode()
    info=probe(video)
    v=next(t for t in info['tracks'] if t['type']=='vide')
    assert [v['width'],v['height']]==meta['resolution'],info
    assert v['samples']==meta['frames'] and abs(v['fps']-meta['fps'])<.001,info
    assert abs(v['duration']-meta['duration'])<.01,info
    if audio.exists():
        assert any(t['type']=='soun' for t in info['tracks']), 'Missing audio track'
    decoded=subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
    (out/'ffmpeg_decode.log').write_text(decoded.stderr,encoding='utf-8')
    decoded.check_returncode()
    assert not decoded.stderr.strip(),decoded.stderr
    info.update(full_decode_passed=True,expected=meta,video=str(video))
    (out/'video_validation.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print('VIDEO PASS '+json.dumps(info))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='episodes/episode_001.json')
    p.add_argument('--out',default='artifacts/episode_001')
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    a=p.parse_args()
    if not a.ffmpeg:
        p.error('FFmpeg not on PATH; supply --ffmpeg /path/to/ffmpeg')
    encode((ROOT/a.config).resolve(),(ROOT/a.out).resolve(),a.ffmpeg)
