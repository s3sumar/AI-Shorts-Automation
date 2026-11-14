"""Validate and optionally CPU-render the saved MCP elevator sequence.

blender -b artifacts/cinematic_elevator_10s/elevator_suspense_10s.blend \
  --python-exit-code 1 -P tests/validate_cinematic_10s.py -- --render-previews
"""
import bpy
import json
import math
import sys
import time
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

s = bpy.context.scene
out = Path(__file__).resolve().parents[1] / 'artifacts' / 'cinematic_elevator_10s'
checks = []


def check(ok, label):
    if not ok:
        raise AssertionError(label)
    checks.append(label)


check(bpy.app.version[:2] == (5, 2), 'Blender 5.2 runtime')
check((s.frame_start, s.frame_end, s.render.fps, s.render.fps_base) == (1,240,24,1), '240 frames / 24 FPS / 10 seconds')
check(s.camera and s.camera.name == 'Cinematic portrait camera', 'Correct active camera')
check((s.render.resolution_x,s.render.resolution_y)==(540,960), '540 x 960 portrait')
check(s.render.engine=='CYCLES' and s.cycles.device=='CPU', 'CPU Cycles renderer')
opening=s.objects['Floor indicator']
ending=s.objects['Floor changes to negative one']
check(opening.data.body=='13' and ending.data.body=='-1', 'Correct indicator text')
head=s.objects['Head reaction pivot']
left,right=s.objects['Door left'],s.objects['Door right']
light=s.objects['Cold overhead lighting'].data
s.frame_set(1)
start=s.camera.location.copy()
initial=light.energy
check(light.color.b>light.color.r*3, 'Cold blue arrival')
s.frame_set(47)
check(light.energy<initial*.05, 'Fluorescent power failure')
s.frame_set(83)
check(light.color.r>.3 and light.color.b>.3, 'Intermediate color during gradual transition')
s.frame_set(120)
check(light.color.r>light.color.b*20, 'Red alarm lighting')
s.frame_set(144)
check(head.rotation_euler.z>1.8, 'Independent head turn')
check(abs(s.objects['Character rig pivot'].rotation_euler.z)<.001, 'Head turn does not rotate the entire body')
s.frame_set(240)
check(right.location.x-left.location.x>3.7, 'Doors fully open')
check((s.camera.location-start).length>.8, 'Cinematic camera movement')
check(s.objects['Character rig pivot'].location.y<0, 'Passenger recoil')
check(s.objects['Arm'].rotation_euler.x>.1, 'Arm reaction')

# Verify actual geometry occlusion from the camera, rather than visibility flags.
def first_hit(target):
    origin=s.camera.matrix_world.translation
    direction=(Vector(target)-origin).normalized()
    hit,loc,normal,index,obj,matrix=s.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,direction,distance=20)
    return obj.name if hit else None

s.frame_set(1)
check(first_hit((.5,3.45,2.7)) in ['Door left','Door right'], 'Closed doors physically conceal silhouette')
s.frame_set(240)
check(first_hit((.5,3.45,2.7))=='Silhouette hood', 'Open doorway reveals silhouette from active camera')
previous=None
max_step=0
for f in range(1,241):
    s.frame_set(f)
    assert s.camera.name=='Cinematic portrait camera'
    assert opening.hide_render==(f>=104) and opening.hide_viewport==(f>=104), f'Opening visibility {f}'
    assert ending.hide_render==(f<104) and ending.hide_viewport==(f<104), f'Ending visibility {f}'
    for obj in [head,left,right,s.camera]:
        assert all(math.isfinite(v) for row in obj.matrix_world for v in row), (f,obj.name)
    for obj in [opening, s.objects['Rounded helmet head']]:
        projected=world_to_camera_view(s,s.camera,obj.matrix_world.translation)
        assert .015<projected.x<.985 and .015<projected.y<.985 and projected.z>0, (f,obj.name,list(projected))
    pos=s.camera.location.copy()
    if previous is not None:
        max_step=max(max_step,(pos-previous).length)
    previous=pos
check(max_step<.02, 'Continuous camera motion across all 240 frames')
checks.append('All 240 frames: finite transforms, stable camera, indicator visibility, head and indicator in frame')
actions=[a.name for a in bpy.data.actions if a.name.startswith('S10 |')]
check(len(actions)>=12 and all(bpy.data.actions[a].use_fake_user for a in actions), 'Reusable named actions retained')
report={'blender':bpy.app.version_string,'checks':checks,'actions':actions,'max_camera_step':max_step,
        'previews':[], 'limitations':['No complete 240-frame render or audio pass', 'Preview renders use half resolution and 16 samples; final scene uses 24 samples at 540 x 960']}
if '--render-previews' in sys.argv:
    s.render.resolution_percentage=50
    s.cycles.samples=16
    for f in [1,83,144,240]:
        s.frame_set(f)
        path=out/f'preview_{f:04d}.png'
        s.render.filepath=str(path)
        t=time.monotonic()
        bpy.ops.render.render(write_still=True)
        report['previews'].append({'frame':f,'path':str(path),'seconds':round(time.monotonic()-t,3),'bytes':path.stat().st_size})
        (out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
s.frame_set(1)
(out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS: '+json.dumps(report))
