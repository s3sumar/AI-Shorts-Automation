"""Optimistic durable creative-ledger storage on a dedicated checkpoint path.

The legacy Episode 1/2/3 checkpoint is never read or overwritten by this tool.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from autonomy.creative_store import CreativeStore,unpack_snapshot
from autonomy.contracts import write_json
from tools.cloud_checkpoint import GitHub

FILE='checkpoint/creative_development.json'


def recover(api,state,receipt,initialize=False):
    if Path(state).exists():raise FileExistsError('Restore creative cloud state only to a fresh database')
    remote=api.call('GET','contents/'+FILE+'?ref=autonomy-state')
    if not remote and not initialize:raise RuntimeError('Creative checkpoint missing; explicit initialization required')
    store=CreativeStore(state)
    try:
        if remote:
            value=json.loads(base64.b64decode(remote['content']));store.restore(value)
        value=store.snapshot()
        write_json(receipt,{'remote_sha':remote['sha'] if remote else None,'previous':value})
    finally:store.close()


def refuse_regression(previous,current):
    old=unpack_snapshot(previous);new=unpack_snapshot(current)
    new_series={s['id']:s for s in new['series']};new_episodes={e['uid']:e for e in new['episodes']}
    for s in old['series']:
        if s['id'] not in new_series or s['bible']!=new_series[s['id']]['bible']:raise ValueError('Creative series removed or rewritten')
        before=json.loads(s['memory']);after=json.loads(new_series[s['id']]['memory'])
        if after['next_episode']<before['next_episode'] or after['history'][:len(before['history'])]!=before['history']:raise ValueError('Creative memory regressed')
    for e in old['episodes']:
        candidate=new_episodes.get(e['uid'])
        if not candidate or e['script']!=candidate['script'] or e['prior_hash']!=candidate['prior_hash']:raise ValueError('Creative reservation was lost or rewritten')
        if e['status']=='verified' and candidate!=e:raise ValueError('Verified creative episode changed')
    if not {(r['run_key'],r['uid']) for r in old['runs']}<={(r['run_key'],r['uid']) for r in new['runs']}:raise ValueError('Creative run history regressed')
    reviews={r['uid']:r['receipt'] for r in new.get('reviews',[])}
    if any(reviews.get(r['uid'])!=r['receipt'] for r in old.get('reviews',[])):raise ValueError('Editorial provenance regressed')


def persist(api,state,receipt):
    prior=json.loads(Path(receipt).read_text());store=CreativeStore(state)
    try:current=store.snapshot()
    finally:store.close()
    refuse_regression(prior['previous'],current)
    body={'branch':'autonomy-state','message':'Checkpoint isolated creative development run '+os.environ.get('GITHUB_RUN_ID','manual'),
          'content':base64.b64encode(json.dumps(current,indent=2).encode()).decode()}
    if prior['remote_sha']:body['sha']=prior['remote_sha']
    result=api.call('PUT','contents/'+FILE,body)
    write_json(receipt,{'remote_sha':result['content']['sha'],'previous':current})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['restore','save'])
    p.add_argument('--state',default='artifacts/creative_cloud_state/ledger.sqlite3')
    p.add_argument('--receipt',default='artifacts/creative_cloud_state/recovery.json')
    p.add_argument('--initialize-if-missing',action='store_true')
    a=p.parse_args();api=GitHub()
    if a.command=='restore':recover(api,ROOT/a.state,ROOT/a.receipt,a.initialize_if_missing)
    else:persist(api,ROOT/a.state,ROOT/a.receipt)
