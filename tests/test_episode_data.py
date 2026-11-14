"""Contract checks independent of Blender, including narration and preview readability."""
import json
import unittest
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'episodes/episode_001.json').read_text(encoding='utf-8'))


class EpisodeContract(unittest.TestCase):
    def test_floor_story_and_readability(self):
        events=C['floor_events']
        self.assertEqual([v for _,v in events[:14]],[str(i) for i in range(13,-1,-1)])
        self.assertEqual(events[-1][1],'-1')
        for i,(t,v) in enumerate(events[:14]):
            self.assertGreaterEqual((events[i+1][0]-t)*C['preview']['fps'],3,'Number too brief at preview rate: '+v)
        intervals=[events[i+1][0]-events[i][0] for i in range(3,13)]
        self.assertTrue(all(a>b for a,b in zip(intervals,intervals[1:])))

    def test_shots_cover_master_without_gaps(self):
        shots=C['shots']
        self.assertEqual(shots[0]['start'],0)
        self.assertEqual(shots[-1]['end'],45)
        for a,b in zip(shots,shots[1:]):
            self.assertEqual(a['end'],b['start'])
        self.assertEqual(C['fps']%C['preview']['fps'],0)
        self.assertGreaterEqual(len(shots),10)

    def test_each_spoken_line_has_a_caption(self):
        for voice in C['narration']:
            matches=[caption for caption in C['captions'] if caption['text'].replace('\n',' ')==voice['text']]
            self.assertEqual(len(matches),1)
            self.assertEqual((matches[0]['start'],matches[0]['end']),(voice['start'],voice['end']))

    def test_generated_audio_contract(self):
        out=ROOT/'artifacts/episode_001/audio'
        if not (out/'episode_mix.wav').exists():
            self.skipTest('Run tools/prepare_audio.py for generated audio checks')
        report=json.loads((out/'audio_manifest.json').read_text())
        self.assertEqual(report['duration'],45)
        self.assertLessEqual(report['peak'],.94)
        self.assertEqual(len(report['narration']),7)
        self.assertTrue(all(line['status']=='synthesized' for line in report['narration']))
        for line in report['narration']:
            self.assertLessEqual(line['source_duration'],line['end']-line['start']+.01,'Voice requires excessive time compression')
        with wave.open(str(out/'episode_mix.wav')) as w:
            self.assertEqual(w.getnframes()/w.getframerate(),45)
            self.assertEqual(w.getsampwidth(),2)

    def test_protected_workflow(self):
        import hashlib
        # Git checks out CRLF on this Windows workstation and LF on Linux.
        # Protect the original content independently of checkout line endings.
        content=(ROOT/'.github/workflows/render.yml').read_bytes().replace(b'\r\n',b'\n')
        digest=hashlib.sha256(content).hexdigest().upper()
        self.assertEqual(digest,'3BAB8CAC3CC55DAEF0B3F1E711F1576CC498EE0634FBD649E10A48B679F327CF')


if __name__=='__main__':
    unittest.main()
