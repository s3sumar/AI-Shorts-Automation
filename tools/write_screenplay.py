"""Write an isolated screenplay and inspectable information-state treatment."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.screenwriter import write_delivery
from autonomy.suspense import validate_story


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--strategy',choices=['withdrawal','verification'],required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--subject',default='they');p.add_argument('--possessive',default='their')
    a=p.parse_args()
    if a.out.exists(): raise FileExistsError('Preserve completed screenplays; choose a new output')
    plan=json.loads(a.plan.read_text())
    script=write_delivery(plan,a.strategy,{'subject':a.subject,'possessive':a.possessive,'object':'parcel'})
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(script,indent=2))
    review=validate_story(script['suspense'],script['narration'])
    a.out.with_suffix('.states.json').write_text(json.dumps(review,indent=2))
    rows=[script['title']+' — '+a.strategy,'Planned windows; actual speech timing is measured during synthesis.','']
    for line in script['narration']:
        rows.append(f'{line["start"]:05.2f}–{line["end"]:05.2f} {line["role"].upper()} [{line["emotion"]}]\n{line["text"]}\n')
    a.out.with_suffix('.txt').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps({'script':str(a.out),'choices':review['choices'],'consequences':review['consequences'],'status':'structurally checked; editorial review pending'},indent=2))
