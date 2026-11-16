import copy
import json
import math
import os
import shutil
import tempfile
import subprocess
import sys
from unittest.mock import patch
import unittest
from pathlib import Path
import numpy as np
from quality.production_gate import evaluate
from soundstage.events import event_plan,sound,duck_envelope,SR
from soundstage.media import write,normalize

ROOT=Path(__file__).resolve().parents[1]
STANDARDS=json.loads((ROOT/'config/production_standards.json').read_text())


class ProductionGateTests(unittest.TestCase):
    def setUp(self):
        self.facts={'video':{'width':1080,'height':1920,'fps':24,'duration':45,'frames':1080,'constant_frame_rate':True},
            'audio':{'channels':2,'sample_rate':48000,'integrated_lufs':-16,'true_peak_dbtp':-1.5,
                     'speech_over_bed_db':12,'clipped_samples':0,'nonfinite_samples':0,'unexpected_silence':False},
            'render_evidence':{'native':True,'source_frames':1080,'contiguous':True,'duplicate_moving_frames':0,'source_resolution':[1080,1920]},
            'full_decode_passed':True,'voice_identity_approved':True,'scene_continuity_passed':True,'assets_passed':True,
            'narration':[{'start':.2,'actual_end':2,'status':'synthesized','overrun_seconds':0}],
            'captions':[{'start':.2,'end':2,'text':'It knows her name.'}],'media_sha256':'a'*64}
        self.review={'reviewed_by':'test human reviewer','media_sha256':'a'*64,
                     'checks':{name:'approved' for name in STANDARDS['required_human_reviews']}}

    def test_render_success_alone_cannot_make_production_ready(self):
        report=evaluate(self.facts,STANDARDS)
        self.assertEqual(report['status'],'NOT_READY')
        self.assertEqual(len(report['pending_human_reviews']),6)
        self.assertFalse(report['public_publishing_allowed'])

    def test_complete_review_never_enables_disabled_publishing(self):
        report=evaluate(self.facts,STANDARDS,self.review)
        self.assertEqual(report['status'],'READY')
        self.assertFalse(report['public_publishing_allowed'])

    def test_stale_review_or_bad_voice_identity_fails(self):
        self.review['media_sha256']='b'*64
        self.assertEqual(evaluate(self.facts,STANDARDS,self.review)['status'],'NOT_READY')
        self.review['media_sha256']='a'*64
        self.facts['voice_identity_approved']=False
        self.assertIn('voice_identity_not_approved',evaluate(self.facts,STANDARDS,self.review)['technical_failures'])

    def test_low_fps_inside_24_fps_container_is_rejected(self):
        self.facts['render_evidence']['source_frames']=90
        report=evaluate(self.facts,STANDARDS,self.review)
        self.assertIn('native_animation_not_proven',report['technical_failures'])

    def test_average_24_fps_with_irregular_timestamps_is_not_accepted(self):
        self.facts['video']['constant_frame_rate']=False
        self.assertIn('constant_frame_cadence_not_verified',evaluate(self.facts,STANDARDS,self.review)['technical_failures'])

    def test_upscaled_preview_cannot_pass_as_native_hd(self):
        self.facts['render_evidence']['source_resolution']=[180,320]
        self.assertIn('native_render_resolution_not_proven',evaluate(self.facts,STANDARDS,self.review)['technical_failures'])

    def test_duplicates_clipping_loudness_and_missing_assets_fail(self):
        self.facts['render_evidence']['duplicate_moving_frames']=2
        self.facts['audio'].update(clipped_samples=4,true_peak_dbtp=.2,integrated_lufs=-24)
        self.facts['assets_passed']=False
        failures=evaluate(self.facts,STANDARDS,self.review)['technical_failures']
        self.assertTrue({'duplicate_moving_frames_not_verified','clipped_or_invalid_audio','true_peak','integrated_loudness','assets_not_verified'}<=set(failures))

    def test_narration_overrun_and_unreadable_captions_fail(self):
        self.facts['narration'][0]['overrun_seconds']=.7
        self.facts['captions'][0]['end']=.3
        failures=evaluate(self.facts,STANDARDS,self.review)['technical_failures']
        self.assertIn('narration_presence_or_sync',failures)
        self.assertIn('caption_timing_or_readability',failures)

    def test_cli_pause_stops_new_episode_before_creating_story_database(self):
        with tempfile.TemporaryDirectory() as name:
            state=Path(name)/'should_not_exist.sqlite3'
            result=subprocess.run([sys.executable,'-m','autonomy.pipeline','plan','--state',str(state)],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('paused for Episode 3 quality review',result.stderr)
            self.assertFalse(state.exists())


class SoundDesignTests(unittest.TestCase):
    def test_paid_narration_is_blocked_before_any_network_call(self):
        from soundstage.narration import Narrator
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(PermissionError):
                Narrator({'provider':'elevenlabs','voice_id':'unapproved'},'unused')
            network.assert_not_called()

    def test_doors_and_step_sounds_follow_authored_animation_keys(self):
        c=json.loads((ROOT/'episodes/episode_001.json').read_text())
        events=event_plan(c)
        door=next(e for e in events if e['category']=='doors')
        self.assertEqual((door['start'],door['end']),(29.5,35.5))
        impact=next(e for e in events if e['category']=='impact')
        self.assertEqual(impact['start'],c['effects']['impact_time'])
        self.assertTrue(all(0<=e['start']<e['end']<=45 for e in events))

    def test_ducking_reduces_bed_before_speech_and_recovers_smoothly(self):
        envelope=duck_envelope(SR*3,[(1,2)],12)
        self.assertAlmostEqual(envelope[SR],10**(-12/20),places=5)
        self.assertEqual(envelope[0],1)
        self.assertEqual(envelope[-1],1)
        self.assertLess(np.max(np.abs(np.diff(envelope))),.001)

    def test_original_effects_are_repeatable_finite_and_faded(self):
        for category in ['environment','footstep','movement','mechanical','doors','radio','alarm','impact','transition','cliffhanger']:
            a=sound(category,.25,seed=77)
            self.assertTrue(np.array_equal(a,sound(category,.25,seed=77)))
            self.assertTrue(np.isfinite(a).all())
            self.assertEqual(a[0],0)

    def test_measured_stereo_normalization_integration(self):
        ffmpeg=shutil.which('ffmpeg')
        local=ROOT/'artifacts/tooling/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v9.0.2.exe'
        if not ffmpeg and local.exists(): ffmpeg=str(local)
        if not ffmpeg: self.skipTest('FFmpeg integration requires the production tool')
        with tempfile.TemporaryDirectory() as name:
            t=np.arange(SR*4)/SR
            wave=.04*np.sin(2*math.pi*220*t)
            path=Path(name)
            write(path/'input.wav',np.column_stack((wave,wave)))
            result=normalize(path/'input.wav',path/'output.wav',ffmpeg)
            self.assertLess(abs(result['input_i']+16),1)
            self.assertLessEqual(result['input_tp'],-1)


if __name__=='__main__':
    unittest.main()
