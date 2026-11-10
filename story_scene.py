"""Original animated elevator suspense scene for Blender 5.2.x.

GitHub usage: set EPISODE_CONFIG=episodes/episode_002.json and run
  blender -b -t 4 --python story_scene.py --python-expr \
    "import bpy; bpy.ops.render.render(animation=True)"

Creates 48 frames at 12 FPS (4-second animation). PNGs go to frames/.
The paired GitHub workflow converts them into an MP4.
"""
import bpy
import json
import math
import os
from mathutils import Vector

CONFIG = os.environ.get('EPISODE_CONFIG', 'episodes/episode_001.json')
with open(CONFIG, encoding='utf-8') as f:
    cfg = json.load(f)

mood = cfg.get('mood', 'red_alert')
hex_color = cfg.get('character_color', '#D8E0E4').lstrip('#')
if len(hex_color) != 6 or any(c not in '0123456789ABCDEFabcdef' for c in hex_color):
    raise ValueError('character_color must be six hex digits, e.g. #D8E0E4')
char_rgb = tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
opening = str(cfg.get('opening_floor', '13'))[:10]
ending = str(cfg.get('ending_floor', '-1'))[:10]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 432
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.fps = 12
scene.frame_start, scene.frame_end = 1, 48
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.abspath('frames/frame_')
scene.render.film_transparent = False
scene.world.color = (0.015, 0.02, 0.028)
scene.view_settings.view_transform = 'AgX'

# Keep sample counts low for GitHub's CPU-only runner.
if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 16

def material(name, rgb, rough=.48, metal=0, emit=None, strength=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit is not None:
        bsdf.inputs['Emission Color'].default_value = (*emit, 1)
        bsdf.inputs['Emission Strength'].default_value = strength
    return m

metal = material('Brushed blue-grey steel', (.18, .22, .28), .44, .55)
metal_dark = material('Dark steel', (.038, .05, .07), .55, .35)
black = material('Pure shadow', (.009, .012, .016), .86)
pale = material('Character porcelain', char_rgb, .58, .05)
eyes = material('Eyes', (.016, .020, .027), .52)
light_white = material('Fluorescent panel', (.65, .78, .90), emit=(.48, .68, 1), strength=2)
red_glow = material('Warning display', (.35, .04, .04), emit=(1, .055, .07), strength=2)


def cube(name, xyz, size, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def sphere(name, xyz, radius, mat, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=radius, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
