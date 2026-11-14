"""Portable scene assembly and JSON sequencing for the elevator asset library."""
import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector
from .common import frame,animate,visibility,material,unlit,box,text,aim,area
from .characters import passenger,antagonist

ENVIRONMENT=['Elevator floor','Rear metallic wall','Left wall','Right wall','Elevator ceiling',
 'Door left','Door right','Door header','Hand rail','Hand rail.001','Ceiling LED panel',
 'Ceiling LED panel.001','Indicator housing','Door pocket wall','Door pocket wall.001',
 'Vertical frame','Vertical frame.001','Corridor floor','Corridor darkness','Corridor wall',
 'Corridor wall.001','Cold overhead lighting','Red back rim','Soft face fill']


def load_config(path):
    c=json.loads(Path(path).read_text(encoding='utf-8'))
    assert c.get('schema_version')==2
    assert c['fps']==24 and c['duration']>0
    assert c['preview']['fps']>0 and c['fps']%c['preview']['fps']==0
    assert c['shots'][0]['start']==0 and c['shots'][-1]['end']==c['duration']
    assert all(a['end']==b['start'] for a,b in zip(c['shots'],c['shots'][1:])), 'Shot gap/overlap'
    assert all(a[0]<b[0] for a,b in zip(c['floor_events'],c['floor_events'][1:]))
    for cue in c['narration']+c['captions']:
        assert 0<=cue['start']<cue['end']<=c['duration']
    return c


def environment(s,root,c):
    with bpy.data.libraries.load(str(root/c['template']),link=False) as (src,dst):
        assert set(ENVIRONMENT)<=set(src.objects), 'Incomplete environment template'
        dst.objects=ENVIRONMENT
    for o in dst.objects:
        s.collection.objects.link(o)
        o.animation_data_clear()
        o.hide_render=o.hide_viewport=False
        if o.data and hasattr(o.data,'animation_data_clear'):
            o.data.animation_data_clear()
        for slot in o.material_slots:
            if slot.material and slot.material.node_tree:
                slot.material.node_tree.animation_data_clear()
    s.objects['Elevator floor'].location.y=-1.6
    s.objects['Elevator floor'].dimensions.y=7.4
    trim=material('Episode | dark anodized controls',(.035,.052,.07),.38,.55)
    brass=material('Episode | aged brass',(.3,.21,.12),.4,.65)
    corridor=material('Episode | corridor charcoal',(.045,.06,.075),.75)
    s.objects['Corridor darkness'].location.y=9.5
    s.objects['Corridor darkness'].dimensions=(3.6,.15,4.2)
    s.objects['Corridor darkness'].data.materials[0]=corridor
    s.objects['Corridor floor'].location.y=5.7
    s.objects['Corridor floor'].dimensions.y=7.6
    for name in ['Corridor wall','Corridor wall.001']:
        s.objects[name].location.y=5.7
        s.objects[name].dimensions.y=7.6
    glow=material('Episode | guide lights',(.10,.32,.4),.5,0,.7)
    for side in [-1,1]:
        for y in [-1.1,-.1,.9]:
            box('Cab panel joint',(side*1.918,y,2),(.018,.023,3.9),trim,bevel=.005)
        box('Cab skirting',(side*1.9,0,.19),(.04,3.7,.12),brass)
        for y in [3.1,5.2,7.3]:
            box('Corridor rib',(side*1.69,y,1.9),(.08,.16,3.8),trim)
            box('Corridor guide',(side*1.68,y,1.9),(.025,.17,.8),glow,bevel=.004)
    box('Corridor lintel',(0,2.1,3.65),(2.6,.2,.12),trim)
    box('Corridor ceiling',(0,5.6,4),(3.6,7.6,.12),trim)
    box('Threshold',(0,1.83,.035),(2.55,.43,.035),brass,bevel=.005)
    for x in [-.36,-.18,0,.18,.36]:
        box('Threshold groove',(x,1.83,.056),(.014,.38,.008),trim,bevel=0)
    box('Radio intercom',(1.60,1.55,2.45),(.3,.13,.44),trim)
    for z in [2.32,2.37,2.42,2.47,2.52]:
        box('Radio grille',(1.60,1.473,z),(.2,.01,.015),brass,bevel=.003)
    box('Control plate',(1.59,1.55,1.65),(.3,.12,.8),trim)
    for z in [1.4,1.62,1.84]:
        box('Lift button',(1.59,1.478,z),(.12,.025,.11),glow)
    plaque=text(s,'Lift label','LIFT 013',(1.58,1.46,2.04),.085,brass)
    plaque.rotation_euler.x=math.pi/2
    area(s,'Corridor silhouette rim',(.6,8.1,3.5),(.5,5.4,1.7),170,(.12,.35,.46),2)
    area(s,'Corridor depth wash',(0,7.5,3.4),(0,9.4,2),180,(.12,.35,.46),2)
    if c.get('environment',{}).get('id')=='freight_lift':
        industrial=material('Environment | freight enamel',(.12,.18,.16),.48,.3)
        caution=material('Environment | caution ochre',(.42,.27,.055),.6)
        for name in ['Left wall','Right wall']:
            s.objects[name].data.materials[0]=industrial
        for side in [-1,1]:
            for z in [.4,.6,.8]:
                box('Freight safety band',(side*1.90,.3,z),(.025,2.4,.07),caution)
            box('Service pipe',(side*1.5,6,3.4),(.12,5,.12),trim)


def display(s,c):
    glow=material('Display | red phosphor',(1,.10,.055),.45,0,2)
    for value in dict.fromkeys(v for _,v in c['floor_events'] if v):
        o=text(s,'Display '+value,value,(0,1.58,3.72),.29,glow)
        o.rotation_euler.x=math.pi/2
        for prop in ['hide_render','hide_viewport']:
            animate(o,prop,[(frame(t),v!=value) for t,v in c['floor_events']],
                    'EP01 | display '+value,'CONSTANT')
        o['display_value']=value


def motion(s,c,r,brows):
    for command,keys in c['motion'].items():
        target,path=command.rsplit('.',1)
        animate(r[target],path,[(frame(t),v) for t,v in keys],'EP01 | '+command)
    duration=c['duration']
    period=c['effects']['breathing_period']
    animate(r['passenger.breath'],'scale',[(frame(t/4),(1,1,1+.009*math.sin(t/4*math.tau/period)))
        for t in range(int(duration*4)+1)],'EP01 | breathing')
    a,b=c['effects']['sway_start'],c['effects']['sway_end']
    sway=[(1,(0,0,0))]
    t=a
    while t<b:
        phase=(t-a)*math.tau*1.3
        ramp=min((t-a)/6,1)
        sway.append((frame(t),(.018*math.sin(phase)*ramp,.045*math.sin(phase*.8)*ramp,.025*math.sin(phase)*ramp)))
        t+=.25
    impact=c['effects']['impact_time']
    sway.extend([(frame(b),(0,0,0)),(frame(impact+.12),(.09,0,0)),(frame(impact+.6),(-.03,0,0)),
                 (frame(impact+1.2),(0,0,0)),(frame(duration),(0,0,0))])
    animate(r['passenger.root'],'rotation_euler',sway,'EP01 | passenger sway and impact')
    for sign,label in [(-1,'L'),(1,'R')]:
        fear=c['effects']['fear_start']
        entry=c['effects']['entry_end']
        animate(r['passenger.leg.'+label],'rotation_euler',[(1,(sign*.15,0,0)),(frame(entry*.36),(sign*-.12,0,0)),
            (frame(entry),(0,0,0)),(frame(fear),(0,0,0)),(frame(fear+.7),(sign*.18,0,0)),
            (frame(fear+1.7),(0,0,0)),(frame(duration),(0,0,0))],'EP01 | passenger step '+label)
    for brow in brows:
        loc=brow.location.copy()
        animate(brow,'location',[(frame(t),loc+Vector((0,0,lift))) for t,lift in c['facial_reactions']],
            'EP01 | '+brow.name+' expression')
    for name,sign in [('Door left',-1),('Door right',1)]:
        keys=[(1,(sign*.625,1.83,1.75)),
            (frame(c['effects']['door_start']),(sign*.625,1.83,1.75)),
            (frame(c['effects']['door_end']),(sign*1.9,1.83,1.75)),
            (frame(duration),(sign*1.9,1.83,1.75))]
        if 'door_events' in c:
            keys=[(frame(t),(sign*(.625+1.275*aperture),1.83,1.75)) for t,aperture in c['door_events']]
        animate(s.objects[name],'location',keys,'EP01 | '+name+' opening')
    if 'shadow_visibility' in c:
        for obj in s.objects:
            if obj.type=='MESH' and obj.name.startswith('Shadow '):
                for prop in ['hide_render','hide_viewport']:
                    animate(obj,prop,[(frame(t),not visible) for t,visible in c['shadow_visibility']],
                            'EP01 | '+obj.name+' presence','CONSTANT')


def lighting(s,c):
    blue,red=c['lighting']['cold'],c['lighting']['emergency']
    powers=c['lighting']['power']
    stop,restore=c['effects']['blackout']
    alarm=c['effects']['red_at']
    duration=c['duration']
    rim_power=c['lighting']['emergency_rim_power']
    for name,power in c['lighting']['lamps'].items():
        d=s.objects[name].data
        animate(d,'energy',[(frame(t),power*v) for t,v in powers],'EP01 | '+name+' power','LINEAR')
        animate(d,'color',[(1,blue),(frame(restore),blue),(frame(alarm),red),(frame(duration),red)],'EP01 | '+name+' power')
    rim_keys=c['lighting'].get('rim_events',[[0,0],[restore,0],[alarm,rim_power],[duration,rim_power]])
    animate(s.objects['Red back rim'].data,'energy',[(frame(t),p) for t,p in rim_keys],'EP01 | red rim')
    panel=s.objects['Ceiling LED panel'].data.materials[0]
    bs=next(n for n in panel.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for t,v in powers:
        socket=bs.inputs['Emission Strength']
        socket.default_value=v*c['lighting']['tube_strength']
        socket.keyframe_insert('default_value',frame=frame(t))
    for t,col in [(0,blue),(restore,blue),(alarm,red),(duration,red)]:
        socket=bs.inputs['Emission Color']
        socket.default_value=(*col,1)
        socket.keyframe_insert('default_value',frame=frame(t))
    action=panel.node_tree.animation_data.action
    action.name='EP01 | fluorescent emission'
    action.use_fake_user=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND')
    for t,v in [(0,.06),(stop-.1,.06),(stop,0),(restore,0),(alarm,.025),(duration,.025)]:
        bg.inputs['Strength'].default_value=v
        bg.inputs['Strength'].keyframe_insert('default_value',frame=frame(t))
    s.world.node_tree.animation_data.action.name='EP01 | ambient power'
    s.world.node_tree.animation_data.action.use_fake_user=True


def cameras(s,c):
    result={}
    for shot in c['shots']:
        name='Shot | '+shot['id']
        d=bpy.data.cameras.new(name)
        o=bpy.data.objects.new(name,d)
        s.collection.objects.link(o)
        d.lens=shot['lens']
        d.clip_start,d.clip_end=.04,100
        d.dof.use_dof=False
        start,end=frame(shot['start']),frame(shot['end'])-1
        frames={start,end}
        if 'shake' in shot:
            a,b,amp=shot['shake']
            frames.update(range(max(start,frame(a)),min(end,frame(b))+1,3))
        keys,rotations=[],[]
        for f in sorted(frames):
            u=(f-start)/max(end-start,1)
            u=u*u*(3-2*u)
            loc=Vector(shot['from']).lerp(Vector(shot['to']),u)
            t=(f-1)/c['fps']
            if 'shake' in shot and a<=t<=b:
                envelope=max(min((t-a)*3,1,(b-t)*3),0)
                loc+=Vector((math.sin(f*1.7),math.cos(f*1.3)*.3,math.sin(f*2.2)))*amp*envelope
            o.location=loc
            aim(o,shot['target'])
            keys.append((f,tuple(loc)))
            rotations.append((f,tuple(o.rotation_euler)))
        animate(o,'location',keys,'EP01 | '+shot['id']+' camera')
        animate(o,'rotation_euler',rotations,'EP01 | '+shot['id']+' camera')
        marker=s.timeline_markers.new(shot['id'],frame=start)
        marker.camera=o
        o['shot_start'],o['shot_end']=start,end
        result[shot['id']]=o
    s.camera=result[c['shots'][0]['id']]
    black=unlit('Overlay | absolute black',(0,0,0))
    box('Final black screen',(0,0,-22),(20,20,.01),black,bevel=0)
    return result


def captions(s,c,cams):
    white=unlit('Caption | ivory',(1,1,1))
    black=unlit('Caption | black backing',(.001,.001,.001))
    for shot in c['shots']:
        cam=cams[shot['id']]
        corners=cam.data.view_frame(scene=s)
        xs=[v.x/(-v.z) for v in corners]
        ys=[v.y/(-v.z) for v in corners]
        w,h=max(xs)-min(xs),max(ys)-min(ys)
        for i,cue in enumerate(c['captions']):
            a,b=max(shot['start'],cue['start']),min(shot['end'],cue['end'])
            if a>=b:
                continue
            center=0 if shot['id']=='black' else -.28*h
            o=text(s,f'Caption | {shot["id"]} | {i}',cue['text'],(-.02*w,center,-1),.045*h,white,cam)
            bpy.context.view_layer.update()
            if o.dimensions.x>w*.78:
                o.data.size*=w*.78/o.dimensions.x
            bpy.context.view_layer.update()
            backing=box(f'Caption backing | {shot["id"]} | {i}',(-.02*w,center,-1.006),
                (max(o.dimensions.x+.055*w,.35*w),o.dimensions.y+.024*h,.001),black,cam,0)
            for overlay in [o,backing]:
                if hasattr(overlay,'visible_shadow'):
                    overlay.visible_shadow=False
                visibility(overlay,frame(a),frame(b),s.frame_end)
            o['safe_caption']=True
            o['caption_start'],o['caption_end']=frame(a),frame(b)-1


def build(root,config_path):
    c=load_config(config_path)
    out=Path(os.environ.get('EPISODE_OUTPUT',str(root/'artifacts'/f'episode_{c["episode"]:03d}')))
    if not out.is_absolute():
        out=root/out
    out.mkdir(parents=True,exist_ok=True)
    path=Path(os.environ.get('SCENE_BLEND',str(out/f'episode_{c["episode"]:03d}_master.blend')))
    if not path.is_absolute():
        path=root/path
    if path.exists() and os.environ.get('ALLOW_REBUILD')!='1':
        raise FileExistsError('Refusing to overwrite '+str(path))
    s=bpy.data.scenes.new(f'Episode {c["episode"]:03d} | {c["title"]}')
    bpy.context.window.scene=s
    s.frame_start,s.frame_end=1,round(c['duration']*c['fps'])
    s.render.fps,s.render.fps_base=c['fps'],1
    s.render.resolution_x,s.render.resolution_y=c['resolution']
    s.render.resolution_percentage=100
    s.render.engine=os.environ.get('RENDER_ENGINE','BLENDER_EEVEE')
    if s.render.engine=='CYCLES':
        s.cycles.device='CPU'
        s.cycles.samples=12
        s.cycles.use_denoising=True
        s.cycles.max_bounces=3
    if hasattr(s,'eevee'):
        s.eevee.use_raytracing=os.environ.get('ENABLE_REFLECTIONS','1')=='1'
        for prop in ['taa_render_samples','taa_samples']:
            if hasattr(s.eevee,prop):
                setattr(s.eevee,prop,32)
    s.render.image_settings.file_format='PNG'
    s.render.image_settings.color_mode='RGB'
    s.render.filepath=str(out/'frames'/'frame_')
    s.view_settings.view_transform='AgX'
    s.world=bpy.data.worlds.new('Episode | unlit void')
    s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs['Color'].default_value=(.02,.035,.065,1)
    bg.inputs['Strength'].default_value=.06
    environment(s,root,c)
    rgb=tuple(int(c['character_color'][i:i+2],16)/255 for i in (1,3,5))
    rigs,brows=passenger(s,rgb)
    rigs.update(antagonist(s))
    display(s,c)
    motion(s,c,rigs,brows)
    lighting(s,c)
    cams=cameras(s,c)
    captions(s,c,cams)
    audio=out/'audio'/'episode_mix.wav'
    if audio.exists():
        s.sequence_editor_create().strips.new_sound('Sound design + radio',str(audio),channel=1,frame_start=1)
    s['episode_config']=json.dumps(c)
    if c['episode']!=1:
        for action in bpy.data.actions:
            if action.name.startswith('EP01 |'):
                action.name=f'EP{c["episode"]:02d} |'+action.name[len('EP01 |'):]
    s['source_template']=c['template']
    s['production_notes']='24 FPS master; PNG preview sampled separately; captions rendered in scene'
    s.frame_set(1)
    path.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print('EPISODE READY '+json.dumps({'blend':str(path),'objects':len(s.objects),'frames':s.frame_end,'shots':len(cams)}))
    return s
