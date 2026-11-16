"""Isolated Episode 3 editorial staging. Does not reserve or commit story state."""
from .directing import lift_director_pass


def return_to_sender(score):
    c=lift_director_pass(score)
    first=c['shots'][0]
    first.update(id='delivery_hook',lens=32,subject='Courier parcel',
                 **{'from':[.1,-2.3,1.2],'to':[.85,-5.2,2.58],
                    'target':[-.18,-.99,.8],'target_to':[-.1,.8,1.9]})
    for shot in c['shots']:
        if shot['id']=='listening_reaction':
            shot.update(lens=32,subject='Emergency stop button',
                        **{'from':[.9,-2.7,2.2],'to':[.75,-2.6,2.15],'target':[-1.2,.3,1.65]})
        elif shot['id']=='wrong_floor':
            shot.update(lens=46,**{'from':[.08,-.9,3.6],'to':[.02,-.8,3.62],'target':[0,1.58,3.58]})
        elif shot['id']=='shoulder':
            shot.update(lens=28,**{'from':[.5,-4.2,2.75],'to':[.4,-4.0,2.7],'target':[0,3.2,1.9]})
        elif shot['id']=='presence':
            shot.update(lens=32,subject='Passenger head',
                        **{'from':[1.4,2.9,2.3],'to':[1.25,2.7,2.25],'target':[-.7,-.35,1.55]})
        elif shot['id']=='approach':
            shot.update(lens=28,**{'from':[1.1,-5.1,2.65],'to':[1,-4.8,2.6],'target':[-.1,2.2,1.8]})
    c['motion']['passenger.head.rotation_euler']=[
        [0,[0,0,-.1]],[2.2,[0,0,-.1]],[4.6,[-.2,0,.3]],
        [8.8,[-.2,0,.3]],[9.3,[0,0,.85]],[10.3,[0,0,.85]],
        [14,[.13,0,.1]],[17,[.13,0,.1]],[19.8,[0,0,.7]],
        [20.8,[.1,0,-.6]],[22.2,[.1,0,-.6]],[24,[-.13,0,.35]],
        [26.15,[.18,0,-.1]],[27.5,[-.08,0,.25]],
        [29,[0,0,.65]],[30,[-.05,0,1.3]],[34,[-.05,0,1]],
        [38,[-.03,0,1]],[43,[-.03,0,1]],[45,[-.03,0,2.35]]]
    c['motion']['passenger.arm.R.rotation_euler']=[
        [0,[0,0,-.1]],[2,[0,0,0]],[14.1,[0,0,0]],
        [14.7,[-.12,.08,0]],[17.4,[-.12,.08,0]],[20,[0,0,0]],
        [25,[0,0,0]],[26.2,[-.35,.3,0]],[28,[-.1,.12,0]],
        [34,[-.1,.12,0]],[36,[-1.05,.65,0]],[42.5,[-1.05,.65,0]],
        [45,[-.3,.3,0]]]
    c['directing'].update(performance_v4=True,
        body_turn=[[29,[0,0,0]],[30,[0,0,.6]],[34,[0,0,1.8]],[43.5,[0,0,1.8]],[45,[0,0,0]]],
        intentional_holds=[{'start':29,'end':34.6,'reason':'Opening doors reveal the threat before the courier refuses'},
                           {'start':37.6,'end':40.6,'reason':'Protective gesture and retreat precede the answer'}])
    return c
