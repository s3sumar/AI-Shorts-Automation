"""Prepare private upload jobs; remote execution requires explicit approval gates.

Uses the Google client library's resumable media upload implementation.
No credentials are written to disk or included in upload plans.
"""
import argparse
import json
import os
from pathlib import Path
from .contracts import ROOT,digest,file_digest,write_json,identifier


def prepare_upload(out,evidence,plan):
    job={'video':evidence['video'],'video_sha256':evidence['video_sha256'],'episode_uid':plan['uid'],
        'approved':False,'metadata':{'snippet':{'title':(plan['series_title']+' | '+plan['title'])[:100],
        'description':plan['summary']+'\nOriginal stylized 3D suspense animation.',
        'categoryId':'24','defaultLanguage':'en','tags':['3D animation','suspense',plan['series_title']]},
        'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}}}
    write_json(out/'youtube_private_upload.json',job)
    return job


def google_upload(video,metadata,session_callback):
    names=['YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN']
    if not all(os.environ.get(name) for name in names):
        raise RuntimeError('YouTube OAuth credentials are not configured')
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds=Credentials(token=None,refresh_token=os.environ[names[2]],client_id=os.environ[names[0]],
        client_secret=os.environ[names[1]],token_uri='https://oauth2.googleapis.com/token',
        scopes=['https://www.googleapis.com/auth/youtube.upload'])
    creds.refresh(Request())
    service=build('youtube','v3',credentials=creds,cache_discovery=False)
    request=service.videos().insert(part='snippet,status',notifySubscribers=False,body=metadata,
        media_body=MediaFileUpload(str(video),mimetype='video/mp4',chunksize=1024*1024,resumable=True))
    response=None
    while response is None:
        progress,response=request.next_chunk(num_retries=3)
        session_callback()
    return {'video_id':response['id'],'privacy':response.get('status',{}).get('privacyStatus')}


def execute_private(job_path,settings,execute=False,transport=None):
    job_path=Path(job_path)
    job=json.loads(job_path.read_text())
    if job['metadata']['status'].get('privacyStatus')!='private' or 'publishAt' in job['metadata']['status']:
        raise ValueError('Only private uploads without a publication schedule are supported')
    if not execute:
        return {'dry_run':True,'privacy':'private','episode_uid':job['episode_uid']}
    if not settings['youtube']['enabled'] or os.environ.get('YOUTUBE_UPLOAD_APPROVED')!='YES_PRIVATE_UPLOAD':
        raise PermissionError('Remote upload requires enabled configuration and explicit private-upload approval')
    if transport is None:
        if not all(os.environ.get(k) for k in ['YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN']):
            raise RuntimeError('Configure OAuth credentials before starting an upload')
        # Missing dependencies are a preflight failure, not an uncertain remote upload.
        import googleapiclient.discovery
        import google.oauth2.credentials
    video=(ROOT/job['video'].replace('\\','/')).resolve()
    if not video.is_relative_to(ROOT.resolve()) or file_digest(video)!=job['video_sha256']:
        raise ValueError('Upload file no longer matches the verified video')
    receipt_dir=(ROOT/settings['youtube'].get('receipt_dir','state/uploads')).resolve()
    if not receipt_dir.is_relative_to(ROOT.resolve()):
        raise ValueError('Upload receipts must stay in the project')
    receipt=receipt_dir/(identifier(job['episode_uid'])+'.json')
    if receipt.exists():
        previous=json.loads(receipt.read_text())
        if previous.get('status')=='complete' and previous.get('video_sha256')==job['video_sha256']:
            return previous
        raise RuntimeError('An earlier upload is incomplete or uncertain; reconcile it before trying again')
    write_json(receipt,{'status':'started','episode_uid':job['episode_uid'],'video_sha256':job['video_sha256']})
    try:
        result=(transport or google_upload)(video,job['metadata'],lambda:None)
        if result.get('privacy')!='private' or not result.get('video_id'):
            raise RuntimeError('Upload response did not confirm private status')
        result.update(status='complete',video_sha256=job['video_sha256'])
        write_json(receipt,result)
        return result
    except Exception:
        write_json(receipt,{'status':'uncertain','episode_uid':job['episode_uid'],
            'video_sha256':job['video_sha256'],'action':'Review YouTube before retrying; duplicate uploads are blocked'})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('job')
    p.add_argument('--settings',default='config/autonomy.json')
    p.add_argument('--execute-private',action='store_true')
    a=p.parse_args()
    print(json.dumps(execute_private(ROOT/a.job,json.loads((ROOT/a.settings).read_text()),a.execute_private),indent=2))
