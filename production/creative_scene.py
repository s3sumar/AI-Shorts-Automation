"""CPU-practical stylized scene adapters and typed animation sequencing.

Run only in a NEW background Blender process. No source scene is overwritten.
This is an original blockout asset library, not a claim of finished film quality.
"""
import bpy
import json
import math
import os
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from production.common import box,sphere,empty,text,material,area,aim,animate,frame
from production.characters import passenger


def make_prop(scene,name,kind,loc,materials):
    wood,paper,metal,glow=materials
    if kind=='tree':
        obj=empty(scene,name,loc)
        box(name+' trunk',(0,0,.6),(.14,.15,1.2),wood,obj)
        for x,z in [(-.35,1.4),(.3,1.6),(0,1.9)]:sphere(name+' canopy',(x,0,z),(.5,.35,.45),glow,obj)
        for x in [-.3,-.15,.15,.3]:box(name+' root',(x,0,.1),(.06,.4,.08),wood,obj)
    elif kind in ['paper','map','book']:
        obj=box(name,loc,(1.25,.75,.06 if kind!='book' else .16),paper)
        if kind=='map':
            for x in [-.4,0,.4]:box(name+' road',(x,0,.05),(.035,.6,.008),wood,obj)
    elif kind=='seal':obj=sphere(name,loc,(.13,.13,.045),material(name+' wax',(.45,.015,.02),.55))
    elif kind=='knife':
        obj=box(name,loc,(.08,.5,.03),metal)
        box(name+' handle',(0,-.3,0),(.12,.2,.07),wood,obj)
    elif kind=='river':obj=box(name,loc,(.1,1.9,.025),glow)
    elif kind=='window':
        obj=box(name,loc,(1.7,.1,1.1),material(name+' sky',(.035,.18,.3),.5,0,.7))
        for x in [-.8,0,.8]:box(name+' frame',(x,-.07,0),(.04,.05,1.2),wood,obj)
    elif kind=='cell':
        obj=empty(scene,name,loc)
        for x in [-.8,-.5,-.2,.1,.4,.7]:box(name+' bar',(x,0,1.4),(.055,.06,2.8),metal,obj)
        box(name+' bed',(0,1,.35),(1.3,.7,.18),wood,obj)
    elif kind in ['house','bridge','well']:
        obj=box(name,loc,(.5,.45,.35),wood)
        if kind=='house':box(name+' roof',(0,0,.25),(.65,.55,.1),metal,obj)
        elif kind=='well':sphere(name+' water',(0,0,.2),(.18,.18,.03),glow,obj)
    elif kind=='chamber':
        obj=empty(scene,name,loc)
        for x in [-.9,.9]:box(name+' upright',(x,0,1.3),(.06,.07,2.6),metal,obj)
        box(name+' overhead',(0,0,2.6),(1.9,.1,.08),glow,obj)
    else:obj=box(name,loc,(.4,.25,.25),metal)
    obj['asset_id']=name
    return obj


def build(config,storyboard,episode,bible,audio,out):
    if out.exists():raise FileExistsError('Preserve existing master; choose a new output revision')
    if not storyboard['readiness']['renderable']:raise ValueError('Unregistered creative assets')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE';scene.render.fps=24;scene.frame_start=1;scene.frame_end=1080
    scene.render.resolution_x,scene.render.resolution_y=config['preview']['resolution'];scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Creative world');scene.world.color=(.035,.035,.035)
    scene.view_settings.view_transform='AgX'
    scene.render.image_settings.file_format='PNG'
    scene['episode_config']=json.dumps(config)
    wood=material('Warm wood',(.16,.07,.025),.7)
    paper=material('Ivory paper',(.7,.62,.44),.85)
    metal=material('Brushed metal',(.12,.16,.19),.45,.45)
    glow=material('River and living tissue',(.06,.35,.25),.45,0,.8)
    ground=material('Matte floor',(.075,.09,.11),.8)
    box('Stage floor',(0,1,-.08),(10,9,.15),ground)
    box('Back wall',(0,4,2.4),(10,.2,5),wood)
    world_id=episode['shots'][0]['environment_id']
    if world_id=='royal_record_room':
        area(scene,'Window blue',(-3,-1,5),(0,0,1),650,(.38,.55,1),4)
        area(scene,'Prison candle',(2,-2,3),(0,1,1.2),550,(1,.56,.22),3)
    elif world_id=='lunar_greenhouse':
        area(scene,'Cold grow lights',(0,1,5),(0,1,1),850,(.42,.72,1),4)
        area(scene,'Warm face',(1,-3,3),(0,0,1.5),400,(1,.7,.45),3)
    else:
        area(scene,'Workshop sun',(-3,-2,5),(0,0,1),800,(1,.68,.35),4)
        area(scene,'Rain fill',(3,0,4),(0,1,1),500,(.3,.6,1),3)
    area(scene,'Face fill',(0,-5,3),(0,0,1.5),300,(.7,.8,1),4)
    box('Worktable',(0,1.2,.8),(2.8,1.3,.16),wood)
    for x in [-1.2,1.2]:box('Table leg',(x,1.2,.38),(.12,.12,.8),wood)
    objects={};rigs={};mouths={}
    for i,c in enumerate(bible['characters']):
        color=(.63,.72,.77) if i==0 else (.55,.42,.3)
        before=set(bpy.data.objects)
        rig,brows=passenger(scene,color,True)
        for obj in set(bpy.data.objects)-before:obj.name=c['id']+' | '+obj.name
        root=rig['passenger.root'];root.location=(-.85 if i==0 else .85,0,0)
        objects[c['id']]=root;rigs[c['id']]=rig
        mouth=sphere(c['id']+' mouth',(0,-.385,-.08),(.08,.015,.018),metal,rig['passenger.head'])
        mouths[c['id']]=mouth
        animate(rig['passenger.breath'],'scale',[(f,(1,1,1+.008*math.sin(f/24*2))) for f in range(1,1082,12)],c['id']+' breathing')
        keys=[(1,(0,0,0))]
        for line in episode['narration']:
            if line['speaker']==c['id']:
                keys.extend([(frame(line['start']),(0,0,-.06)),(frame((line['start']+line['end'])/2),(.025,0,.07)),(frame(line['end']),(0,0,0))])
        keys.append((1081,(0,0,0)));animate(rig['passenger.head'],'rotation_euler',keys,c['id']+' dialogue head')
        closed=(.08,.015,.018);opened=(.08,.015,.05)
        jaw=[(1,closed)]
        for word in audio['words']:
            if word['speaker']==c['id']:
                a,b=frame(word['start']),frame(word['end'])
                jaw.extend([(a,closed),(max(a+1,(a+b)//2),opened),(max(a+2,b),closed)])
        jaw.append((1081,closed));animate(mouth,'scale',sorted(jaw),c['id']+' timed mouth')
    for name,binding in storyboard['asset_bindings'].items():
        if name in objects:continue
        if binding.get('factory') not in {'paper','map','book','seal','knife','tree','river','window','cell','house','bridge','well','chamber','box'}:
            raise ValueError('Unknown reviewed prop factory')
        objects[name]=make_prop(scene,name,binding['factory'],binding['position'],(wood,paper,metal,glow))
    scene.view_layers.update()
    # Explicit typed performances, not keyword guesses about prose.
    for shot in episode['shots']:
        for perf in shot.get('performances',[]):
            rig=rigs[perf['actor']];a,b=frame(perf['start']),frame(perf['end']);kind=perf['action']
            if kind in ['reach','point','recoil']:
                angle=-1.0 if kind!='recoil' else .45
                animate(rig['passenger.arm.R'],'rotation_euler',[(max(1,a-3),(0,0,0)),(a+3,(angle,0,0)),(b,(0,0,0))],perf['actor']+' '+kind)
            elif kind=='look':
                target=objects[perf['target']].matrix_world.translation
                pos=rig['passenger.root'].location
                yaw=max(-.7,min(.7,math.atan2(target.x-pos.x,max(.2,abs(target.y-pos.y)))))
                animate(rig['passenger.head'],'rotation_euler',[(a,(0,0,0)),(a+4,(0,0,yaw)),(b,(0,0,yaw))],perf['actor']+' look')
            elif kind=='walk':
                p=rig['passenger.root'].location.copy();q=Vector(perf['position'])
                animate(rig['passenger.root'],'location',[(a,p),(b,q)],perf['actor']+' walk')
                for label,sign in [('L',1),('R',-1)]:
                    animate(rig['passenger.leg.'+label],'rotation_euler',[(f,(sign*.18*math.sin((f-a)/5),0,0)) for f in range(a,b+1,4)],perf['actor']+' stepping')
    for event in episode.get('visual_events',[]):
        obj=objects[event['target']];f=frame(event['at']);prop=event['property'];value=event['value']
        if prop=='visible':animate(obj,'hide_render',[(1,not value),(f,not value)],obj.name+' visibility','CONSTANT') if f==1 else animate(obj,'hide_render',[(1,value),(f,not value)],obj.name+' reveal','CONSTANT')
        elif prop=='location':animate(obj,'location',[(1,obj.location.copy()),(f,Vector(value))],obj.name+' placement')
        elif prop=='text':
            label=text(scene,event['target']+' revealed text',value,tuple(obj.matrix_world.translation+Vector((0,-.05,.2))),.12,metal)
            label.rotation_euler.x=math.pi/2
            animate(label,'hide_render',[(1,True),(f,False)],label.name+' reveal','CONSTANT')
    cameras=[]
    for shot in episode['shots']:
        subject=objects[shot['subject']];pos=subject.matrix_world.translation.copy()
        if shot['subject'] in rigs:pos.z+=2.0 if shot['framing'] in ['close','detail'] else 1.35
        if shot['framing']=='wide':pos.x=0
        distance={'wide':8.8,'medium':4.8,'close':3.3,'detail':2.3}[shot['framing']]
        data=bpy.data.cameras.new(shot['id']);data.lens=45;data.clip_start=.05
        cam=bpy.data.objects.new(shot['id'],data);scene.collection.objects.link(cam)
        a,b=frame(shot['start']),min(1080,frame(shot['end'])-1)
        start=pos+Vector((.15,-distance,distance*.27));finish=start.copy()
        if shot['camera_move']=='dolly':finish.y+=.3
        elif shot['camera_move'] in ['pan','orbit']:finish.x+=.35
        cam.location=start;aim(cam,pos);rot_a=cam.rotation_euler.copy()
        cam.location=finish;aim(cam,pos);rot_b=cam.rotation_euler.copy()
        animate(cam,'location',[(a,start),(b,finish)],shot['id']+' camera travel')
        animate(cam,'rotation_euler',[(a,rot_a),(b,rot_b)],shot['id']+' camera aim')
        marker=scene.timeline_markers.new(shot['id'],frame=a);marker.camera=cam
        cameras.append(cam)
    scene.camera=cameras[0]
    # Check all shot midpoints and subject centres in normalized camera space.
    from bpy_extras.object_utils import world_to_camera_view
    checks=[]
    for shot,cam in zip(episode['shots'],cameras):
        scene.frame_set(frame((shot['start']+shot['end'])/2));scene.camera=cam
        subject=objects[shot['subject']];p=subject.matrix_world.translation.copy()
        if shot['subject'] in rigs:p.z+=2.0 if shot['framing'] in ['close','detail'] else 1.35
        uv=world_to_camera_view(scene,cam,p)
        checks.append({'shot':shot['id'],'subject':shot['subject'],'inside_camera':0<uv.x<1 and 0<uv.y<1 and uv.z>0})
    if not all(c['inside_camera'] for c in checks):raise ValueError('Creative camera framing check failed')
    scene.frame_set(1);scene.camera=cameras[0]
    if any(max(m.dimensions)>.25 for m in mouths.values()):raise ValueError('Mouth geometry exceeds character proportions')
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    report={'passed':True,'master_frames':1080,'fps':24,'active_camera':scene.camera.name,'shots':checks,
        'objects':len(scene.objects),'named_actions':len(bpy.data.actions),'source':'original procedural blockout assets',
        'limitations':['Basic mannequin acting','Word-timed mouth opening, not phoneme lip sync','No human visual-quality approval']}
    (out.parent/'scene_validation.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]).resolve()
    episode_file='performance_episode.json' if (folder/'performance_episode.json').exists() else 'episode.json'
    build(*[json.loads((folder/name).read_text()) for name in ['render_config.json','blender_storyboard.json',episode_file,'series_bible.json','audio/audio_manifest.json']],folder/'creative_master.blend')
