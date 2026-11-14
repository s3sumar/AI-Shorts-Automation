"""Connected, transform-driven recurring characters; no simulation dependency."""
import bpy
from .common import empty,sphere,box,material


def passenger(s,color):
    skin=material('Passenger | porcelain',color,.43,.04)
    joints=material('Passenger | flexible joints',(.12,.17,.21),.65)
    eyes=material('Passenger | obsidian eyes',(.008,.012,.019),.32)
    root=empty(s,'Passenger root',(-.68,0,0))
    breath=empty(s,'Passenger breathing',(0,0,0),root)
    sphere('Passenger torso',(0,0,1.22),(.35,.28,.53),skin,breath)
    sphere('Passenger pelvis',(0,0,.82),(.29,.24,.20),skin,root)
    sphere('Passenger neck',(0,0,1.77),(.14,.14,.19),joints,breath)
    head=empty(s,'Passenger head pivot',(0,0,2.08),breath)
    sphere('Passenger head',(0,0,.10),(.443,.372,.48),skin,head)
    brows=[]
    limbs={}
    for side,label in [(-1,'L'),(1,'R')]:
        sphere('Passenger eye '+label,(side*.16,-.366,.17),(.066,.045,.082),eyes,head)
        brow=box('Passenger brow '+label,(side*.16,-.357,.32),(.16,.045,.035),eyes,head,.008)
        brow.rotation_euler.y=side*.14
        brows.append(brow)
        arm=empty(s,'Passenger shoulder '+label,(side*.34,0,1.55),breath)
        sphere('Passenger shoulder joint '+label,(0,0,0),(.14,.14,.14),skin,arm)
        sphere('Passenger upper arm '+label,(side*.08,0,-.20),(.12,.125,.25),skin,arm)
        sphere('Passenger elbow '+label,(side*.13,0,-.39),(.105,.105,.11),joints,arm)
        sphere('Passenger forearm '+label,(side*.15,-.01,-.54),(.105,.11,.20),skin,arm)
        sphere('Passenger hand '+label,(side*.16,-.03,-.72),(.11,.11,.13),skin,arm)
        leg=empty(s,'Passenger hip '+label,(side*.19,0,.82),root)
        sphere('Passenger thigh '+label,(0,0,-.18),(.145,.15,.25),skin,leg)
        sphere('Passenger knee '+label,(0,0,-.39),(.12,.12,.12),joints,leg)
        sphere('Passenger shin '+label,(0,0,-.54),(.12,.13,.20),skin,leg)
        sphere('Passenger shoe '+label,(0,-.065,-.70),(.15,.23,.10),joints,leg)
        limbs['passenger.arm.'+label]=arm
        limbs['passenger.leg.'+label]=leg
    sphere('Passenger nose',(0,-.397,.04),(.045,.065,.05),skin,head)
    return dict({'passenger.root':root,'passenger.breath':breath,'passenger.head':head},**limbs),brows


def antagonist(s):
    dark=material('The Listener | matte cloth',(.002,.003,.005),1,0)
    p=next(n for n in dark.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Specular IOR Level'].default_value=.05
    root=empty(s,'Shadow root',(.5,5.4,0))
    body=empty(s,'Shadow body pivot',(0,0,0),root)
    # A tapered coat joins shoulders to the legs, with no floating body parts.
    bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.30,radius2=.44,depth=1.55,location=(0,0,1.65))
    coat=bpy.context.object
    coat.name='Shadow coat'
    coat.parent=body
    coat.data.materials.append(dark)
    for p in coat.data.polygons:
        p.use_smooth=True
    sphere('Shadow shoulders',(0,0,2.33),(.5,.26,.2),dark,body)
    head=empty(s,'Shadow head pivot',(0,0,2.55),body)
    sphere('Shadow head',(0,0,.19),(.29,.26,.40),dark,head)
    # Reserved attachment: future facial meshes/effects can be parented here.
    socket=empty(s,'Shadow facial effects socket',(0,-.26,.20),head)
    socket['purpose']='Reserved for later episodes; no facial features in episode 1'
    rigs={'shadow.root':root,'shadow.body':body,'shadow.head':head}
    for side,label in [(-1,'L'),(1,'R')]:
        shoulder=empty(s,'Shadow shoulder '+label,(side*.40,0,2.27),body)
        sphere('Shadow sleeve '+label,(side*.06,0,-.47),(.13,.16,.57),dark,shoulder)
        sphere('Shadow hand '+label,(side*.07,-.02,-1),(.10,.11,.16),dark,shoulder)
        hip=empty(s,'Shadow hip '+label,(side*.17,0,1.04),root)
        sphere('Shadow leg '+label,(0,0,-.45),(.14,.16,.52),dark,hip)
        sphere('Shadow foot '+label,(0,-.09,-.91),(.15,.25,.12),dark,hip)
        rigs['shadow.leg.'+label]=hip
    return rigs
