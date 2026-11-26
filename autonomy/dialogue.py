"""Role-based dialogue for the supported story grammar, independent of episode number."""
import json
from .contracts import ROOT
from soundstage.voice_contract import freeze_cast,validate_cast_lock,validate_dialogue

DEFAULT_CAST='config/voice_cast_local.json'


def initial_voice_lock(series_id,library=None):
    library=library or json.loads((ROOT/DEFAULT_CAST).read_text())
    registry=ROOT/'config/series_voice_casts.json'
    locked=json.loads(registry.read_text()).get('series',{}).get(series_id) if registry.exists() else None
    if locked:
        validate_cast_lock(locked,library,series_id)
        return locked
    return freeze_cast(library,series_id)


def role_dialogue(plan):
    """The same causal screenwriter serves old plans without authored role cues."""
    from .screenwriter import draft_story
    return validate_dialogue(draft_story(plan)['narration'])
