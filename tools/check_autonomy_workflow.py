"""Parse workflow YAML and assert no automatic publishing/paid-service defaults."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
try:
    import yaml
except ModuleNotFoundError:
    sys.path.insert(0,str(ROOT/'artifacts/tooling'))
    import yaml
path=ROOT/'.github/workflows/autonomous_production.yml'
workflow=yaml.load(path.read_text(encoding='utf-8-sig'),Loader=yaml.BaseLoader)
assert set(workflow['on'])=={'workflow_dispatch'}
assert workflow['permissions']=={'contents':'read'}
assert workflow['concurrency']['cancel-in-progress']=='false'
job=workflow['jobs']['produce']
assert job['permissions']=={'contents':'write'}
steps=job['steps']
commands=[s.get('run','') for s in steps]
restore=next(i for i,c in enumerate(commands) if 'cloud_checkpoint.py restore' in c)
reservation=next(i for i,s in enumerate(steps) if s.get('id')=='reservation')
render=next(i for i,c in enumerate(commands) if 'pipeline produce' in c)
save=next(i for i,c in enumerate(commands) if i>render and 'cloud_checkpoint.py save' in c)
assert restore<reservation<render<save
assert "steps.reservation.outcome == 'success'" in steps[save]['if']
assert 'always()' in steps[save]['if']
assert any(s.get('uses')=='actions/upload-artifact@v4' and s.get('if')=='always()' for s in steps)
for command in commands:
    assert not any(v in command for v in ['execute-private','cloud_private_upload','git push','--render-anim','C:/'])
assert 'youtube' not in str(job).lower()
assert not any('actions/cache' in s.get('uses','') for s in steps)
print('WORKFLOW PASS: manual only; durable reservation before render; failure checkpoint; artifacts; no uploads/MCP/cache dependency')
