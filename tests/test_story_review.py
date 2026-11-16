import copy
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from autonomy.compiler import compile_plan
from autonomy.checkpoint import unpack
from production.story_revision import return_to_sender
from production.directing import assess_coverage
from soundstage.engine_alignment import phoneme_words
from soundstage.captions import chunks
from tools.review_episode3_story import engine_captions
from tools.render_story_review_clips import WINDOWS,check_completed_preview,optional_reuse_evidence

ROOT=Path(__file__).resolve().parents[1]


class EngineAlignmentTests(unittest.TestCase):
    def test_exact_sample_boundaries_include_bos_and_pause_offsets(self):
        phones=[{'phoneme':p,'num_samples':n} for p,n in [('^',10),('h',20),('i',30),(' ',40),('ð',20),('e',30),('.',20),('$',10)]]
        words=phoneme_words('Hi there.',phones,100)
        self.assertEqual([(w['word'],w['start'],w['end']) for w in words],[('Hi',.1,.6),('there.',1,1.5)])

    def test_ambiguous_word_map_fails_instead_of_reporting_success(self):
        with self.assertRaises(ValueError):
            phoneme_words('two words',[{'phoneme':'t','num_samples':100}],100)

    def test_invalid_engine_durations_are_rejected(self):
        with self.assertRaises(ValueError):
            phoneme_words('word',[{'phoneme':'w','num_samples':-1}],100)

    def test_caption_groups_avoid_an_isolated_trailing_word(self):
        cue={'start':0,'end':4,'text':"It's still in her hand."}
        words=[{'word':w,'start':i*.5,'end':i*.5+.4} for i,w in enumerate(cue['text'].split())]
        values=chunks(cue,words)
        self.assertEqual([len(v['text'].split()) for v in values],[3,2])

    def test_synthesis_captions_preserve_text_and_bind_audio_hash(self):
        cues=[{'start':0,'end':1,'text':'Keep it.'},{'start':43,'end':44,'text':"You're the delivery."}]
        words=[]
        for cue in cues:
            words.extend({'word':w,'start':cue['start']+i*.2,'end':cue['start']+i*.2+.18} for i,w in enumerate(cue['text'].split()))
        result=engine_captions({'captions':cues,'words':words,'mix_sha256':'audio-id'})
        self.assertFalse(result['fallback_phrases'])
        self.assertEqual(result['audio_mix_sha256'],'audio-id')
        self.assertEqual(result['captions'][-1]['end'],44.95)
        self.assertTrue(result['requires_human_timing_review'])


class StoryReviewTests(unittest.TestCase):
    def setUp(self):
        seed=unpack(json.loads((ROOT/'config/story_checkpoint.json').read_text()))
        plan=json.loads(next(e for e in seed['episodes'] if e['number']==3)['plan'])
        self.original=compile_plan(plan,json.loads((ROOT/'config/cloud_preview.json').read_text()))

    def test_isolated_draft_preserves_original_and_canonical_endpoints(self):
        before=copy.deepcopy(self.original)
        c=return_to_sender(self.original)
        self.assertEqual(self.original,before)
        self.assertEqual(c['production'],before['production'])
        for command in ['passenger.root.location','passenger.head.rotation_euler','shadow.root.location']:
            self.assertEqual(c['motion'][command][-1],before['motion'][command][-1])
        self.assertEqual(c['floor_events'],before['floor_events'])
        self.assertTrue(assess_coverage(c)['passed'])
        self.assertEqual(len(c['shots']),15)

    def test_old_display_shot_remains_eligible_for_cache_comparison(self):
        from production.directing import lift_director_pass
        a=lift_director_pass(self.original);b=return_to_sender(self.original)
        self.assertEqual(next(s for s in a['shots'] if s['id']=='countdown_pressure'),next(s for s in b['shots'] if s['id']=='countdown_pressure'))
        self.assertEqual(a['lighting'],b['lighting'])

    def test_preview_windows_never_render_the_full_episode(self):
        self.assertEqual(WINDOWS,[('beginning',0,5),('middle',17.5,5),('ending',38,7)])
        self.assertEqual(sum(w[2] for w in WINDOWS),17)

    def test_dialogue_leaves_an_uninterrupted_door_reveal(self):
        direction=json.loads((ROOT/'config/episode3_director_v4.json').read_text())
        self.assertFalse(any(v['start']<34 and v['end']>29 for v in direction['narration']))
        self.assertEqual(direction['narration'][-1]['speaker'],'dispatcher')


class PreviewProvenanceTests(unittest.TestCase):
    def test_clean_checkout_does_not_require_prior_render_cache(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            self.assertEqual(optional_reuse_evidence(root,root/'missing_old_cache'),[])

    def test_completed_preview_checks_audio_and_caption_inputs(self):
        with tempfile.TemporaryDirectory() as name:
            paths=[Path(name)/v for v in ['video','scene','audio']]
            for i,path in enumerate(paths): path.write_bytes(str(i).encode())
            hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            receipt=dict(zip(['sha256','source_scene_sha256','source_audio_sha256'],hashes))
            receipt['source_caption_sha256']='captions-v1'
            check_completed_preview(receipt,*paths,'captions-v1')
            with self.assertRaises(ValueError): check_completed_preview(receipt,*paths,'captions-v2')
            paths[2].write_bytes(b'new audio')
            with self.assertRaises(ValueError): check_completed_preview(receipt,*paths,'captions-v1')

    def test_legacy_incomplete_receipts_cannot_silently_validate_stale_previews(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'asset';path.write_bytes(b'data')
            old={'sha256':hashlib.sha256(b'data').hexdigest(),'source_scene_sha256':hashlib.sha256(b'data').hexdigest()}
            with self.assertRaises(ValueError): check_completed_preview(old,path,path,path,'captions')


if __name__=='__main__': unittest.main()
