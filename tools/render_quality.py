"""Run inside a disposable Blender process. Never saves changes to the source blend."""
import bpy
import json
import os
import sys
import time
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quality.profile import apply
from tools.media import validate_png

job=json.loads(Path(os.environ['QUALITY_JOB']).read_text())
out=Path(job['out'])
out.mkdir(parents=True,exist_ok=True)
s=bpy.context.scene
c=json.loads(s['episode_config'])
changes=apply(s,job['profile'],job['samples'])
caption_objects=[o for o in s.objects if o.name.startswith(('Caption |','Caption backing |'))]
if job.get('external_captions',True):
    # Hide animation must be disconnected: Blender re-evaluates it in render().
    for obj in caption_objects:
        obj.animation_data_clear()
        obj.hide_render=True
s.render.resolution_x,s.render.resolution_y=job['resolution']
s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
s.render.image_settings.color_mode='RGB'
sound=next((v for v in bpy.data.sounds if v.packed_file),None)
if sound and not (out/'audio.wav').exists():
    (out/'audio.wav').write_bytes(bytes(sound.packed_file.data))
records=[]
prior=json.loads((out/'timings.json').read_text()) if (out/'timings.json').exists() else []
prior_times={(r['part'],r['index']):r['seconds'] for r in prior}
started=time.monotonic()
checks=[]
continuity=[]
if 'production' in c:
    for f,key in [(1,'start_state'),(s.frame_end,'end_state')]:
        s.frame_set(f)
        state=c['production'][key]
        for name,attribute,value in [('Passenger root','location',state['passenger_position']),
                                      ('Passenger head pivot','rotation_euler',state['passenger_head']),
                                      ('Shadow root','location',state['shadow_position'])]:
            assert (Vector(getattr(s.objects[name],attribute))-Vector(value)).length<.015,(key,name)
        continuity.append({'frame':f,'state':key,'passed':True})
for part_index,part in enumerate(job['segments']):
    directory=out/f'part_{part_index:03d}'
    directory.mkdir(exist_ok=True)
    for index,f in enumerate(part['frames'],1):
        if time.monotonic()-started>job.get('max_seconds',1800):
            raise TimeoutError('Quality benchmark render budget exhausted; completed frames preserved')
        s.frame_set(f)
        assert s.camera.name=='Shot | '+part['shot'],(f,'camera continuity')
        shot=next(sh for sh in c['shots'] if sh['id']==part['shot'])
        subject=shot.get('subject')
        if subject:
            point=Vector((0,1.58,3.72)) if subject.startswith('Display') else s.objects[subject].matrix_world.translation
            p=world_to_camera_view(s,s.camera,point)
            assert .035<p.x<.965 and .035<p.y<.965 and p.z>0,(f,'subject outside frame')
        if part['shot'] in ['arrival','impact_reaction','doors']:
            head=s.objects['Passenger head']
            p=world_to_camera_view(s,s.camera,head.matrix_world.translation)
            assert not head.hide_render and .01<p.x<.99 and .01<p.y<.99 and p.z>0,(f,'character visibility')
        for light in [o for o in s.objects if o.type=='LIGHT']:
            assert light.data.energy>=0 and all(0<=v<=1 for v in light.data.color),(f,'invalid lighting')
        path=directory/f'frame_{index:04d}.png'
        reused=path.exists()
        if not path.exists():
            s.render.filepath=str(path)
            t=time.monotonic()
            bpy.ops.render.render(write_still=True)
            seconds=time.monotonic()-t
        else:
            seconds=prior_times.get((part_index,index))
        validate_png(path,job['resolution'])
        if job.get('external_captions',True):
            assert all(o.hide_render and o.animation_data is None for o in caption_objects),'Caption animation re-enabled'
        record={'part':part_index,'index':index,'master_frame':f,'camera':s.camera.name,'seconds':seconds,'reused':reused}
        if index in [1,len(part['frames'])//2,len(part['frames'])]:
            import numpy as np
            img=bpy.data.images.load(str(path),check_existing=False)
            pixels=np.empty(len(img.pixels),dtype=np.float32)
            img.pixels.foreach_get(pixels)
            rgb=pixels.reshape(-1,4)[:,:3]
            # Blender decodes PNG pixels to linear; distinguish intentional blackout.
            luminance=rgb@np.array([.2126,.7152,.0722])
            dark=c['effects']['blackout'][0]<=(f-1)/24<=c['effects']['blackout'][1] or part['shot']=='black'
            mean=float(luminance.mean())
            assert dark or mean>.002,(f,'unexpected black frame',mean)
            assert np.isfinite(rgb).all()
            record['image']={'mean_linear_luminance':mean,'bright_fraction':float((luminance>.8).mean()),'intended_blackout':dark}
            bpy.data.images.remove(img)
            checks.append(record.copy())
        records.append(record)
        (out/'timings.json').write_text(json.dumps(records,indent=2))
        print('QUALITY FRAME '+json.dumps(record),flush=True)
report={'passed':True,'profile':changes,'resolution':job['resolution'],'frame_count':len(records),
        'render_seconds':sum(r['seconds'] or 0 for r in records),'representative_checks':checks,
        'continuity_checks':continuity,
        'scope':'Camera binding/framing and pixel exposure sanity; editorial review still required'}
(out/'visual_validation.json').write_text(json.dumps(report,indent=2))
print('QUALITY COMPLETE '+json.dumps(report),flush=True)
