import json
import unittest
from pathlib import Path
from autonomy.checkpoint import unpack
from autonomy.compiler import compile_plan
from quality.plan import segments,interpolation_filter

ROOT=Path(__file__).resolve().parents[1]


class QualityTests(unittest.TestCase):
    def setUp(self):
        seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
        plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
        self.config=compile_plan(plan,json.loads((ROOT/'config/cloud_preview.json').read_text()))

    def test_native_clip_covers_all_240_output_frames(self):
        parts=segments(self.config,26,10,'native')
        self.assertEqual([f for p in parts for f in p['frames']],list(range(625,865)))
        self.assertEqual(sum(p['output_frames'] for p in parts),240)

    def test_hybrid_never_samples_across_camera_cuts(self):
        parts=segments(self.config,0,45,'hybrid')
        for part in parts:
            shot=next(s for s in self.config['shots'] if s['id']==part['shot'])
            self.assertGreaterEqual((min(part['frames'])-1)/24,shot['start'])
            self.assertLess((max(part['frames'])-1)/24,shot['end'])
        self.assertEqual(sum(p['output_frames'] for p in parts),1080)
        self.assertLess(sum(len(p['frames']) for p in parts),800)

    def test_impacts_and_blackout_boundaries_use_native_frames(self):
        parts=segments(self.config,26,10,'hybrid')
        self.assertTrue(all(p['fps']==24 for p in parts if p['shot']=='impact_reaction'))
        self.assertIn(round(26.55*24)/24,{p['start'] for p in parts})

    def test_invalid_windows_do_not_render_or_advance_state(self):
        for start,duration in [(-1,10),(40,10),(0,0),(0,.01)]:
            with self.assertRaises(ValueError):
                segments(self.config,start,duration,'native')

    def test_interpolation_has_padding_and_exact_output_length(self):
        value=interpolation_filter(12,120)
        self.assertIn('scd=fdiff',value)
        self.assertIn('tpad=',value)
        self.assertIn('trim=end_frame=120',value)

    def test_display_changes_split_hybrid_and_black_uses_reusable_plate(self):
        parts=segments(self.config,0,45,'hybrid')
        starts={p['start'] for p in parts}
        for t,value in self.config['floor_events']:
            if 0<t<45:
                self.assertIn(round(t*24)/24,starts)
        black=[p for p in parts if p['shot']=='black']
        self.assertEqual(len(black),1)
        self.assertEqual(len(black[0]['frames']),1)
        self.assertEqual(black[0]['output_frames'],48)

    def test_cloud_benchmark_cannot_write_story_state_or_publish(self):
        # The benchmark must never gain the production workflow's write token.
        text=(ROOT/'.github/workflows/quality_benchmark.yml').read_text()
        self.assertIn('contents: read',text)
        self.assertIn('github.event.repository.private == false',text)
        for forbidden in ['contents: write','schedule:','pipeline produce','cloud_checkpoint.py',
                          'cloud_private_upload','execute-private','GH_TOKEN','secrets.']:
            self.assertNotIn(forbidden,text)
        script=(ROOT/'tools/benchmark_quality.py').read_text()
        self.assertNotIn('Memory(',script)
        self.assertNotIn('commit_verified(',script)


if __name__=='__main__':
    unittest.main()
