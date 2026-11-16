"""Recheck exact reviewed media; never uploads, approves reviews or edits canon."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quality.production_gate import collect,save_report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--video',type=Path,required=True)
    p.add_argument('--gate',type=Path,required=True)
    p.add_argument('--human-review',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--narrator-settings',type=Path,default=ROOT/'config/narrator_candidate.json')
    a=p.parse_args()
    prior=json.loads(a.gate.read_text())['facts']
    if hashlib.sha256(a.video.read_bytes()).hexdigest()!=prior['media_sha256']:
        raise ValueError('Media changed after evidence collection; rebuild evidence instead of approving stale facts')
    settings=json.loads(a.narrator_settings.read_text())
    facts=collect(a.video,a.ffmpeg,{'narration':prior['narration'],'speech_over_bed_db':prior['audio']['speech_over_bed_db']},
                  prior['render_evidence'],prior['captions'],prior['scene_continuity_passed'],prior['assets_passed'],
                  settings.get('identity_approved',False))
    review=json.loads(a.human_review.read_text()) if a.human_review else None
    report=save_report(a.out,facts,review)
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='READY' else 2)
