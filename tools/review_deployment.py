"""Review candidate or staged Git files; never reads credentials outside the repo."""
import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def review(staged=False):
    command=['git','diff','--cached','--name-only','--diff-filter=ACMR','-z'] if staged else ['git','ls-files','--cached','--others','--exclude-standard','-z']
    paths=subprocess.check_output(command,cwd=ROOT).decode().split('\0')
    paths=sorted(set(p for p in paths if p))
    forbidden={'.mp4','.wav','.mp3','.png','.sqlite3','.db','.exe','.dll','.zip','.xz','.pem','.key'}
    patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',
              r'AIza[0-9A-Za-z_-]{30,}',r'sk-proj-[A-Za-z0-9_-]{20,}',
              r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
              r'"(?:client_secret|refresh_token)"\s*:\s*"[^"$]{8,}"']
    for name in paths:
        path=Path(name)
        if path.parts[0] in ['artifacts','state','blender-app','output','frames','local-renders'] or path.suffix.lower() in forbidden:
            raise ValueError('Generated/sensitive file in deployment: '+name)
        if path.name.startswith(('.env','client_secret','youtube_token')) or (path.suffix=='.blend' and name!='assets/elevator_template.blend'):
            raise ValueError('Unexpected sensitive or binary file: '+name)
        data=subprocess.check_output(['git','show',':'+name],cwd=ROOT) if staged else (ROOT/name).read_bytes()
        if b'\x00' in data[:8192]:
            if name!='assets/elevator_template.blend':
                raise ValueError('Unexpected binary file: '+name)
            continue
        text=data.decode('utf-8-sig')
        if any(re.search(pattern,text) for pattern in patterns):
            raise ValueError('Possible credential detected in '+name)
        if path.suffix=='.py':
            ast.parse(text,filename=name)
    required=['autonomy/checkpoint.py','autonomy/pipeline.py','production/episode.py',
              'assets/elevator_template.blend','config/story_checkpoint.json','config/cloud_preview.json',
              'tools/cloud_checkpoint.py','.github/workflows/autonomous_production.yml',
              'requirements-production.txt','episodes/episode_001.json','legacy_story_scene.py']
    for name in required:
        if not (ROOT/name).is_file():
            raise ValueError('Required deployment file missing: '+name)
    settings=json.loads((ROOT/'config/cloud_preview.json').read_text())
    if settings['youtube']['enabled'] or settings['paid_services_enabled'] or settings['director']['provider']!='offline':
        raise ValueError('Cloud acceptance must keep uploads and paid services disabled')
    if staged:
        for name in required:
            subprocess.run(['git','cat-file','-e',':'+name],cwd=ROOT,check=True,capture_output=True)
    return {'passed':True,'files_reviewed':len(paths),'staged':staged,'secrets_detected':0,
            'generated_media_or_databases':0,'required_blender_asset':'assets/elevator_template.blend'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--staged',action='store_true')
    print(json.dumps(review(parser.parse_args().staged),indent=2))
