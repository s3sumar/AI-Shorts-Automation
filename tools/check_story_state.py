"""Check SQLite integrity and close/checkpoint it before persisting a cloud cache."""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--allow-missing',action='store_true')
    a=p.parse_args()
    path=ROOT/'state/story.sqlite3'
    if not path.exists():
        if a.allow_missing:
            print('No story memory to checkpoint')
            raise SystemExit(0)
        raise FileNotFoundError('No story memory')
    connection=sqlite3.connect(path)
    integrity=connection.execute('PRAGMA integrity_check').fetchone()[0]
    if integrity!='ok':
        raise RuntimeError('SQLite integrity check failed')
    connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    rows=connection.execute('SELECT uid,status FROM episodes ORDER BY number').fetchall()
    connection.close()
    print(json.dumps({'integrity':integrity,'episodes':rows}))
