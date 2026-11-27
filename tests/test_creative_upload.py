"""Private-upload protocol doubles; no real OAuth or YouTube requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autonomy.contracts import ROOT,digest,file_digest
from autonomy.creative_store import CreativeStore
from autonomy.creative_upload import reserve,upload


class DurablePrivateUploadTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'artifacts').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'artifacts');self.out=Path(self.temp.name)
        p=ROOT/'examples/creative/creative_kings_mercy'
        self.b,self.e,self.m=[json.loads((p/n).read_text()) for n in ['series_bible.json','episode_001.json','input_memory.json']]
        self.store=CreativeStore(self.out/'ledger.sqlite3');self.store.initialize(self.b,self.m)
        self.row=self.store.reserve(self.b,self.e,'example')
        self.video=self.out/'video.mp4';self.video.write_bytes(b'protocol fixture; actual video decoding tested separately')
        self.ev={'passed':True,'scene_passed':True,'audio_passed':True,'full_decode_passed':True,
            'video_sha256':file_digest(self.video),'script_sha256':digest(self.e),'input_memory_sha256':digest(self.m)}
        self.store.commit_verified(self.row['uid'],self.ev,self.video)
        self.job={'episode_uid':self.row['uid'],'video':str(self.video.relative_to(ROOT)),
            'video_sha256':file_digest(self.video),'metadata':{'snippet':{'title':'test'},
                'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}}}
        self.path=self.out/'job.json';self.path.write_text(json.dumps(self.job));self.checkpoint=self.out/'recovery.json'
        self.calls=0
    def tearDown(self):self.store.close();self.temp.cleanup()
    def fake(self,*args):self.calls+=1;return {'video_id':'mock-private-video','privacy':'private'}
    def persist(self):self.checkpoint.write_text(json.dumps({'remote_sha':'mock-persisted-sha','previous':self.store.snapshot()}))

    def test_public_and_changed_video_are_rejected(self):
        self.job['metadata']['status']['privacyStatus']='public'
        with self.assertRaises(ValueError):reserve(self.store,self.job,'one')
        self.job['metadata']['status']['privacyStatus']='private';self.video.write_bytes(b'changed')
        with self.assertRaises(ValueError):reserve(self.store,self.job,'one')

    def test_network_cannot_start_before_durable_reservation(self):
        reserve(self.store,self.job,'one');self.checkpoint.write_text(json.dumps({'remote_sha':None,'previous':self.store.snapshot()}))
        with self.assertRaises(RuntimeError):upload(self.store,self.path,'one',self.checkpoint,self.fake)
        self.assertEqual(self.calls,0)

    def test_wrong_attempt_cannot_execute_old_reservation(self):
        reserve(self.store,self.job,'one');self.persist()
        with self.assertRaises(RuntimeError):upload(self.store,self.path,'two',self.checkpoint,self.fake)
        self.assertEqual(self.calls,0)

    def test_success_is_private_and_recovered_receipt_prevents_duplicates(self):
        reserve(self.store,self.job,'one');self.persist()
        with patch.dict('os.environ',{'YOUTUBE_UPLOAD_APPROVED':'YES_PRIVATE_UPLOAD'}):
            result=upload(self.store,self.path,'one',self.checkpoint,self.fake)
            second=upload(self.store,self.path,'one',self.checkpoint,self.fake)
        self.assertEqual(self.calls,1);self.assertEqual(second['status'],'complete');self.assertEqual(result['privacy'],'private')
        restored=CreativeStore(self.out/'restored.sqlite3')
        try:
            restored.restore(self.store.snapshot())
            again=reserve(restored,self.job,'another-run');self.assertEqual(again['status'],'complete')
        finally:restored.close()

    def test_uncertain_network_result_blocks_later_retry(self):
        reserve(self.store,self.job,'one');self.persist()
        def failed(*args):raise OSError('synthetic network interruption')
        with patch.dict('os.environ',{'YOUTUBE_UPLOAD_APPROVED':'YES_PRIVATE_UPLOAD'}),self.assertRaises(OSError):upload(self.store,self.path,'one',self.checkpoint,failed)
        self.assertEqual(self.store.upload_receipt(self.row['uid'])['status'],'uncertain')
        with self.assertRaises(RuntimeError):reserve(self.store,self.job,'two')

    def test_missing_explicit_execution_gate_never_calls_transport(self):
        reserve(self.store,self.job,'one');self.persist()
        with patch.dict('os.environ',{},clear=True),self.assertRaises(PermissionError):upload(self.store,self.path,'one',self.checkpoint,self.fake)
        self.assertEqual(self.calls,0)


if __name__=='__main__':unittest.main()
