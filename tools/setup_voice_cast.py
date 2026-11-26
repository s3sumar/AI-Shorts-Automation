"""Explicit, bounded free voice downloads. Synthesis itself never uses a network."""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def setup(settings):
    if settings.get('paid_services_enabled'): raise PermissionError('Paid voice services disabled')
    receipts=[]
    for voice in settings['voices'].values():
        if voice['provider']!='piper': raise ValueError('This installer supports pinned local Piper assets only')
        revision=voice['model_revision'];relative=voice['repository_path']
        if not re.fullmatch('[a-f0-9]{40}',revision) or not re.fullmatch(r'[A-Za-z0-9_/-]+/',relative):
            raise ValueError('Pinned safe repository path required')
        model=(ROOT/voice['model']).resolve()
        if not model.is_relative_to((ROOT/'artifacts/audio_models').resolve()): raise ValueError('Model must stay under ignored audio_models')
        model.parent.mkdir(parents=True,exist_ok=True)
        for name,expected in [(model.name,voice['model_sha256']),(model.name+'.json',voice.get('config_sha256')),('MODEL_CARD',None)]:
            target=model.parent/name
            if not target.exists():
                url=f'https://huggingface.co/rhasspy/piper-voices/resolve/{revision}/{relative}{name}'
                temp=target.with_suffix(target.suffix+'.download')
                with urllib.request.urlopen(url,timeout=60) as response,temp.open('wb') as stream:
                    count=0
                    while block:=response.read(1024*1024):
                        count+=len(block)
                        if count>160*1024*1024: raise ValueError('Voice download exceeds 160 MiB limit')
                        stream.write(block)
                if expected and hashlib.sha256(temp.read_bytes()).hexdigest()!=expected: raise ValueError('Voice download checksum mismatch')
                temp.replace(target)
            if expected and hashlib.sha256(target.read_bytes()).hexdigest()!=expected: raise ValueError('Existing voice asset checksum mismatch; preserve and review')
        receipt={'voice_id':voice['voice_id'],'model_sha256':voice['model_sha256'],'revision':revision,
                 'dataset_license':voice['dataset_license'],'source':f'https://huggingface.co/rhasspy/piper-voices/blob/{revision}/{relative}MODEL_CARD'}
        (model.parent/'cast_provenance.json').write_text(json.dumps(receipt,indent=2))
        receipts.append(receipt);print('LOCAL VOICE VERIFIED: '+voice['voice_id'],flush=True)
    return receipts


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--settings',type=Path,default=ROOT/'config/voice_cast_local.json')
    a=p.parse_args();setup(json.loads(a.settings.read_text()))
