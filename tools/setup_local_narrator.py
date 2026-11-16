"""Explicit free model download; SHA-verified, ignored locally, never a paid request."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    settings=json.loads((ROOT/'config/narrator_candidate.json').read_text())
    destination=ROOT/settings['model']
    destination.parent.mkdir(parents=True,exist_ok=True)
    base='https://huggingface.co/rhasspy/piper-voices/resolve/'+settings['model_revision']+'/en/en_US/ljspeech/high/'
    for name in ['MODEL_CARD',destination.name+'.json',destination.name]:
        target=destination.parent/name
        if not target.exists():
            temporary=target.with_suffix(target.suffix+'.download')
            with urllib.request.urlopen(base+name,timeout=120) as response,temporary.open('wb') as stream:
                while block:=response.read(1024*1024): stream.write(block)
            if name==destination.name and hashlib.sha256(temporary.read_bytes()).hexdigest()!=settings['model_sha256']:
                raise ValueError('Downloaded narrator checksum mismatch; model was not activated')
            temporary.replace(target)
    assert hashlib.sha256(destination.read_bytes()).hexdigest()==settings['model_sha256']
    print('Verified local narrator candidate. Human voice approval is still pending.')


if __name__=='__main__':
    main()
