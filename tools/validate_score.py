"""Validate any compiled production score in Blender, including canon endpoints."""
import bpy
import json
import math
import os
import hashlib
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

s=bpy.context.scene
c=json.loads(s['episode_config'])
root=Path(__file__).resolve().parents[1]
out=Path(os.environ.get('EPISODE_OUTPUT',str(root/'artifacts'/f'episode_{c["episode"]:03d}')))
if not out.is_absolute():
    out=root/out
out.mkdir(parents=True,exist_ok=True)
checks=[]


def require(ok,message):
    if not ok:
        raise AssertionError(message)
    checks.append(message)


def frame(t):
    return round(t*c['fps'])+1


def near(a,b):
    return (Vector(a)-Vector(b)).length<.015


require(bpy.app.version[:3]==(5,2,3),'Blender 5.2.3 runtime')
require((s.frame_start,s.frame_end,s.render.fps)==(1,round(c['duration']*24),24),'Master timing')
require(s.render.resolution_x*16==s.render.resolution_y*9,'Vertical 9:16 master')
require(len([m for m in s.timeline_markers if m.camera])==len(c['shots']),'Complete shot bindings')
require(s.sequence_editor is not None and len(s.sequence_editor.strips)==1,'Sound strip present')
require(any(sound.packed_file for sound in bpy.data.sounds),'Sound packed in master')
events=[(frame(t),v) for t,v in c['floor_events']]
last_camera,last_position=None,None
max_step=0
for f in range(1,s.frame_end+1):
    s.frame_set(f)
    t=(f-1)/24
    shot=next(sh for sh in c['shots'] if sh['start']<=t<sh['end'])
    assert s.camera and s.camera.name=='Shot | '+shot['id'],(f,'shot camera')
    value=next(v for start,v in reversed(events) if start<=f)
    visible=[o['display_value'] for o in s.objects if 'display_value' in o and not o.hide_render]
    assert visible==([value] if value else []),(f,'floor visibility',visible,value)
    for name in ['Passenger root','Passenger head pivot','Shadow root','Shadow head pivot','Door left','Door right',s.camera.name]:
        assert all(math.isfinite(x) for row in s.objects[name].matrix_world for x in row),(f,name)
    if shot.get('subject'):
        target=Vector((0,1.58,3.72)) if shot['subject'].startswith('Display') else s.objects[shot['subject']].matrix_world.translation
        p=world_to_camera_view(s,s.camera,target)
        assert .035<p.x<.965 and .035<p.y<.965 and p.z>0,(f,shot['id'],'subject outside frame',list(p))
    if last_camera==s.camera:
        max_step=max(max_step,(s.camera.location-last_position).length)
    last_camera,last_position=s.camera,s.camera.location.copy()
require(max_step<.15,'No within-shot camera jumps')
checks.append(f'All {s.frame_end} frames: camera, floor display, framing, finite transforms')
for sh in c['shots']:
    if not sh.get('subject'):
        continue
    for t in [sh['start']+.1,(sh['start']+sh['end'])/2,sh['end']-.1]:
        s.frame_set(frame(t))
        if sh['subject'].startswith('Display'):
            obj=next((o for o in s.objects if 'display_value' in o and not o.hide_render),None)
        else:
            obj=s.objects[sh['subject']]
        if obj is None:
            continue
        direction=obj.matrix_world.translation-s.camera.matrix_world.translation
        hit=s.ray_cast(bpy.context.evaluated_depsgraph_get(),s.camera.matrix_world.translation,direction.normalized(),distance=direction.length+.5)
        name=hit[4].name if hit[0] else None
        allowed={obj.name}
        if obj.type=='FONT':
            allowed.add('Indicator housing')
        if obj.name=='Passenger head':
            allowed.update(['Passenger eye L','Passenger eye R','Passenger nose','Passenger brow L','Passenger brow R'])
        assert name in allowed,(sh['id'],t,obj.name,'occluded by',name)
checks.append('Representative shot rays: no unintended primary-subject occlusion')
for obj in [o for o in s.objects if o.get('safe_caption')]:
    s.frame_set((obj['caption_start']+obj['caption_end'])//2)
    assert s.camera==obj.parent
    for corner in obj.bound_box:
        p=world_to_camera_view(s,s.camera,obj.matrix_world@Vector(corner))
        assert .06<=p.x<=.90 and .12<=p.y<=.89,(obj.name,'caption safe bounds',list(p))
checks.append('Captions inside viewing-safe bounds')
if 'production' in c:
    for f,key in [(1,'start_state'),(s.frame_end,'end_state')]:
        s.frame_set(f)
        state=c['production'][key]
        for name,path,expected in [
            ('Passenger root','location',state['passenger_position']),
            ('Passenger head pivot','rotation_euler',state['passenger_head']),
            ('Shadow root','location',state['shadow_position']),
            ('Shadow head pivot','rotation_euler',state['shadow_head']),
            ('Shadow hip L','rotation_euler',state['shadow_leg_l']),
            ('Shadow hip R','rotation_euler',state['shadow_leg_r'])]:
            require(near(getattr(s.objects[name],path),expected),key+': '+name)
        require(abs(s.objects['Door right'].location.x-(.625+1.275*state['doors']))<.01,key+': door aperture')
        require(s.objects['Shadow head'].hide_render != state['shadow_visible'],key+': antagonist visibility')
    checks.append('Story continuity endpoints match rendered rig and doors')
actions=[a for a in bpy.data.actions if a.name.startswith(f'EP{c["episode"]:02d} |')]
require(len(actions)>25 and all(a.use_fake_user for a in actions),'Reusable actions retained')
s.frame_set(s.frame_end)
require(s.camera.name=='Shot | black','Final cut to black')
report={'passed':True,'runtime':bpy.app.version_string,'master_frames':s.frame_end,'checks':checks,
        'actions':len(actions),'max_camera_step':max_step,'production':c.get('production',{}),
        'score_hash':hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(out/'scene_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
s.frame_set(1)
print('SCORE PASS '+json.dumps({'frames':s.frame_end,'checks':len(checks),'actions':len(actions)}))
