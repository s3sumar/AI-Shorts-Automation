"""Build an eight-second elevator suspense scene for Blender 5.2.x.

GitHub usage: set EPISODE_CONFIG=episodes/episode_002.json and run
  blender -b -t 4 --python story_scene.py --python-expr \
    "import bpy; bpy.ops.render.render(animation=True)"

Creates 96 frames at 12 FPS. PNGs go to frames/; FFmpeg encodes the MP4.
Paths are relative to this script, so running from another directory works.
Optional: FRAMES_DIR, SCENE_BLEND (save a reusable .blend), RENDER_ENGINE
(BLENDER_EEVEE or CYCLES; CPU Cycles works on headless CI without a GPU).
"""
import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('EPISODE_CONFIG', 'episodes/episode_001.json'))
if not CONFIG.is_absolute():
    CONFIG = ROOT / CONFIG
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
scene.render.engine = os.environ.get('RENDER_ENGINE', 'BLENDER_EEVEE')
if scene.render.engine == 'CYCLES':
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
scene.render.resolution_x = 432
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.fps = 12
scene.frame_start, scene.frame_end = 1, 96
scene.render.fps_base = 1
scene.render.use_file_extension = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
frames_dir = Path(os.environ.get('FRAMES_DIR', 'frames'))
if not frames_dir.is_absolute():
    frames_dir = ROOT / frames_dir
frames_dir.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(frames_dir / 'frame_')
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new('Night outside the lift')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.025, .035, .06, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .12
scene.view_settings.view_transform = 'AgX'

# Keep sample counts low for GitHub's CPU-only runner.
if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 64
elif hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_samples'):
    scene.eevee.taa_samples = 64

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


def curves(owner):
    """Support both legacy actions and Blender 5's layered actions."""
    action = owner.animation_data.action
    if hasattr(action, 'fcurves'):
        yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves


def animate(owner, path, keys, interpolation='BEZIER'):
    for frame, value in keys:
        setattr(owner, path, value)
        owner.keyframe_insert(data_path=path, frame=frame)
    for curve in curves(owner):
        if curve.data_path == path:
            for key in curve.keyframe_points:
                key.interpolation = interpolation
                key.handle_left_type = key.handle_right_type = 'AUTO_CLAMPED'


def empty(name, location):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.location = location
    return obj


def parent_local(obj, parent):
    # Geometry is authored in the parent's local coordinates.
    obj.parent = parent
    return obj


def text(name, value, location, size, mat):
    data = bpy.data.curves.new(name, 'FONT')
    data.body = value
    data.size = size
    data.align_x = data.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.pi / 2, 0, 0)
    data.materials.append(mat)
    return obj


def area(name, location, target, power, color, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.color, data.size = power, color, size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


# The rear wall has a real opening: no wall or seam blocks the reveal.
floor = material('Graphite terrazzo', (.055, .07, .09), .29, .25)
trim = material('Satin brass trim', (.36, .25, .12), .32, .7)
cube('Cab floor', (0, -2, -.12), (4.8, 8.8, .24), floor)
cube('Ceiling', (0, -2, 4.18), (4.8, 8.8, .16), metal_dark)
for side in (-1, 1):
    cube('Side wall', (side * 2.4, -2, 2.05), (.16, 8.8, 4.2), metal)
    cube('Hand rail', (side * 2.28, -.1, 1.05), (.09, 3.8, .10), trim, .025)
    for y in (-1.6, -.7, .2, 1.1):
        cube('Wall joint', (side * 2.305, y, 2.1), (.012, .018, 4), metal_dark)
    cube('Rear side panel', (side * 1.92, 2.24, 2.05), (.96, .2, 4.2), metal)
    cube('Door jamb', (side * 1.43, 2.06, 1.68), (.09, .23, 3.36), trim, .015)
    cube('Ceiling strip', (side * 1.45, -.1, 4.065), (.18, 3.8, .035), light_white, .015)
cube('Rear lintel', (0, 2.24, 3.78), (3, .20, .85), metal)
cube('Door header', (0, 2.05, 3.4), (2.95, .25, .12), trim, .02)
cube('Door sill', (0, 2.2, .015), (2.9, .45, .03), trim)
for x in (-.52, -.26, 0, .26, .52):
    cube('Floor inlay', (x, -.6, .006), (.014, 3.4, .012), trim)

doors = []
for side, name in ((-1, 'Door left'), (1, 'Door right')):
    obj = cube(name, (side * .695, 2.18, 1.68), (1.38, .12, 3.30), metal, .018)
    animate(obj, 'location', [(1, (side * .695, 2.18, 1.68)),
                             (56, (side * .695, 2.18, 1.68)),
                             (82, (side * 2.12, 2.18, 1.68)),
                             (96, (side * 2.12, 2.18, 1.68))])
    doors.append(obj)

# Corridor gives the silhouette a contrasting rim without lighting its face.
cube('Corridor floor', (0, 4.5, -.08), (3, 4.7, .16), floor)
cube('Corridor end', (0, 6.8, 2), (3.2, .15, 4.2), metal_dark)
for side in (-1, 1):
    cube('Corridor wall', (side * 1.55, 4.6, 2), (.15, 4.8, 4.2), metal_dark)
    cube('Corridor warning strip', (side * 1.46, 5.8, 2), (.035, .08, 3.5), red_glow)

cube('Display housing', (0, 2.04, 3.72), (1.65, .13, .43), black, .045)
opening_text = text('Opening floor', opening, (0, 1.96, 3.73), .30, red_glow)
ending_text = text('Ending floor', ending, (0, 1.955, 3.73), .30, red_glow)
# Font bodies cannot be keyframed. Swap two text objects with step visibility.
for obj, before, after in ((opening_text, False, True), (ending_text, True, False)):
    for path in ('hide_render', 'hide_viewport'):
        animate(obj, path, [(1, before), (39, before), (40, after), (96, after)], 'CONSTANT')
text('Cab plaque', 'SERVICE  /  013', (1.90, 2.10, 2.68), .105, trim)
cube('Control plate', (1.92, 2.10, 1.85), (.27, .09, .66), metal_dark, .025)
for z in (1.68, 1.88, 2.08):
    sphere('Control button', (1.92, 2.035, z), .045, red_glow, (1, .35, 1))

# Separate neck pivot: the face turns while the torso remains planted.
body = empty('Character body', (-.82, -.65, 0))
parent_local(sphere('Character torso', (0, 0, 1.18), .43, pale, (.87, .68, 1.22)), body)
for side in (-1, 1):
    parent_local(sphere('Character arm', (side * .52, 0, 1.20), .17, pale, (.65, .78, 2.15)), body)
    parent_local(sphere('Character leg', (side * .23, 0, .48), .18, pale, (.85, .95, 2.25)), body)
    parent_local(sphere('Character shoe', (side * .23, -.08, .11), .18, metal_dark, (1, 1.5, .6)), body)
neck = parent_local(empty('Head turn pivot', (0, 0, 2.08)), body)
parent_local(sphere('Character head', (0, 0, .10), .46, pale, (1, .86, 1.06)), neck)
for side in (-1, 1):
    parent_local(sphere('Character eye', (side * .16, -.373, .17), .065, eyes, (1, .45, 1.22)), neck)
    brow = parent_local(cube('Character brow', (side * .16, -.373, .32), (.16, .04, .035), eyes, .008), neck)
    brow.rotation_euler[1] = side * .15
parent_local(sphere('Character nose', (0, -.418, .04), .065, pale, (.65, 1, .7)), neck)
animate(neck, 'rotation_euler', [(1, (0, 0, -.12)), (41, (0, 0, -.12)),
                                (48, (0, .06, .25)), (67, (0, -.04, 2.18)),
                                (96, (0, -.04, 2.18))])

figure = empty('Shadow figure approach', (.38, 4.45, 0))
figure_parts = [
    sphere('Shadow hood', (0, 0, 2.62), .36, black, (.85, .78, 1.1)),
    sphere('Shadow coat', (0, 0, 1.57), .48, black, (.9, .64, 1.75)),
]
for side in (-1, 1):
    figure_parts.append(sphere('Shadow arm', (side * .48, 0, 1.52), .15, black, (.8, .9, 3.6)))
    figure_parts.append(sphere('Shadow leg', (side * .20, 0, .55), .17, black, (.85, 1, 3.15)))
for obj in figure_parts:
    parent_local(obj, figure)
    for path in ('hide_render', 'hide_viewport'):
        animate(obj, path, [(1, True), (75, True), (76, False), (96, False)], 'CONSTANT')
animate(figure, 'location', [(1, (.38, 4.45, 0)), (76, (.38, 4.45, 0)),
                             (96, (.38, 3.25, 0))], 'LINEAR')

blue, red = (.16, .44, 1), (1, .025, .045)
overhead = area('Flickering overhead', (0, -.1, 3.96), (0, 0, 0), 650, blue, 3.2)
fill = area('Face fill', (1, -3.3, 2.8), (-.82, -.65, 1.8), 170, blue, 3)
area('Doorway red rim', (-.1, 5.9, 3.1), (.38, 3.25, 1.6), 720, red, 2.3)
area('Corridor backdrop wash', (0, 5.4, 3.5), (0, 6.75, 2), 230, red, 2)
# Explicit deterministic keys: rapid failures, then sustained red after floor change.
flicker = [(1, 1, False), (18, 1, False), (20, .04, False), (22, .85, False),
           (24, .08, True), (26, .95, False), (29, .04, False), (31, .9, True),
           (33, .08, True), (35, .65, False), (38, .025, False), (40, 1, True),
           (46, .85, True), (48, .12, True), (50, 1, True), (70, 1, True),
           (72, .25, True), (74, .9, True), (96, .9, True)]
base_power = 540 if mood == 'red_alert' else 650
for lamp, power in ((overhead, base_power), (fill, 170)):
    animate(lamp.data, 'energy', [(f, power * level) for f, level, _ in flicker], 'CONSTANT')
    animate(lamp.data, 'color', [(f, red if alarm else blue) for f, _, alarm in flicker], 'CONSTANT')
emission = light_white.node_tree.nodes['Principled BSDF'].inputs
for frame, level, alarm in flicker:
    emission['Emission Color'].default_value = (*(red if alarm else blue), 1)
    emission['Emission Color'].keyframe_insert('default_value', frame=frame)
    emission['Emission Strength'].default_value = 3 * level
    emission['Emission Strength'].keyframe_insert('default_value', frame=frame)
for curve in curves(light_white.node_tree):
    for key in curve.keyframe_points:
        key.interpolation = 'CONSTANT'

# Establish both the passenger and indicator, then push toward the open doorway.
camera_data = bpy.data.cameras.new('Cinematic portrait camera')
camera = bpy.data.objects.new('Cinematic portrait camera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera  # Required: deleting the startup scene also deletes its camera.
camera_data.lens = 32
camera_data.clip_start, camera_data.clip_end = .05, 100
for frame, location, target in (
    (1, (1.65, -6.7, 2.8), (-.1, .8, 1.95)),
    (40, (1.45, -6.2, 2.7), (-.1, .9, 2.0)),
    (70, (1.25, -5.9, 2.65), (-.15, 1.0, 2.02)),
    (96, (1.05, -5.55, 2.6), (-.2, 1.25, 2.05)),
):
    camera.location = location
    look_at(camera, target)
    camera.keyframe_insert('location', frame=frame)
    camera.keyframe_insert('rotation_euler', frame=frame)
for curve in curves(camera):
    for key in curve.keyframe_points:
        key.handle_left_type = key.handle_right_type = 'AUTO_CLAMPED'
for name, frame in (('Cold arrival', 1), ('Power failure', 20), ('Wrong floor', 40),
                    ('Head turns', 48), ('Doors open', 57), ('Someone waiting', 76)):
    marker = scene.timeline_markers.new(name, frame=frame)
    marker.camera = camera

scene.frame_set(1)
if scene.camera is None or scene.camera.type != 'CAMERA':
    raise RuntimeError('Scene construction did not create an active camera')
if os.environ.get('SCENE_BLEND'):
    blend_path = Path(os.environ['SCENE_BLEND'])
    if not blend_path.is_absolute():
        blend_path = ROOT / blend_path
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
print(f'SCENE READY: {CONFIG.name}; camera={scene.camera.name}; '
      f'{scene.frame_end} frames at {scene.render.fps} FPS; output={scene.render.filepath}')
