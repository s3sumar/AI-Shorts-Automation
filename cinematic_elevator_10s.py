"""Upgrade the original first_scene.blend in Blender 5.2.x.

Run on the original scene or its backup. Outputs never replace the input file.
No external assets, handlers or simulation caches are required.
"""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts' / 'cinematic_elevator_10s'
OUT.mkdir(parents=True, exist_ok=True)


def curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def animate(owner, path, keys, name, constant=False, linear=False):
    for frame, value in keys:
        setattr(owner, path, value)
        owner.keyframe_insert(data_path=path, frame=frame)
    action = owner.animation_data.action
    action.name = name
    action.use_fake_user = True
    for fc in curves(action):
        if fc.data_path != path:
            continue
        for key in fc.keyframe_points:
            key.interpolation = 'CONSTANT' if constant else 'LINEAR' if linear else 'BEZIER'
            key.handle_left_type = key.handle_right_type = 'AUTO_CLAMPED'
    return action


def material(name, rgb, rough=.5, metal=0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = 2
    return mat


def box(name, loc, size, mat, bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new('Edge highlights', 'BEVEL')
        mod.width, mod.segments = bevel, 2
    return ob


def ellipsoid(name, loc, size, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def build():
    s = bpy.context.scene
    if 'Head reaction pivot' in s.objects:
        raise RuntimeError('Already upgraded: open the original backup before rebuilding.')
    required = ['Rear metallic wall', 'Rounded helmet head', 'Character rig pivot',
                'Floor indicator', 'Floor changes to negative one', 'Cinematic portrait camera']
    assert all(n in s.objects for n in required), 'Open the original first_scene scene first'
    s.frame_set(1)
    for ob in list(s.objects):
        ob.animation_data_clear()
        if ob.data and hasattr(ob.data, 'animation_data_clear'):
            ob.data.animation_data_clear()
    s.frame_start, s.frame_end = 1, 240
    s.render.fps, s.render.fps_base = 24, 1
    # Cycles CPU works on cloud machines with no graphics device.
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = 24
    s.cycles.use_denoising = True
    s.cycles.max_bounces = 4
    s.cycles.diffuse_bounces = 2
    s.cycles.glossy_bounces = 2
    s.cycles.transmission_bounces = 0
    s.cycles.volume_bounces = 0
    s.render.resolution_x, s.render.resolution_y = 540, 960
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.render.filepath = str(OUT / 'frames' / 'frame_')
    s.view_settings.view_transform = 'AgX'
    s.world.use_nodes = True
    bg = next(n for n in s.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (.025, .045, .085, 1)
    bg.inputs['Strength'].default_value = .12
    steel = material('S10 | satin brushed steel', (.19, .24, .30), .36, .65)
    p = next(n for n in steel.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    nt = steel.node_tree
    tex = nt.nodes.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = 95
    tex.inputs['Detail'].default_value = 1
    mapping = nt.nodes.new('ShaderNodeVectorMath')
    mapping.operation = 'MULTIPLY'
    mapping.inputs[1].default_value = (1, 1, .035)
    coord = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(coord.outputs['Generated'], mapping.inputs[0])
    nt.links.new(mapping.outputs[0], tex.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .12
    bump.inputs['Distance'].default_value = .012
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    floor = material('S10 | graphite floor', (.045, .055, .07), .28, .3)
    shadow = material('S10 | light absorbing cloth', (.004, .006, .009), .95)
    trim = material('S10 | dark door trim', (.025, .035, .048), .32, .6)
    for ob in s.objects:
        if ob.type == 'MESH' and ob.data.materials:
            if ob.data.materials[0].name == 'Cold brushed steel':
                ob.data.materials[0] = steel
            elif ob.name in ['Elevator floor', 'Elevator ceiling']:
                ob.data.materials[0] = floor
    skin = bpy.data.materials.get('Smooth ivory character')
    if skin:
        bs = next(n for n in skin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bs.inputs['Roughness'].default_value = .42
    # Open a true aperture; the original rear wall covered both sliding doors.
    wall = s.objects['Rear metallic wall']
    wall.location = (0, 1.94, 3.88)
    wall.dimensions = (4.1, .15, .44)
    for x in [-1.66, 1.66]:
        box('Door pocket wall', (x, 1.70, 1.78), (.78, .18, 3.58), steel)
        box('Vertical frame', (x/abs(x)*1.27, 1.58, 1.78), (.055,.12,3.58), trim)
    seam = s.objects['Door seam']
    seam.hide_render = seam.hide_viewport = True
    for name, sign in [('Door left', -1), ('Door right', 1)]:
        ob = s.objects[name]
        ob.dimensions.x = 1.25
        animate(ob, 'location', [(1,(sign*.625,1.83,1.75)), (154,(sign*.625,1.83,1.75)),
                                (210,(sign*1.90,1.83,1.75)), (240,(sign*1.90,1.83,1.75))], 'S10 | '+name+' slide')
    box('Corridor floor', (0,4,-.08), (4,4.2,.2), floor)
    box('Corridor darkness', (0,6,2), (4,.15,4.2), shadow)
    for x in [-1.8,1.8]:
        box('Corridor wall', (x,4,1.9), (.16,4,4), trim)
    # Stage passenger left, leaving the right side of the opening readable.
    pivot = s.objects['Character rig pivot']
    pivot.rotation_euler = (0,0,0)
    pivot.location.x = -.68
    head = bpy.data.objects.new('Head reaction pivot', None)
    s.collection.objects.link(head)
    head.parent = pivot
    head.location = (0,0,2.15)
    bpy.context.view_layer.update()
    for name in ['Rounded helmet head','Eye','Eye.001','Brow','Brow.001']:
        ob = s.objects[name]
        world = ob.matrix_world.copy()
        ob.parent = head
        ob.matrix_parent_inverse.identity()
        ob.matrix_world = world
    animate(head, 'rotation_euler', [(1,(0,0,0)),(98,(0,0,0)),(116,(-.06,0,-.25)),
            (144,(.03,.07,1.85)),(166,(.03,.07,1.85)),(196,(-.1,.04,2.35)),(240,(-.06,.04,2.28))], 'S10 | head look and recoil')
    animate(pivot, 'location', [(1,(-.68,.08,0)),(174,(-.68,.08,0)),(195,(-.82,-.12,-.035)),
            (216,(-.82,-.12,0)),(240,(-.82,-.12,0))], 'S10 | passenger recoil')
    for name, sign in [('Arm',-1),('Arm.001',1)]:
        ob = s.objects[name]
        animate(ob,'rotation_euler',[(1,(0,0,0)),(178,(0,0,0)),(198,(.25,sign*.3,0)),(240,(.18,sign*.23,0))], 'S10 | '+name+' tension')
    for name, sign in [('Brow',-1),('Brow.001',1)]:
        ob=s.objects[name]
        start=ob.location.copy()
        animate(ob,'location',[(1,start),(102,start),(119,start+Vector((0,0,.065))), (240,start+Vector((0,0,.065)))], 'S10 | '+name+' alarm')
    # Visibility is discrete; shader and power transitions are continuous.
    for name, body, invert in [('Floor indicator','13',False),('Floor changes to negative one','-1',True)]:
        ob=s.objects[name]
        ob.data.body=body
        ob.data.size=.29
        for prop in ['hide_render','hide_viewport']:
            animate(ob,prop,[(1,invert),(103,invert),(104,not invert),(240,not invert)],'S10 | '+name+' switch',constant=True)
    cold=(.24,.52,1)
    red=(1,.018,.028)
    power=[(1,520),(45,520),(47,12),(49,450),(57,450),(59,8),(62,330),
           (72,330),(74,18),(77,390),(88,390),(90,15),(93,430),(120,470),(240,470)]
    light=s.objects['Cold overhead lighting'].data
    animate(light,'energy',power,'S10 | fluorescent power',linear=True)
    animate(light,'color',[(1,cold),(60,cold),(83,(.46,.20,.48)),(112,red),(240,red)],'S10 | fluorescent power')
    fluorescent=bpy.data.materials['Cold fluorescent light']
    fluorescent.node_tree.animation_data_clear()
    bs=next(n for n in fluorescent.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for f,power_value in power:
        bs.inputs['Emission Strength'].default_value=power_value/100
        bs.inputs['Emission Strength'].keyframe_insert(data_path='default_value',frame=f)
    for f,col in [(1,cold),(60,cold),(83,(.46,.20,.48)),(112,red),(240,red)]:
        bs.inputs['Emission Color'].default_value=(*col,1)
        bs.inputs['Emission Color'].keyframe_insert(data_path='default_value',frame=f)
    fluorescent.node_tree.animation_data.action.name='S10 | tube emission flicker and color'
    fluorescent.node_tree.animation_data.action.use_fake_user=True
    fill=s.objects['Soft face fill'].data
    animate(fill,'energy',[(1,85),(60,85),(112,55),(240,55)],'S10 | face fill')
    animate(fill,'color',[(1,cold),(60,cold),(112,(1,.12,.13)),(240,(1,.12,.13))],'S10 | face fill')
    rim=s.objects['Red back rim'].data
    animate(rim,'energy',[(1,0),(70,0),(112,180),(240,180)],'S10 | alarm rim')
    # Tall faceless hooded presence, physically occluded by the closed doors.
    figure=[]
    figure.append(ellipsoid('Silhouette hood',(.50,3.45,2.70),(.33,.24,.44),shadow))
    figure.append(ellipsoid('Silhouette coat',(.50,3.48,1.62),(.46,.27,.83),shadow))
    for x in [.17,.83]:
        figure.append(ellipsoid('Silhouette sleeve',(x,3.43,1.58),(.14,.16,.65),shadow))
    for x in [.32,.68]:
        figure.append(ellipsoid('Silhouette leg',(x,3.48,.52),(.15,.17,.51),shadow))
    glow=material('S10 | corridor cold rim',(.10,.25,.35),emission=(.16,.50,.7))
    box('Corridor luminous recess',(0,5.85,2.1),(2.9,.03,3.7),glow,0)
    data=bpy.data.lights.new('Silhouette separation','AREA')
    ob=bpy.data.objects.new('Silhouette separation',data)
    s.collection.objects.link(ob)
    ob.location=(.5,5.4,3.3)
    data.energy=180
    data.color=(.15,.5,.7)
    data.shape='DISK'
    data.size=2
    aim(ob,(.5,3.4,1.7))
    # Smooth dolly with a slight lateral move, keeping the display in frame.
    camera=s.objects['Cinematic portrait camera']
    s.camera=camera
    camera.data.lens=32
    camera.data.clip_start=.05
    camera.data.clip_end=100
    positions=[(1,(1,-5.5,2.65)),(104,(.85,-5.15,2.58)),(156,(.7,-4.95,2.52)),(240,(.45,-4.65,2.48))]
    rotations=[]
    for f,loc in positions:
        camera.location=loc
        aim(camera,(-.05,.95,2.02))
        rotations.append((f,tuple(camera.rotation_euler)))
    animate(camera,'location',positions,'S10 | cinematic dolly')
    animate(camera,'rotation_euler',rotations,'S10 | cinematic dolly')
    camera.data.dof.use_dof=False  # Keep both display and distant figure legible at low samples.
    for marker in list(s.timeline_markers):
        s.timeline_markers.remove(marker)
    for f,label in [(1,'01 BLUE ARRIVAL'),(47,'02 POWER FAILURE'),(104,'03 FLOOR -1'),(116,'04 HEAD TURN'),(155,'05 DOORS OPEN'),(210,'06 THE PRESENCE')]:
        s.timeline_markers.new(label,frame=f)
    s['sequence']='Elevator / Floor -1 / 10 seconds'
    s['render_notes']='CPU Cycles, 24 samples + denoising; no volumes, textures or simulation dependencies'
    s.frame_set(1)
    return s


if __name__=='__main__':
    path=OUT/'elevator_suspense_10s.blend'
    if path.exists():
        raise FileExistsError('Choose a new output filename; refusing to overwrite '+str(path))
    scene=build()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print(json.dumps({'saved':str(path),'frames':240,'fps':24,'camera':scene.camera.name}))
