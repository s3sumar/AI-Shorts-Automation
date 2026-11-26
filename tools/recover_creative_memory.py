"""Read-only recovery from the existing state branch. Never seeds missing state."""
import argparse
import base64
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.creative_memory import unpack
from autonomy.contracts import write_json
from tools.cloud_checkpoint import GitHub


def recover(api,series,out):
    if not re.fullmatch(r'creative_[a-z0-9_]{1,54}',series): raise ValueError('Invalid creative series ID')
    out=Path(out).resolve()
    if not out.is_relative_to((ROOT/'artifacts').resolve()): raise ValueError('Recover only to isolated artifacts')
    if out.exists(): raise FileExistsError('Preserve existing recovered state')
    remote=api.call('GET','contents/checkpoint/creative/'+series+'.json?ref=autonomy-state')
    if not remote: raise RuntimeError('Accepted creative checkpoint is missing; refuse to restart the series')
    bible,memory=unpack(json.loads(base64.b64decode(remote['content'])))
    if bible['id']!=series: raise ValueError('Recovered a different series')
    write_json(out/'bible.json',bible);write_json(out/'memory.json',memory)
    print('CREATIVE MEMORY RECOVERED: '+series+'; next='+str(memory['next_episode']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--series',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();recover(GitHub(),a.series,a.out)
