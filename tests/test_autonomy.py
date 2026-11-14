import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from autonomy.contracts import ROOT,digest,validate_plan,write_json
from autonomy.store import Memory
from autonomy.director import LocalModel,new_series
from autonomy.compiler import compile_plan
from autonomy import youtube
from tools.media import validate_png

SETTINGS=json.loads((ROOT/'config/autonomy.json').read_text())
EVIDENCE={'passed':True,'scene_passed':True,'audio_passed':True,'video_sha256':'a'*64}


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'memory.sqlite3'
        self.m=Memory(self.path)
        self.m.bootstrap(verify_local=False)

    def tearDown(self):
        self.m.close()
        self.temp.cleanup()

    def test_two_consecutive_episodes_and_season_rollover(self):
        first=json.loads(self.m.db.execute('SELECT plan FROM episodes').fetchone()[0])
        row=self.m.reserve('day-2')
        second=json.loads(row['plan'])
        self.assertEqual(first['end_state'],second['start_state'])
        self.assertEqual(second['start_state']['floor'],'-1')
        self.assertEqual(second['start_state']['doors'],1)
        self.assertEqual(second['start_state']['lighting'],'red')
        self.assertEqual(second['end_state']['location'],'ground_corridor')
        before=self.m.db.execute('SELECT canon FROM series').fetchone()[0]
        self.m.mark(row['uid'],'failed','synthetic renderer failure')
        self.assertEqual(before,self.m.db.execute('SELECT canon FROM series').fetchone()[0])
        self.assertEqual(self.m.reserve('day-2-retry')['uid'],row['uid'])
        self.m.commit_verified(row['uid'],EVIDENCE)
        new=json.loads(self.m.reserve('day-3')['plan'])
        self.assertNotEqual(new['series_id'],second['series_id'])
        self.assertEqual(new['ordinal'],1)
        self.assertNotEqual(new['series_title'],second['series_title'])
        self.assertEqual(new['start_state']['floor'],'13')

    def test_idempotent_retry_does_not_create_episode_three(self):
        row=self.m.reserve('same-run')
        self.m.commit_verified(row['uid'],EVIDENCE)
        self.assertEqual(self.m.reserve('same-run')['uid'],row['uid'])
        self.assertEqual(self.m.db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0],2)
        self.m.commit_verified(row['uid'],EVIDENCE)
        with self.assertRaises(ValueError):
            self.m.commit_verified(row['uid'],dict(EVIDENCE,video_sha256='b'*64))

    def test_missing_verification_and_stale_canon_do_not_commit(self):
        row=self.m.reserve('stale')
        with self.assertRaises(ValueError):
            self.m.commit_verified(row['uid'],{'passed':True})
        self.m.db.execute("UPDATE series SET canon='{}' WHERE id='series_001'")
        with self.assertRaises(ValueError):
            self.m.commit_verified(row['uid'],EVIDENCE)
        self.assertNotEqual(self.m.db.execute('SELECT status FROM episodes WHERE uid=?',(row['uid'],)).fetchone()[0],'verified')

    def test_concurrent_schedulers_reserve_only_one_episode(self):
        def reserve(key):
            m=Memory(self.path)
            try:
                return m.reserve(key)['uid']
            finally:
                m.close()
        with ThreadPoolExecutor(max_workers=3) as pool:
            ids=list(pool.map(reserve,['parallel-1','parallel-2','parallel-3']))
        self.assertEqual(len(set(ids)),1)
        self.assertEqual(self.m.db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0],2)

    def test_compiler_preserves_canon_and_budget(self):
        plan=json.loads(self.m.reserve('compile')['plan'])
        c=compile_plan(plan,SETTINGS)
        self.assertEqual(c['floor_events'][0][1],plan['start_state']['floor'])
        self.assertEqual(c['door_events'][0][1],1)
        self.assertEqual(c['motion']['passenger.root.location'][0][1],plan['start_state']['passenger_position'])
        self.assertEqual(c['preview']['fps']*c['duration'],270)
        self.assertEqual(c['production']['plan_hash'],digest(plan))
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(c['shots'],c['shots'][1:])))

    def test_unrenderable_and_identity_changes_rejected(self):
        plan=json.loads(self.m.reserve('bad')['plan'])
        plan['environment']='unknown-world'
        with self.assertRaises(ValueError):
            validate_plan(plan)
        plan['environment']='lift_013'
        plan['end_state']['characters']['protagonist']['name']='someone else'
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_local_model_adapter_only_loopback(self):
        with self.assertRaises(ValueError):
            LocalModel('model','https://paid-api.example')
        class FakeModel:
            def generate(self,prompt):
                return {'title':'The Silent Parcel','radio_lines':['Keep the receiver down.']*7}
        row=self.m.reserve('model',FakeModel())
        plan=json.loads(row['plan'])
        self.assertEqual(plan['source'],'local_llm')
        self.assertEqual(plan['title'],'The Silent Parcel')
        self.assertEqual(plan['start_state']['floor'],'-1')

    def test_invalid_model_output_rolls_back(self):
        class Broken:
            def generate(self,prompt):
                return {'title':'bad','radio_lines':['Too few.']}
        with self.assertRaises(ValueError):
            self.m.reserve('broken-model',Broken())
        self.assertEqual(self.m.db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0],1)

    def test_concept_variation_and_backup_roundtrip(self):
        self.assertNotEqual(new_series(2)['title'],new_series(3)['title'])
        backup=Path(self.temp.name)/'backup.sqlite3'
        self.m.backup(backup)
        other=Memory(backup)
        try:
            self.assertEqual(other.db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(other.db.execute('SELECT COUNT(*) FROM series').fetchone()[0],1)
        finally:
            other.close()

    def test_backup_is_immutable_and_paths_are_portable(self):
        backup=Path(self.temp.name)/'immutable.sqlite3'
        self.m.backup(backup)
        with self.assertRaises(FileExistsError):
            self.m.backup(backup)
        seed=self.m.db.execute('SELECT uid,evidence FROM episodes').fetchone()
        data=json.loads(seed['evidence'])
        data['video']='artifacts\\episode_001\\episode_001_preview.mp4'
        self.m.db.execute('UPDATE episodes SET evidence=? WHERE uid=?',(json.dumps(data),seed['uid']))
        self.m.close()
        self.m=Memory(self.path)
        value=json.loads(self.m.db.execute('SELECT evidence FROM episodes').fetchone()[0])
        self.assertEqual(value['video'],'artifacts/episode_001/episode_001_preview.mp4')

    def test_production_build_failure_never_advances_canon(self):
        import subprocess
        from autonomy import pipeline
        row=self.m.reserve('failed-build')
        before=self.m.db.execute('SELECT canon FROM series').fetchone()[0]
        isolated=Path(self.temp.name)
        out=isolated/'artifacts/autonomy'/row['uid']
        def fake(command,**kwargs):
            if any('prepare_audio.py' in str(value) for value in command):
                write_json(out/'audio/audio_manifest.json',{'narration':[{'status':'synthesized'}]*7})
                return subprocess.CompletedProcess(command,0)
            return subprocess.CompletedProcess(command,1)
        with patch.object(pipeline,'ROOT',isolated),patch.object(pipeline.subprocess,'run',side_effect=fake):
            with self.assertRaises(subprocess.CalledProcessError):
                pipeline.produce(self.m,row,SETTINGS,'fake-blender','fake-ffmpeg')
        self.assertEqual(before,self.m.db.execute('SELECT canon FROM series').fetchone()[0])
        self.assertEqual(self.m.db.execute('SELECT status FROM episodes WHERE uid=?',(row['uid'],)).fetchone()[0],'failed')
        self.assertFalse(json.loads((out/'production_error.json').read_text())['canon_advanced'])


class UploadTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'artifacts').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'artifacts')
        self.out=Path(self.temp.name)
        self.video=self.out/'video.mp4'
        self.video.write_bytes(b'verified-video-test-fixture')
        from autonomy.contracts import file_digest
        self.job={'episode_uid':'test_episode','video':str(self.video.relative_to(ROOT)),
                  'video_sha256':file_digest(self.video),'metadata':{'snippet':{'title':'test'},'status':{'privacyStatus':'private'}}}
        self.path=self.out/'job.json'
        write_json(self.path,self.job)
        self.settings=copy.deepcopy(SETTINGS)
        self.settings['youtube']['receipt_dir']=str(self.out/'receipts')
        self.fake_calls=[]

    def tearDown(self):
        self.temp.cleanup()

    def fake(self,video,metadata,callback):
        self.fake_calls.append(metadata)
        return {'video_id':'mock-video','privacy':'private'}

    def test_dry_run_and_disabled_upload_never_call_network(self):
        self.assertTrue(youtube.execute_private(self.path,self.settings,transport=self.fake)['dry_run'])
        with self.assertRaises(PermissionError):
            youtube.execute_private(self.path,self.settings,True,self.fake)
        self.assertEqual(self.fake_calls,[])

    def test_public_and_scheduled_uploads_are_rejected(self):
        for status in [{'privacyStatus':'public'},{'privacyStatus':'private','publishAt':'tomorrow'}]:
            self.job['metadata']['status']=status
            write_json(self.path,self.job)
            with self.assertRaises(ValueError):
                youtube.execute_private(self.path,self.settings,transport=self.fake)

    def test_mock_private_upload_is_idempotent(self):
        self.settings['youtube']['enabled']=True
        with patch.dict(os.environ,{'YOUTUBE_UPLOAD_APPROVED':'YES_PRIVATE_UPLOAD'}):
            first=youtube.execute_private(self.path,self.settings,True,self.fake)
            second=youtube.execute_private(self.path,self.settings,True,self.fake)
        self.assertEqual(first,second)
        self.assertEqual(len(self.fake_calls),1)
        self.assertEqual(self.fake_calls[0]['status']['privacyStatus'],'private')

    def test_uncertain_upload_blocks_duplicate_retry(self):
        self.settings['youtube']['enabled']=True
        def broken(*args):
            raise OSError('mock connection lost')
        with patch.dict(os.environ,{'YOUTUBE_UPLOAD_APPROVED':'YES_PRIVATE_UPLOAD'}):
            with self.assertRaises(OSError):
                youtube.execute_private(self.path,self.settings,True,broken)
            with self.assertRaises(RuntimeError):
                youtube.execute_private(self.path,self.settings,True,self.fake)
        self.assertEqual(self.fake_calls,[])


class MediaRecoveryTests(unittest.TestCase):
    def test_png_truncation_and_corruption_detected(self):
        import struct,zlib
        def chunk(kind,data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        image=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
        image+=chunk(b'IDAT',zlib.compress(b'\x00\x80\x40\x20'))+chunk(b'IEND',b'')
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'valid.png'
            source.write_bytes(image)
            self.assertEqual(validate_png(source),[1,1])
            bad=Path(tmp)/'bad.png'
            bad.write_bytes(source.read_bytes()[:-12])
            with self.assertRaises(ValueError):
                validate_png(bad)
            data=bytearray(source.read_bytes())
            data[20]^=1
            bad.write_bytes(data)
            with self.assertRaises(ValueError):
                validate_png(bad)


if __name__=='__main__':
    unittest.main()
