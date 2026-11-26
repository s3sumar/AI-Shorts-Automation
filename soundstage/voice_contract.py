"""Portable voice identity locks and data-only dialogue validation (no synthesis)."""
import hashlib
import json
import math
import re


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def voice_fingerprint(voice):
    if not re.fullmatch('[a-z0-9_]{1,64}',voice.get('voice_id','')): raise ValueError('Safe stable voice ID required')
    if voice.get('provider')!='piper' or not voice.get('phoneme_alignment'):
        raise ValueError('A cast voice requires local Piper with engine alignment')
    for key in ['model_sha256','config_sha256']:
        if not re.fullmatch('[a-f0-9]{64}',voice.get(key,'')): raise ValueError('Pinned voice and config hashes required')
    return digest({k:voice.get(k) for k in ['voice_id','provider','model_sha256','config_sha256','speaker_id']})


def freeze_cast(library,series_id):
    if library.get('paid_services_enabled'): raise PermissionError('Paid voice services are disabled')
    roles=library['roles']
    if not re.fullmatch('[a-z0-9_]{1,64}',library.get('cast_id','')): raise ValueError('Safe stable cast ID required')
    if any(not re.fullmatch(r'(narrator|protagonist|antagonist|supporting_[a-z0-9_]+)',r) for r in roles):
        raise ValueError('Unknown cast role')
    if not all(r in roles for r in ['narrator','protagonist','antagonist']): raise ValueError('Three primary cast roles required')
    fingerprints={role:voice_fingerprint(library['voices'][key]) for role,key in roles.items()}
    # Distinct identities must mean separate models/speakers, not three aliases.
    sources=[(library['voices'][voice_id]['model_sha256'],library['voices'][voice_id].get('speaker_id')) for voice_id in roles.values()]
    if len(set(sources))!=len(roles): raise ValueError('Narrator and characters require distinct source identities')
    return {'schema':1,'series_id':series_id,'cast_id':library['cast_id'],
            'roles':dict(roles),'fingerprints':fingerprints}


def validate_cast_lock(lock,library,series_id):
    if lock!=freeze_cast(library,series_id):
        raise ValueError('Voice identities changed since the series was cast; explicit recasting is required')


def validate_dialogue(lines,duration=45):
    if not isinstance(lines,list) or not 1<=len(lines)<=40: raise ValueError('One to forty dialogue cues required')
    previous=0
    for line in lines:
        if not isinstance(line,dict): raise ValueError('Dialogue must contain data objects')
        allowed={'id','start','end','speaker','role','emotion','text','phrases','pace','direction'}
        if set(line)-allowed: raise ValueError('Unknown dialogue instruction')
        start,end=line.get('start'),line.get('end')
        if any(isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) for t in [start,end]):
            raise ValueError('Finite dialogue times required')
        if not previous<=start<end<=duration: raise ValueError('Dialogue overlaps or exceeds the episode')
        previous=end
        if not re.fullmatch('[a-z][a-z0-9_]{0,63}',line.get('speaker','')): raise ValueError('Stable speaker ID required')
        role=line.get('role',line['speaker'])
        if not re.fullmatch(r'(narrator|protagonist|antagonist|supporting_[a-z0-9_]+)',role): raise ValueError('Unknown cast role')
        text=line.get('text')
        if not isinstance(text,str) or not text.strip() or len(text)>200 or any(ord(c)<32 for c in text):
            raise ValueError('Bounded plain dialogue text required')
        if line.get('emotion') is not None and not re.fullmatch('[a-z_]{1,32}',line['emotion']): raise ValueError('Invalid emotion')
        if 'pace' in line and not .75<=line['pace']<=1.35: raise ValueError('Pace outside supported range')
        phrases=line.get('phrases',[{'text':text}])
        if not isinstance(phrases,list) or not phrases or len(phrases)>8: raise ValueError('Invalid phrasing')
        if ' '.join(p.get('text','') for p in phrases)!=text: raise ValueError('Phrase text must exactly preserve dialogue')
        for phrase in phrases:
            if set(phrase)-{'text','pause_after'}: raise ValueError('Unknown phrase instruction')
            if not isinstance(phrase.get('pause_after',0),(int,float)) or not 0<=phrase.get('pause_after',0)<=1.5:
                raise ValueError('Invalid phrase pause')
    return lines
