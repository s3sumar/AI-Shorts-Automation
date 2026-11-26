"""Portable creative memory; restoring/exporting never advances an episode.

Proposed memory is not a verified production checkpoint. This wrapper is for
explicitly accepted input state; production review outputs never auto-install it.
"""
import copy
from .contracts import digest
from .creative_contract import validate_bible,validate_memory


def pack(bible,memory):
    validate_bible(bible);validate_memory(memory,bible)
    state={'bible':copy.deepcopy(bible),'memory':copy.deepcopy(memory)}
    return {'format':1,'sha256':digest(state),**state}


def unpack(value):
    if value.get('format')!=1 or value.get('sha256')!=digest({k:value[k] for k in ['bible','memory']}):
        raise ValueError('Creative memory checksum mismatch')
    validate_bible(value['bible']);validate_memory(value['memory'],value['bible'])
    return copy.deepcopy(value['bible']),copy.deepcopy(value['memory'])
