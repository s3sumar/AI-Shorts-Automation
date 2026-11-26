"""Transactional creative-series ledger and portable durable recovery.

Independent of the protected pilot ledger. Reservations survive failed media
production; verified commits advance exactly one episode. No uploading here.
"""
import copy
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from .contracts import digest,file_digest
from .creative_contract import initial_memory,validate_bible,validate_memory,validate_episode,propose_memory


class CreativeStore:
    def __init__(self,path):
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists() and self.path.stat().st_size:
            with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)) as check:
                columns={r[1] for r in check.execute('PRAGMA table_info(series)')}
                if columns and columns!={'id','bible','memory'}:
                    raise ValueError('Refusing to modify a legacy or unrelated database as creative state')
        self.db=sqlite3.connect(self.path,timeout=30,isolation_level=None);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS series(id TEXT PRIMARY KEY,bible TEXT NOT NULL,memory TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS episodes(uid TEXT PRIMARY KEY,series_id TEXT NOT NULL REFERENCES series(id),
            ordinal INTEGER NOT NULL,script TEXT NOT NULL,prior_hash TEXT NOT NULL,status TEXT NOT NULL,
            evidence TEXT,error TEXT,UNIQUE(series_id,ordinal));
          CREATE TABLE IF NOT EXISTS runs(run_key TEXT PRIMARY KEY,uid TEXT NOT NULL REFERENCES episodes(uid));
          CREATE TABLE IF NOT EXISTS reviews(uid TEXT PRIMARY KEY REFERENCES episodes(uid),receipt TEXT NOT NULL);
        ''')

    def close(self):self.db.close()

    def initialize(self,bible,memory=None):
        validate_bible(bible);memory=copy.deepcopy(memory or initial_memory(bible));validate_memory(memory,bible)
        row=self.db.execute('SELECT * FROM series WHERE id=?',(bible['id'],)).fetchone()
        if row:
            if json.loads(row['bible'])!=bible:raise ValueError('Cannot replace an existing series bible')
            return json.loads(row['memory'])
        self.db.execute('INSERT INTO series VALUES(?,?,?)',(bible['id'],json.dumps(bible),json.dumps(memory)))
        return memory

    def current(self,series_id):
        row=self.db.execute('SELECT * FROM series WHERE id=?',(series_id,)).fetchone()
        if not row:raise ValueError('Unknown creative series')
        return json.loads(row['bible']),json.loads(row['memory'])

    def by_run(self,key):
        row=self.db.execute('SELECT e.* FROM episodes e JOIN runs r ON r.uid=e.uid WHERE r.run_key=?',(key,)).fetchone()
        return dict(row) if row else None

    def reserve(self,bible,episode,run_key):
        if not isinstance(run_key,str) or not 1<=len(run_key)<=150:raise ValueError('Bounded run key required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.by_run(run_key)
            if old:
                if json.loads(old['script'])!=episode:raise ValueError('Run key cannot refer to a different script')
                self.db.execute('COMMIT');return old
            b,m=self.current(bible['id'])
            if b!=bible:raise ValueError('Series bible changed')
            pending=self.db.execute("SELECT * FROM episodes WHERE series_id=? AND status!='verified'",(bible['id'],)).fetchone()
            if pending:
                # Reuse the failed/pending script, not a newly generated competitor.
                if json.loads(pending['script'])!=episode:raise ValueError('A pending episode must be recovered before generating another')
                uid=pending['uid']
            else:
                validate_episode(episode,b,m);uid=b['id']+f'_e{episode["episode"]:03d}'
                self.db.execute('INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?)',
                    (uid,b['id'],episode['episode'],json.dumps(episode),digest(m),'planned',None,None))
            self.db.execute('INSERT INTO runs VALUES(?,?)',(run_key,uid))
            row=dict(self.db.execute('SELECT * FROM episodes WHERE uid=?',(uid,)).fetchone())
            self.db.execute('COMMIT');return row
        except Exception:self.db.execute('ROLLBACK');raise

    def fail(self,uid,message):
        self.db.execute("UPDATE episodes SET status='failed',error=? WHERE uid=? AND status!='verified'",(str(message)[:500],uid))

    def save_review(self,uid,receipt):
        row=self.db.execute('SELECT receipt FROM reviews WHERE uid=?',(uid,)).fetchone()
        if row and json.loads(row['receipt'])!=receipt:raise ValueError('Cannot rewrite the editorial provenance of a reservation')
        if not row:self.db.execute('INSERT INTO reviews VALUES(?,?)',(uid,json.dumps(receipt)))

    def commit_verified(self,uid,evidence,video_path):
        if not all(evidence.get(k) is True for k in ['passed','scene_passed','audio_passed','full_decode_passed']):raise ValueError('Complete media verification required')
        if evidence.get('video_sha256')!=file_digest(video_path):raise ValueError('Verified video is missing or changed')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT * FROM episodes WHERE uid=?',(uid,)).fetchone()
            if not row:raise ValueError('Unknown reservation')
            if row['status']=='verified':
                if json.loads(row['evidence'])!=evidence:raise ValueError('Cannot replace verified evidence')
                self.db.execute('COMMIT');return
            bible,memory=self.current(row['series_id']);episode=json.loads(row['script'])
            if row['prior_hash']!=digest(memory) or evidence.get('script_sha256')!=digest(episode) or evidence.get('input_memory_sha256')!=digest(memory):
                raise ValueError('Stale creative state or mismatched media')
            next_memory=propose_memory(episode,bible,memory)
            self.db.execute('UPDATE series SET memory=? WHERE id=?',(json.dumps(next_memory),bible['id']))
            self.db.execute("UPDATE episodes SET status='verified',evidence=?,error=NULL WHERE uid=?",(json.dumps(evidence),uid))
            self.db.execute('COMMIT')
        except Exception:self.db.execute('ROLLBACK');raise

    def snapshot(self):
        self.db.execute('BEGIN')
        try:
            value={'schema':1,'series':[dict(r) for r in self.db.execute('SELECT * FROM series ORDER BY id')],
                   'episodes':[dict(r) for r in self.db.execute('SELECT * FROM episodes ORDER BY uid')],
                   'runs':[dict(r) for r in self.db.execute('SELECT * FROM runs ORDER BY run_key')],
                   'reviews':[dict(r) for r in self.db.execute('SELECT * FROM reviews ORDER BY uid')]}
            self.db.execute('COMMIT')
        except Exception:self.db.execute('ROLLBACK');raise
        validate_snapshot(value)
        return {'format':2,'sha256':digest(value),'creative_store':value}

    def restore(self,value):
        state=unpack_snapshot(value)
        if self.db.execute('SELECT COUNT(*) FROM series').fetchone()[0]:raise FileExistsError('Restore only into an empty creative ledger')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            for table,columns in [('series',['id','bible','memory']),('episodes',['uid','series_id','ordinal','script','prior_hash','status','evidence','error']),('runs',['run_key','uid']),('reviews',['uid','receipt'])]:
                for row in state.get(table,[]):
                    self.db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in columns)+')',[row[c] for c in columns])
            self.db.execute('COMMIT')
        except Exception:self.db.execute('ROLLBACK');raise


def validate_snapshot(state):
    if state.get('schema')!=1:raise ValueError('Unsupported creative ledger snapshot')
    series={r['id']:r for r in state['series']}
    if len(series)!=len(state['series']):raise ValueError('Duplicate creative series')
    ids=set();ordinals=set()
    for sid,row in series.items():
        b=json.loads(row['bible']);m=json.loads(row['memory']);validate_bible(b);validate_memory(m,b)
        if b['id']!=sid:raise ValueError('Snapshot series identity mismatch')
    for row in state['episodes']:
        if row['uid'] in ids or (row['series_id'],row['ordinal']) in ordinals:raise ValueError('Duplicate snapshot episode')
        ids.add(row['uid']);ordinals.add((row['series_id'],row['ordinal']))
        if row['series_id'] not in series or row['status'] not in ['planned','failed','verified']:raise ValueError('Invalid snapshot reservation')
        ep=json.loads(row['script']);s=series[row['series_id']];m=json.loads(s['memory'])
        if ep['episode']!=row['ordinal'] or ep['series_id']!=row['series_id'] or ep['prior_memory_sha256']!=row['prior_hash']:raise ValueError('Snapshot script/reservation mismatch')
        if row['status']=='verified':
            evidence=json.loads(row['evidence'])
            if not all(evidence.get(k) is True for k in ['passed','scene_passed','audio_passed','full_decode_passed']) or evidence['script_sha256']!=digest(ep):raise ValueError('Unverified creative snapshot media')
            entry=next((h for h in m['history'] if h['episode']==row['ordinal']),None)
            if not entry or entry['script_sha256']!=digest(ep):raise ValueError('Snapshot memory lost an episode')
        else:validate_episode(ep,json.loads(s['bible']),m)
    keys=set()
    for row in state['runs']:
        if row['run_key'] in keys or row['uid'] not in ids:raise ValueError('Invalid snapshot run')
        keys.add(row['run_key'])
    reviewed=set()
    for row in state.get('reviews',[]):
        if row['uid'] not in ids or row['uid'] in reviewed:raise ValueError('Invalid snapshot editorial receipt')
        reviewed.add(row['uid']);receipt=json.loads(row['receipt'])
        if receipt.get('authorship') not in ['authored_development_example','hosted_model']:raise ValueError('Editorial provenance must identify authorship')
    return state


def unpack_snapshot(value):
    if value.get('format')!=2 or value.get('sha256')!=digest(value['creative_store']):raise ValueError('Creative ledger checksum mismatch')
    return validate_snapshot(value['creative_store'])
