"""A real audio bridge and a capability-gated, portable Blender storyboard.

The legacy lift compiler is never asked to disguise a different world. Named
assets must be registered before a storyboard can become a Blender scene.
"""
import copy
import json
from .contracts import ROOT,digest
from .creative_contract import validate_episode
from soundstage.voice_contract import freeze_cast,validate_cast_lock


def compile_creative(ep,bible,memory,registry=None,voice_library=None):
    review=validate_episode(ep,bible,memory)
    registry=registry if registry is not None else json.loads((ROOT/'config/creative_assets.json').read_text())
    library=voice_library if voice_library is not None else json.loads((ROOT/'config/voice_cast_local.json').read_text())
    lock=freeze_cast(library,bible['id'])
    validate_cast_lock(memory['voice_cast'],library,bible['id'])
    required={asset for env in bible['environments'] for asset in env['required_assets']}
    required.update(c['id'] for c in bible['characters'])
    bindings=copy.deepcopy(registry['assets'])
    for character in bible['characters']:
        bindings.setdefault(character['id'],{'factory':'character','quality':'development_blockout'})
    missing=sorted(required-set(bindings))
    settings={e['id'] for e in bible['environments']}
    missing_worlds=sorted(settings-set(registry['environments']))
    multi_world=len({shot['environment_id'] for shot in ep['shots']})>1
    audio={'duration':45,'fps':24,'title':ep['title'],'narration':copy.deepcopy(ep['narration']),
        'narrative_treatment':copy.deepcopy(ep['suspense']),
        'sound_events':copy.deepcopy(ep['sound_events']),
        'production':{'series_id':bible['id'],'ordinal':ep['episode'],'script_sha256':digest(ep)},
        'audio_production':{'schema':3,'narrator_settings':'config/voice_cast_local.json','cast_lock':lock}}
    storyboard={'schema':1,'fps':24,'duration':45,'resolution':[720,1280],
        'series_id':bible['id'],'script_sha256':digest(ep),'shots':copy.deepcopy(ep['shots']),
        'required_assets':sorted(required),'environments':copy.deepcopy(bible['environments']),
        'asset_bindings':{a:copy.deepcopy(bindings[a]) for a in required if a in bindings},
        'environment_bindings':{e:copy.deepcopy(registry['environments'][e]) for e in settings if e in registry['environments']},
        'readiness':{'renderable':not missing and not missing_worlds and not multi_world,'missing_assets':missing,
                     'unsupported_multi_world_cut':multi_world,
                     'missing_environments':missing_worlds,'animation_mapping_verified':False}}
    return {'audio_score':audio,'blender_storyboard':storyboard,'narrative_review':review}


def require_renderable(storyboard):
    if not storyboard['readiness']['renderable']:
        raise ValueError('Missing registered assets/environments; the elevator renderer cannot substitute them')
    return storyboard
