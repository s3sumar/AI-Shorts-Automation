"""Explicit private upload with durable duplicate prevention. Never public."""
import argparse
import json
import os
from pathlib import Path
from .contracts import ROOT,file_digest
from .creative_store import CreativeStore
from .youtube import execute_private


def reserve(store,job,attempt):
    if job['metadata']['status']!={'privacyStatus':'private','selfDeclaredMadeForKids':False}:
        raise ValueError('Only unscheduled private uploads are supported')
    path=(ROOT/job['video'].replace('\\','/')).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or file_digest(path)!=job['video_sha256']:
        raise ValueError('Private upload video is missing or changed')
    return store.reserve_upload(job['episode_uid'],job['video_sha256'],attempt)


def upload(store,job_path,attempt,checkpoint_receipt,transport=None):
    job=json.loads(Path(job_path).read_text());receipt=store.upload_receipt(job['episode_uid'])
    if receipt and receipt['status']=='complete':return receipt
    if not receipt or receipt['status']!='reserved' or receipt['attempt']!=attempt:
        raise RuntimeError('Missing matching durable upload reservation')
    # The reservation must already be persisted remotely before a side effect.
    checkpoint=json.loads(Path(checkpoint_receipt).read_text())
    remote=checkpoint['previous']['creative_store'].get('uploads',[])
    if not checkpoint.get('remote_sha') or not any(r['uid']==job['episode_uid'] and json.loads(r['receipt'])==receipt for r in remote):
        raise RuntimeError('Persist the upload reservation before contacting YouTube')
    if os.environ.get('YOUTUBE_UPLOAD_APPROVED')!='YES_PRIVATE_UPLOAD':raise PermissionError('Explicit private-upload execution gate is required')
    settings={'youtube':{'enabled':True,'receipt_dir':str(Path(job_path).resolve().parent.relative_to(ROOT)/'upload_receipts')}}
    try:
        result=execute_private(job_path,settings,True,transport)
        store.finish_upload(job['episode_uid'],'complete',result);return result
    except Exception:
        store.finish_upload(job['episode_uid'],'uncertain');raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['reserve','upload']);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--job',type=Path,required=True);p.add_argument('--attempt',required=True);p.add_argument('--checkpoint-receipt',type=Path)
    a=p.parse_args()
    if os.environ.get('YOUTUBE_UPLOAD_APPROVED')!='YES_PRIVATE_UPLOAD':p.error('Explicit private-upload execution gate is required')
    if not all(os.environ.get(k) for k in ['YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN']):p.error('Missing YouTube OAuth credentials')
    s=CreativeStore(a.state)
    try:
        if a.command=='reserve':result=reserve(s,json.loads(a.job.read_text()),a.attempt)
        else:
            if not a.checkpoint_receipt:p.error('Upload needs the persisted checkpoint receipt')
            result=upload(s,a.job,a.attempt,a.checkpoint_receipt)
        print(json.dumps(result,indent=2))
    finally:s.close()
