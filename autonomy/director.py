"""Continuity-constrained director. Offline grammar or an explicitly selected local LLM.

No cloud inference, API key, model download or paid request is performed.
The local model can author dialogue/title; canon and renderable grammar are enforced.
"""
import copy
import json
import urllib.request
import urllib.parse
from .contracts import digest,validate_plan

CONCEPTS=[
    ('Dead Air Dispatch','A night courier finds a freight lift that delivers messages from tomorrow.','freight_lift','Courier','The Dispatcher','#D5CAB5'),
    ('The Last Archive','An archivist must return a recording before the building remembers it.','lift_013','Archivist','The Keeper','#B9CFD9'),
    ('Second Shift','A night technician receives maintenance calls from an unoccupied floor.','freight_lift','Technician','The Tenant','#C4D0BC'),
]


class LocalModel:
    def __init__(self,model,endpoint='http://127.0.0.1:11434'):
        if not isinstance(model,str) or not model.strip() or len(model)>120:
            raise ValueError('Choose an already-installed local model name')
        parsed=urllib.parse.urlparse(endpoint)
        if parsed.scheme!='http' or parsed.hostname not in ['127.0.0.1','localhost','::1'] or parsed.username or parsed.password:
            raise ValueError('Only a loopback local-model endpoint is permitted')
        self.model,self.endpoint=model,endpoint.rstrip('/')

    def generate(self,prompt):
        request=urllib.request.Request(self.endpoint+'/api/generate',data=json.dumps({
            'model':self.model,'prompt':prompt,'format':'json','stream':False,
            'options':{'temperature':.55,'num_predict':600}}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=60) as response:
            result=json.load(response)
        return json.loads(result['response'])


def initial_state(protagonist='Passenger',antagonist='The Listener',color='#C7D4D9'):
    return {'floor':'13','doors':0,'lighting':'cold','passenger_position':[-.68,-.8,0],
        'passenger_head':[0,0,-.1],'passenger_arms':[0,0,0],
        'shadow_position':[.5,5.4,0],'shadow_head':[0,0,0],'shadow_leg_l':[0,0,0],'shadow_leg_r':[0,0,0],
        'shadow_visible':True,'characters':{'protagonist':{'id':'passenger','name':protagonist,'color':color},
        'antagonist':{'id':'shadow','name':antagonist,'face_revealed':False}},'facts':[],'location':'inside_lift'}


def arrival_end(start):
    s=copy.deepcopy(start)
    s.update(floor='-1',doors=1,lighting='red',passenger_position=[-.9,-.48,0],passenger_head=[-.03,0,2.35],
        passenger_arms=[-.3,.3,0],shadow_position=[.5,4.85,0],shadow_head=[.12,0,-.12],
        shadow_leg_l=[-.08,0,0],shadow_leg_r=[.08,0,0],
        facts=['The lower floor is sealed.','The figure recognizes the passenger.','Its face has not been seen.'])
    return s


def new_series(index,model=None):
    title,premise,environment,protagonist,antagonist,color=CONCEPTS[(index-2)%len(CONCEPTS)]
    title=f'{title}' if index<=4 else f'{title}: Signal {index-1}'
    source='offline_story_grammar'
    if model:
        response=model.generate('Invent an original suspense miniseries. Return JSON with short title and premise. '
            'Setting is an elevator and service corridor. No copyrighted characters. '
            f'Creative seed: {index}; premise direction: {premise}')
        if not isinstance(response.get('title'),str) or not isinstance(response.get('premise'),str):
            raise ValueError('Local model returned an invalid series concept')
        if not 1<=len(response['title'])<=80 or not 1<=len(response['premise'])<=400:
            raise ValueError('Model concept too long')
        title,premise=response['title'],response['premise']
        source='local_llm'
    return {'id':f'series_{index:03d}','title':title,'premise':premise,'season_length':2,
        'environment':environment,'source':source,'canon':initial_state(protagonist,antagonist,color)}


def plan_episode(series,ordinal,global_number,model=None):
    start=copy.deepcopy(series['canon'])
    if ordinal==1:
        kind='arrival'
        end=arrival_end(start)
        title='The Undelivered Signal'
        lines=[f'{start["characters"]["protagonist"]["name"]}. Your delivery is waiting.',
               'Do not take it below ground.', 'The signal is moving.', 'Someone else is on this line.',
               'That floor is sealed.', 'Leave the recording inside.', 'It remembers who sent you.']
        summary='A new transmission draws the protagonist below ground; a faceless presence recognizes them.'
    else:
        kind='escape'
        end=copy.deepcopy(start)
        end.update(floor='0',doors=1,lighting='cold',passenger_position=[-.4,2.35,0],passenger_head=[0,0,2.35],
            passenger_arms=[0,0,0],shadow_visible=False,location='ground_corridor',
            facts=start['facts']+['The presence borrows voices.','Silence and the ground control seal it below.','The passenger leaves at ground level.'])
        title='The Door That Listens'
        lines=['It has learned your voice.','Do not answer it.','Choose ground. Say nothing.',
               'Let the doors close.','Zero. Hold your breath.','The corridor is empty.','Walk out. Do not turn around.']
        summary='The passenger refuses the borrowed voice, seals the presence below, and exits at ground level.'
    source='offline_story_grammar'
    if model:
        result=model.generate('Write original radio dialogue for this fixed suspense scene. Return JSON containing '
            'title and radio_lines (exactly 7 strings, each at most 8 words). Do not alter the plot. '
            +json.dumps({'series':series['title'],'canon':start,'outcome':end,'outline':summary}))
        title=result.get('title','')
        lines=result.get('radio_lines',[])
        if any(len(line.split())>8 for line in lines if isinstance(line,str)):
            raise ValueError('Local model dialogue exceeds timing budget')
        source='local_llm'
    plan={'uid':f'{series["id"]}_e{ordinal:03d}','series_id':series['id'],'series_title':series['title'],
        'ordinal':ordinal,'global_number':global_number,'kind':kind,'title':title,'summary':summary,
        'environment':series['environment'],'source':source,'start_state':start,'end_state':end,
        'start_hash':digest(start),'radio_lines':lines,'season_finale':ordinal==series['season_length']}
    return validate_plan(plan)
