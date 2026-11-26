"""Genre-neutral story contracts, epistemic continuity and proposed memory.

No generated code is evaluated. Creative instructions stay data. These checks
audit declared structure; a model critic and human review address prose meaning.
"""
import copy
import json
import math
from .contracts import ROOT,digest,identifier
from .suspense import validate_story
from soundstage.voice_contract import validate_dialogue

EMOTIONS={'storytelling','uneasy','afraid','desperate','terrified','resolute','unsettling',
          'curious','hopeful','urgent','awed','sad','amused'}
MOVES={'static','dolly','pan','orbit'}
FRAMING={'wide','medium','close','detail'}


def text(value,limit=1000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 and c!='\n' for c in value):
        raise ValueError('Bounded nonempty plain story text required')
    return value


def validate_bible(b):
    if b['schema']!=1: raise ValueError('Unsupported creative series schema')
    identifier(b['id']);text(b['title'],80);text(b['genre'],80)
    if not b['id'].startswith('creative_'): raise ValueError('New creative series use a separate creative_ namespace')
    for k in ['logline','central_conflict','theme']: text(b[k])
    chars=b['characters']
    if len(chars)!=2 or {c['role'] for c in chars}!={'protagonist','antagonist'}:
        raise ValueError('Two stable characters plus the external narrator are currently supported')
    if len({c['id'] for c in chars})!=2 or any(c['id']=='narrator' for c in chars): raise ValueError('Unique cast IDs required')
    for c in chars:
        identifier(c['id'])
        for k in ['name','personality','desire','flaw','voice_direction']: text(c[k],500)
    environments=b['environments']
    if not 1<=len(environments)<=4 or len({e['id'] for e in environments})!=len(environments): raise ValueError('One to four distinct settings required')
    for e in environments:
        identifier(e['id']);text(e['description']);
        if not isinstance(e['required_assets'],list) or not e['required_assets']: raise ValueError('Explicit environment assets required')
        for asset in e['required_assets']: identifier(asset)
    for key,value in b['initial_facts'].items(): identifier(key);text(value['statement']);_status(value)
    for c in chars:
        if not set(c['initial_knows'])<=set(b['initial_facts']): raise ValueError('Character initial knowledge is unknown')
    mysteries=b['mysteries']
    if not mysteries: raise ValueError('Series needs a central unresolved question')
    for k,v in mysteries.items():
        identifier(k);text(v['question']);text(v['writer_only_answer'])
        if type(v['reveal_episode'])!=int or v['reveal_episode']<1: raise ValueError('Secret reveal episode required')
    arc=b['season_arc']
    if not 3<=len(arc)<=8 or [a['episode'] for a in arc]!=list(range(1,len(arc)+1)):
        raise ValueError('Three to eight consecutive season episodes required')
    for a in arc:
        for k in ['goal','conflict','turn','payoff']: text(a[k])
    if any(v['reveal_episode']>len(arc) for v in mysteries.values()): raise ValueError('Season mystery has no scheduled resolution')
    if not any(a.get('resolves') for a in arc): raise ValueError('Season arc must resolve a planted mystery')
    for a in arc:
        if not set(a.get('resolves',[]))<=set(mysteries): raise ValueError('Arc resolves an unknown mystery')
    return b


def _status(fact):
    if fact.get('status') not in ['observed','claim']: raise ValueError('Distinguish an observation from a spoken claim')


def initial_memory(bible):
    validate_bible(bible)
    from soundstage.voice_contract import freeze_cast
    library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
    return {'schema':1,'series_id':bible['id'],'bible_sha256':digest(bible),'next_episode':1,
        'voice_cast':freeze_cast(library,bible['id']),
        'facts':copy.deepcopy(bible['initial_facts']),'beliefs':{},'audience_knows':[],'audience_believes':[],
        'characters':{c['id']:{'knows':list(c['initial_knows']),'beliefs':[],
            'goal':{'id':'goal_'+c['id'],'description':c['desire']}} for c in bible['characters']},
        'unresolved':list(bible['mysteries']),'resolved':[],'history':[]}


def validate_memory(memory,bible):
    if memory['schema']!=1 or memory['series_id']!=bible['id'] or memory['bible_sha256']!=digest(bible): raise ValueError('Memory belongs to another series/bible')
    if type(memory['next_episode'])!=int or not 1<=memory['next_episode']<=len(bible['season_arc'])+1: raise ValueError('Invalid next episode')
    if set(memory['characters'])!={c['id'] for c in bible['characters']}: raise ValueError('Memory recasts a character')
    if memory['voice_cast'].get('series_id')!=bible['id']: raise ValueError('Voice cast belongs to another series')
    for k,value in memory['facts'].items(): identifier(k);text(value['statement']);_status(value)
    if not set(memory['audience_knows'])<=set(memory['facts']): raise ValueError('Memory invents audience knowledge')
    if not set(memory['audience_believes'])<=set(memory['beliefs']): raise ValueError('Memory invents audience beliefs')
    for value in memory['characters'].values():
        if not set(value['knows'])<=set(memory['facts']) or not set(value['beliefs'])<=set(memory['beliefs']): raise ValueError('Memory references unknown knowledge or belief')
        identifier(value['goal']['id']);text(value['goal']['description'])
    if set(memory['unresolved']) & set(memory['resolved']) or set(memory['unresolved']+memory['resolved'])!=set(bible['mysteries']): raise ValueError('Memory loses or duplicates a mystery')
    if len(memory['history'])!=memory['next_episode']-1 or [h['episode'] for h in memory['history']]!=list(range(1,memory['next_episode'])): raise ValueError('Memory episode history is inconsistent')
    for k,v in bible['initial_facts'].items():
        if memory['facts'].get(k)!=v: raise ValueError('Memory rewrites a world fact')
    return memory


def validate_episode(ep,bible,memory):
    validate_bible(bible);validate_memory(memory,bible)
    if ep['schema']!=1 or ep['duration']!=45 or ep['series_id']!=bible['id']: raise ValueError('Creative episode must be 45 seconds in this series')
    if ep['episode']!=memory['next_episode'] or ep['episode']>len(bible['season_arc']): raise ValueError('Wrong episode number or completed season')
    if ep['prior_memory_sha256']!=digest(memory): raise ValueError('Stale story memory')
    text(ep['title'],80);text(ep['synopsis'])
    lines=validate_dialogue(ep['narration']);model=ep['suspense']
    dialogue_sha=digest([l['text'].casefold().strip() for l in lines])
    if any(h.get('dialogue_sha256')==dialogue_sha for h in memory['history']): raise ValueError('Episode repeats a prior complete script')
    roles={c['role']:c['id'] for c in bible['characters']};roles['narrator']='narrator'
    for line in lines:
        if line['speaker']!=roles.get(line['role']) or line.get('emotion') not in EMOTIONS: raise ValueError('Uncast voice or unsupported emotion')
        pauses=sum(p.get('pause_after',0) for p in line.get('phrases',[]))
        window=line['end']-line['start']-pauses
        if window<=0 or len(line['text'].split())>max(2,window*3.1): raise ValueError('Dialogue exceeds preliminary timing budget')
    if {l['role'] for l in lines}!={'narrator','protagonist','antagonist'}: raise ValueError('Distinct narrator and two character voices required')
    hero=roles['protagonist'];other=roles['antagonist']
    initial=model['initial']
    if set(initial['audience_knows'])!=set(memory['audience_knows']) or set(initial['protagonist_knows'])!=set(memory['characters'][hero]['knows']): raise ValueError('Episode rewrites starting knowledge')
    if set(initial['audience_believes'])!=set(memory['audience_believes']): raise ValueError('Episode rewrites audience beliefs')
    if set(initial['protagonist_believes'])!=set(memory['characters'][hero]['beliefs']) or initial['goal']!=memory['characters'][hero]['goal']['id']:
        raise ValueError('Episode rewrites protagonist beliefs or immediate goal')
    if model['goals'].get(initial['goal'])!=memory['characters'][hero]['goal']['description']: raise ValueError('Episode redefines an existing goal')
    for k,v in memory['facts'].items():
        if model['facts'].get(k)!=v: raise ValueError('Episode silently rewrites or drops an established fact/claim')
    for k,v in memory['beliefs'].items():
        if model['beliefs'].get(k)!=v: raise ValueError('Episode silently rewrites a belief')
    for k,v in model['facts'].items():
        identifier(k);_status(v)
        if v.get('secret_id'):
            secret=bible['mysteries'].get(v['secret_id'])
            if not secret or ep['episode']<secret['reveal_episode']: raise ValueError('Writer-only secret revealed in the wrong episode')
    review=validate_story(model,lines)
    shots=ep['shots'];end=0
    if not 5<=len(shots)<=18: raise ValueError('Five to eighteen connected shots required')
    environment_ids={e['id'] for e in bible['environments']}
    assets={a for e in bible['environments'] for a in e['required_assets']}
    shot_ids=set();by_cue={l['id']:l for l in lines};coverage={k:[] for k in by_cue}
    for shot in shots:
        identifier(shot['id'])
        if shot['id'] in shot_ids: raise ValueError('Duplicate shot ID')
        shot_ids.add(shot['id'])
        if not end==shot['start']<shot['end']<=45: raise ValueError('Shot timeline gap or overlap')
        end=shot['end']
        if shot['environment_id'] not in environment_ids or shot['framing'] not in FRAMING or shot['camera_move'] not in MOVES: raise ValueError('Unsupported shot instruction')
        if shot['subject'] not in (set(roles.values())-{'narrator'})|assets: raise ValueError('Shot targets an undeclared physical character/prop')
        for k in ['action','motivation','transition']: text(shot[k])
        for performance in shot.get('performances',[]):
            if performance['actor'] not in set(roles.values())-{'narrator'} or performance['action'] not in ['idle','look','reach','point','recoil','walk']:
                raise ValueError('Unsupported typed character performance')
            if not shot['start']<=performance['start']<performance['end']<=shot['end']: raise ValueError('Performance falls outside shot')
            if performance.get('target',performance['actor']) not in (set(roles.values())-{'narrator'})|assets: raise ValueError('Unknown physical performance target')
            if performance['action']=='walk' and (len(performance.get('position',[]))!=3 or any(type(v) not in [int,float] or not math.isfinite(v) or abs(v)>8 for v in performance['position'])): raise ValueError('Walk position outside stage')
        if not set(shot['reveals'])<=set(model['facts']): raise ValueError('Shot reveals unknown information')
        for fact in shot['reveals']:
            if model['facts'][fact].get('earliest_reveal',0)>shot['start']: raise ValueError('Camera spoils a protected reveal')
        if not shot.get('cue_ids') or not set(shot['cue_ids'])<={l['id'] for l in lines}: raise ValueError('Shot needs a linked dialogue cue')
        for cue_id in shot['cue_ids']:
            cue=by_cue[cue_id];a=max(cue['start'],shot['start']);b=min(cue['end'],shot['end'])
            if a>=b: raise ValueError('Shot links dialogue outside its time window')
            coverage[cue_id].append((a,b))
    if end!=45: raise ValueError('Shot plan does not cover 45 seconds')
    for event in ep.get('visual_events',[]):
        if event['target'] not in assets or not 0<=event['at']<=45: raise ValueError('Invalid visual event target/time')
        prop=event['property'];value=event['value']
        if prop=='visible':
            if type(value)!=bool: raise ValueError('Visibility requires boolean')
        elif prop=='location':
            if not isinstance(value,list) or len(value)!=3 or any(type(v) not in [int,float] or not -8<=v<=8 for v in value): raise ValueError('Invalid visual placement')
        elif prop=='text':text(value,100)
        else:raise ValueError('Unsupported visual property')
    all_cues={cue for shot in shots for cue in shot['cue_ids']}
    if all_cues!={l['id'] for l in lines}: raise ValueError('A dialogue cue has no visual coverage')
    for cue_id,pieces in coverage.items():
        cursor=by_cue[cue_id]['start']
        for a,b in sorted(pieces):
            if a>cursor: raise ValueError('A spoken line has a gap in visual coverage')
            cursor=max(cursor,b)
        if cursor<by_cue[cue_id]['end']: raise ValueError('A spoken line ends without visual coverage')
    # Secondary characters also have time-dependent knowledge, not omniscience.
    side=ep['counterpart_state']
    if side['id']!=other: raise ValueError('Counterpart identity changed')
    known=set(memory['characters'][other]['knows']);events=side['learns']
    if any(not 0<=e['at']<=45 or e['fact'] not in model['facts'] or not e.get('evidence') for e in events): raise ValueError('Invalid counterpart information event')
    if set(ep['line_knowledge'])!={l['id'] for l in lines if l['role']!='narrator'}: raise ValueError('Character dialogue requires knowledge dependencies')
    for line in lines:
        if line['role']=='narrator': continue
        available=set(memory['characters'][line['speaker']]['knows'])
        if line['speaker']==other:
            available.update(e['fact'] for e in events if e['at']<=line['start'])
        else:
            for beat in model['beats']:
                available.update(e['fact'] for e in beat.get('reveals',[]) if 'protagonist' in e['to'] and e['at']<=line['start'])
        if not set(ep['line_knowledge'][line['id']])<=available: raise ValueError('Character speaks from unavailable knowledge')
    if not set(side['beliefs'])<=set(model['beliefs']) or side['goal'] not in model['goals']: raise ValueError('Counterpart beliefs/goal are not modeled')
    if not set(ep['resolved_mysteries'])<=set(memory['unresolved']): raise ValueError('Cannot resolve an unknown/already resolved mystery')
    scheduled=set(bible['season_arc'][ep['episode']-1].get('resolves',[]))
    if set(ep['resolved_mysteries'])!=scheduled: raise ValueError('Episode loses the scheduled season payoff')
    for event in ep['sound_events']:
        if event['category'] not in {'environment','footstep','movement','mechanical','doors','radio','alarm','impact','transition','cliffhanger'} or not 0<=event['start']<event['end']<=45 or not 0<=event['gain']<=1: raise ValueError('Unsupported sound instruction')
    return review


def propose_memory(ep,bible,memory):
    review=validate_episode(ep,bible,memory)
    proposed=copy.deepcopy(memory);proposed['next_episode']+=1
    proposed['facts']=copy.deepcopy(ep['suspense']['facts']);proposed['beliefs']=copy.deepcopy(ep['suspense']['beliefs'])
    state=review['final_state'];proposed['audience_knows']=state['audience_knows'];proposed['audience_believes']=state['audience_believes']
    hero=next(c['id'] for c in bible['characters'] if c['role']=='protagonist')
    proposed['characters'][hero]={'knows':state['protagonist_knows'],'beliefs':state['protagonist_believes'],
        'goal':{'id':state['goal'],'description':ep['suspense']['goals'][state['goal']]}}
    side=ep['counterpart_state'];target=proposed['characters'][side['id']]
    target['knows']=sorted(set(target['knows'])|{e['fact'] for e in side['learns']});target['beliefs']=side['beliefs']
    target['goal']={'id':side['goal'],'description':ep['suspense']['goals'][side['goal']]}
    proposed['resolved']+=ep['resolved_mysteries'];proposed['unresolved']=[q for q in memory['unresolved'] if q not in proposed['resolved']]
    proposed['history'].append({'episode':ep['episode'],'script_sha256':digest(ep),'title':ep['title'],
        'dialogue_sha256':digest([l['text'].casefold().strip() for l in ep['narration']]),
        'summary':ep['synopsis'],'open_episode_questions':review['unresolved']})
    validate_memory(proposed,bible)
    return proposed
