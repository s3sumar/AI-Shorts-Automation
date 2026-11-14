import base64
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autonomy.checkpoint import capture, envelope, unpack, restore, refuse_regression
from autonomy.contracts import ROOT
from autonomy.store import Memory
from tools.cloud_checkpoint import recover, persist


class FakeGitHub:
    """In-memory implementation of exactly the API operations used by the store."""
    def __init__(self):
        self.branch = False
        self.remote = None
        self.calls = []
        self.pending = None

    def call(self, method, route, data=None):
        self.calls.append((method, route))
        if route.startswith('git/ref/'):
            return {'object': {'sha': 'head'}} if self.branch else None
        if route.startswith('contents/') and method == 'GET':
            return self.remote
        if route.startswith('git/commits/'):
            return {'tree': {'sha': 'base-tree'}}
        if route == 'git/trees':
            self.pending = json.loads(data['tree'][0]['content'])
            return {'sha': 'new-tree'}
        if route == 'git/commits':
            return {'sha': 'new-commit'}
        if route == 'git/refs':
            if self.branch:
                raise RuntimeError('Branch initialization conflict')
            self.branch = True
            self.remote = {'sha': 'first', 'content': base64.b64encode(json.dumps(self.pending).encode()).decode()}
            return {'ref': data['ref']}
        if route.startswith('contents/') and method == 'PUT':
            if data['sha'] != self.remote['sha']:
                raise RuntimeError('HTTP 409: stale checkpoint')
            self.remote = {'sha': self.remote['sha'] + 'x', 'content': data['content']}
            return {'content': self.remote}
        raise AssertionError((method, route))


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.seed = ROOT/'config/story_checkpoint.json'
        self.story = unpack(json.loads(self.seed.read_text()))

    def tearDown(self):
        self.temp.cleanup()

    def test_seed_restores_two_verified_episodes_and_reserves_global_three(self):
        path = self.root/'state.sqlite3'
        restore(self.story,path)
        memory = Memory(path)
        try:
            row = memory.reserve('first-cloud-test')
            self.assertEqual(row['number'],3)
            self.assertEqual(row['status'],'planned')
            self.assertEqual(row['uid'],'series_002_e001')
            self.assertEqual(memory.reserve('first-cloud-test')['uid'],row['uid'])
            self.assertEqual(memory.db.execute("SELECT COUNT(*) FROM episodes WHERE status='verified'").fetchone()[0],2)
        finally:
            memory.close()

    def test_checksum_and_canon_tampering_are_rejected(self):
        value = envelope(self.story)
        value['story']['episodes'][0]['status'] = 'failed'
        with self.assertRaises(ValueError):
            unpack(value)
        value = copy.deepcopy(self.story)
        value['series'][0]['completed'] = 1
        with self.assertRaises(ValueError):
            envelope(value)

    def test_restore_never_overwrites_existing_database(self):
        path = self.root/'state.sqlite3'
        restore(self.story,path)
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            restore(self.story,path)
        self.assertEqual(before,path.read_bytes())

    def test_durable_initialization_recovery_and_failure_retry(self):
        api = FakeGitHub()
        path, receipt = self.root/'state.sqlite3', self.root/'receipt.json'
        recover(api,self.seed,path,receipt)
        memory = Memory(path)
        row = memory.reserve('github-123')
        memory.mark(row['uid'],'failed','synthetic render error')
        memory.close()
        with patch.dict(os.environ,{'GITHUB_SHA':'reviewed-source','GITHUB_RUN_ID':'123'}):
            persist(api,path,receipt)
        recovered = self.root/'recovered.sqlite3'
        new_receipt = self.root/'new-receipt.json'
        recover(api,self.seed,recovered,new_receipt)
        memory = Memory(recovered)
        self.assertEqual(memory.reserve('github-123')['number'],3)
        self.assertEqual(memory.reserve('github-124')['number'],3)
        memory.close()
        with patch.dict(os.environ,{'GITHUB_RUN_ID':'124'}):
            persist(api,recovered,new_receipt)
        self.assertTrue(api.branch)

    def test_stale_remote_write_fails_without_replacing_new_state(self):
        api = FakeGitHub()
        first, r1 = self.root/'one.sqlite3', self.root/'one.json'
        recover(api,self.seed,first,r1)
        with patch.dict(os.environ,{'GITHUB_SHA':'source'}):
            persist(api,first,r1)
        second, r2 = self.root/'two.sqlite3', self.root/'two.json'
        recover(api,self.seed,second,r2)
        persist(api,first,r1)
        newer = copy.deepcopy(api.remote)
        with self.assertRaises(RuntimeError):
            persist(api,second,r2)
        self.assertEqual(newer,api.remote)

    def test_existing_branch_without_checkpoint_fails_closed(self):
        api = FakeGitHub()
        api.branch = True
        with self.assertRaises(RuntimeError):
            recover(api,self.seed,self.root/'state.sqlite3',self.root/'receipt.json')
        self.assertFalse((self.root/'state.sqlite3').exists())

    def test_regression_or_verified_evidence_rewrite_is_rejected(self):
        changed = copy.deepcopy(self.story)
        evidence = json.loads(changed['episodes'][1]['evidence'])
        evidence['video_sha256'] = 'a'*64
        changed['episodes'][1]['evidence'] = json.dumps(evidence)
        with self.assertRaises(ValueError):
            refuse_regression(self.story,changed)
        changed = copy.deepcopy(self.story)
        changed['runs'] = []
        with self.assertRaises(ValueError):
            refuse_regression(self.story,changed)

    def test_manual_workflow_has_no_schedule_or_upload_step(self):
        text=(ROOT/'.github/workflows/autonomous_production.yml').read_text()
        self.assertNotIn('schedule:',text)
        self.assertNotIn('execute-private',text)
        self.assertNotIn('cloud_private_upload',text)
        self.assertIn('cloud_checkpoint.py restore',text)
        self.assertIn('Persist reservation before rendering',text)


if __name__=='__main__':
    unittest.main()
