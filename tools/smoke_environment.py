"""Small render of the second environment variant; not a completed episode."""
import bpy
import json
import time
from pathlib import Path

s=bpy.context.scene
c=json.loads(s['episode_config'])
assert c['environment']['id']=='freight_lift'
assert len([o for o in s.objects if o.name.startswith('Freight safety band')])==6
assert len([o for o in s.objects if o.name.startswith('Service pipe')])==2
assert s.objects['Left wall'].data.materials[0].name.startswith('Environment | freight enamel')
assert s.camera and s.camera.name=='Shot | arrival'
out=Path(bpy.data.filepath).parent
s.render.resolution_percentage=20
s.eevee.taa_render_samples=4
s.frame_set(1)
s.render.filepath=str(out/'freight_environment_smoke.png')
t=time.monotonic()
bpy.ops.render.render(write_still=True)
(out/'environment_validation.json').write_text(json.dumps({'passed':True,'environment':'freight_lift',
    'resolution':[108,192],'seconds':time.monotonic()-t,'scope':'Geometry and one small still; no episode narration or complete video'},indent=2))
print('ENVIRONMENT SMOKE PASS')
