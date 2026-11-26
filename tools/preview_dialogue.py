"""Audio-only preview for any compiled story score and role-based dialogue script."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from soundstage.pipeline import prepare
from soundstage.media import read
from soundstage.voice_contract import freeze_cast,validate_dialogue


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--score',type=Path,required=True)
    p.add_argument('--script',type=Path,required=True)
    p.add_argument('--cast-settings',type=Path,default=ROOT/'config/voice_cast_local.json')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--reuse-audio',type=Path,action='append',default=[],help='Optional verified prior take directories')
    a=p.parse_args();out=a.out.resolve()
    if not out.is_relative_to((ROOT/'artifacts/audio_previews').resolve()): raise ValueError('Use isolated artifacts/audio_previews output')
    out.mkdir(parents=True,exist_ok=True)
    if (out/'validation.json').exists(): raise FileExistsError('Preserve completed previews; choose a new --out')
    c=copy.deepcopy(json.loads(a.score.read_text()))
    script=json.loads(a.script.read_text());library=json.loads(a.cast_settings.read_text())
    c['narration']=validate_dialogue(script['narration'],c['duration'])
    if 'suspense' in script:
        from autonomy.suspense import validate_story
        story_review=validate_story(script['suspense'],c['narration'],c['duration'])
        (out/'story_review.json').write_text(json.dumps(story_review,indent=2))
        c['narrative_treatment']=script['suspense']
    c['title']=script.get('title',c.get('title','Dialogue review'))
    lock=freeze_cast(library,c.get('production',{}).get('series_id',c.get('series_id','standalone')))
    c['audio_production']={'schema':3,'narrator_settings':str(a.cast_settings.resolve()),'cast_lock':lock}
    score_path=out/'episode.json'
    if score_path.exists() and {k:v for k,v in json.loads(score_path.read_text()).items() if k!='captions'}!={k:v for k,v in c.items() if k!='captions'}:
        raise ValueError('Preserve partial takes; use a new revision')
    score_path.write_text(json.dumps(c,indent=2))
    if a.reuse_audio:
        from soundstage.take_cache import seed_takes
        reuse=seed_takes(c['narration'],library,out/'audio',a.reuse_audio)
        (out/'take_reuse.json').write_text(json.dumps(reuse,indent=2))
    print('AUDIO PREVIEW: generating role-based line takes and sound',flush=True)
    manifest=prepare(c,out/'audio',library,a.ffmpeg)
    c['captions']=manifest['captions'];score_path.write_text(json.dumps(c,indent=2))
    (out/'final_dialogue_script.json').write_text(json.dumps(script,indent=2))
    wav=out/'audio/episode_mix.wav'
    with wave.open(str(wav)) as stream:
        assert stream.getnframes()==round(c['duration']*stream.getframerate())
        audio_format={'frames':stream.getnframes(),'sample_rate':stream.getframerate(),'channels':stream.getnchannels()}
    samples=read(wav,a.ffmpeg)
    assert np.isfinite(samples).all() and np.max(np.abs(samples))<1 and np.sqrt(np.mean(samples**2))>.005
    assert all(line['spoken_end']<=line['end'] for line in manifest['narration'])
    used_roles={line.get('role',line['speaker']) for line in c['narration']}
    expected_voices={library['roles'][role] for role in used_roles}
    assert {line['voice_id'] for line in manifest['narration']}==expected_voices
    assert len({line['voice_fingerprint'] for line in manifest['narration']})==len(expected_voices)
    assert len(list((out/'audio/voice').glob('take_*/delivered.wav')))==len(c['narration'])
    assert manifest['caption_fallbacks']==0
    assert all(len(cue['text'])/(cue['end']-cue['start'])<=22 for cue in manifest['captions']), 'Subtitle reading speed exceeds 22 characters/second'
    decoded=subprocess.run([a.ffmpeg,'-v','error','-i',str(wav),'-f','null','-'],capture_output=True,text=True,check=True)
    assert not decoded.stderr.strip()
    mp3=out/'dialogue_and_sound_preview.mp3'
    subprocess.run([a.ffmpeg,'-v','error','-y','-i',str(wav),'-c:a','libmp3lame','-b:a','192k',str(mp3)],check=True)
    subprocess.run([a.ffmpeg,'-v','error','-i',str(mp3),'-f','null','-'],check=True)
    report={'passed':True,'duration':c['duration'],'wav':str(wav),'mp3':str(mp3),'audio_format':audio_format,
        'loudness':manifest['loudness'],'voice_cast':manifest['voice_cast'],'line_count':len(c['narration']),
        'caption_count':len(manifest['captions']),'caption_fallbacks':0,'used_voice_identities':len(expected_voices),
        'wav_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'mp3_sha256':hashlib.sha256(mp3.read_bytes()).hexdigest(),
        'checkpoint_written':False,'three_d_render_started':False,'paid_services_used':False,
        'readiness':'NOT_READY','human_listening_review':'pending',
        'limitations':['Pacing, pitch and tremor controls are not a trained dramatic-emotion model',
                       'Engine-timed subtitles still need pronunciation/listening review',
                       'New dialogue is not canonical until reviewed; existing animation was not rerendered']}
    (out/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
