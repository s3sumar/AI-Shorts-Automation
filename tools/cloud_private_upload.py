"""Resolve this production run's outbox job. Runs only in an explicitly approved step."""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.store import Memory
from autonomy.youtube import execute_private

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-key',required=True)
    a=p.parse_args()
    memory=Memory(ROOT/'state/story.sqlite3')
    try:
        row=memory.db.execute('SELECT e.* FROM episodes e JOIN runs r ON r.uid=e.uid WHERE r.run_key=?',(a.run_key,)).fetchone()
        if not row or row['status']!='verified':
            raise RuntimeError('This run has no verified episode')
        receipt=ROOT/'state/uploads'/(row['uid']+'.json')
        if receipt.exists():
            prior=json.loads(receipt.read_text())
            if prior.get('status')=='complete':
                print('Verified episode already uploaded privately; duplicate skipped')
                raise SystemExit(0)
        job=ROOT/'artifacts/autonomy'/row['uid']/'youtube_private_upload.json'
        if not job.exists():
            raise RuntimeError('Upload outbox missing; recover this run artifact before retrying')
        settings=json.loads((ROOT/'config/autonomy.json').read_text())
        settings['youtube']['enabled']=True
        print(json.dumps(execute_private(job,settings,execute=True)))
    finally:
        memory.close()
