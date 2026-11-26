"""Reuse verified voice takes by content/identity/delivery rather than cue number."""
import hashlib
import json
import shutil
from pathlib import Path
from .casting import resolve_delivery
from .narration import request_signature


def seed_takes(lines,library,target_audio,sources):
    available={}
    for source in sources:
        for path in Path(source).glob('voice/take_*/voice.json'):
            receipt=json.loads(path.read_text());wav=path.parent/'voice.wav'
            if wav.exists() and hashlib.sha256(wav.read_bytes()).hexdigest()==receipt.get('sha256'):
                available[receipt['signature']]=path.parent
    reused=[]
    for i,line in enumerate(lines):
        role,emotion,delivery=resolve_delivery(library,line)
        voice=library['voices'][library['roles'][role]]
        phrases=line.get('phrases',[{'text':line['text'],'pause_after':.08}])
        signature=request_signature(voice,phrases,delivery.get('pace',1),delivery)
        source=available.get(signature);target=Path(target_audio)/'voice'/f'take_{i:02d}'
        if source and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(source,target,ignore=shutil.ignore_patterns('delivered.wav','delivery.json','pitch*'))
            reused.append({'cue_id':line['id'],'source':str(source),'signature':signature})
    return reused
