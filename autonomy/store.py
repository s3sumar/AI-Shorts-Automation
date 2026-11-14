"""SQLite story ledger: planning is idempotent; canon advances only after verification."""
import copy
import json
import sqlite3
from pathlib import Path
from .contracts import digest,file_digest,write_json,ROOT
from .director import initial_state,arrival_end,new_series,plan_episode


class Memory:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS series(id TEXT PRIMARY KEY,bible TEXT NOT NULL,canon TEXT NOT NULL,
          completed INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'active');
        CREATE TABLE IF NOT EXISTS episodes(uid TEXT PRIMARY KEY,series_id TEXT NOT NULL REFERENCES series(id),
          ordinal INTEGER NOT NULL,number INTEGER NOT NULL,status TEXT NOT NULL,plan TEXT NOT NULL,
          evidence TEXT,error TEXT,UNIQUE(series_id,ordinal));
        CREATE TABLE IF NOT EXISTS runs(run_key TEXT PRIMARY KEY,uid TEXT NOT NULL REFERENCES episodes(uid));
        ''')
        # Portable relative media references for memory restored on Linux runners.
        for row in self.db.execute('SELECT uid,evidence FROM episodes WHERE evidence IS NOT NULL').fetchall():
            value=json.loads(row['evidence'])
            changed=False
            for key in ['video','scene','video_report']:
                if isinstance(value.get(key),str) and '\\' in value[key]:
                    value[key]=value[key].replace('\\','/')
                    changed=True
            if changed:
                self.db.execute('UPDATE episodes SET evidence=? WHERE uid=?',(json.dumps(value),row['uid']))

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.db.close()

    def bootstrap(self,verify_local=True):
        if self.db.execute('SELECT COUNT(*) FROM series').fetchone()[0]:
            return
        seed_path=ROOT/'config/verified_episode_001.json'
        seed=json.loads(seed_path.read_text())
        if verify_local:
            video=ROOT/seed['video']
            report=json.loads((ROOT/seed['video_report']).read_text())
            if not report.get('full_decode_passed') or file_digest(video)!=seed['video_sha256']:
                raise ValueError('Episode 1 seed video does not match verified provenance')
        start=initial_state()
        end=arrival_end(start)
        bible={'id':'series_001','title':'Below Zero','premise':'A sealed lower floor borrows the voices of its visitors.',
            'environment':'lift_013','season_length':2,'source':'verified_original','canon':end}
        plan={'uid':'series_001_e001','series_id':'series_001','ordinal':1,'global_number':1,
              'start_state':start,'end_state':end,'start_hash':digest(start),'title':'The Floor Below Zero','kind':'arrival'}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT INTO series VALUES(?,?,?,?,?)',('series_001',json.dumps(bible),json.dumps(end),1,'active'))
            self.db.execute('INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?)',
                ('series_001_e001','series_001',1,1,'verified',json.dumps(plan),json.dumps(seed),None))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def reserve(self,run_key,model=None):
        if not isinstance(run_key,str) or not 1<=len(run_key)<=200:
            raise ValueError('A bounded, nonempty run key is required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            existing=self.db.execute('SELECT e.* FROM episodes e JOIN runs r ON r.uid=e.uid WHERE r.run_key=?',(run_key,)).fetchone()
            if existing:
                self.db.execute('COMMIT')
                return dict(existing)
            current=self.db.execute("SELECT * FROM episodes WHERE status!='verified' ORDER BY number LIMIT 1").fetchone()
            if current:
                self.db.execute('INSERT INTO runs VALUES(?,?)',(run_key,current['uid']))
                self.db.execute('COMMIT')
                return dict(current)
            row=self.db.execute('SELECT * FROM series ORDER BY rowid DESC LIMIT 1').fetchone()
            if row is None:
                raise ValueError('No story memory. Explicit bootstrap or restore a verified snapshot first.')
            if row['status']=='complete':
                index=self.db.execute('SELECT COUNT(*) FROM series').fetchone()[0]+1
                bible=new_series(index,model)
                self.db.execute('INSERT INTO series VALUES(?,?,?,?,?)',(bible['id'],json.dumps(bible),json.dumps(bible['canon']),0,'active'))
                completed=0
            else:
                bible=json.loads(row['bible'])
                bible['canon']=json.loads(row['canon'])
                completed=row['completed']
            number=self.db.execute('SELECT COALESCE(MAX(number),0)+1 FROM episodes').fetchone()[0]
            plan=plan_episode(bible,completed+1,number,model)
            self.db.execute('INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?)',
                (plan['uid'],bible['id'],completed+1,number,'planned',json.dumps(plan),None,None))
            self.db.execute('INSERT INTO runs VALUES(?,?)',(run_key,plan['uid']))
            result=dict(self.db.execute('SELECT * FROM episodes WHERE uid=?',(plan['uid'],)).fetchone())
            self.db.execute('COMMIT')
            return result
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def mark(self,uid,status,error=None):
        if status not in ['rendering','failed']:
            raise ValueError('Invalid production status')
        self.db.execute("UPDATE episodes SET status=?,error=? WHERE uid=? AND status!='verified'",(status,error,uid))

    def commit_verified(self,uid,evidence):
        if evidence.get('passed') is not True or not evidence.get('video_sha256') or not evidence.get('scene_passed') or not evidence.get('audio_passed'):
            raise ValueError('Missing verification evidence')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT * FROM episodes WHERE uid=?',(uid,)).fetchone()
            if not row:
                raise ValueError('Unknown episode')
            if row['status']=='verified':
                old=json.loads(row['evidence'])
                if old.get('video_sha256')!=evidence['video_sha256']:
                    raise ValueError('Verified episode is immutable')
                self.db.execute('COMMIT')
                return
            plan=json.loads(row['plan'])
            series=self.db.execute('SELECT * FROM series WHERE id=?',(row['series_id'],)).fetchone()
            if digest(json.loads(series['canon']))!=plan['start_hash'] or series['completed']+1!=row['ordinal']:
                raise ValueError('Continuity changed since planning; refusing stale commit')
            bible=json.loads(series['bible'])
            status='complete' if row['ordinal']>=bible['season_length'] else 'active'
            self.db.execute('UPDATE episodes SET status=?,evidence=?,error=NULL WHERE uid=?',('verified',json.dumps(evidence),uid))
            self.db.execute('UPDATE series SET canon=?,completed=?,status=? WHERE id=?',
                            (json.dumps(plan['end_state']),row['ordinal'],status,row['series_id']))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def export(self,path):
        write_json(path,{'schema':1,'series':[dict(r) for r in self.db.execute('SELECT * FROM series ORDER BY id')],
                        'episodes':[dict(r) for r in self.db.execute('SELECT * FROM episodes ORDER BY number')],
                        'runs':[dict(r) for r in self.db.execute('SELECT * FROM runs ORDER BY run_key')]})

    def backup(self,path):
        if Path(path).exists():
            raise FileExistsError('Refusing to overwrite a story-memory backup')
        destination=sqlite3.connect(path)
        self.db.backup(destination)
        destination.close()
