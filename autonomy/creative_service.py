"""Resumable creative production coordinator; exactly one episode per run.

Development state is isolated from canonical production. Missing AI credentials
never turn into a procedural fallback. Private-upload plans are not executed.
"""
import argparse
import json
from pathlib import Path
from .contracts import ROOT,digest,file_digest,write_json
from .creative_store import CreativeStore
from .creative import CreativeDirector
from .creative_provider import from_config
from .creative_contract import initial_memory
from .creative_media import produce


def reserve_next(store,key,director,brief,approved=None):
    old=store.by_run(key)
    if old:return old
    pending=store.db.execute("SELECT * FROM episodes WHERE status!='verified' ORDER BY uid LIMIT 1").fetchone()
    if pending:
        bible,memory=store.current(pending['series_id'])
        return store.reserve(bible,json.loads(pending['script']),key)
    if approved:
        bible,episode,memory=approved
        store.initialize(bible,memory)
        reserved=store.reserve(bible,episode,key)
        store.save_review(reserved['uid'],{'authorship':'authored_development_example','script_sha256':digest(episode),'live_model_test':False})
        return reserved
    row=store.db.execute('SELECT id FROM series ORDER BY rowid DESC LIMIT 1').fetchone()
    registry=json.loads((ROOT/'config/creative_assets.json').read_text())
    brief=brief+' Use one of these registered environment IDs: '+', '.join(registry['environments'])+'. '+\
        'Use only these prop asset IDs (new character IDs are permitted): '+', '.join(registry['assets'])+'. '+\
        'Use exactly one registered environment per episode. Author fresh plots and dialogue within those resources, not a fixed story template.'
    if row:
        bible,memory=store.current(row['id']);result=director.next_episode(bible,memory,brief)
    else:
        bible=director.new_series(brief);result=director.episode(bible,initial_memory(bible),brief)
    store.initialize(result['bible'],result['input_memory'])
    reserved=store.reserve(result['bible'],result['episode'],key)
    store.save_review(reserved['uid'],{'authorship':'hosted_model','script_sha256':digest(result['episode']),
        'audit':result['audit'],'provider_receipts':result['provider_receipts'],'approval':result['approval'],
        'live_model_test':result['live_api_test']})
    return reserved


def produce_reserved(store,row,out,blender,ffmpeg,settings):
    if row['status']=='verified':
        evidence=json.loads(row['evidence']);path=ROOT/evidence['video']
        if not path.is_file() or file_digest(path)!=evidence['video_sha256']:
            raise FileNotFoundError('Recover verified video artifact; do not create a duplicate episode')
        return evidence
    bible,memory=store.current(row['series_id']);episode=json.loads(row['script'])
    try:
        evidence=produce(bible,episode,memory,out,blender,ffmpeg,tuple(settings['resolution']),
                         settings['fps'],settings['max_seconds'])
        store.commit_verified(row['uid'],evidence,ROOT/evidence['video'])
        return evidence
    except Exception as error:store.fail(row['uid'],error);raise


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['plan','produce','status'])
    p.add_argument('--state',type=Path,required=True);p.add_argument('--run-key',default='manual-creative')
    p.add_argument('--brief',default='Write an original coherent suspense episode with motivated decisions and an earned reveal.')
    p.add_argument('--development',action='store_true');p.add_argument('--approved-example',type=Path)
    p.add_argument('--out',type=Path);p.add_argument('--blender');p.add_argument('--ffmpeg')
    p.add_argument('--settings',type=Path,default=ROOT/'config/creative_production.json')
    a=p.parse_args();state=a.state.resolve();settings=json.loads(a.settings.read_text())
    if settings['paid_services_enabled'] or settings['youtube']['enabled']:p.error('Free-only production with upload outbox only')
    if a.development:
        if not state.is_relative_to((ROOT/'artifacts').resolve()):p.error('Development memory must be isolated under artifacts')
    elif json.loads((ROOT/'config/production_standards.json').read_text())['episode_generation_paused']:
        p.error('Canonical production remains paused pending quality approval')
    if a.approved_example and not a.development:p.error('Authored examples are development tests, never an AI fallback')
    store=CreativeStore(state)
    try:
        if a.command=='status':
            print(json.dumps(store.snapshot(),indent=2));return
        approved=None
        if a.approved_example:
            approved=tuple(json.loads((a.approved_example/n).read_text()) for n in ['series_bible.json','episode_001.json','input_memory.json'])
        provider=from_config(ROOT/'config/creative_director.json')
        director=CreativeDirector(provider)
        row=reserve_next(store,a.run_key,director,a.brief,approved)
        if a.command=='plan':print(json.dumps({'reserved':row['uid'],'status':row['status'],'live_provider_calls':provider.calls}));return
        if not a.out or not a.blender or not a.ffmpeg:p.error('Produce needs --out, --blender and --ffmpeg')
        result=produce_reserved(store,row,a.out,a.blender,a.ffmpeg,settings)
        print(json.dumps(result,indent=2))
    finally:store.close()


if __name__=='__main__':main()
