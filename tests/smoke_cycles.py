"""Tiny CPU-only fallback render; never save modified preview settings."""
import bpy
import json
import time
from pathlib import Path

s=bpy.context.scene
s.render.engine='CYCLES'
s.cycles.device='CPU'
s.cycles.samples=4
s.cycles.use_denoising=True
s.cycles.max_bounces=3
s.render.resolution_percentage=20
s.frame_set(937)
out=Path(__file__).resolve().parents[1]/'artifacts/episode_001'
s.render.filepath=str(out/'cycles_cpu_smoke.png')
t=time.monotonic()
bpy.ops.render.render(write_still=True)
assert (out/'cycles_cpu_smoke.png').stat().st_size>100
report={'passed':True,'engine':s.render.engine,'device':s.cycles.device,'samples':4,
        'resolution':[108,192],'frame':937,'seconds':time.monotonic()-t}
(out/'cycles_cpu_smoke.json').write_text(json.dumps(report,indent=2))
print('CPU SMOKE PASS '+json.dumps(report))
