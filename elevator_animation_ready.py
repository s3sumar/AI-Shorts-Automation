"""Original automated mystery scene for Blender 4.x/5.x.
Run from Blender's Scripting workspace or: blender -b -P first_cinematic_scene.py
Creates and saves a Blender scene. Does not automatically render (to avoid a long wait).
"""
import bpy, math, os
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'  # Blender 5.2.3
scene.render.resolution_x = 540
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 96
scene.world.color = (0.025, 0.035, 0.06)

# Materials
def mat(name, color, metallic=0, roughness=0.5, emission=None, power=1):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = power
    return m

steel = mat('Cold brushed steel', (0.19,.23,.29), .65, .34)
dark = mat('Dark floor', (.035,.044,.06), .28, .42)
black = mat('Matte black',(.009,.011,.018),0,.8)
white = mat('Smooth ivory character',(.78,.83,.85),.04,.34)
red = mat('Alarm red',(.23,.01,.025),.15,.4, (.9,.015,.035),2)
lightmat = mat('Cold fluorescent light',(.7,.88,1),0,.3,(.38,.67,1),4)

def cube(name, location, scale, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o=bpy.context.object; o.name=name
    o.dimensions=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel:
        mod=o.modifiers.new('Soft edges', 'BEVEL'); mod.width=bevel; mod.segments=2
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def sphere(name, location, radius, material, scl=(1,1,1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=location)
    o=bpy.context.object; o.name=name; o.scale=scl
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth(); return o

def track(o, target):
    direction=Vector(target)-o.location
    o.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

# Elevator dimensions: x=width, y=depth, z=height. Camera faces rear wall.
cube('Elevator floor', (0,0,-.08), (4.1,4.2,.2),dark)
cube('Rear metallic wall', (0,1.94,2), (4.1,.15,4.2),steel)
cube('Left wall',(-2,0,2),(.14,4.1,4.2),steel)
cube('Right wall',(2,0,2),(.14,4.1,4.2),steel)
cube('Elevator ceiling',(0,0,4.05),(4.1,4.2,.13),dark)
# Closed door on rear wall and glowing seam
cube('Door left',(-.64,1.83,1.75),(1.2,.10,3.4),steel,.025)
cube('Door right',(.64,1.83,1.75),(1.2,.10,3.4),steel,.025)
cube('Door seam',(0,1.75,1.75),(.025,.08,3.4),black)
cube('Door header',(0,1.77,3.55),(2.65,.18,.18),dark)
# Horizontal side rails
for x in [-1.9,1.9]:
    cube('Hand rail', (x,.15,1.15),(.10,2.75,.09),steel,.03)
# Ceiling strips
for x in [-1.28,1.28]:
    cube('Ceiling LED panel',(x,0,3.93),(.20,2.9,.03),lightmat,.02)
# Floor indicator
cube('Indicator housing',(0,1.67,3.73),(1.1,.12,.36),black,.03)

def textobj(name, value, loc, size=.20, material=red, rotation=(math.pi/2,0,0)):
    curve=bpy.data.curves.new(name,'FONT'); curve.body=value; curve.size=size
    curve.align_x='CENTER'; curve.align_y='CENTER'
    o=bpy.data.objects.new(name,curve); bpy.context.collection.objects.link(o)
    o.location=loc; o.rotation_euler=rotation; o.data.materials.append(material)
    return o

indicator=textobj('Floor indicator','13',(0,1.58,3.72),.25,red)

# Character is simple and deliberately original (no copied character design).
# Standing in foreground at x=0. Parent to pivot so animation is coherent.
pivot=bpy.data.objects.new('Character rig pivot',None); bpy.context.collection.objects.link(pivot)
pivot.location=(0,.08,0)
def child(o):
    o.parent=pivot
    o.matrix_parent_inverse=pivot.matrix_world.inverted()

child(sphere('Rounded helmet head',(0,.08,2.15),.47,white,(.94,.79,1.02)))
child(sphere('Rounded torso',(0,.08,1.20),.43,white,(.79,.64,1.15)))
for x in [-.28,.28]:
    child(sphere('Arm', (x*2.05,.04,1.24),.17,white,(.60,.68,2.0)))
    child(sphere('Leg', (x,.08,.50),.18,white,(.80,.8,2.2)))
    child(sphere('Eye',(x*.66,-.31,2.23),.072,black,(1,.52,1.18)))
    brow=cube('Brow',(x*.67,-.31,2.38),(.16,.035,.045),black,.01)
    brow.rotation_euler[1]=(-.14 if x<0 else .14); child(brow)

# Film lighting
def area(name,loc,power,color,size,target):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.color=color; data.shape='RECTANGLE'; data.size=size; data.size_y=size
    ob=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(ob)
    ob.location=loc; track(ob,target); return ob
area('Cold overhead lighting',(-.9,-.6,3.80),430,(.55,.75,1),2.7,(0,0,1.2))
area('Red back rim',(.9,1.0,2.9),260,(1,.10,.16),1.5,(0,0,1.5))
area('Soft face fill',(0,-2.3,2.35),120,(.70,.82,1),1.6,(0,0,2.0))

# Dramatic wide-to-close camera animation
camdata=bpy.data.cameras.new('Cinematic portrait camera')
cam=bpy.data.objects.new('Cinematic portrait camera',camdata); bpy.context.collection.objects.link(cam)
scene.camera=cam
camdata.type='PERSP'; camdata.lens=35
for f,loc,target in [
    (1,(1.15,-3.85,2.35),(0,.15,1.82)),
    (55,(.60,-3.0,2.25),(0,.15,1.92)),
    (96,(.15,-2.5,2.22),(0,.17,2.05)),
]:
    cam.location=loc; track(cam,target)
    cam.keyframe_insert('location',frame=f)
    cam.keyframe_insert('rotation_euler',frame=f)
for fc in cam.animation_data.action.fcurves if hasattr(cam.animation_data.action,'fcurves') else []:
    for kp in fc.keyframe_points: kp.interpolation='BEZIER'

# Subtle unsettling head/pivot rotation, not complex motion capture
for f,angle in [(1,0),(45,0),(75,-.20),(96,-.36)]:
    pivot.rotation_euler[2]=angle; pivot.keyframe_insert('rotation_euler',frame=f)
indicator.data.body='13'; indicator.data.keyframe_insert('body',frame=1) if False else None
# Text isn't keyframeable directly; use visibility swapping
minus=textobj('Floor changes to negative one','-1',(0,1.57,3.72),.25,red)
indicator.hide_render=False
minus.hide_render=True
for o, states in [(indicator,[(1,False),(67,False),(68,True)]),(minus,[(1,True),(67,True),(68,False)])]:
    for f,state in states:
        o.hide_render=state; o.keyframe_insert('hide_render',frame=f)
        o.hide_viewport=state; o.keyframe_insert('hide_viewport',frame=f)

scene.view_settings.view_transform='AgX'
scene.frame_set(1)
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4'
scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='MEDIUM'
output_folder=os.path.join(os.path.expanduser('~'),'Documents','AI_Shorts','Renders')
os.makedirs(output_folder, exist_ok=True)
scene.render.filepath=os.path.join(output_folder,'elevator_test.mp4')
project=os.path.join(os.path.expanduser('~'),'Documents','AI_Shorts','first_scene.blend')
os.makedirs(os.path.dirname(project),exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=project)
print('SUCCESS: Scene created at',project)
print('To test: press Numpad 0 for camera and F12 to render one frame.')
print('Animation ready: Render > Render Animation (Ctrl+F12). MP4 output:',scene.render.filepath)
