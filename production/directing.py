"""Original lift-specific coverage and performance, independent of reference assets."""
import copy


def lift_director_pass(score):
    c=copy.deepcopy(score)
    if c['opening_floor']!='13':
        raise ValueError('This directing pass supports the arrival episode only')
    shots=[]
    for shot in c['shots']:
        if shot['id']!='countdown_fast':
            shots.append(shot)
            continue
        first=copy.deepcopy(shot); first['end']=14.5; first.pop('shake',None)
        parcel={'id':'parcel_evidence','start':14.5,'end':17.5,'lens':48,
                'from':[.23,-1.9,1.15],'to':[.12,-1.68,1.09],
                'target':[-.18,-.11,.8],'subject':'Courier parcel'}
        middle=copy.deepcopy(shot);middle.update(id='countdown_pressure',start=17.5,end=20)
        reaction={'id':'listening_reaction','start':20,'end':22.5,'lens':40,
                  'from':[.6,-2.8,2.62],'to':[.5,-2.65,2.58],
                  'target':[-.65,0,2.1],'subject':'Passenger head'}
        last=copy.deepcopy(shot);last.update(id='countdown_last',start=22.5)
        shots.extend([first,parcel,middle,reaction,last])
    c['shots']=shots
    original=c['motion']['passenger.head.rotation_euler']
    head=[]
    for t,value in original:
        value=list(value)
        yaw=0 if t<=29 else 1.05*min((t-29)/5,1) if t<=43.5 else 1.05*max((45-t)/1.5,0)
        value[2]-=yaw
        head.append([t,value])
    head.extend([[.9,[0,0,.65]],[1.8,[0,0,.65]],[3.5,[0,0,-.1]]])
    c['motion']['passenger.head.rotation_euler']=sorted(head,key=lambda p:p[0])
    c['directing']={'profile':'original_lift_v1','parcel':True,'intercom_light':True,'cohesive_face_details':True,
                    'body_turn':[[29,[0,0,0]],[34,[0,0,1.05]],[42,[0,0,1.05]],[43.5,[0,0,1.05]],[45,[0,0,0]]],
                    'radio_light':[[0,0],[.15,2],[1.6,2],[2,0],[16.5,0],[17,1.5],[19.8,0],[45,0]],
                    'intentional_holds':[{'start':12.2,'end':14.6,'reason':'Reveal the delivery label through a close insert'},
                                         {'start':32.6,'end':34.2,'reason':'Let the opening doors expose the silhouette before narration resumes'}],
                    'originality':'Original courier, parcel and sealed-floor story; no reference characters, dialogue, graphics or audio'}
    return c


def assess_coverage(c):
    long_inserts=[s['id'] for s in c['shots'] if s.get('subject','').startswith('Display') and s['end']-s['start']>4.01]
    shots=c['shots']
    complete=bool(shots) and shots[0]['start']==0 and shots[-1]['end']==c['duration']
    complete=complete and all(a['end']==b['start'] for a,b in zip(shots,shots[1:]))
    complete=complete and all(s['end']>s['start'] for s in shots)
    parcel=any(s.get('subject')=='Courier parcel' for s in shots)
    return {'shot_count':len(c['shots']),'unbroken_display_inserts_over_4s':long_inserts,
            'parcel_has_assigned_shot':parcel,'complete_timeline':complete,
            'passed':not long_inserts and complete and parcel}
