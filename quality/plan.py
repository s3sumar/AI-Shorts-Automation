"""Cut-aware sampling: never interpolate across edits or lighting discontinuities."""
import math


def segments(config,start,duration,mode):
    end=start+duration
    if mode not in ['native','hybrid','baseline'] or start<0 or duration<=0 or end>config['duration']:
        raise ValueError('Invalid quality clip')
    # All boundaries land exactly on the 24 FPS output grid.
    if any(abs(t*24-round(t*24))>1e-6 for t in [start,end]):
        raise ValueError('Clip boundaries must land on output frames')
    boundaries={start,end}
    boundaries.update(sh['start'] for sh in config['shots'] if start<sh['start']<end)
    # Blackouts/flickers/display changes must not dissolve into adjacent frames.
    if mode=='hybrid':
        boundaries.update(round(t*24)/24 for t,v in config['floor_events'] if start<t<end)
        boundaries.update(round(t*24)/24 for t,v in config['lighting']['power'] if start<t<end)
        boundaries.update(config['effects']['blackout'])
    boundaries=sorted({round(t*24)/24 for t in boundaries if start<=t<=end})
    result=[]
    for a,b in zip(boundaries,boundaries[1:]):
        first,last=round(a*24)+1,round(b*24)
        shot=next(s for s in config['shots'] if s['start']<=a<s['end'])
        fps=24 if mode=='native' else 2 if mode=='baseline' else 12
        if mode=='hybrid' and (b-a<.5 or shot['id'] in ['impact_reaction','wrong_floor']):
            fps=24
        step=24//fps
        frames=list(range(first,last+1,step))
        reusable_plate=mode=='hybrid' and shot['id']=='black'
        if reusable_plate:
            frames=[first]
        # Last-frame padding is inside this segment only, never the next cut.
        result.append({'start':a,'end':b,'frames':frames,'fps':fps,'output_frames':last-first+1,
                       'shot':shot['id'],'reusable_plate':reusable_plate})
    return result


def interpolation_filter(fps,output_frames):
    if fps==24:
        return f'trim=end_frame={output_frames},setpts=PTS-STARTPTS'
    # A four-frame hold supplies temporal neighbors at the end of a shot.
    # Native sampling is retained for impacts and flashes; optical flow has limits.
    return ('tpad=stop_mode=clone:stop_duration=0.25,'
            'minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff,'
            f'trim=end_frame={output_frames},setpts=PTS-STARTPTS')
