"""Always produce an Actions summary without obscuring a prior failure."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path
root=Path(__file__).resolve().parents[1]
lines=['## Autonomous preview run', '', 'Manual execution; offline narration; no video upload; no daily schedule.', '']
state=root/'state/story.sqlite3'
if state.exists():
    with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True)) as db:
        for uid,status,error in db.execute('SELECT uid,status,error FROM episodes ORDER BY number'):
            lines.append(f'- {uid}: **{status}**'+(f' — {error}' if error else ''))
else:
    lines.append('Story state was not restored. See the failed step; no episode was created.')
lines += ['', 'Download the shorts-production artifact for videos, shot scores, validation and recovery files.',
          'Durable checkpoint history is on the autonomy-state branch. API conflicts fail closed.']
text='\n'.join(lines)+'\n'
out=root/'artifacts/autonomy'
out.mkdir(parents=True,exist_ok=True)
(out/'run_summary.md').write_text(text,encoding='utf-8')
print(text)
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:
        stream.write(text)
