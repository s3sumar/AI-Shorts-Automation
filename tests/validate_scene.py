"""Check the built scene in Blender, before spending time rendering it.

blender -b --factory-startup --python-exit-code 1 \
    --python story_scene.py --python tests/validate_scene.py
Run once per EPISODE_CONFIG. Also used by dynamic_render.yml.
"""
import json
import math
import os
from pathlib import Path

import bpy


def check(condition, message):
    if not condition:
        raise AssertionError(message)


scene = bpy.context.scene
root = Path(__file__).resolve().parents[1]
config_path = Path(os.environ.get('EPISODE_CONFIG', 'episodes/episode_001.json'))
if not config_path.is_absolute():
    config_path = root / config_path
with config_path.open(encoding='utf-8') as handle:
    config = json.load(handle)

check(scene.camera is not None and scene.camera.type == 'CAMERA', 'Missing active camera')
check(scene.camera.name in scene.objects, 'Camera must be linked to the rendered scene')
check((scene.frame_start, scene.frame_end, scene.render.fps) == (1, 96, 12), 'Unexpected duration')
check((scene.render.resolution_x, scene.render.resolution_y) == (432, 768), 'Expected portrait render')
check(scene.render.image_settings.file_format == 'PNG', 'FFmpeg expects PNG frames')
check(bpy.data.objects['Opening floor'].data.body == str(config.get('opening_floor', '13'))[:10],
      'Opening floor ignores episode configuration')
check(bpy.data.objects['Ending floor'].data.body == str(config.get('ending_floor', '-1'))[:10],
      'Ending floor ignores episode configuration')

head = bpy.data.objects['Head turn pivot']
left, right = (bpy.data.objects[name] for name in ('Door left', 'Door right'))
opening, ending = (bpy.data.objects[name] for name in ('Opening floor', 'Ending floor'))
figure = bpy.data.objects['Shadow hood']
light = bpy.data.lights['Flickering overhead']

scene.frame_set(1)
initial_head = head.rotation_euler.z
initial_camera = scene.camera.location.copy()
initial_power = light.energy
check(not opening.hide_render and ending.hide_render, 'Wrong opening indicator visibility')
check(figure.hide_render, 'Figure must be hidden on arrival')
check(light.color.b > light.color.r, 'Arrival must be blue')
check(abs(left.location.x + .695) < .001 and abs(right.location.x - .695) < .001,
      'Doors must start closed')
scene.frame_set(20)
check(light.energy < initial_power * .1, 'Missing power failure flicker')
scene.frame_set(39)
check(not opening.hide_render and ending.hide_render, 'Indicator changed too early')
scene.frame_set(40)
check(opening.hide_render and not ending.hide_render, 'Floor display did not switch')
check(light.color.r > light.color.b * 5, 'Lighting must switch to red')
scene.frame_set(56)
check(abs(left.location.x + .695) < .001, 'Door opened before head turn')
scene.frame_set(67)
check(abs(head.rotation_euler.z - initial_head) > 2, 'Head did not turn')
check(sum(abs(angle) for angle in bpy.data.objects['Character body'].rotation_euler) < .001,
      'Head motion incorrectly rotates the entire character')
scene.frame_set(75)
check(figure.hide_render, 'Figure appeared before reveal')
scene.frame_set(76)
check(not figure.hide_render, 'Figure did not appear')
scene.frame_set(96)
check(right.location.x - left.location.x > 4.2, 'Door opening incomplete')
check((scene.camera.location - initial_camera).length > 1, 'Missing camera push')
check(abs(bpy.data.objects['Shadow figure approach'].location.y - 3.25) < .001,
      'Figure did not approach the doorway')

# Scrub all frames to exercise evaluation, including visibility in reverse order.
for frame in range(96, 0, -1):
    scene.frame_set(frame)
    check(scene.camera == bpy.data.objects['Cinematic portrait camera'], 'Marker changed active camera')
    for obj in (scene.camera, head, left, right):
        check(all(math.isfinite(value) for row in obj.matrix_world for value in row),
              f'Invalid transform at frame {frame}: {obj.name}')
    check(opening.hide_render == (frame >= 40), f'Opening display wrong at frame {frame}')
    check(ending.hide_render == (frame < 40), f'Ending display wrong at frame {frame}')
    check(figure.hide_render == (frame < 76), f'Figure visibility wrong at frame {frame}')

scene.frame_set(1)
print(f'PASS: {config_path.name}: camera, 96-frame evaluation, floor swap, flicker, '
      'head turn, doors, figure reveal and camera motion')
