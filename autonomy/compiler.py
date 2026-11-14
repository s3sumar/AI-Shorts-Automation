"""Compile safe story grammar into the existing, fully explicit Blender score.

Models never return Python, asset paths, arbitrary properties or shell commands.
"""
import copy
import json
from .contracts import ROOT,digest,validate_plan


def compile_plan(plan,settings):
    validate_plan(plan)
    c=json.loads((ROOT/'episodes/episode_001.json').read_text(encoding='utf-8'))
    c.update(episode=plan['global_number'],title=plan['title'],series=plan['series_title'])
    c['preview']=copy.deepcopy(settings['preview'])
    c['character_color']=plan['start_state']['characters']['protagonist']['color']
    c['environment']={'id':plan['environment']}
    c['production']={'uid':plan['uid'],'series_id':plan['series_id'],'ordinal':plan['ordinal'],
        'source':plan['source'],'plan_hash':digest(plan),'start_state':plan['start_state'],'end_state':plan['end_state']}
    c['continuity']={'protagonist':plan['start_state']['characters']['protagonist']['name'],
        'antagonist':plan['start_state']['characters']['antagonist']['name'],'summary':plan['summary']}
    for cue,line in zip(c['narration'],plan['radio_lines']):
        cue['text']=line
    c['captions']=[{'start':0,'end':.65,'text':plan['title'].upper()}]+copy.deepcopy(c['narration'])
    c['captions'].append({'start':43.3,'end':45,'text':'THE SIGNAL IS SEALED.\nEND OF '+plan['series_title'].upper()
                          if plan['season_finale'] else 'THE SIGNAL REMEMBERS.\nTO BE CONTINUED'})
    if plan['kind']=='arrival':
        return c
    state=plan['start_state']
    end=plan['end_state']
    c['floor_events']=[[0,state['floor']],[21,''],[21.2,state['floor']],[24,'0']]
    c['opening_floor'],c['ending_floor']=state['floor'],end['floor']
    c['door_events']=[[0,state['doors']],[14,1],[19,0],[29.5,0],[35.5,1],[45,1]]
    c['shadow_visibility']=[[0,True],[19,True],[20,False],[45,False]]
    c['lighting']['cold']=[1,.018,.027]
    c['lighting']['emergency']=[.28,.57,1]
    c['lighting']['power']=[[0,.85],[17.7,.85],[18,.08],[18.12,.85],[25.7,.85],[26,0],[26.55,0],[27.4,1],[45,1]]
    c['lighting']['rim_events']=[[0,180],[25.7,180],[26,0],[45,0]]
    c['facial_reactions']=[[0,.075],[19,.075],[29,.025],[43,0],[45,0]]
    p=state['passenger_position']
    c['motion']['passenger.root.location']=[[0,p],[25.7,p],[26,[p[0],p[1],-.04]],
        [26.3,[p[0],p[1],0]],[37,p],[39,[-.7,.35,.02]],[40.5,[-.55,1.1,0]],[42,end['passenger_position']],[45,end['passenger_position']]]
    c['motion']['passenger.head.rotation_euler']=[[0,state['passenger_head']],[4,state['passenger_head']],
        [9,[-.1,0,.3]],[24,[-.1,0,.3]],[27,[0,0,.2]],[32,[0,0,2.35]],[45,end['passenger_head']]]
    for side,label in [(-1,'L'),(1,'R')]:
        c['motion']['passenger.arm.'+label+'.rotation_euler']=[[0,[-.3,side*.3,0]],[4,[-.1,side*.1,0]],
            [26,[-.25,side*.25,0]],[29,[-.1,side*.1,0]],[38,[0,0,0]],[45,[0,0,0]]]
        c['motion']['shadow.leg.'+label+'.rotation_euler']=[[0,state['shadow_leg_l' if label=='L' else 'shadow_leg_r']],
            [45,state['shadow_leg_l' if label=='L' else 'shadow_leg_r']]]
    c['motion']['shadow.root.location']=[[0,state['shadow_position']],[45,state['shadow_position']]]
    c['motion']['shadow.head.rotation_euler']=[[0,state['shadow_head']],[45,state['shadow_head']]]
    c['motion']['shadow.body.rotation_euler']=[[0,[0,0,0]],[45,[0,0,0]]]
    c['effects']['entry_end']=2.2
    shots=c['shots']
    shots[2]['end']=14
    seal=copy.deepcopy(shots[6])
    seal.update(id='doors_seal',start=14,end=19)
    shots[3]['start']=19
    shots[3].pop('shake',None)
    shots.insert(3,seal)
    for shot in shots:
        if shot['id'] in ['shoulder','presence','approach']:
            shot['subject']='Corridor darkness'
            shot['target']=[0,9.4,2]
    # Steady exit after ground return; keep the hall in view as the passenger leaves.
    c['effects']['fear_start']=37
    c['audio_cues']=[cue for cue in c['audio_cues'] if cue['type']!='knock']
    c['audio_cues'].append({'type':'doors','start':14,'end':19,'gain':.13})
    return c
