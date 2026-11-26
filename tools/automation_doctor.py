"""Read-only operational readiness. Never prints credential values."""
import json
import os
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def inspect():
    standards=json.loads((ROOT/'config/production_standards.json').read_text())
    settings=json.loads((ROOT/'config/creative_production.json').read_text())
    api=bool(os.environ.get('OPENROUTER_API_KEY'))
    oauth=all(os.environ.get(k) for k in ['YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN'])
    blender=shutil.which('blender') or next((str(p) for p in [Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'),ROOT/'blender-app/blender'] if p.is_file()),None)
    ffmpeg=shutil.which('ffmpeg') or next((str(p) for p in (ROOT/'artifacts/tooling').glob('**/ffmpeg*.exe') if p.is_file()),None)
    cast=json.loads((ROOT/'config/voice_cast_local.json').read_text())
    missing_models=[v['voice_id'] for v in cast['voices'].values() if not (ROOT/v['model']).is_file()]
    blockers=[]
    if not api:blockers.append('OPENROUTER_API_KEY missing: live creative writing cannot run')
    if not oauth:blockers.append('YouTube OAuth credentials missing: remote upload cannot run')
    if standards['episode_generation_paused']:blockers.append('Canonical production paused for quality review')
    if not blender:blockers.append('Blender executable not found')
    if not ffmpeg:blockers.append('FFmpeg executable not found')
    if missing_models:blockers.append('Pinned local voice models must be installed')
    return {'live_ai_configured':api,'youtube_oauth_configured':oauth,'blender':blender,'ffmpeg':ffmpeg,
        'missing_voice_models':missing_models,'daily_enabled':settings['daily_enabled'],
        'public_publishing_enabled':standards['public_publishing_enabled'],
        'paid_services_enabled':settings['paid_services_enabled'],
        'can_test_authored_development':bool(blender and ffmpeg and not missing_models),
        'full_production_ready':not blockers,'blockers':blockers,
        'note':'Readiness is not permission to publish or enable billing; model/YouTube secrets are never printed.'}


if __name__=='__main__':print(json.dumps(inspect(),indent=2))
