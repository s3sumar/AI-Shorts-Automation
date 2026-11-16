"""Opt-in stylized hand contacts, facial acting and motivated story gestures."""
import math
import bpy
from mathutils import Vector,Matrix
from .common import sphere,box,text,empty,material,unlit,animate,frame,visibility


def capsule(name,a,b,radius,mat,parent):
    a,b=Vector(a),Vector(b)
    o=sphere(name,(a+b)/2,(radius,radius,(b-a).length/2+radius),mat,parent)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o


def apply_story_performance(s,c,r,brows):
    skin=bpy.data.materials['Passenger | porcelain']
    ink=bpy.data.materials['Passenger | obsidian eyes']
    head=r['passenger.head']
    # Surface-following brows replace the earlier linear approximation.
    for brow in brows:
        brow.animation_data_clear()
        x=brow.location.x
        values=[]
        for t,lift in [[0,0],[8.8,.005],[9.3,.025],[14,.015],[20,.035],[26.2,.06],[34,.055],[38,.065],[45,.065]]:
            z=.32+lift
            y=-.372*math.sqrt(max(.01,1-(x/.443)**2-((z-.10)/.48)**2))-.014
            values.append((frame(t),(x,y,z)))
        animate(brow,'location',values,'EP01 | surface attached brow '+brow.name)
    eye_white=material('Passenger | muted eye whites',(.62,.65,.63),.55)
    blink_times=[3.7,9.0,18.4,26.65,35.7,40.2]
    for side,label in [(-1,'L'),(1,'R')]:
        eye=s.objects['Passenger eye '+label]
        eye.data.materials[0]=eye_white
        pupil=sphere('Passenger pupil '+label,(side*.16,-.376,.17),(.032,.012,.045),ink,head)
        for obj,opened in [(eye,tuple(eye.scale)),(pupil,tuple(pupil.scale))]:
            keys=[(1,opened)]
            for t in blink_times:
                keys.extend([(frame(t-.08),opened),(frame(t),(opened[0],opened[1],opened[2]*.09)),(frame(t+.12),opened)])
            keys.append((frame(45),opened))
            animate(obj,'scale',keys,'EP01 | blink '+obj.name)
        animate(pupil,'location',[(frame(t),(side*.16+dx,-.376,.17+dz)) for t,dx,dz in
            [[0,0,0],[4.6,.012,.012],[9.3,.018,0],[14,0,-.012],[20.8,-.018,-.008],[29,.018,0],[34,0,.006],[45,0,.006]]],
            'EP01 | eyeline '+label)
    mouth=sphere('Passenger mouth',(0,-.336,-.10),(.07,.013,.011),ink,head)
    # Authored closed / open shapes follow the measured speech envelope. This is
    # deliberately a simple jaw shape, not a claim of full phonetic lip sync.
    samples=c['directing'].get('mouth_envelope',[])
    animate(mouth,'scale',[(frame(t),(.07+.018*v,.013,.011+.045*v)) for t,v in samples] or [(1,(.07,.013,.011))],
            'EP01 | measured courier mouth shapes','LINEAR')

    arm=r['passenger.arm.R']
    bpy.data.objects.remove(s.objects['Passenger hand R'],do_unlink=True)
    capsule('Courier wrist contact',(.15,-.03,-.65),(.32,-.12,-.72),.055,skin,arm)
    sphere('Courier gripping palm',(.33,-.16,-.75),(.052,.095,.105),skin,arm)
    for i,z in enumerate([-.69,-.75,-.81]):
        pivot=empty(s,'Courier grip finger '+str(i),(.32,-.255,z),arm)
        capsule('Courier finger proximal '+str(i),(0,0,0),(-.055,-.06,0),.022,skin,pivot)
        capsule('Courier finger distal '+str(i),(-.055,-.06,0),(-.10,-.065,0),.021,skin,pivot)
        animate(pivot,'rotation_euler',[(frame(t),(0,0,v)) for t,v in [[0,0],[14.3,0],[15,-.12],[17.5,-.12],[20,0],[34,0],[36,-.16],[45,-.16]]],
                'EP01 | parcel grip finger '+str(i))
    capsule('Courier bracing thumb',(.32,-.12,-.67),(.22,-.18,-.61),.035,skin,arm)
    capsule('Courier thumb tip',(.22,-.18,-.61),(.15,-.245,-.615),.027,skin,arm)
    # Keep the readable label clear of the new fingers.
    stamp=s.objects['Courier parcel stamp'];stamp.location.x=.10;stamp.data.size=.028
    s.objects['Courier parcel label'].location.x=.11
    s.objects['Courier parcel label'].dimensions.x=.19
    paper=bpy.data.materials['Courier | label paper']
    box('Courier destination label',(.115,-.305,-.83),(.19,.004,.045),paper,arm,0)
    dest=text(s,'Courier destination','LOBBY',(.115,-.308,-.83),.021,ink,arm);dest.rotation_euler.x=math.pi/2

    # A reachable wall control, not the distant front-wall buttons.
    trim=material('Stop control | dark plate',(.025,.035,.04),.5,.2)
    red=material('Stop control | red',(.5,.015,.008),.4,0,.4)
    box('Emergency stop plate',(-1.88,.4,1.52),(.08,.35,.42),trim)
    button=box('Emergency stop button',(-1.82,.4,1.52),(.06,.12,.12),red)
    caption=text(s,'Emergency stop label','STOP',(-1.829,.4,1.68),.065,unlit('Stop lettering',(.8,.8,.75)))
    caption.rotation_euler=(math.pi/2,0,math.pi/2)
    animate(button,'location',[(frame(t),(x,.4,1.52)) for t,x in [[0,-1.82],[20.8,-1.82],[20.9,-1.84],[21.15,-1.84],[21.4,-1.82],[45,-1.82]]],
            'EP01 | stop button press')

    left=r['passenger.arm.L']
    bpy.data.objects.remove(s.objects['Passenger hand L'],do_unlink=True)
    wrist=empty(s,'Courier left wrist',(-.16,-.03,-.72),left)
    sphere('Courier left palm',(0,0,0),(.09,.045,.09),skin,wrist)
    for i,x in enumerate([-.06,0,.06]):
        capsule('Courier left finger '+str(i),(x,0,-.055),(x,0,-.14),.022,skin,wrist)
    capsule('Courier left thumb',(.065,0,.025),(.115,-.015,-.035),.027,skin,wrist)
    # Compute the shoulder rotations in its parent's coordinates; moving the
    # parent torso cannot detach the palm or make it jump between world poses.
    keys=list(c['motion']['passenger.arm.L.rotation_euler'])
    keys=[(t,v) for t,v in keys if not 19.8<=t<=22.5 and not 37<=t<43]
    keys.extend([(19.8,[0,0,0]),(22.5,[0,0,0])])
    for t,point in [(20.8,(-1.78,.4,1.52)),(20.95,(-1.80,.4,1.52)),(21.15,(-1.80,.4,1.52)),(21.4,(-1.78,.4,1.52)),
                    (38,(-.55,-.05,1.75)),(40.5,(-.55,-.05,1.75)),(42.8,(-.55,-.05,1.75))]:
        s.frame_set(frame(t));bpy.context.view_layer.update()
        origin=left.location.copy()
        target=left.parent.matrix_world.inverted()@Vector(point)-origin
        rest=Vector((-.16,-.03,-.86)) if t<22 else Vector((-.16,-.03,-.72))
        rot=rest.rotation_difference(target).to_euler()
        keys.append((t,tuple(rot)))
    left.animation_data_clear()
    animate(left,'rotation_euler',[(frame(t),v) for t,v in sorted(keys)],'EP01 | stop attempt and refusal palm')
    # Place the fingertip's rounded surface on the animated button face. A small
    # wrist correction avoids driving the rigid finger through the plate.
    wrist_locations=[(1,(-.16,-.03,-.72)),(frame(19.8),(-.16,-.03,-.72))]
    for t,x in [(20.8,-1.77),(20.95,-1.79),(21.15,-1.79),(21.4,-1.77)]:
        s.frame_set(frame(t));bpy.context.view_layer.update()
        tip=left.matrix_world.inverted()@Vector((x,.4,1.52))
        wrist_locations.append((frame(t),tuple(tip-Vector((0,0,-.14)))))
    wrist_locations.extend([(frame(22.5),(-.16,-.03,-.72)),(frame(45),(-.16,-.03,-.72))])
    animate(wrist,'location',wrist_locations,'EP01 | fingertip button contact')
    # At refusal the finger direction reverses upward, making an open palm rather
    # than a dangling mitten. Wrist correction is separate from shoulder reach.
    wrist_keys=[(1,(0,0,0)),(frame(36),(0,0,0))]
    for t in [38,40.5,42.8]:
        s.frame_set(frame(t));bpy.context.view_layer.update()
        normal=(s.objects['Shadow root'].matrix_world.translation-wrist.matrix_world.translation)
        normal.z=0;normal.normalize()
        zaxis=Vector((0,0,-1));yaxis=-normal;xaxis=yaxis.cross(zaxis).normalized()
        world=Matrix((xaxis,yaxis,zaxis)).transposed().to_quaternion()
        local=left.matrix_world.to_quaternion().inverted()@world
        wrist_keys.append((frame(t),tuple(local.to_euler())))
    wrist_keys.append((frame(45),(0,0,0)))
    animate(wrist,'rotation_euler',wrist_keys,'EP01 | refusal wrist')

    # The sealed-floor evidence is part of the set, not a narrator-only fact.
    plaque=box('Sealed floor plaque',(0,1.55,3.41),(.73,.025,.14),trim)
    lettering=text(s,'Sealed floor lettering','SERVICE -1 / SEALED',(0,1.53,3.41),.063,paper)
    lettering.rotation_euler.x=math.pi/2
    for obj in [plaque,lettering]:
        visibility(obj,frame(24),frame(43),s.frame_end)

    shadow=s.objects['Shadow shoulder R']
    animate(shadow,'rotation_euler',[(frame(t),(x,y,z)) for t,x,y,z in
        [[0,0,0,0],[39,0,0,0],[40.5,-1.45,0,-.30],[42.8,-1.45,0,-.30],[45,-1.45,0,-.30]]],
        'EP01 | dispatcher points to courier')
    # An extended finger clarifies who is wanted; no face is added to the figure.
    glove=material('Dispatcher | worn glove',(.09,.13,.15),.85)
    s.objects['Shadow hand R'].data.materials[0]=glove
    capsule('Shadow pointing finger',(.07,-.02,-1.08),(.07,-.02,-1.26),.033,glove,shadow)
