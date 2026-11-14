import bpy
import math
from mathutils import Vector


def frame(seconds, fps=24):
    return round(seconds * fps) + 1


def curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def animate(owner, path, keys, name, interpolation='BEZIER'):
    for f, value in keys:
        setattr(owner, path, value)
        owner.keyframe_insert(data_path=path, frame=f)
    action = owner.animation_data.action
    action.name = name
    action.use_fake_user = True
    for fc in curves(action):
        if fc.data_path == path:
            for k in fc.keyframe_points:
                k.interpolation = interpolation
                k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
    return action


def visibility(obj, start, end, last):
    for prop in ('hide_render','hide_viewport'):
        keys = [(1, True)]
        if start == 1:
            keys = [(1, False)]
        else:
            keys.append((start,False))
        keys.extend([(end,True),(last+1,True)])
        animate(obj,prop,keys,'EP01 | '+obj.name+' visibility','CONSTANT')


def material(name, color, rough=.5, metal=0, emission=0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    p.inputs['Emission Color'].default_value=(*color,1)
    p.inputs['Emission Strength'].default_value=emission
    return m


def unlit(name, color):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    nt=m.node_tree
    nt.nodes.clear()
    e=nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value=(*color,1)
    out=nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0],out.inputs['Surface'])
    return m


def empty(s,name,loc=(0,0,0),parent=None):
    o=bpy.data.objects.new(name,None)
    s.collection.objects.link(o)
    o.parent=parent
    o.location=loc
    return o


def box(name,loc,size,mat,parent=None,bevel=.018):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object
    o.name=name
    o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.parent=parent
    o.data.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Rounded edge highlights','BEVEL')
        m.width,m.segments=bevel,2
    return o


def sphere(name,loc,size,mat,parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,radius=1,location=loc)
    o=bpy.context.object
    o.name=name
    o.scale=size
    o.parent=parent
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth=True
    return o


def text(s,name,body,loc,size,mat,parent=None):
    d=bpy.data.curves.new(name,'FONT')
    d.body=body
    d.size=size
    d.align_x=d.align_y='CENTER'
    o=bpy.data.objects.new(name,d)
    s.collection.objects.link(o)
    o.parent=parent
    o.location=loc
    d.materials.append(mat)
    return o


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def area(s,name,loc,target,power,color,size):
    d=bpy.data.lights.new(name,'AREA')
    d.energy,d.color,d.size=power,color,size
    o=bpy.data.objects.new(name,d)
    s.collection.objects.link(o)
    o.location=loc
    aim(o,target)
    return o
