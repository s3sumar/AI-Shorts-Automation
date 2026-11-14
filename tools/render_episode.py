"""Blender runner: render a complete sampled preview without changing the master."""
import bpy
import json
import os
import time
import hashlib
import datetime
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from media import validate_png

s=bpy.context.scene
c=json.loads(s['episode_config'])
root=Path(__file__).resolve().parents[1]
out=Path(os.environ.get('EPISODE_OUTPUT',str(root/'artifacts'/f'episode_{c["episode"]:03d}')))
if not out.is_absolute():
    out=root/out
out.mkdir(parents=True,exist_ok=True)
mode=os.environ.get('EPISODE_RENDER_MODE','preview')
s.render.engine=os.environ.get('RENDER_ENGINE',s.render.engine)
settings=c['preview'] if mode=='preview' else {'fps':c['fps'],'resolution':c['resolution'],'samples':16}
step=c['fps']//settings['fps']
if mode not in ['preview','master'] or step<1 or c['fps']%settings['fps']:
    raise ValueError('Invalid render mode or sampling rate')
if len(range(1,s.frame_end+1,step))>int(os.environ.get('MAX_PREVIEW_FRAMES','100000')):
    raise ValueError('Render exceeds configured frame budget')
s.render.resolution_x,s.render.resolution_y=settings['resolution']
s.render.resolution_percentage=100
if hasattr(s,'eevee'):
    for prop in ['taa_render_samples','taa_samples']:
        if hasattr(s.eevee,prop):
            setattr(s.eevee,prop,settings['samples'])
if s.render.engine=='CYCLES':
    s.cycles.device='CPU'
    s.cycles.samples=settings['samples']
    s.cycles.use_denoising=True
frames_dir=out/(mode+'_frames')
render_identity={'settings':settings,'engine':s.render.engine}
signature=hashlib.sha256(Path(bpy.data.filepath).read_bytes()+json.dumps(render_identity,sort_keys=True).encode()).hexdigest()
plan=out/(mode+'_render_plan.json')
previous=json.loads(plan.read_text()) if plan.exists() else {}
if frames_dir.exists() and any(frames_dir.iterdir()) and previous.get('signature')!=signature:
    # Preserve stale renders; never silently mix versions during resume.
    revisions=out/'revisions'
    revisions.mkdir(exist_ok=True)
    destination=revisions/(mode+'_frames_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    assert frames_dir.resolve().parent==out.resolve()
    assert destination.resolve().parent==revisions.resolve() and revisions.resolve().parent==out.resolve()
    assert not destination.exists()
    frames_dir.rename(destination)
frames_dir.mkdir(exist_ok=True)
plan.write_text(json.dumps({'signature':signature,'settings':settings,'source_blend':bpy.data.filepath},indent=2))
timings_path=out/'frame_timings.json'
records=json.loads(timings_path.read_text()) if timings_path.exists() and previous.get('signature')==signature else []
times=[]
total=len(range(1,s.frame_end+1,step))
for index,f in enumerate(range(1,s.frame_end+1,step),1):
    path=frames_dir/f'frame_{index:04d}.png'
    s.frame_set(f)
    if path.exists():
        try:
            validate_png(path,settings['resolution'])
        except ValueError:
            damaged=out/'revisions'
            damaged.mkdir(exist_ok=True)
            path.rename(damaged/(path.stem+'_damaged_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.png'))
    if not path.exists():
        s.render.filepath=str(path)
        start=time.monotonic()
        bpy.ops.render.render(write_still=True)
        times.append(time.monotonic()-start)
        validate_png(path,settings['resolution'])
        records=[r for r in records if r['index']!=index]
        records.append({'index':index,'master_frame':f,'camera':s.camera.name,'seconds':times[-1]})
        temporary=timings_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(records))
        temporary.replace(timings_path)
    print(f'EPISODE FRAME {index}/{total} master={f} camera={s.camera.name}',flush=True)
    (out/'render_progress.json').write_text(json.dumps({'completed':index,'total':total,'fps':settings['fps'],
        'resolution':settings['resolution'],'engine':s.render.engine,'samples':settings['samples'],'seconds_rendering':sum(times)}))
metadata={'fps':settings['fps'],'resolution':settings['resolution'],'frames':total,'duration':total/settings['fps'],
          'master_fps':c['fps'],'master_frames':s.frame_end,'engine':s.render.engine,'samples':settings['samples'],
          'seconds_rendering':sum(r['seconds'] for r in records),'mode':mode}
(out/'render_metadata.json').write_text(json.dumps(metadata,indent=2))
print('COMPLETE '+json.dumps(metadata),flush=True)
