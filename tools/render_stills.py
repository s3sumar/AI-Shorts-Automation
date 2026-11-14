import bpy
import json
import time
from pathlib import Path

s=bpy.context.scene
root=Path(__file__).resolve().parents[1]
out=root/'artifacts'/'episode_001'/'stills'
out.mkdir(parents=True,exist_ok=True)
s.render.resolution_percentage=50
times=[]
for second in [1,6,9.5,21.9,24.5,26.3,28,32,36,39,42,44]:
    s.frame_set(round(second*24)+1)
    s.render.filepath=str(out/f'still_{second:04.1f}.png')
    start=time.monotonic()
    bpy.ops.render.render(write_still=True)
    times.append({'second':second,'camera':s.camera.name,'seconds_rendering':time.monotonic()-start})
(out/'timings.json').write_text(json.dumps(times,indent=2))
print('STILLS COMPLETE '+json.dumps(times))
