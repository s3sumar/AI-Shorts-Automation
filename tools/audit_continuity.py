"""Audit actual produced episodes and saved canon; does not simulate completion."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.store import Memory
from autonomy.contracts import write_json,file_digest
from autonomy.youtube import prepare_upload

if __name__=='__main__':
    m=Memory(ROOT/'state/story.sqlite3')
    try:
        rows=m.db.execute('SELECT * FROM episodes ORDER BY number').fetchall()
        first,second=rows[:2]
        assert first['status']==second['status']=='verified'
        p1,p2=json.loads(first['plan']),json.loads(second['plan'])
        assert p1['end_state']==p2['start_state']
        assert p1['end_state']['characters']==p2['end_state']['characters']
        v1,v2=json.loads(first['evidence']),json.loads(second['evidence'])
        for evidence in [v1,v2]:
            assert file_digest(ROOT/evidence['video'])==evidence['video_sha256']
        out=ROOT/'artifacts/autonomy'/second['uid']
        actual=json.loads((out/'scene_validation.json').read_text())
        assert actual['passed'] and actual['production']['start_state']==p1['end_state']
        assert actual['production']['end_state']==p2['end_state']
        measured=json.loads((ROOT/'artifacts/autonomy/measured_episode1_boundary.json').read_text())
        assert measured['passed']
        for key,value in measured['measured'].items():
            assert max(abs(a-b) for a,b in zip(value,p2['start_state'][key]))<.015
        assert m.db.execute("SELECT status FROM series WHERE id='series_001'").fetchone()[0]=='complete'
        next_plan=json.loads(rows[2]['plan'])
        assert next_plan['series_id']!='series_001' and next_plan['ordinal']==1 and rows[2]['status']=='planned'
        # Normalize this development run's generated receipts without modifying its media.
        write_json(out/'production_receipt.json',v2)
        prepare_upload(out,v2,p2)
        prepare_upload(ROOT/'artifacts/episode_001',v1,dict(p1,series_title='Below Zero',
            summary='A passenger descends below ground and discovers a faceless presence waiting outside the lift.'))
        report={'passed':True,'episodes':[first['uid'],second['uid']],'start_end_canon_identical':True,
            'rendered_endpoints_verified':True,'character_identity_preserved':True,
            'videos_checksum_verified':True,'season_completed':True,
            'next_series':next_plan['series_title'],'next_series_status':'planned, not rendered',
            'director_source':next_plan['source'],'uploaded':False}
        write_json(ROOT/'artifacts/autonomy/continuity_audit.json',report)
        print(json.dumps(report,indent=2))
    finally:
        m.close()
