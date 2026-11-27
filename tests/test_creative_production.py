import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from autonomy.contracts import ROOT,digest,file_digest
from autonomy.creative_store import CreativeStore,unpack_snapshot
from autonomy.creative_compile import compile_creative
from autonomy.creative_contract import validate_episode
from autonomy.creative_service import reserve_next,produce_reserved


def sample():
    p=ROOT/'examples/creative/creative_kings_mercy'
    return tuple(json.loads((p/n).read_text()) for n in ['series_bible.json','episode_001.json','input_memory.json'])


class CreativeProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.store=CreativeStore(self.folder/'ledger.sqlite3');self.b,self.e,self.m=sample()
        self.store.initialize(self.b,self.m)
    def tearDown(self):self.store.close();self.temp.cleanup()

    def evidence(self):
        video=self.folder/'test.mp4';video.write_bytes(b'decode verification is supplied by separate media integration, not this transaction fixture')
        return video,{'passed':True,'scene_passed':True,'audio_passed':True,'full_decode_passed':True,
            'video_sha256':file_digest(video),'script_sha256':digest(self.e),'input_memory_sha256':digest(self.m)}

    def test_reserved_run_is_idempotent_and_failed_work_keeps_canon(self):
        row=self.store.reserve(self.b,self.e,'one');self.store.fail(row['uid'],'renderer failed')
        self.assertEqual(self.store.current(self.b['id'])[1],self.m)
        second=self.store.reserve(self.b,self.e,'two')
        self.assertEqual(row['uid'],second['uid'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0],1)

    def test_legacy_ledger_cannot_be_migrated_accidentally(self):
        import sqlite3
        from contextlib import closing
        p=self.folder/'legacy.sqlite3'
        with closing(sqlite3.connect(p)) as db:
            db.execute('CREATE TABLE series(id TEXT,bible TEXT,canon TEXT)');db.commit()
        before=p.read_bytes()
        with self.assertRaises(ValueError):CreativeStore(p)
        self.assertEqual(p.read_bytes(),before)

    def test_concurrent_run_keys_reserve_only_one_episode(self):
        def reserve(key):
            s=CreativeStore(self.store.path)
            try:return s.reserve(self.b,self.e,key)['uid']
            finally:s.close()
        with ThreadPoolExecutor(max_workers=3) as pool:ids=list(pool.map(reserve,['a','b','c']))
        self.assertEqual(len(set(ids)),1)

    def test_reusing_run_key_for_another_script_is_rejected(self):
        self.store.reserve(self.b,self.e,'one');changed=copy.deepcopy(self.e);changed['title']='A different draft'
        with self.assertRaises(ValueError):self.store.reserve(self.b,changed,'one')

    def test_successful_media_commit_advances_once(self):
        row=self.store.reserve(self.b,self.e,'one');video,ev=self.evidence()
        self.store.commit_verified(row['uid'],ev,video);self.store.commit_verified(row['uid'],ev,video)
        memory=self.store.current(self.b['id'])[1]
        self.assertEqual(memory['next_episode'],2);self.assertEqual(len(memory['history']),1)
        self.assertEqual(memory['characters']['ivo']['goal']['id'],'cliff_goal')

    def test_missing_media_checks_and_changed_bytes_cannot_advance(self):
        row=self.store.reserve(self.b,self.e,'one');video,ev=self.evidence()
        with self.assertRaises(ValueError):self.store.commit_verified(row['uid'],dict(ev,full_decode_passed=False),video)
        video.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.store.commit_verified(row['uid'],ev,video)
        self.assertEqual(self.store.current(self.b['id'])[1],self.m)

    def test_stale_state_and_wrong_script_media_are_rejected(self):
        row=self.store.reserve(self.b,self.e,'one');video,ev=self.evidence()
        with self.assertRaises(ValueError):self.store.commit_verified(row['uid'],dict(ev,script_sha256='b'*64),video)
        changed=copy.deepcopy(self.m);changed['audience_knows']=['pardon_owned']
        self.store.db.execute('UPDATE series SET memory=? WHERE id=?',(json.dumps(changed),self.b['id']))
        with self.assertRaises(ValueError):self.store.commit_verified(row['uid'],ev,video)

    def test_durable_snapshot_restores_pending_script_without_rewriting(self):
        row=self.store.reserve(self.b,self.e,'one');self.store.fail(row['uid'],'interrupted')
        value=self.store.snapshot();other=CreativeStore(self.folder/'restored.sqlite3')
        try:
            other.restore(value);self.assertEqual(other.by_run('one')['script'],row['script'])
            self.assertEqual(other.current(self.b['id'])[1],self.m)
            with self.assertRaises(FileExistsError):other.restore(value)
        finally:other.close()

    def test_snapshot_checksum_and_verified_history_detect_corruption(self):
        self.store.reserve(self.b,self.e,'one');value=self.store.snapshot()
        value['creative_store']['episodes'][0]['script']='{}'
        with self.assertRaises(ValueError):unpack_snapshot(value)

    def test_editorial_provenance_survives_snapshot_and_cannot_be_rewritten(self):
        row=self.store.reserve(self.b,self.e,'one')
        review={'authorship':'authored_development_example','live_model_test':False}
        self.store.save_review(row['uid'],review)
        value=self.store.snapshot();self.assertEqual(json.loads(value['creative_store']['reviews'][0]['receipt']),review)
        with self.assertRaises(ValueError):self.store.save_review(row['uid'],dict(review,live_model_test=True))

    def test_timing_probe_respects_tail_limit_not_only_spoken_word_end(self):
        from autonomy.creative_media import fit_dialogue
        library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
        score={'narration':[copy.deepcopy(self.e['narration'][0])]}
        takes=[{'words':[{'end':4.8}],'duration':5.01},{'words':[{'end':4.6}],'duration':4.8}]
        with patch('soundstage.casting.VoiceCast') as cast,patch('soundstage.take_cache.seed_takes',return_value=[]):
            cast.return_value.render_line.side_effect=takes
            fitted=fit_dialogue(score,library,self.folder,'unused')
        self.assertEqual(cast.return_value.render_line.call_count,2)
        self.assertLess(fitted['narration'][0]['pace'],library['delivery_profiles']['storytelling']['pace'])
        self.assertEqual(fitted['narration'][0]['text'],score['narration'][0]['text'])

    def test_platform_timing_slack_stays_inside_original_beat_and_keeps_words(self):
        from autonomy.creative_media import fit_dialogue
        library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
        line=copy.deepcopy(self.e['narration'][2]);line['pace']=.75
        score={'narration':[line],'narrative_treatment':self.e['suspense']}
        take={'words':[{'end':3.5038}],'duration':3.6643}
        with patch('soundstage.casting.VoiceCast') as cast,patch('soundstage.take_cache.seed_takes',return_value=[]):
            cast.return_value.render_line.return_value=take
            fitted=fit_dialogue(score,library,self.folder,'unused')
        actual=fitted['narration'][0]
        self.assertGreater(actual['end'],line['end']);self.assertLessEqual(actual['end'],11.78)
        self.assertEqual(actual['text'],line['text']);self.assertEqual(actual['start'],line['start'])

    def test_unauthored_neural_sentence_pause_is_replaced_before_speeding(self):
        from autonomy.creative_media import fit_dialogue
        library=json.loads((ROOT/'config/voice_cast_local.json').read_text())
        line=copy.deepcopy(self.e['narration'][2]);score={'narration':[line],'narrative_treatment':self.e['suspense']}
        first={'duration':4.15,'words':[{'start':.07,'end':1.2},{'start':2.67,'end':2.8},{'start':2.83,'end':3.34},{'start':3.4,'end':3.52},{'start':3.54,'end':4.0}]}
        second={'duration':2.9,'words':[{'end':2.8}]}
        with patch('soundstage.casting.VoiceCast') as cast,patch('soundstage.take_cache.seed_takes',return_value=[]):
            cast.return_value.render_line.side_effect=[first,second]
            fitted=fit_dialogue(score,library,self.folder,'unused')['narration'][0]
        self.assertEqual(fitted['text'],line['text'])
        self.assertEqual(len(fitted['phrases']),2);self.assertEqual(fitted['phrases'][0]['pause_after'],.18)
        self.assertNotIn('pace',fitted)

    def test_fast_seven_word_caption_uses_readable_group_without_lost_words(self):
        from soundstage.aligned_captions import build
        words='Can you make it reach our street?'.split()
        cue={'start':0,'end':2.5,'text':' '.join(words),'speaker':'kid','role':'antagonist'}
        timings=[{'word':w,'start':i*.16,'end':i*.16+.12} for i,w in enumerate(words)]
        result=build([cue],timings,3)
        self.assertEqual(' '.join(c['text'] for c in result).split(),words)
        self.assertLessEqual(max(len(c['text'])/(c['end']-c['start']) for c in result),22)

    def test_cloud_regression_cannot_drop_run_or_reservation(self):
        from tools.cloud_creative_store import refuse_regression
        before=self.store.snapshot();self.store.reserve(self.b,self.e,'one');after=self.store.snapshot()
        refuse_regression(before,after)
        with self.assertRaises(ValueError):refuse_regression(after,before)

    def test_coordinator_recovers_pending_without_model_requests(self):
        class Forbidden:
            def new_series(self,*args):raise AssertionError('No model calls on retry')
            def next_episode(self,*args):raise AssertionError('No model calls on retry')
        row=self.store.reserve(self.b,self.e,'one');self.store.fail(row['uid'],'failure')
        recovered=reserve_next(self.store,'new-run',Forbidden(),'irrelevant')
        self.assertEqual(row['uid'],recovered['uid'])

    def test_renderer_failure_does_not_commit_or_lose_pending_script(self):
        row=self.store.reserve(self.b,self.e,'one')
        with patch('autonomy.creative_service.produce',side_effect=RuntimeError('synthetic render failure')):
            with self.assertRaises(RuntimeError):produce_reserved(self.store,row,self.folder/'media','blender','ffmpeg',{'resolution':[180,320],'fps':2,'max_seconds':1200})
        self.assertEqual(self.store.current(self.b['id'])[1],self.m)
        self.assertEqual(self.store.by_run('one')['status'],'failed')

    def test_three_new_worlds_have_real_registered_adapter_bindings(self):
        for name in ['creative_kings_mercy','creative_mapmakers_rain','creative_last_greenhouse']:
            folder=ROOT/'examples/creative'/name
            b,e,m=[json.loads((folder/n).read_text()) for n in ['series_bible.json','episode_001.json','input_memory.json']]
            compiled=compile_creative(e,b,m)
            self.assertTrue(compiled['blender_storyboard']['readiness']['renderable'])
            self.assertTrue(all(s['performances'] for s in e['shots']))

    def test_unsupported_typed_performance_and_visual_events_are_rejected(self):
        for change in ['action','property','target']:
            ep=copy.deepcopy(self.e)
            if change=='action':ep['shots'][0]['performances'][0]['action']='execute_python'
            else:ep['visual_events'][0][change]='unknown'
            with self.assertRaises(ValueError):validate_episode(ep,self.b,self.m)

    def test_development_cloud_workflow_preserves_reservation_before_render(self):
        import yaml
        w=yaml.load((ROOT/'.github/workflows/creative_production.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(w['on']),{'workflow_dispatch'})
        self.assertEqual(w['concurrency']['cancel-in-progress'],'false')
        steps=w['jobs']['produce']['steps'];commands=[s.get('run','') for s in steps]
        plan=next(i for i,c in enumerate(commands) if 'creative_service plan' in c)
        saves=[i for i,c in enumerate(commands) if 'cloud_creative_store.py save' in c]
        render=next(i for i,c in enumerate(commands) if 'creative_service produce' in c)
        self.assertLess(plan,saves[0]);self.assertLess(saves[0],render);self.assertGreater(saves[1],render)
        self.assertIn("steps.reservation.outcome == 'success'",steps[saves[-1]]['if'])
        upload=next(s for s in steps if 'creative_upload upload' in s.get('run',''))
        self.assertIn('inputs.private_upload == true',upload['if'])
        self.assertEqual(w['on']['workflow_dispatch']['inputs']['private_upload']['default'],'false')


if __name__=='__main__':unittest.main()
