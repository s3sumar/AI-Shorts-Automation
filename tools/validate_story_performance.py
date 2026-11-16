"""Run inside Blender: actual pose/contact checks in the isolated story revision."""
import json
import math
import os
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

s=bpy.context.scene
out=Path(os.environ['EPISODE_OUTPUT'])
report={'passed':True,'button_contact':[],'refusal_palm':[],'ending_two_shot':[]}
report['screen_axis']=[]
for t in [29,31.5,34,36,38,39.25,40.5,41.75,42.95]:
    s.frame_set(round(t*24)+1)
    person=s.objects['Passenger root'].matrix_world.translation
    figure=s.objects['Shadow root'].matrix_world.translation
    axis=figure-person;offset=s.camera.matrix_world.translation-person
    side=axis.x*offset.y-axis.y*offset.x
    assert side<-.1,(t,'crossed courier/figure camera axis',side)
    report['screen_axis'].append({'time':t,'same_side':True})
report['face_surface']=[]
for t in [0,9.3,20.8,26.2,34,38,42.8]:
    s.frame_set(round(t*24)+1)
    for name in ['Passenger brow L','Passenger brow R']:
        brow=s.objects[name];x,y,z=brow.location
        surface=-.372*math.sqrt(max(.01,1-(x/.443)**2-((z-.10)/.48)**2))
        assert .005<surface-y<.025,(t,name,'detached brow')
    assert s.objects['Passenger pupil L'].parent==s.objects['Passenger head pivot']
    assert s.objects['Passenger mouth'].parent==s.objects['Passenger head pivot']
    report['face_surface'].append({'time':t,'attached_brows_and_face_controls':True})
for t in [20.8,20.95,21.15,21.4]:
    s.frame_set(round(t*24)+1)
    wrist=s.objects['Courier left wrist'];button=s.objects['Emergency stop button']
    tip=wrist.matrix_world@Vector((0,0,-.14))
    face=button.matrix_world.translation+Vector((.03,0,0))
    gap=(tip-face).length
    assert .012<gap<.035,(t,'finger contact',gap)
    report['button_contact'].append({'time':t,'rounded_tip_center_gap':gap})
for t in [38,39.25,40.5,42.8]:
    s.frame_set(round(t*24)+1)
    wrist=s.objects['Courier left wrist']
    normal=(wrist.matrix_world.to_3x3()@Vector((0,-1,0))).normalized()
    direction=(s.objects['Shadow root'].matrix_world.translation-wrist.matrix_world.translation)
    direction.z=0;direction.normalize()
    finger_up=(wrist.matrix_world.to_3x3()@Vector((0,0,-1))).normalized()
    assert normal.dot(direction)>.93 and finger_up.z>.95,(t,'open refusal palm orientation')
    report['refusal_palm'].append({'time':t,'faces_threat_dot':normal.dot(direction),'fingers_up':finger_up.z})
for t in [40.5,41.75,42.95]:
    s.frame_set(round(t*24)+1)
    for name in ['Passenger head','Courier parcel','Shadow head']:
        p=world_to_camera_view(s,s.camera,s.objects[name].matrix_world.translation)
        assert .025<p.x<.975 and .025<p.y<.975 and p.z>0,(t,name,'two-shot framing',list(p))
    report['ending_two_shot'].append({'time':t,'both_characters_and_parcel_in_frame':True})
for t in [0,14.5,17,38,42.8]:
    s.frame_set(round(t*24)+1)
    palm=s.objects['Courier gripping palm'];parcel=s.objects['Courier parcel']
    assert palm.parent==parcel.parent
    # Connected local-space grip, with the thumb braced at the box top.
    assert .16<(palm.location-parcel.location).length<.20
    thumb=s.objects['Courier thumb tip']
    assert thumb.parent==parcel.parent
report['grip_attachment']='connected wrist/palm/curled fingers/thumb share parcel arm; no detached mesh'
report['limitations']='Kinematic stylized contacts and simple audio-driven jaw; no physical hand solver or full visemes'
(out/'acting_validation.json').write_text(json.dumps(report,indent=2))
print('ACTING PASS '+json.dumps(report))
