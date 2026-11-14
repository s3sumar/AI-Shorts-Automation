"""Read the actual Episode 1 final rig state and compare it to the canon seed."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
memory=json.loads((root/'state/story_memory.json').read_text())
row=next(e for e in memory['episodes'] if e['uid']=='series_001_e001')
expected=json.loads(row['plan'])['end_state']
s=bpy.context.scene
assert s.name.startswith('Episode 001')
s.frame_set(s.frame_end)
measured={
 'passenger_position':list(s.objects['Passenger root'].location),
 'passenger_head':list(s.objects['Passenger head pivot'].rotation_euler),
 'shadow_position':list(s.objects['Shadow root'].location),
 'shadow_head':list(s.objects['Shadow head pivot'].rotation_euler),
 'shadow_leg_l':list(s.objects['Shadow hip L'].rotation_euler),
 'shadow_leg_r':list(s.objects['Shadow hip R'].rotation_euler)}
for key,value in measured.items():
    assert (Vector(value)-Vector(expected[key])).length<.015,(key,value,expected[key])
for side,label in [(-1,'L'),(1,'R')]:
    actual=s.objects['Passenger shoulder '+label].rotation_euler
    assert (Vector(actual)-Vector((-.3,side*.3,0))).length<.015
value=[o.data.body for o in s.objects if 'display_value' in o and not o.hide_render]
assert value==[expected['floor']]
assert abs(s.objects['Door right'].location.x-(.625+1.275*expected['doors']))<.01
assert s.objects['Shadow head'].hide_render!=expected['shadow_visible']
assert (Vector(s.objects['Cold overhead lighting'].data.color)-Vector((1,.018,.027))).length<.01
report={'passed':True,'file':bpy.data.filepath,'frame':s.frame_end,'measured':measured,
        'floor':value[0],'doors':expected['doors'],'lighting':'red','shoulder_pose_matches':True}
(root/'artifacts/autonomy/measured_episode1_boundary.json').write_text(json.dumps(report,indent=2))
print('SEED BOUNDARY PASS: actual original Episode 1 final state matches persistent canon')
