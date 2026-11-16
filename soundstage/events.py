"""Reusable sound categories anchored to the authored animation, not random time cues."""
import math
import numpy as np
from .media import SR

CATEGORIES={'environment','footstep','movement','mechanical','doors','radio','alarm','impact','transition','cliffhanger'}


def event_plan(c):
    end=c['duration']
    events=[{'category':'environment','start':0,'end':end,'gain':.075,'anchor':'scene duration'},
            {'category':'mechanical','start':0,'end':c['effects']['impact_time'],'gain':.06,'anchor':'descent until impact'},
            {'category':'movement','start':c['effects']['impact_time'],'end':c['effects']['impact_time']+.4,'gain':.035,'anchor':'passenger recoil'},
            {'category':'impact','start':c['effects']['impact_time'],'end':c['effects']['impact_time']+.8,'gain':.32,'anchor':'impact keyframe'},
            {'category':'transition','start':max(0,c['effects']['impact_time']-1.8),'end':c['effects']['impact_time'],'gain':.08,'anchor':'blackout approach'},
            {'category':'radio','start':23.7,'end':25.5,'gain':.025,'anchor':'floor glitch'},
            {'category':'cliffhanger','start':c['effects']['cut_black']-.25,'end':end-.15,'gain':.17,'anchor':'cut to black'},
            {'category':'alarm','start':c['effects']['red_at'],'end':c['effects']['red_at']+.65,'gain':.07,'anchor':'red-light recovery'}]
    if c.get('directing',{}).get('intercom_light'):
        events.extend([{'category':'radio','start':.15,'end':2,'gain':.012,'anchor':'intercom status pulse'},
                       {'category':'radio','start':16.5,'end':19.8,'gain':.015,'anchor':'intercom activity then silence'}])
    doors=c.get('door_events',[[0,0],[c['effects']['door_start'],0],[c['effects']['door_end'],1]])
    for (a,x),(b,y) in zip(doors,doors[1:]):
        if x!=y:
            events.append({'category':'doors','start':a,'end':b,'gain':.08,'anchor':'door aperture keyframes'})
    entry=c['effects']['entry_end']; fear=c['effects']['fear_start']
    for i,t in enumerate([entry*.36,entry,fear+.7,fear+1.7]):
        if t<end:
            events.append({'category':'footstep','start':t,'end':min(t+.24,end),'gain':.10,
                'pan':(-.2 if i%2==0 else .2),'anchor':'passenger step animation keys'})
    roots=c['motion']['shadow.root.location']
    for i,((t,p),(next_t,next_p)) in enumerate(zip(roots,roots[1:])):
        if p!=next_p and next_t<end:
            events.append({'category':'footstep','start':next_t,'end':min(next_t+.3,end),'gain':.12,
                'pan':.25,'anchor':'antagonist root step landing key'})
    for t,value in c['floor_events']:
        if value=='-1':
            events.append({'category':'alarm','start':t,'end':min(t+.25,end),'gain':.035,'anchor':'display becomes -1'})
    if c.get('directing',{}).get('performance_v4'):
        events=[e for e in events if not(e['category']=='radio' and e['start']>=19.8)]
        events.append({'category':'impact','start':20.9,'end':21.03,'gain':.012,'anchor':'failed emergency stop press'})
    return sorted(events,key=lambda e:e['start'])


def sound(category,duration,seed=0):
    if category not in CATEGORIES or duration<=0:
        raise ValueError('Unknown/invalid sound event')
    n=round(duration*SR); t=np.arange(n)/SR
    noise=np.random.default_rng(seed).normal(0,1,n)
    spectrum=np.fft.rfft(noise)
    frequencies=np.fft.rfftfreq(n,1/SR)
    band=(frequencies>120)&(frequencies<4500)
    air=np.fft.irfft(spectrum*band,n=n)
    if category=='environment':
        x=.18*np.sin(2*math.pi*82*t)+.10*np.sin(2*math.pi*164*t)+air*.035
    elif category=='mechanical':
        x=(.35*np.sin(2*math.pi*117*t)+.12*np.sin(2*math.pi*234*t)+air*.08)*(.85+.15*np.sin(2*math.pi*.23*t))
    elif category=='footstep':
        x=(.7*np.sin(2*math.pi*95*t)+.25*np.sin(2*math.pi*190*t)+air*.20)*np.exp(-t*22)
    elif category=='movement':
        x=air*.35*np.sin(np.pi*np.arange(n)/max(1,n-1))**2
    elif category=='doors':
        x=.22*np.sin(2*math.pi*(142*t+1.3*t*t))+.12*np.sin(2*math.pi*284*t)+air*.13
    elif category=='radio':
        x=air*.25*(.5+.5*np.sin(2*math.pi*17*t))
    elif category=='alarm':
        x=(np.sin(2*math.pi*520*t)+.25*np.sin(2*math.pi*780*t))*np.sin(np.pi*np.arange(n)/max(n-1,1))**2*.4
    elif category=='impact':
        x=(.65*np.sin(2*math.pi*66*t)+.25*np.sin(2*math.pi*132*t)+air*.16)*np.exp(-t*9)
    elif category=='transition':
        x=air*.3*(np.arange(n)/max(n-1,1))**2
    else:
        x=(.3*np.sin(2*math.pi*73.4*t)+.2*np.sin(2*math.pi*110*t)+air*.07)*np.exp(-t*.9)
    fade_in=min(.015,duration/8); fade_out=min(.20,duration/4)
    envelope=np.minimum(t/fade_in,1)*np.minimum((duration-t)/fade_out,1)
    return x*envelope


def duck_envelope(length,windows,depth_db):
    envelope=np.ones(length)
    floor=10**(-depth_db/20)
    for start,end in windows:
        a=max(0,round((start-.08)*SR)); b=min(length,round((end+.4)*SR))
        t=np.arange(a,b)/SR
        attack=np.clip((t-(start-.08))/.06,0,1)
        release=np.clip(((end+.4)-t)/.4,0,1)
        envelope[a:b]=np.minimum(envelope[a:b],1-(1-floor)*np.minimum(attack,release))
    return envelope
