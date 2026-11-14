"""Functional scene checks on all 1080 master frames; no render required."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

s=bpy.context.scene
c=json.loads(s['episode_config'])
out=Path(__file__).resolve().parents[1]/'artifacts'/f'episode_{c["episode"]:03d}'
checks=[]


def check(ok,message):
    if not ok:
        raise AssertionError(message)
    checks.append(message)


def f(t):
    return round(t*c['fps'])+1


def hit_subject(obj):
    origin=s.camera.matrix_world.translation
    target=obj.matrix_world.translation
    delta=target-origin
    result=s.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,delta.normalized(),distance=delta.length+.5)
    return result[4].name if result[0] else None


check(bpy.app.version[:3]==(5,2,3),'Blender 5.2.3 runtime')
check((s.frame_start,s.frame_end,s.render.fps)==(1,1080,24),'45-second 24 FPS master')
check(s.render.resolution_x*16==s.render.resolution_y*9,'Vertical 9:16 output')
check(len([m for m in s.timeline_markers if m.camera])==len(c['shots']),'All shot cameras bound to timeline markers')
check(s.objects.get('Shadow facial effects socket') is not None,'Future facial-effects attachment exists')
check(all(o.data.body not in ['HELP'] for o in s.objects if o.type=='FONT'),'Episode 1 display contains no legacy HELP text')
check(s.sequence_editor and len(s.sequence_editor.strips)==1,'Sound mix linked to saved master')
actions=[a for a in bpy.data.actions if a.name.startswith('EP01 |')]
check(len(actions)>30 and all(a.use_fake_user for a in actions),'Named reusable animation actions retained')
events=[(f(t),v) for t,v in c['floor_events']]
projection_failures=[]
occlusion_failures=[]
max_step=0
previous=None
previous_camera=None
for frame in range(1,s.frame_end+1):
    s.frame_set(frame)
    t=(frame-1)/c['fps']
    shot=next(sh for sh in c['shots'] if sh['start']<=t<sh['end'])
    assert s.camera and s.camera.name=='Shot | '+shot['id'], (frame,'camera binding')
    display=next(v for start,v in reversed(events) if start<=frame)
    visible=[o['display_value'] for o in s.objects if 'display_value' in o and not o.hide_render]
    assert visible==([display] if display else []), (frame,'display',visible,display)
    for name in ['Passenger head pivot','Passenger root','Shadow root','Shadow head pivot','Door left','Door right',s.camera.name]:
        assert all(math.isfinite(v) for row in s.objects[name].matrix_world for v in row), (frame,name,'nonfinite transform')
    if shot.get('subject'):
        name=shot['subject']
        if name.startswith('Display'):
            target=Vector((0,1.58,3.72))
        else:
            target=s.objects[name].matrix_world.translation
        p=world_to_camera_view(s,s.camera,target)
        if not (.04<p.x<.96 and .04<p.y<.96 and p.z>.04):
            projection_failures.append((frame,name,list(p)))
    cam_pos=s.camera.location.copy()
    if previous is not None and previous_camera==s.camera:
        max_step=max(max_step,(cam_pos-previous).length)
    previous,previous_camera=cam_pos,s.camera
check(not projection_failures,'All 1080 frames: primary subjects remain inside camera safe bounds: '+str(projection_failures[:3]))
check(max_step<.15,'No accidental within-shot camera jumps')
checks.append('All 1080 frames: exact countdown visibility, finite transforms and correct active shot camera')
for sh in c['shots']:
    if sh['id']=='black':
        continue
    for t in [sh['start']+.1,(sh['start']+sh['end'])/2,sh['end']-.1]:
        s.frame_set(f(t))
        if sh['subject'].startswith('Display'):
            target=next((o for o in s.objects if 'display_value' in o and not o.hide_render),None)
        else:
            target=s.objects[sh['subject']]
        if target is not None:
            hit=hit_subject(target)
            # Font centers can fall between glyph strokes; the backing is expected.
            # Eyes/nose are part of the passenger's face, not an occluding obstacle.
            allowed={target.name}
            if target.type=='FONT':
                allowed.add('Indicator housing')
            if target.name=='Passenger head':
                allowed.update(['Passenger eye L','Passenger eye R','Passenger nose','Passenger brow L','Passenger brow R'])
            if hit not in allowed:
                occlusion_failures.append((sh['id'],round(t,2),target.name,hit))
        if sh['id'] in ['presence','approach']:
            head=s.objects['Shadow head']
            for corner in head.bound_box:
                p=world_to_camera_view(s,s.camera,head.matrix_world@Vector(corner))
                assert .03<p.x<.97 and .03<p.y<.97,(sh['id'],t,'cropped antagonist head',list(p))
check(not occlusion_failures,'Shot subject ray tests, including corridor reveal: '+str(occlusion_failures))
for o in [o for o in s.objects if o.get('safe_caption')]:
    s.frame_set((o['caption_start']+o['caption_end'])//2)
    assert s.camera==o.parent
    for corner in o.bound_box:
        p=world_to_camera_view(s,s.camera,o.matrix_world@Vector(corner))
        assert .06<=p.x<=.90 and .12<=p.y<=.89,(o.name,'caption outside safe area',list(p))
checks.append('All caption bounds inside Shorts-safe area')
s.frame_set(1)
check(s.objects['Cold overhead lighting'].data.color.b>s.objects['Cold overhead lighting'].data.color.r*2,'Cold arrival lighting')
s.frame_set(f(26.25))
check(s.objects['Cold overhead lighting'].data.energy<1,'True overhead blackout after impact')
s.frame_set(f(28))
check(s.objects['Cold overhead lighting'].data.color.r>.9,'Emergency red lighting')
s.frame_set(f(29))
check(abs(s.objects['Door left'].location.x+.625)<.01,'Doors closed before reveal')
s.frame_set(f(37))
check(s.objects['Door right'].location.x-s.objects['Door left'].location.x>3.7,'Doors fully open for reveal')
check(s.objects['Passenger root'].location.y<-.4,'Passenger steps backward in fear')
s.frame_set(f(39))
start=s.objects['Shadow root'].location.copy()
s.frame_set(f(42))
check((s.objects['Shadow root'].location-start).length>.5,'Antagonist takes a forward step')
check(abs(s.objects['Shadow hip L'].rotation_euler.x)>.05,'Antagonist leg articulated during step')
check(s.objects['Passenger shoulder L'].children[0].parent==s.objects['Passenger shoulder L'],'Connected shoulder hierarchy')
s.frame_set(f(44))
check(s.camera.name=='Shot | black','Final cut to black')
report={'passed':True,'runtime':bpy.app.version_string,'master_frames':1080,'checks':checks,'actions':len(actions),
 'max_within_shot_camera_step':max_step,'projection_failures':projection_failures,'occlusion_failures':occlusion_failures}
(out/'scene_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
s.frame_set(1)
print('PASS '+json.dumps(report))
