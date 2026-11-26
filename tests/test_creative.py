"""Contract/protocol tests. Test doubles are not creative-quality evidence."""
import base64
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autonomy.contracts import ROOT,digest
from autonomy.creative import CreativeDirector,CRITERIA
from autonomy.creative_contract import initial_memory,validate_bible,validate_episode,propose_memory
from autonomy.creative_memory import pack,unpack
from autonomy.creative_compile import compile_creative,require_renderable
from autonomy.creative_provider import FreeCreativeProvider,ProviderError,free_model


def sample(name='creative_kings_mercy'):
    p=ROOT/'examples/creative'/name
    return tuple(json.loads((p/n).read_text()) for n in ['series_bible.json','episode_001.json','input_memory.json'])


def editorial(approved=True):
    return {'approved':approved,'scores':{k:{'score':4 if approved else 2,'reason':'Specific test evidence for this protocol score.'} for k in CRITERIA},
        'issues':[] if approved else [{'severity':'major','location':'middle','problem':'The decision has no credible motive.','revision':'Give the decision a visible cost and reason.'}]}


class ContractTests(unittest.TestCase):
    def setUp(self): self.b,self.e,self.m=sample()

    def test_three_distinct_original_review_documents(self):
        settings=set();genres=set()
        for name in ['creative_kings_mercy','creative_last_greenhouse','creative_mapmakers_rain']:
            b,e,m=sample(name);validate_episode(e,b,m)
            settings.add(b['environments'][0]['id']);genres.add(b['genre'])
            self.assertEqual({l['role'] for l in e['narration']},{'narrator','protagonist','antagonist'})
            self.assertEqual(e['duration'],45)
            self.assertIn('Not a hosted-provider output',(ROOT/'examples/creative'/name/'PROVENANCE.txt').read_text())
        self.assertEqual(len(settings),3);self.assertEqual(len(genres),3)

    def reject(self,change):
        ep=copy.deepcopy(self.e);change(ep)
        with self.assertRaises((ValueError,KeyError)): validate_episode(ep,self.b,self.m)

    def test_stale_memory_and_episode_order_rejected(self):
        self.reject(lambda e:e.update(prior_memory_sha256='0'*64))
        self.reject(lambda e:e.update(episode=2))

    def test_world_fact_and_goal_rewrites_rejected(self):
        self.reject(lambda e:e['suspense']['facts']['pardon_owned'].update(statement='A different fact'))
        self.reject(lambda e:e['suspense']['goals'].update(goal_ivo='Abandon his sister.'))

    def test_character_cannot_use_counterpart_knowledge_early(self):
        self.reject(lambda e:e['line_knowledge']['ask'].append('sale'))
        self.reject(lambda e:e['counterpart_state'].update(learns=[]))

    def test_secret_cannot_leak_before_scheduled_episode(self):
        self.reject(lambda e:e['suspense']['facts']['sale'].update(secret_id='central'))

    def test_unknown_voice_identity_and_emotion_rejected(self):
        self.reject(lambda e:e['narration'][1].update(speaker='new_person'))
        self.reject(lambda e:e['narration'][1].update(emotion='unsupported_delivery'))

    def test_overlong_speech_and_uncovered_dialogue_rejected(self):
        def long(e):
            e['narration'][1].update(text='A very long sentence spoken far too quickly in this tiny window.',phrases=[{'text':'A very long sentence spoken far too quickly in this tiny window.'}])
        self.reject(long)
        self.reject(lambda e:e['shots'][0].update(cue_ids=['hook']))

    def test_shot_spoiler_and_timeline_gap_rejected(self):
        self.reject(lambda e:e['shots'][0].update(reveals=['sale']))
        self.reject(lambda e:e['shots'][1].update(start=12))

    def test_impossible_season_resolution_rejected(self):
        self.reject(lambda e:e.update(resolved_mysteries=['central']))
        b=copy.deepcopy(self.b);b['season_arc'][-1]['resolves']=[]
        with self.assertRaises(ValueError): validate_bible(b)

    def test_proposed_memory_is_pure_and_preserves_knowledge(self):
        before=copy.deepcopy(self.m)
        after=propose_memory(self.e,self.b,self.m)
        self.assertEqual(self.m,before)
        self.assertEqual(after['next_episode'],2)
        self.assertIn('sale',after['audience_knows'])
        self.assertIn('sale',after['characters']['ivo']['knows'])
        self.assertIn('central',after['unresolved'])
        self.assertEqual(after['history'][0]['dialogue_sha256'],digest([l['text'].casefold().strip() for l in self.e['narration']]))

    def test_portable_memory_roundtrip_rejects_corruption_and_recasting(self):
        after=propose_memory(self.e,self.b,self.m);value=pack(self.b,after)
        bible,memory=unpack(value);self.assertEqual(memory,after)
        value['memory']['next_episode']=1
        with self.assertRaises(ValueError): unpack(value)
        b=copy.deepcopy(bible);b['characters'][0]['name']='Someone Else'
        with self.assertRaises(ValueError): pack(b,after)

    def test_replayed_complete_script_rejected_in_next_episode(self):
        after=propose_memory(self.e,self.b,self.m);ep=copy.deepcopy(self.e)
        ep.update(episode=2,prior_memory_sha256=digest(after))
        with self.assertRaisesRegex(ValueError,'repeats'):validate_episode(ep,self.b,after)

    def test_audio_bridge_and_capability_gate_do_not_substitute_elevator(self):
        c=compile_creative(self.e,self.b,self.m,registry={'assets':{},'environments':{}})
        self.assertEqual(c['audio_score']['narration'],self.e['narration'])
        self.assertEqual(c['audio_score']['audio_production']['schema'],3)
        self.assertFalse(c['blender_storyboard']['readiness']['renderable'])
        self.assertIn('royal_record_room',c['blender_storyboard']['readiness']['missing_environments'])
        with self.assertRaises(ValueError): require_renderable(c['blender_storyboard'])


class DirectorProtocolTests(unittest.TestCase):
    def setUp(self): self.b,self.e,self.m=sample()

    def test_live_protocol_can_request_original_events_not_fixed_prose(self):
        b,e=self.b,self.e;prompts=[]
        class Double:
            def generate(self,prompt,stage='write'):
                prompts.append((stage,prompt))
                return editorial() if stage=='critique' else copy.deepcopy(b if prompt.startswith('CREATE SERIES') else e)
        director=CreativeDirector(Double())
        bible=director.new_series('An original historical conspiracy with a difficult moral choice.')
        result=director.episode(bible)
        self.assertEqual(len(prompts),4)
        self.assertIn('writer_only_answer',prompts[0][1])
        self.assertIn('memory_sha256',prompts[2][1])
        self.assertNotIn('cue_skeleton',prompts[2][1])
        self.assertFalse(result['live_api_test'])
        self.assertTrue(result['approval']['script_editorial_approved'])
        self.assertFalse(result['approval']['production_ready'])

    def test_weak_script_is_revised_and_criticized_again(self):
        ep=self.e;calls=[]
        class Double:
            critiques=0
            def generate(self,prompt,stage='write'):
                calls.append((stage,prompt))
                if stage=='critique':
                    self.critiques+=1;return editorial(self.critiques==2)
                return copy.deepcopy(ep)
        result=CreativeDirector(Double()).episode(self.b,self.m)
        self.assertEqual([s for s,_ in calls],['write','critique','revise','critique'])
        self.assertIn('credible motive',calls[2][1])
        self.assertEqual(len(result['audit']),2)

    def test_structural_failure_is_revised_before_critic(self):
        ep=self.e;calls=[]
        class Double:
            def generate(self,prompt,stage='write'):
                calls.append(stage)
                if stage=='critique': return editorial()
                candidate=copy.deepcopy(ep)
                if stage=='write':candidate['prior_memory_sha256']='bad'
                return candidate
        CreativeDirector(Double()).episode(self.b,self.m)
        self.assertEqual(calls,['write','revise','critique'])

    def test_failed_critic_never_silently_uses_offline_fallback(self):
        ep=self.e;count=[]
        class Double:
            def generate(self,prompt,stage='write'):
                count.append(stage);return editorial(False) if stage=='critique' else copy.deepcopy(ep)
        with self.assertRaisesRegex(ValueError,'bounded'): CreativeDirector(Double()).episode(self.b,self.m)
        self.assertEqual(count.count('write')+count.count('revise'),3)

    def test_critic_requires_reasons_not_just_approval(self):
        from autonomy.creative import critique_pass
        with self.assertRaises(ValueError):critique_pass({'approved':True,'scores':{},'issues':[]})
        review=editorial();review['scores']['clarity']['score']=2
        self.assertFalse(critique_pass(review))

    def test_continuation_prompt_receives_committed_input_without_mutating_it(self):
        after=propose_memory(self.e,self.b,self.m);before=copy.deepcopy(after);prompts=[]
        class Stop:
            def generate(self,prompt,stage='write'):
                prompts.append(prompt);raise ProviderError('No live credential in test')
        with self.assertRaises(ProviderError):CreativeDirector(Stop()).episode(self.b,after)
        self.assertIn('"next_episode": 2',prompts[0]);self.assertIn('"sale"',prompts[0])
        self.assertEqual(after,before)

    def test_completed_season_requests_a_new_model_authored_series(self):
        b,e,m=sample('creative_mapmakers_rain')
        previous=copy.deepcopy(self.m);previous.update(next_episode=4,unresolved=[],resolved=['central'],
            history=[{'episode':i,'script_sha256':str(i)*64} for i in range(1,4)])
        prompts=[]
        class Double:
            def generate(self,prompt,stage='write'):
                prompts.append(prompt)
                if stage=='critique':return editorial()
                return copy.deepcopy(b if prompt.startswith('CREATE SERIES') else e)
        result=CreativeDirector(Double()).next_episode(self.b,previous,'An independent original fantasy with a costly act of kindness.')
        self.assertTrue(result['season_rollover'])
        self.assertEqual(result['episode']['episode'],1)
        self.assertNotEqual(result['bible']['id'],self.b['id'])
        self.assertIn('not a sequel or reskin',prompts[0])

    def test_pipeline_review_lane_never_instantiates_production_memory(self):
        from autonomy import pipeline
        with patch('sys.argv',['pipeline','creative-review','--creative-brief','Original story review','--review-out','artifacts/test_review']),patch('tools.creative_director.run') as run,patch.object(pipeline,'Memory') as memory:
            pipeline.main()
        run.assert_called_once();memory.assert_not_called()


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.settings=json.loads((ROOT/'config/creative_director.json').read_text())
        self.catalog={'data':[{'id':m,'context_length':100000,'pricing':{'prompt':'0','completion':'0','request':'0'},'supported_parameters':['response_format']} for m in [self.settings['writer_model'],self.settings['critic_model']]]}

    def response(self,model,value=None):
        return {'model':model,'usage':{'cost':0,'total_tokens':50},'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value or {'original':'test payload, not creative quality evidence'})}}]}

    def test_missing_key_never_makes_any_network_request(self):
        calls=[];provider=FreeCreativeProvider(self.settings,lambda *a:calls.append(a))
        with patch.dict(os.environ,{},clear=True),self.assertRaises(ProviderError):provider.generate('test')
        self.assertEqual(calls,[])

    def test_paid_model_and_fallback_configuration_rejected(self):
        for change in [{'writer_model':'paid/model'},{'allow_model_fallback':True},{'paid_services_enabled':True}]:
            with self.assertRaises(PermissionError):FreeCreativeProvider(dict(self.settings,**change))

    def test_catalog_zero_price_and_json_capability_enforced(self):
        for mutation in ['price','missing_price','small','json']:
            data=copy.deepcopy(self.catalog);item=data['data'][0]
            if mutation=='price':item['pricing']['completion']='0.1'
            elif mutation=='missing_price':del item['pricing']['prompt']
            elif mutation=='small':item['context_length']=2048
            else:item['supported_parameters']=[]
            with self.assertRaises((PermissionError,ProviderError)):free_model(data,item['id'])

    def test_free_routing_receipt_and_different_critic_model(self):
        seen=[]
        def transport(method,path,body=None,key=None):
            seen.append((method,path,body))
            return self.catalog if method=='GET' else self.response(body['model'])
        p=FreeCreativeProvider(self.settings,transport)
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-not-a-real-secret'}):
            p.generate('Write original events.');p.generate('Critique them.',stage='critique')
        bodies=[b for m,u,b in seen if m=='POST']
        self.assertNotEqual(bodies[0]['model'],bodies[1]['model'])
        self.assertEqual(bodies[0]['provider']['max_price'],{'prompt':0,'completion':0,'request':0})
        self.assertFalse(bodies[0]['provider']['allow_fallbacks'])
        self.assertNotIn('test-not-a-real-secret',json.dumps(p.receipts))
        self.assertFalse(p.is_live_provider)

    def test_truncation_refusal_and_wrong_model_are_not_success(self):
        for change in ['length','refusal','model']:
            def transport(method,path,body=None,key=None):
                if method=='GET': return self.catalog
                r=self.response(body['model'])
                if change=='length': r['choices'][0]['finish_reason']='length'
                elif change=='refusal':r['choices'][0]['message']['refusal']='No'
                else:r['model']='different/model:free'
                return r
            p=FreeCreativeProvider(self.settings,transport)
            with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-only'}),self.assertRaises(ProviderError):p.generate('test')

    def test_429_retry_is_bounded_and_counts_against_budget(self):
        count=[];sleep=[]
        def transport(method,path,body=None,key=None):
            if method=='GET':return self.catalog
            count.append(1);raise ProviderError('Provider HTTP 429')
        p=FreeCreativeProvider(dict(self.settings,max_calls=2),transport,sleep.append)
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-only'}):
            with self.assertRaises(ProviderError):p.generate('test')
            with self.assertRaisesRegex(ProviderError,'budget'):p.generate('test')
        self.assertEqual(len(count),2);self.assertEqual(sleep,[10])

    def test_http_auth_failure_does_not_echo_headers_or_error_body(self):
        import io
        import urllib.error
        from autonomy.creative_provider import http_json
        error=urllib.error.HTTPError('https://openrouter.ai/api/v1/chat/completions',401,'Denied',{},io.BytesIO(b'test-key-must-not-be-logged'))
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=error
            with self.assertRaises(ProviderError) as result:http_json('POST','/chat/completions',{},'test-key-must-not-be-logged')
        self.assertEqual(str(result.exception),'Provider HTTP 401')

    def test_proposed_memory_cannot_silently_recast_voices(self):
        b,e,m=sample();library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
        library['voices'][library['roles']['protagonist']]['model_sha256']='a'*64
        with self.assertRaises(ValueError):compile_creative(e,b,m,voice_library=library)

    def test_nonzero_reported_cost_stops_without_further_request(self):
        def transport(method,path,body=None,key=None):
            if method=='GET':return self.catalog
            response=self.response(body['model']);response['usage']['cost']=.01;return response
        p=FreeCreativeProvider(self.settings,transport)
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-only'}),self.assertRaisesRegex(ProviderError,'nonzero cost'):p.generate('test')
        self.assertEqual(p.calls,1)


class CloudReviewTests(unittest.TestCase):
    def test_workflow_is_manual_read_only_and_has_no_production_commit(self):
        import yaml
        w=yaml.load((ROOT/'.github/workflows/creative_writing_review.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(w['on']),{'workflow_dispatch'})
        self.assertEqual(w['permissions'],{'contents':'read'})
        commands='\n'.join(s.get('run','') for s in w['jobs']['writing']['steps'])
        for forbidden in ['git push','autonomy.pipeline plan','autonomy.pipeline produce','cloud_checkpoint.py save','blender','execute-private']:
            self.assertNotIn(forbidden,commands)
        self.assertIn('recover_creative_memory',commands)

    def test_missing_or_corrupt_durable_memory_cannot_restart_a_series(self):
        from tools.recover_creative_memory import recover
        (ROOT/'artifacts').mkdir(exist_ok=True)
        class Missing:
            def call(self,*args):return None
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as tmp:
            with self.assertRaises(RuntimeError):recover(Missing(),'creative_kings_mercy',Path(tmp)/'new')
            class Corrupt:
                def call(self,*args):return {'content':base64.b64encode(b'{"format":0}').decode()}
            with self.assertRaises((ValueError,KeyError)):recover(Corrupt(),'creative_kings_mercy',Path(tmp)/'new')


if __name__=='__main__':unittest.main()
