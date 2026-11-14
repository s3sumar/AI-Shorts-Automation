"""One local command: audio -> build -> validate -> sampled render -> MP4.

Supply executable paths or put blender and ffmpeg on PATH. No publishing actions.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='episodes/episode_001.json')
    p.add_argument('--blender',default=shutil.which('blender'))
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--engine',choices=['BLENDER_EEVEE','CYCLES'],default='BLENDER_EEVEE')
    p.add_argument('--rebuild-generated',action='store_true',help='Allow replacing generated master; original assets remain protected')
    a=p.parse_args()
    if not a.blender or not a.ffmpeg:
        p.error('Supply --blender and --ffmpeg or add them to PATH')
    cfg=(ROOT/a.config).resolve()
    c=json.loads(cfg.read_text(encoding='utf-8'))
    if c.get('schema_version')!=2:
        p.error('This production command requires schema_version 2; legacy episodes use story_scene.py directly')
    out=ROOT/'artifacts'/f'episode_{c["episode"]:03d}'
    master=out/f'episode_{c["episode"]:03d}_master.blend'
    if master.exists() and not a.rebuild_generated:
        p.error('Generated master exists; use --rebuild-generated to revise it')
    if master.exists():
        import datetime
        backup=out/'revisions'/('master_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(master,backup)
    env=os.environ.copy()
    env.update(EPISODE_CONFIG=str(cfg),SCENE_BLEND=str(master),EPISODE_OUTPUT=str(out),
               RENDER_ENGINE=a.engine,ALLOW_REBUILD='1' if a.rebuild_generated else '0')
    subprocess.run([sys.executable,str(ROOT/'tools/prepare_audio.py'),'--config',str(cfg),'--out',str(out/'audio')],cwd=ROOT,check=True)
    subprocess.run([a.blender,'--background','--factory-startup','--python-exit-code','1','--python',str(ROOT/'story_scene.py'),
                    '--python',str(ROOT/'tests/validate_episode.py')],env=env,cwd=ROOT,check=True)
    # A native graphics crash cannot be caught inside Blender Python. Fresh
    # processes can resume the validated frame plan without rebuilding the scene.
    for attempt in range(1,4):
        result=subprocess.run([a.blender,'--background',str(master),'--python-exit-code','1',
                               '--python',str(ROOT/'tools/render_episode.py')],env=env,cwd=ROOT)
        if result.returncode==0:
            break
        if attempt==3:
            result.check_returncode()
        print(f'Render process exited {result.returncode}; resuming in a fresh process ({attempt}/3)',flush=True)
    subprocess.run([sys.executable,str(ROOT/'tools/encode_episode.py'),'--config',str(cfg),'--out',str(out),'--ffmpeg',a.ffmpeg],cwd=ROOT,check=True)


if __name__=='__main__':
    main()
