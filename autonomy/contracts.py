import hashlib
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    temp.replace(path)


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9_]{1,64}',value):
        raise ValueError('Invalid asset or episode identifier')
    return value


def validate_plan(plan):
    identifier(plan['uid'])
    identifier(plan['series_id'])
    if plan['kind'] not in ['arrival','escape']:
        raise ValueError('Unsupported story grammar')
    if not isinstance(plan.get('radio_lines'),list) or len(plan['radio_lines'])!=7 or any(not isinstance(s,str) or not s.strip() or len(s)>120 for s in plan['radio_lines']):
        raise ValueError('Seven short radio lines are required')
    if not isinstance(plan.get('title'),str) or len(plan['title'])>80 or not plan['title'].strip():
        raise ValueError('Invalid title')
    if plan['start_state']['characters']!=plan['end_state']['characters']:
        raise ValueError('Character identity/appearance cannot change mid-episode')
    if plan['environment'] not in ['lift_013','freight_lift']:
        raise ValueError('Unknown environment asset')
    if plan['start_hash']!=digest(plan['start_state']):
        raise ValueError('Invalid continuity precondition')
    for state in [plan['start_state'],plan['end_state']]:
        if state['floor'] not in ['13','-1','0'] or not 0<=state['doors']<=1:
            raise ValueError('Unsupported state')
        for key in ['passenger_position','passenger_head','shadow_position','shadow_head','shadow_leg_l','shadow_leg_r']:
            if len(state[key])!=3 or not all(isinstance(v,(float,int)) and math.isfinite(v) and abs(v)<20 for v in state[key]):
                raise ValueError('Invalid rig state')
    return plan
