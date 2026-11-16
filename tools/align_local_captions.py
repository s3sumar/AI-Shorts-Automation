"""Optional CPU-only word alignment of our own narration stem. Never copies a reference transcript."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from soundstage.captions import align_phrases,ass


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--audio-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args()
    sys.path.insert(0,str(ROOT/'artifacts/reference_tooling'))
    from faster_whisper import WhisperModel
    audio_dir=a.audio_dir.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=subprocess.run([a.ffmpeg,'-v','error','-i',str(audio_dir/'narration_stem.wav'),'-f','f32le','-ac','1','-ar','16000','-'],capture_output=True,check=True).stdout
    audio=np.frombuffer(raw,dtype='<f4').copy();audio*=.8/max(float(np.max(np.abs(audio))),1e-6)
    model=WhisperModel('tiny.en',device='cpu',compute_type='int8',cpu_threads=4,download_root=str(ROOT/'artifacts/reference_models'))
    segments,_=model.transcribe(audio,language='en',word_timestamps=True,vad_filter=True,condition_on_previous_text=False,beam_size=5)
    words=[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for s in segments for w in s.words]
    manifest=json.loads((audio_dir/'audio_manifest.json').read_text())
    result=align_phrases(manifest['captions'],words)
    (out/'word_alignment.json').write_text(json.dumps(result,indent=2))
    (out/'captions.ass').write_text(ass(result['captions']),encoding='utf-8-sig')
    print(json.dumps({'caption_chunks':len(result['captions']),'fallback_phrases':len(result['fallback_phrases']),
                      'requires_human_review':True,'reference_audio_used':False},indent=2))
