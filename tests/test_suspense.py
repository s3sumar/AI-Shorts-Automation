import copy
import json
import unittest
from autonomy.director import new_series,plan_episode
from autonomy.screenwriter import write_delivery,realize_local
from autonomy.suspense import validate_story
from autonomy.contracts import validate_plan


class SuspenseTests(unittest.TestCase):
    def setUp(self):
        self.series=new_series(2)
        self.plan=plan_episode(self.series,1,101)
        self.a=write_delivery(self.plan,'withdrawal',{'subject':'she','possessive':'her'})
        self.b=write_delivery(self.plan,'verification',{'subject':'she','possessive':'her'})

    def reject(self,mutate):
        draft=copy.deepcopy(self.a)
        mutate(draft)
        with self.assertRaises(ValueError): validate_story(draft['suspense'],draft['narration'])

    def test_two_strategies_keep_hook_reveal_but_change_decisions(self):
        self.assertEqual(self.a['narration'][0]['text'],self.b['narration'][0]['text'])
        self.assertEqual(self.a['narration'][-1]['text'],"You're the delivery.")
        self.assertEqual(self.a['narration'][-1]['text'],self.b['narration'][-1]['text'])
        ar=validate_story(self.a['suspense'],self.a['narration'])
        br=validate_story(self.b['suspense'],self.b['narration'])
        self.assertNotEqual(ar['choices'],br['choices'])
        self.assertNotEqual(ar['knowledge_timeline'],br['knowledge_timeline'])

    def test_audience_and_character_have_different_initial_knowledge(self):
        result=validate_story(self.a['suspense'],self.a['narration'])
        first=result['knowledge_timeline'][0]
        self.assertNotIn('parcel_held',first['before']['audience_knows'])
        self.assertIn('parcel_held',first['before']['protagonist_knows'])
        self.assertIn('why_this_person',result['unresolved'])

    def test_choice_cannot_use_unrevealed_information(self):
        self.reject(lambda d:d['suspense']['beats'][1]['choices'][0].update(requires_known=['human_delivery_claim']))

    def test_character_cannot_speak_from_unavailable_knowledge(self):
        self.reject(lambda d:d['suspense']['cue_links']['cancel'].update(requires_known=['figure_present']))

    def test_choice_cannot_use_unstated_belief_or_wrong_goal(self):
        self.reject(lambda d:d['suspense']['beats'][1]['choices'][0].update(based_on_beliefs=['ordinary_recipient']))
        self.reject(lambda d:d['suspense']['beats'][1]['choices'][0].update(goal='escape'))

    def test_consequence_cannot_precede_decision(self):
        self.reject(lambda d:d['suspense']['beats'][2]['consequences'][0].update(from_choice='refuse_handoff'))

    def test_events_must_stay_in_beats(self):
        self.reject(lambda d:d['suspense']['beats'][1]['choices'][0].update(at=44))

    def test_protected_reveal_and_opening_cannot_change(self):
        self.reject(lambda d:d['suspense']['beats'][-1]['reveals'][0].update(at=42.9))
        self.reject(lambda d:d['narration'][0].update(text='Something strange happened.'))

    def test_narrator_cannot_have_action_inventory_purpose(self):
        self.reject(lambda d:d['suspense']['cue_links']['hope'].update(purpose='visible_action'))
        self.reject(lambda d:d['suspense']['cue_links']['hope'].update(context_facts=[],beliefs=[],goals=[]))

    def test_ending_requires_planted_clue_and_specific_question(self):
        self.reject(lambda d:d['suspense']['cliffhanger'].update(payoff_of=[]))
        self.reject(lambda d:d['suspense']['cliffhanger'].update(unresolved=[]))
        self.reject(lambda d:d['suspense']['questions']['why_this_person'].update(arises_from=[]))

    def test_duplicate_cue_membership_is_rejected(self):
        self.reject(lambda d:d['suspense']['beats'][0]['cues'].append('opening'))

    def test_future_planning_persists_information_without_changing_series(self):
        original=copy.deepcopy(self.series)
        self.assertEqual(self.series,original)
        updated=copy.deepcopy(self.series);updated['canon']=self.plan['end_state']
        second=plan_episode(updated,2,102)
        self.assertEqual(second['start_state'],self.plan['end_state'])
        self.assertEqual(len(second['end_state']['story_memory']['history']),2)
        self.assertIn('called the delivery',second['dialogue'][0]['text'])
        self.assertEqual(second['suspense']['prior_story_memory'],self.plan['end_state']['story_memory'])
        self.assertEqual(self.series,original)
        other=plan_episode(new_series(3),1,103)
        self.assertEqual(other['suspense']['archetype'],'voice_trap')
        self.assertNotIn("You're the delivery",json.dumps(other['dialogue']))
        validate_plan(second)

    def test_treatment_cannot_change_canonical_staging(self):
        p=copy.deepcopy(self.plan);p['suspense']['continuity']['end_state']['floor']='13'
        with self.assertRaises(ValueError): validate_plan(p)

    def test_local_writer_gets_treatment_then_bounded_critique_and_repair(self):
        draft=self.a;prompts=[]
        class Model:
            critiques=0
            def generate(self,prompt):
                prompts.append(prompt)
                if prompt.startswith('SCREENPLAY_'):
                    return {'title':'A Tested Title','radio_lines':['An original short line.']*7,'dialogue':draft['narration']}
                if prompt.startswith('CRITIQUE_'):
                    self.critiques+=1
                    return {'approved':self.critiques==2,'issues':[] if self.critiques==2 else ['Review the motivation.']}
                return {'dialogue':draft['narration']}
        result,title,radio,receipt=realize_local(self.plan,draft,Model())
        self.assertEqual(len(prompts),4)
        self.assertIn('audience_knows',prompts[0]);self.assertIn('requires_known',prompts[0])
        self.assertEqual(receipt['repair_attempts'],1)
        self.assertEqual(result['narration'],draft['narration'])

    def test_local_writer_cannot_change_identity_or_leak_reveal(self):
        candidate=copy.deepcopy(self.a['narration']);candidate[1]['speaker']='different_actor'
        class Model:
            def generate(self,prompt):
                return {'title':'Bad','radio_lines':['Short line.']*7,'dialogue':candidate}
        with self.assertRaises(ValueError): realize_local(self.plan,self.a,Model())

    def test_take_cache_reuses_only_matching_identity_words_and_pacing(self):
        import tempfile
        import hashlib
        from pathlib import Path
        from soundstage.take_cache import seed_takes
        from soundstage.casting import resolve_delivery
        from soundstage.narration import request_signature
        from autonomy.contracts import ROOT
        library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
        line=self.a['narration'][0]
        role,emotion,delivery=resolve_delivery(library,line)
        identity=library['voices'][library['roles'][role]]
        signature=request_signature(identity,line['phrases'],delivery['pace'],delivery)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'old';take=source/'voice/take_09';take.mkdir(parents=True)
            (take/'voice.wav').write_bytes(b'verified test take')
            (take/'voice.json').write_text(json.dumps({'sha256':hashlib.sha256((take/'voice.wav').read_bytes()).hexdigest(),'signature':signature}))
            (take/'delivery.json').write_text('old processing receipt')
            target=Path(temp)/'new'
            self.assertEqual(len(seed_takes([line],library,target,[source])),1)
            self.assertFalse((target/'voice/take_00/delivery.json').exists())
            changed=dict(line,pace=.8)
            self.assertEqual(seed_takes([changed],library,Path(temp)/'changed',[source]),[])
            (take/'voice.wav').write_bytes(b'tampered')
            self.assertEqual(seed_takes([line],library,Path(temp)/'tampered',[source]),[])

    def test_delivery_headroom_preserves_transient_shape(self):
        import numpy as np
        from pathlib import Path
        from soundstage.casting import apply_delivery
        audio=np.array([[.9,-.6],[.2,-.1]],dtype=float)
        processed=apply_delivery(audio,{'gain_db':3},'unused',Path('.'))
        self.assertLessEqual(float(np.max(np.abs(processed))),.980001)
        self.assertAlmostEqual(processed[0,0]/processed[0,1],-1.5)


if __name__=='__main__': unittest.main()
