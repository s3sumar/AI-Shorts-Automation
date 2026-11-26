import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from autonomy.compiler import compile_plan
from autonomy.director import new_series,plan_episode
from autonomy.contracts import validate_plan
from soundstage.voice_contract import freeze_cast,validate_cast_lock,validate_dialogue,voice_fingerprint
from soundstage.casting import resolve_delivery,apply_delivery
from soundstage.engine_alignment import phoneme_words
from soundstage.aligned_captions import build
from soundstage.captions import chunks
from soundstage.events import event_plan
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


class CastIdentityTests(unittest.TestCase):
    def setUp(self): self.library=json.loads((ROOT/'config/voice_cast_local.json').read_text())

    def test_cast_uses_three_actual_models_not_three_names_for_one_voice(self):
        lock=freeze_cast(self.library,'new_series')
        self.assertEqual(len(set(lock['fingerprints'].values())),3)
        self.library['voices']['norman_figure_v1']['model_sha256']=self.library['voices']['john_storyteller_v1']['model_sha256']
        with self.assertRaises(ValueError): freeze_cast(self.library,'new_series')

    def test_recasting_an_established_series_is_rejected(self):
        lock=freeze_cast(self.library,'new_series')
        self.library['voices']['john_storyteller_v1']['model_sha256']='a'*64
        with self.assertRaises(ValueError): validate_cast_lock(lock,self.library,'new_series')

    def test_emotion_changes_delivery_without_changing_actor_identity(self):
        before=freeze_cast(self.library,'new_series')
        a=resolve_delivery(self.library,{'speaker':'passenger','role':'protagonist','emotion':'uneasy'})
        b=resolve_delivery(self.library,{'speaker':'passenger','role':'protagonist','emotion':'terrified'})
        self.assertNotEqual(a[2],b[2]);self.assertEqual(before,freeze_cast(self.library,'new_series'))

    def test_unknown_or_excessive_style_controls_fail(self):
        with self.assertRaises(ValueError): resolve_delivery(self.library,{'speaker':'narrator','emotion':'invented'})
        self.library['delivery_profiles']['storytelling']['pitch_semitones']=20
        with self.assertRaises(ValueError): resolve_delivery(self.library,{'speaker':'narrator'})

    def test_paid_provider_is_rejected_before_any_network_or_synthesis(self):
        self.library['paid_services_enabled']=True
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(PermissionError): freeze_cast(self.library,'new_series')
            network.assert_not_called()

    def test_cast_ids_cannot_escape_local_stem_paths(self):
        self.library['voices']['john_storyteller_v1']['voice_id']='../../outside'
        with self.assertRaises(ValueError): freeze_cast(self.library,'new_series')

    def test_manual_cast_setup_cannot_unpause_or_schedule_production(self):
        text=(ROOT/'.github/workflows/autonomous_production.yml').read_text()
        self.assertIn('default: legacy',text)
        self.assertIn("if: inputs.audio_profile == 'cast'",text)
        self.assertLess(text.index("assert not s['episode_generation_paused']"),text.index('python tools/setup_voice_cast.py'))
        self.assertNotIn('schedule:',text)
        self.assertNotIn('execute-private',text)

    def test_new_series_and_two_episode_plans_keep_the_same_voice_lock(self):
        series=new_series(4)
        first=plan_episode(series,1,12)
        series['canon']=copy.deepcopy(first['end_state'])
        second=plan_episode(series,2,13)
        self.assertEqual(first['voice_cast'],second['voice_cast'])
        self.assertEqual(second['start_state'],first['end_state'])
        self.assertEqual({x['role'] for x in first['dialogue']},{'narrator','protagonist','antagonist'})
        self.assertEqual(first['start_state']['characters']['protagonist']['name'],'Technician')
        self.assertEqual(first['suspense']['archetype'],'voice_trap')

    def test_compiler_integrates_cast_dialogue_as_opt_in(self):
        plan=plan_episode(new_series(3),1,8)
        settings=json.loads((ROOT/'config/cloud_preview.json').read_text())
        old=compile_plan(plan,settings)
        self.assertNotIn('audio_production',old)
        settings['audio']={'mode':'cast','cast_settings':'config/voice_cast_local.json'}
        c=compile_plan(plan,settings)
        self.assertEqual(c['narration'],plan['dialogue'])
        self.assertEqual(c['audio_production']['schema'],3)
        self.assertEqual(c['production']['start_state'],old['production']['start_state'])
        self.assertEqual(c['production']['end_state'],old['production']['end_state'])

    def test_authored_model_dialogue_is_validated_before_use(self):
        plan=plan_episode(new_series(3),1,8)
        plan['dialogue'][0]['role']='run_a_shell_command'
        with self.assertRaises(ValueError): validate_plan(plan)


class DialogueTimingTests(unittest.TestCase):
    def test_six_word_subtitles_split_three_and_three_for_readability(self):
        cue={'start':0,'end':3,'text':"I'm not giving you the parcel."}
        words=[{'word':w,'start':i*.3,'end':i*.3+.25} for i,w in enumerate(cue['text'].split())]
        self.assertEqual([len(c['text'].split()) for c in chunks(cue,words)],[3,3])

    def test_coarticulated_words_use_real_phoneme_boundaries(self):
        marks=[{'phoneme':p,'num_samples':10} for p in ['w','a','z','a']]
        words=phoneme_words('was a',marks,100,word_phonemes=[['w','a','z'],['a']])
        self.assertEqual([(w['start'],w['end']) for w in words],[(0,.3),(.3,.4)])
        self.assertEqual(words[0]['timing_source'],'synthesis_phoneme_boundary_mapping')

    def test_uncertain_phoneme_mapping_is_not_faked(self):
        marks=[{'phoneme':'x','num_samples':10}]*4
        with self.assertRaises(ValueError): phoneme_words('was a',marks,100,word_phonemes=[['w','a','z'],['a']])

    def test_overlap_and_wrong_phrase_text_are_rejected(self):
        base=[{'start':0,'end':1,'speaker':'narrator','text':'One line.'},
              {'start':.8,'end':2,'speaker':'narrator','text':'Another line.'}]
        with self.assertRaises(ValueError): validate_dialogue(base)
        base[1]['start']=1.1;base[0]['phrases']=[{'text':'Different text.'}]
        with self.assertRaises(ValueError): validate_dialogue(base)

    def test_emotional_gain_and_tremor_preserve_duration_and_finite_samples(self):
        audio=np.full((4800,2),.1)
        result=apply_delivery(audio,{'gain_db':-2,'tremor_depth':.03},'unused',Path('.'))
        self.assertEqual(result.shape,audio.shape)
        self.assertTrue(np.isfinite(result).all());self.assertLess(float(result.max()),.1)

    def test_subtitles_preserve_speaker_text_and_timing(self):
        cue={'start':0,'end':2,'text':'Stay back.','speaker':'hero','role':'protagonist'}
        words=[{'word':'Stay','start':.1,'end':.5},{'word':'back.','start':.55,'end':1}]
        captions=build([cue],words,3)
        self.assertEqual(captions[0]['text'],cue['text']);self.assertEqual(captions[0]['speaker'],'hero')
        self.assertEqual(captions[0]['start'],.1)

    def test_effects_can_be_authored_for_other_environments(self):
        score={'duration':5,'sound_events':[{'category':'environment','start':0,'end':5,'gain':.05}]}
        self.assertEqual(event_plan(score),score['sound_events'])
        score['sound_events'][0]['category']='download_audio'
        with self.assertRaises(ValueError): event_plan(score)


if __name__=='__main__': unittest.main()
