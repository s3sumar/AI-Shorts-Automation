"""Validated, portable story checkpoints. Never includes media, databases or secrets."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from .contracts import digest, identifier, validate_plan, write_json
from .store import Memory


def validate(snapshot):
    if snapshot.get('schema') != 1:
        raise ValueError('Unknown checkpoint schema')
    series = {s['id']: s for s in snapshot['series']}
    if len(series) != len(snapshot['series']) or not series:
        raise ValueError('Invalid series inventory')
    ids, numbers, verified = set(), [], {}
    for row in snapshot['episodes']:
        identifier(row['uid'])
        plan = json.loads(row['plan'])
        if row['uid'] in ids or row['series_id'] not in series:
            raise ValueError('Duplicate episode or missing series')
        ids.add(row['uid'])
        numbers.append(row['number'])
        if (plan['uid'], plan['series_id'], plan['ordinal'], plan['global_number']) != (row['uid'], row['series_id'], row['ordinal'], row['number']):
            raise ValueError('Plan identity mismatch')
        if plan['start_hash'] != digest(plan['start_state']):
            raise ValueError('Invalid continuity hash')
        if row['number'] != 1:
            validate_plan(plan)
        if row['status'] not in ['planned', 'rendering', 'failed', 'verified']:
            raise ValueError('Invalid episode status')
        if row['status'] == 'verified':
            evidence = json.loads(row['evidence'])
            if not all(evidence.get(k) for k in ['passed', 'scene_passed', 'audio_passed']):
                raise ValueError('Unverified checkpoint media')
            checksum = evidence.get('video_sha256', '')
            if len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
                raise ValueError('Invalid verified media checksum')
            verified.setdefault(row['series_id'], []).append(plan)
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError('Episode numbering must be contiguous')
    for sid, row in series.items():
        identifier(sid)
        plans = verified.get(sid, [])
        if row['completed'] != len(plans):
            raise ValueError('Completed count mismatch')
        for first, second in zip(plans, plans[1:]):
            if first['end_state'] != second['start_state']:
                raise ValueError('Broken episode continuity')
        bible = json.loads(row['bible'])
        canon = json.loads(row['canon'])
        if plans and canon != plans[-1]['end_state']:
            raise ValueError('Series canon mismatch')
        expected = 'complete' if len(plans) >= bible['season_length'] else 'active'
        if row['status'] != expected:
            raise ValueError('Season status mismatch')
        pending = [e for e in snapshot['episodes'] if e['series_id'] == sid and e['status'] != 'verified']
        for episode in pending:
            plan = json.loads(episode['plan'])
            if plan['start_state'] != canon or episode['ordinal'] != len(plans) + 1:
                raise ValueError('Pending episode has stale canon')
    if sum(e['status'] != 'verified' for e in snapshot['episodes']) > 1:
        raise ValueError('Multiple pending episodes')
    keys = set()
    for run in snapshot['runs']:
        if run['uid'] not in ids or run['run_key'] in keys:
            raise ValueError('Invalid run reservation')
        keys.add(run['run_key'])
    return snapshot


def capture(path):
    # Read only: do not migrate or mutate the user's working ledger.
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Checkpoint source database is corrupt')
        result = {'schema': 1, 'series': [dict(r) for r in db.execute('SELECT * FROM series ORDER BY rowid')],
                  'episodes': [dict(r) for r in db.execute('SELECT * FROM episodes ORDER BY number')],
                  'runs': [dict(r) for r in db.execute('SELECT * FROM runs ORDER BY run_key')]}
    return validate(result)


def envelope(snapshot):
    validate(snapshot)
    return {'format': 1, 'sha256': digest(snapshot), 'story': snapshot}


def unpack(value):
    if value.get('format') != 1 or value.get('sha256') != digest(value['story']):
        raise ValueError('Checkpoint checksum mismatch')
    return validate(value['story'])


def restore(snapshot, path):
    validate(snapshot)
    path = Path(path)
    if path.exists():
        raise FileExistsError('Refusing to replace existing story memory')
    memory = Memory(path)
    try:
        with memory.db:
            memory.db.execute('BEGIN IMMEDIATE')
            for table, columns in [('series', ['id','bible','canon','completed','status']),
                                   ('episodes', ['uid','series_id','ordinal','number','status','plan','evidence','error']),
                                   ('runs', ['run_key','uid'])]:
                for row in snapshot[table]:
                    memory.db.execute('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in columns) + ')',
                                      [row[c] for c in columns])
    finally:
        memory.close()


def refuse_regression(previous, current):
    old = {e['uid']: e for e in validate(previous)['episodes']}
    new = {e['uid']: e for e in validate(current)['episodes']}
    for uid, row in old.items():
        if uid not in new or row['plan'] != new[uid]['plan']:
            raise ValueError('Checkpoint would lose or rewrite an episode')
        if row['status'] == 'verified' and (new[uid]['status'] != 'verified' or row['evidence'] != new[uid]['evidence']):
            raise ValueError('Checkpoint would change verified evidence')
    if not {(r['run_key'],r['uid']) for r in previous['runs']} <= {(r['run_key'],r['uid']) for r in current['runs']}:
        raise ValueError('Checkpoint would lose run reservations')
