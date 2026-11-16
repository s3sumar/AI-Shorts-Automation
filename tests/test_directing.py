import copy
import json
import unittest
from pathlib import Path
from autonomy.checkpoint import unpack
from autonomy.compiler import compile_plan
from production.directing import lift_director_pass,assess_coverage
from soundstage.captions import chunks,align_phrases,ass

ROOT=Path(__file__).resolve().parents[1]


class DirectingTests(unittest.TestCase):
    def setUp(self):
        seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
        self.plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
        self.settings=json.loads((ROOT/'config/cloud_preview.json').read_text())
        self.score=compile_plan(self.plan,self.settings)

    def test_directing_preserves_identity_canon_and_input_score(self):
        before=copy.deepcopy(self.score)
        revised=lift_director_pass(self.score)
        self.assertEqual(self.score,before)
        self.assertEqual(revised['production'],before['production'])
        self.assertEqual(revised['character_color'],before['character_color'])
        self.assertEqual(revised['motion']['passenger.head.rotation_euler'][-1],before['motion']['passenger.head.rotation_euler'][-1])

    def test_coverage_has_no_gaps_and_breaks_long_display_insert(self):
        revised=lift_director_pass(self.score)
        shots=revised['shots']
        self.assertEqual(shots[0]['start'],0)
        self.assertEqual(shots[-1]['end'],45)
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(shots,shots[1:])))
        self.assertTrue(assess_coverage(revised)['passed'])
        self.assertEqual(len(shots),15)
        self.assertTrue(any(s['subject']=='Courier parcel' for s in shots if 'subject' in s))

    def test_profile_is_opt_in(self):
        self.assertNotIn('directing',self.score)
        settings=copy.deepcopy(self.settings);settings['directing']={'profile':'original_lift_v1'}
        self.assertIn('directing',compile_plan(self.plan,settings))

    def test_incomplete_coverage_does_not_pass(self):
        revised=lift_director_pass(self.score)
        revised['shots'][1]['start']+=.1
        self.assertFalse(assess_coverage(revised)['passed'])

    def test_torso_and_head_share_turn_and_restore_original_end_pose(self):
        revised=lift_director_pass(self.score)
        head=dict(revised['motion']['passenger.head.rotation_euler'])
        original=dict(self.score['motion']['passenger.head.rotation_euler'])
        self.assertAlmostEqual(head[34][2]+1.05,original[34][2])
        self.assertLess(abs(head[34][2]),1.5)
        self.assertEqual(revised['directing']['body_turn'][-1],[45,[0,0,0]])


class CaptionChunkTests(unittest.TestCase):
    def setUp(self):
        self.cue={'start':0,'end':3,'text':'The parcel is already delivered.'}
        self.words=[{'word':w,'start':i*.5,'end':i*.5+.4,'probability':.99} for i,w in enumerate(self.cue['text'].split())]

    def test_chunks_preserve_authored_words_and_do_not_exceed_four_words(self):
        result=chunks(self.cue,self.words)
        self.assertEqual(' '.join(c['text'] for c in result),self.cue['text'])
        self.assertTrue(all(len(c['text'].split())<=4 for c in result))
        self.assertTrue(all(a['end']<=b['start'] for a,b in zip(result,result[1:])))

    def test_wrong_transcription_falls_back_without_inventing_subtitles(self):
        self.words[1]['word']='wrong'
        result=align_phrases([self.cue],self.words)
        self.assertFalse(result['all_words_verified'])
        self.assertEqual(result['captions'][0]['timing_method'],'measured_phrase_fallback')
        self.assertEqual(result['captions'][0]['text'].replace('\n',' '),self.cue['text'])

    def test_touching_words_do_not_create_overlapping_chunks(self):
        for i,word in enumerate(self.words):
            word['end']=(i+1)*.5
        result=chunks(self.cue,self.words)
        self.assertTrue(all(a['end']<=b['start'] for a,b in zip(result,result[1:])))

    def test_low_confidence_alignment_is_never_reported_as_verified(self):
        self.words[0]['probability']=.2
        self.assertFalse(align_phrases([self.cue],self.words)['all_words_verified'])

    def test_ass_has_our_own_palette_and_escapes_control_tags(self):
        data=ass([{'start':0,'end':2,'text':'Delivered {malicious}'}])
        self.assertIn('F4E38D',data)
        self.assertNotIn('{malicious}',data)
        self.assertIn('PlayResX: 1080',data)


if __name__=='__main__':
    unittest.main()
