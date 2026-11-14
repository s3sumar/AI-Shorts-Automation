"""Dispatch schema-2 production episodes; preserve schema-1 legacy episodes."""
import json
import os
import runpy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
config=Path(os.environ.get('EPISODE_CONFIG','episodes/episode_001.json'))
if not config.is_absolute():
    config=ROOT/config
cfg=json.loads(config.read_text(encoding='utf-8'))
if cfg.get('schema_version')==2:
    from production.episode import build
    build(ROOT,config)
else:
    runpy.run_path(str(ROOT/'legacy_story_scene.py'),run_name='__main__')
