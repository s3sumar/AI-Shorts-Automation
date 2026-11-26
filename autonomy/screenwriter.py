"""Treatment-first suspense writing with explicit audience and character state.

Offline realizers are bounded story grammars. A configured local model may write
fresh prose against the treatment, with bounded critique/revision; no paid model,
checkpoint write, rendering or publication is performed here.
"""
import copy
import json
from .suspense import validate_story,rules


def _line(plan,cue_id,start,end,role,text,emotion=None,phrases=None):
    speaker='narrator' if role=='narrator' else plan['start_state']['characters'][role]['id']
    result={'id':cue_id,'start':start,'end':end,'speaker':speaker,'role':role,
            'emotion':emotion or {'narrator':'storytelling','protagonist':'afraid','antagonist':'unsettling'}[role],'text':text}
    if phrases: result['phrases']=[{'text':p,'pause_after':pause} for p,pause in phrases]
    return result


def delivery_lines(plan,strategy,context):
    subject=context.get('subject','they');possessive=context.get('possessive','their')
    was='were' if subject=='they' else 'was'
    opening=f'{possessive.capitalize()} last delivery was marked complete. {subject.capitalize()} {was} still holding it.'
    first=f'{possessive.capitalize()} last delivery was marked complete.'
    second=f'{subject.capitalize()} {was} still holding it.'
    item=context.get('object','parcel')
    l=lambda *a,**kw:_line(plan,*a,**kw)
    result=[l('opening',.15,4.5,'narrator',opening,phrases=[(first,.20),(second,.08)])]
    if strategy=='withdrawal':
        result += [
            l('hope',4.95,9.25,'narrator',f'{subject.capitalize()} blamed dispatch. One call, then the lobby and home.',phrases=[(f'{subject.capitalize()} blamed dispatch.',.18),('One call, then the lobby and home.',.08)]),
            l('cancel',9.5,12.8,'protagonist',"Cancel the delivery. I'll bring it back.",'uneasy',[("Cancel the delivery.",.18),("I'll bring it back.",.08)]),
            l('silence_meaning',13.2,18.7,'narrator',f'{subject.capitalize()} waited for an argument. An argument meant someone was listening.',phrases=[(f'{subject.capitalize()} waited for an argument.',.28),('An argument meant someone was listening.',.08)]),
            l('stop',19.1,22.1,'protagonist','Hello? Stop. Please stop.','desperate',[('Hello?',.45),('Stop.',.18),('Please stop.',.08)]),
            l('goal_changes',22.5,27.1,'narrator',f"The lobby passed. {subject.capitalize()} wasn't trying to finish the job anymore." if subject!='they' else "The lobby passed. They weren't trying to finish the job anymore.",phrases=[('The lobby passed.',.25),((f"{subject.capitalize()} wasn't trying to finish the job anymore." if subject!='they' else "They weren't trying to finish the job anymore."),.08)]),
            l('sealed',27.5,29.3,'protagonist',"Minus one? That's sealed.",'terrified',[("Minus one?",.10),("That's sealed.",.08)]),
            l('last_hope',33.6,37.1,'narrator',f'Someone was waiting. {subject.capitalize()} still thought {subject} could cancel.',phrases=[('Someone was waiting.',.22),(f'{subject.capitalize()} still thought {subject} could cancel.',.08)]),
            dict(l('refuse',37.5,39.7,'protagonist',f"I'm taking the {item} back.",'resolute'),pace=.94),
            l('answer',40.6,42.55,'antagonist','Keep it.'),
            l('reversal',43.05,44.95,'antagonist',"You're the delivery.")]
    else:
        result += [
            l('hope',4.9,9.7,'narrator',f'{subject.capitalize()} blamed dispatch. {possessive.capitalize()} customer in the lobby could clear this up.',phrases=[(f'{subject.capitalize()} blamed dispatch.',.15),(f'{possessive.capitalize()} customer in the lobby could clear this up.',.08)]),
            l('ask_dispatch',10.1,12.8,'protagonist',f'Dispatch? Who accepted the {item}?','uneasy', [('Dispatch?',.12),(f'Who accepted the {item}?',.08)]),
            l('reason_for_name',13,18.2,'narrator',f"A name. That was all {subject} needed to prove this wasn't {possessive} mistake.",phrases=[('A name.',.24),(f"That was all {subject} needed to prove this wasn't {possessive} mistake.",.08)]),
            l('choose_verification',18.5,20.2,'protagonist',"I'll ask them myself.",'resolute'),
            l('blocked_route',20.4,26.35,'narrator',f'{subject.capitalize()} expected a customer in the lobby. The lift stopped at a sealed floor.',phrases=[(f'{subject.capitalize()} expected a customer in the lobby.',.20),('The lift stopped at a sealed floor.',.08)]),
            l('plea',26.8,28.8,'protagonist','Let me out upstairs.','desperate'),
            l('possible_answer',31.3,34.8,'narrator',"Someone was waiting. Maybe they'd accepted it.",phrases=[('Someone was waiting.',.24),("Maybe they'd accepted it.",.08)]),
            dict(l('test_recipient',35.1,37,'protagonist',f'Did you accept this {item}?','afraid'),pace=.95),
            l('denial',37.3,40.1,'antagonist',f"I didn't order a {item}."),
            l('follow_up',40.4,42.3,'protagonist','Then what did you order?','terrified'),
            l('reversal',43.05,44.95,'antagonist',"You're the delivery.")]
    return result


def _beat(beat_id,start,end,tension,cues,**kwargs):
    return dict(id=beat_id,start=start,end=end,tension=tension,cues=cues,**kwargs)


def delivery_treatment(plan,strategy,lines):
    facts={
        'job_complete':{'statement':'The delivery is already marked complete.','basis':'opening clue'},
        'parcel_held':{'statement':'The protagonist has not handed over the parcel.','basis':'visible opening contradiction'},
        'destination_lobby':{'statement':'The intended recipient is in the lobby.','basis':'assignment context'},
        'radio_unanswered':{'statement':'Dispatch supplies no answer.','basis':'failed request'},
        'stop_pressed':{'statement':'The protagonist attempts to stop the lift.','basis':'existing control action'},
        'lobby_passed':{'statement':'The lift passes the intended stopping point.','basis':'floor sequence','earliest_reveal':23},
        'sealed_floor':{'statement':'The lower service floor is sealed.','basis':'existing canon/status panel','earliest_reveal':24},
        'figure_present':{'statement':'A figure is waiting beyond the doors.','basis':'existing corridor reveal','earliest_reveal':31},
        'parcel_not_wanted':{'statement':'The figure permits keeping, or denies ordering, the parcel.','basis':'its answer','earliest_reveal':37},
        'human_delivery_claim':{'statement':'The figure identifies the protagonist as the delivery.','basis':'cliffhanger claim, not an explanation of its origin','earliest_reveal':43}
    }
    beliefs={
        'dispatch_error':'The completed status is a clerical error a normal person can correct.',
        'controls_work':'The protagonist can still choose the lobby or stop the lift.',
        'ordinary_recipient':'The figure wants the parcel and can be dealt with as a customer.'}
    goals={'resolve_error':'Clear the impossible completion and finish the shift.',
           'reach_recipient':'Obtain the recipient name to explain the status.',
           'escape':'Get out safely while retaining control of the parcel.'}
    reveal=lambda fact,at,to,evidence:dict(fact=fact,at=at,to=to,evidence=evidence)
    change=lambda at,remove=(),add=(),who=('audience','protagonist'):dict(at=at,remove=list(remove),add=list(add),who=list(who))
    choice=lambda choice_id,at,goal,action,reason,evidence,known=(),believed=():dict(id=choice_id,at=at,goal=goal,action=action,reason=reason,evidence=evidence,requires_known=list(known),based_on_beliefs=list(believed))
    consequence=lambda source,at,effect,meaning:dict(from_choice=source,at=at,effect=effect,meaning=meaning)
    if strategy=='withdrawal':
        beats=[
            _beat('contradiction',0,4.6,2,['opening'],reveals=[reveal('job_complete',2.4,['audience'],'opening'),reveal('parcel_held',4.5,['audience'],'opening')]),
            _beat('reassurance_and_choice',4.6,13,3,['hope','cancel'],reveals=[reveal('destination_lobby',9.25,['audience'],'hope')],choices=[choice('cancel_job',12.7,'resolve_error','Ask dispatch to cancel and return the parcel.','A clerical mistake should be reversible.','cancel',['job_complete','parcel_held'],['dispatch_error'])]),
            _beat('no_human_answer',13,22.5,4,['silence_meaning','stop'],reveals=[reveal('radio_unanswered',18.8,['audience','protagonist'],'silence_meaning and unanswered radio'),reveal('stop_pressed',20.9,['audience','protagonist'],'existing stop press / stop cue')],choices=[choice('try_stop',20.9,'resolve_error','Try the stop control.','Dispatch has not answered, so use a physical control.','existing button press',['radio_unanswered'],['controls_work'])],consequences=[consequence('cancel_job',18.8,'No reply comes.','The imagined normal argument would be reassuring; she cannot even reach it.')]),
            _beat('escape_replaces_job',22.5,29.4,6,['goal_changes','sealed'],reveals=[reveal('lobby_passed',23.4,['audience','protagonist'],'goal_changes and floor zero'),reveal('sealed_floor',25.2,['protagonist'],'minus-one status panel'),reveal('sealed_floor',29.2,['audience'],'sealed')],belief_changes=[change(25.2,['dispatch_error','controls_work'])],consequences=[consequence('try_stop',25.2,'The lift passes the lobby and stops below it.','The problem becomes personal safety rather than finishing a delivery.')],surprise={'contradicts_belief':'controls_work','revealed_by':'lobby_passed'},goal_after='escape'),
            _beat('last_normal_explanation',29.4,37.3,7,['last_hope'],reveals=[reveal('figure_present',35.5,['protagonist'],'opening doors'),reveal('figure_present',37.1,['audience'],'last_hope')],belief_changes=[change(35.5,add=['ordinary_recipient'])]),
            _beat('refusal_fails',37.3,42.8,8,['refuse','answer'],choices=[choice('refuse_handoff',39.6,'escape','Refuse the parcel handoff.','Keeping the parcel should prevent an unwanted exchange.','refuse',['figure_present','parcel_held'],['ordinary_recipient'])],reveals=[reveal('parcel_not_wanted',42.55,['audience','protagonist'],'answer')],consequences=[consequence('refuse_handoff',42.55,'The figure tells her to keep it.','Refusing the object does not cancel what is happening.')]),
            _beat('reversal',42.8,45,10,['reversal'],reveals=[reveal('human_delivery_claim',44.5,['audience','protagonist'],'reversal')],belief_changes=[change(44.5,['ordinary_recipient'])],surprise={'contradicts_belief':'ordinary_recipient','revealed_by':'human_delivery_claim'})]
        purpose={'opening':('context',['job_complete','parcel_held'],[],['resolve_error']),
                 'hope':('belief',['destination_lobby'],['dispatch_error'],['resolve_error']),
                 'cancel':('decision',[],['dispatch_error'],['resolve_error']),
                 'silence_meaning':('interpretation',['radio_unanswered'],[],['resolve_error']),
                 'stop':('request',[],['controls_work'],['resolve_error']),
                 'goal_changes':('goal_change',['lobby_passed'],[],['escape']),
                 'sealed':('reaction',['sealed_floor'],[],['escape']),
                 'last_hope':('belief',['figure_present'],['ordinary_recipient'],['escape']),
                 'refuse':('refusal',[],['ordinary_recipient'],['escape']),
                 'answer':('answer',['parcel_not_wanted'],[],['escape']),
                 'reversal':('answer',['human_delivery_claim'],[],['escape'])}
    else:
        beats=[
            _beat('contradiction',0,4.6,2,['opening'],reveals=[reveal('job_complete',2.4,['audience'],'opening'),reveal('parcel_held',4.5,['audience'],'opening')]),
            _beat('find_a_name',4.6,18.4,3,['hope','ask_dispatch','reason_for_name'],reveals=[reveal('destination_lobby',9.7,['audience'],'hope'),reveal('radio_unanswered',17.9,['audience','protagonist'],'unanswered dispatch request')],choices=[choice('ask_dispatch',12.75,'reach_recipient','Ask who accepted the parcel.','A recipient name could explain the clerical error.','ask_dispatch',['job_complete','parcel_held'],['dispatch_error'])],consequences=[consequence('ask_dispatch',17.9,'Dispatch supplies no name.','She decides to obtain proof from the recipient instead.')]),
            _beat('route_to_proof_blocked',18.4,29.4,5,['choose_verification','blocked_route','plea'],choices=[choice('ask_in_person',20.1,'reach_recipient','Seek the recipient personally.','Dispatch has not answered.','choose_verification',['radio_unanswered'],['dispatch_error']),choice('stop_at_lobby',20.9,'reach_recipient','Try the stop control at the intended destination.','The recipient should be in the lobby.','existing button press',['destination_lobby'],['controls_work'])],reveals=[reveal('stop_pressed',20.9,['audience','protagonist'],'existing stop press'),reveal('lobby_passed',23.4,['audience','protagonist'],'blocked_route and display'),reveal('sealed_floor',25.6,['audience','protagonist'],'blocked_route and status panel')],belief_changes=[change(25.6,['controls_work'])],consequences=[consequence('stop_at_lobby',25.6,'The lift takes her below the intended recipient.','Her reasonable plan has carried her into a place that should not receive deliveries.')],surprise={'contradicts_belief':'controls_work','revealed_by':'sealed_floor'},goal_after='escape'),
            _beat('possible_human_help',29.4,35,6,['possible_answer'],reveals=[reveal('figure_present',34.6,['audience','protagonist'],'possible_answer and opening doors')],belief_changes=[change(34.6,add=['ordinary_recipient'])]),
            _beat('test_the_explanation',35,40.25,8,['test_recipient','denial'],choices=[choice('test_recipient',36.9,'escape','Ask whether this person accepted the parcel.','An answer might explain the destination and help her get out.','test_recipient',['figure_present','sealed_floor'],['ordinary_recipient'])],reveals=[reveal('parcel_not_wanted',40.1,['audience','protagonist'],'denial')],consequences=[consequence('test_recipient',40.1,'The figure denies ordering a parcel.','The last normal explanation fails on its own terms.')],belief_changes=[change(40.1,['dispatch_error'])],surprise={'contradicts_belief':'dispatch_error','revealed_by':'parcel_not_wanted'}),
            _beat('ask_the_dangerous_question',40.25,42.8,9,['follow_up'],choices=[choice('ask_what',42.2,'escape','Ask what was ordered instead.','The person may explain why the lift brought her here.','follow_up',['parcel_not_wanted'],['ordinary_recipient'])]),
            _beat('reversal',42.8,45,10,['reversal'],reveals=[reveal('human_delivery_claim',44.5,['audience','protagonist'],'reversal')],belief_changes=[change(44.5,['ordinary_recipient'])],consequences=[consequence('ask_what',44.5,'The figure names the courier as the delivery.','Her test exposes that she misunderstood what the transaction meant.')],surprise={'contradicts_belief':'ordinary_recipient','revealed_by':'human_delivery_claim'})]
        purpose={'opening':('context',['job_complete','parcel_held'],[],['reach_recipient']),
                 'hope':('belief',['destination_lobby'],['dispatch_error'],['reach_recipient']),
                 'ask_dispatch':('test',[],['dispatch_error'],['reach_recipient']),
                 'reason_for_name':('expectation',[],['dispatch_error'],['reach_recipient']),
                 'choose_verification':('decision',[],['dispatch_error'],['reach_recipient']),
                 'blocked_route':('interpretation',['sealed_floor'],['controls_work'],['escape']),
                 'plea':('request',[],[],['escape']),
                 'possible_answer':('belief',['figure_present'],['ordinary_recipient'],['escape']),
                 'test_recipient':('test',[],['ordinary_recipient'],['escape']),
                 'denial':('answer',['parcel_not_wanted'],[],['escape']),
                 'follow_up':('test',[],['ordinary_recipient'],['escape']),
                 'reversal':('answer',['human_delivery_claim'],[],['escape'])}
    links={}
    for beat in beats:
        if beat.get('goal_after')=='escape': beat['goal_change_at']=23.4 if strategy=='withdrawal' else 25.6
    for beat in beats:
        for cue_id in beat['cues']:
            p,context,assumptions,aims=purpose[cue_id]
            links[cue_id]={'beat':beat['id'],'purpose':p,'context_facts':context,
                'beliefs':assumptions,'goals':aims,'requires_known':[],
                'why_it_matters':f'{p} links this cue to '+', '.join(context+assumptions+aims)}
    for cue_id,known in ({'cancel':['job_complete','parcel_held'],'sealed':['sealed_floor'],'refuse':['figure_present','parcel_held']} if strategy=='withdrawal' else {'ask_dispatch':['job_complete'],'test_recipient':['figure_present'],'follow_up':['parcel_not_wanted']}).items():
        links[cue_id]['requires_known']=known
    questions={'who_marked':{'question':'Who arranged or confirmed the delivery?','arises_from':['job_complete']},
               'why_this_person':{'question':'Why was this courier selected?','arises_from':['human_delivery_claim']},
               'escape':{'question':'Can the courier refuse an already accepted delivery?','arises_from':['human_delivery_claim','lobby_passed']}}
    return {'schema':1,'archetype':'delivery_trap','strategy':strategy,
        'strategy_description':'Attempt to withdraw from a seemingly reversible transaction.' if strategy=='withdrawal' else 'Investigate a supposedly clerical error by testing a recipient.',
        'facts':facts,'beliefs':beliefs,'goals':goals,'questions':questions,
        'initial':{'audience_knows':[],'protagonist_knows':['job_complete','parcel_held','destination_lobby'],
                   'audience_believes':['dispatch_error','controls_work'],'protagonist_believes':['dispatch_error','controls_work'],
                   'goal':'resolve_error' if strategy=='withdrawal' else 'reach_recipient'},
        'beats':beats,'cue_links':links,
        'protected_lines':{'opening':lines[0]['text'],'reversal':"You're the delivery."},
        'cliffhanger':{'cue_id':'reversal','fact':'human_delivery_claim','payoff_of':['job_complete','parcel_held'],
            'reframes_belief':'ordinary_recipient','unresolved':['who_marked','why_this_person','escape']},
        'continuity':{'start_state':copy.deepcopy(plan['start_state']),'end_state':copy.deepcopy(plan['end_state']),
                      'status':'Review treatment only; no canonical checkpoint mutation'}}


def write_delivery(plan,strategy='withdrawal',context=None):
    context=context or plan.get('story_context',{})
    if strategy not in ['withdrawal','verification']: raise ValueError('Unknown suspense strategy')
    lines=delivery_lines(plan,strategy,context)
    treatment=delivery_treatment(plan,strategy,lines)
    review=validate_story(treatment,lines)
    return {'schema':1,'title':'Return to Sender','strategy':strategy,'narration':lines,'suspense':treatment,
        'structural_review':{k:v for k,v in review.items() if k!='knowledge_timeline'},
        'editorial_status':'Human writing/listening review pending; not an automatic quality approval'}



def write_voice_story(plan):
    """A second, renderable archetype: borrowed identity and escape by silence.

    Facts are observations/claims, not an omniscient explanation of the entity.
    Each beat has an intent, evidence, a choice where appropriate and a response.
    """
    escape=plan['kind']=='escape'
    if escape:
        specs=[
          (0,5,2,'The voice below knew their name. They had never given it.','narrator','context','identity','The presence recognizes the passenger.',None,None),
          (5,13,3,'One answer might explain it. That was the temptation.','narrator','belief','temptation','The voice solicits a reply.','refuse','Do not answer the borrowed voice.'),
          (13,19.5,4,'Answer me.','antagonist','request','demand','The presence demands an answer.',None,None),
          (19.5,28.8,6,'They chose the ground control instead. Silence was the only refusal it could not borrow.','narrator','interpretation','descent','Silence and ground control seal the presence below.','ground','Use the ground control without answering.'),
          (28.8,37.3,7,'They expected it at the next door. There was nobody there.','narrator','expectation','empty','The ground corridor is empty.',None,None),
          (37.3,42.8,8,'Getting out answered one question. It did not explain the name.','narrator','interpretation','exit','The passenger leaves at ground level.',None,None),
          (42.8,45,9,'Who gave it my name?','protagonist','test','origin','The source of its knowledge remains unknown.',None,None)]
        goal='escape';goal_text='Reach ground safely without answering the borrowed voice.'
        expectation='Reaching ground will explain or end the encounter.'
        question='Who supplied the presence with the passenger identity?'
        change_id='empty';payoff=['identity','demand']
        history=plan['start_state'].get('story_memory',{}).get('history',[])
        if history and history[-1].get('archetype')=='delivery_trap':
            specs[0]=(0,5,2,"They had been called the delivery. Keeping the parcel hadn't saved them.",'narrator','context','identity','The figure claimed the passenger was the delivery.',None,None)
            specs[-1]=(42.8,45,9,'Who marked me delivered?','protagonist','test','origin','The person who arranged the human delivery remains unidentified.',None,None)
            question='Who arranged the delivery of the protagonist, and why?'

    else:
        specs=[
          (0,5,2,'The radio used their name before they had switched it on.','narrator','context','identity','The presence recognizes the passenger.',None,None),
          (5,13,3,'They assumed dispatch had the wrong channel. A reply could clear that up.','narrator','belief','mistake','The passenger believes this is a crossed radio channel.','contact','Ask who is calling.'),
          (13,19.5,4,'Hello? Who is this?','protagonist','request','reply','Dispatch supplies no identifying answer.',None,None),
          (19.5,28.8,6,'No answer. They tried the lobby control. Below it was a floor nobody used.','narrator','goal_change','wrong_floor','The control fails to stop the lift above the sealed floor.','stop','Press the lobby control to leave.'),
          (28.8,37.3,7,'Someone was waiting. For a moment, that seemed better than being alone.','narrator','belief','figure','A faceless figure waits beyond the doors.',None,None),
          (37.3,42.8,8,'Were you calling me?','protagonist','test','question','The passenger tests whether the figure is the caller.',None,None),
          (42.8,45,10,'I know your voice.','antagonist','answer','recognition','The figure claims familiarity with the passenger voice.',None,None)]
        goal='identify';goal_text='Identify the caller and reach the lobby.'
        expectation='This is an ordinary dispatch error that a reply can resolve.'
        question='How does the figure know a voice it has not heard on this journey?'
        change_id='recognition';payoff=['identity','reply']
    lines=[];beats=[];links={};facts={};previous_choice=None
    for i,(a,b,t,text,role,purpose,fact,statement,choice_id,action) in enumerate(specs):
        cue_id='beat_'+str(i);start=a+.15;end=b-.2
        lines.append(_line(plan,cue_id,start,end,role,text))
        facts[fact]={'statement':statement,'basis':cue_id,'earliest_reveal':a}
        beat=_beat(cue_id,a,b,t,[cue_id],reveals=[{'fact':fact,'at':b-.3,'to':['audience','protagonist'],'evidence':cue_id}])
        if choice_id:
            beat['choices']=[{'id':choice_id,'at':b-.2,'goal':goal,'action':action,
                'reason':goal_text,'evidence':cue_id if escape else 'dialogue and existing control action',
                'requires_known':['identity'],'based_on_beliefs':[]}]
        if previous_choice:
            beat['consequences']=[{'from_choice':previous_choice,'at':b-.3,
                'effect':statement,'meaning':'This response changes the available route toward '+goal_text}]
            previous_choice=None
        if choice_id: previous_choice=choice_id
        if fact==change_id:
            beat['surprise']={'contradicts_belief':'normal_resolution','revealed_by':fact}
            beat['belief_changes']=[{'at':b-.3,'remove':['normal_resolution'],'add':[],'who':['audience','protagonist']}]
        beats.append(beat)
        links[cue_id]={'beat':cue_id,'purpose':purpose,'context_facts':[fact],
            'beliefs':['normal_resolution'] if purpose in ['belief','expectation'] else [],'goals':[goal],
            'requires_known':[],'why_it_matters':statement+' Changes the expectation: '+expectation}
    # Deliberate playable decisions; narrator supplies their motive, actor their intent.
    if not escape:
        lines.insert(2,_line(plan,'request',10,12.7,'protagonist','Dispatch? Can you hear me?','uneasy'))
        lines[1]['end']=9.6
        beats[1]['cues'].append('request')
        links['request']={'beat':'beat_1','purpose':'request','requires_known':['identity'],
            'why_it_matters':'Tests the crossed-channel explanation before resorting to a control.'}
    last=specs[-1][6]
    treatment={'schema':1,'archetype':'voice_trap','strategy':'silent_escape' if escape else 'identify_caller',
        'strategy_description':goal_text,'facts':facts,'beliefs':{'normal_resolution':expectation},
        'goals':{goal:goal_text},'questions':{'source':{'question':question,'arises_from':payoff+[last]}},
        'initial':{'audience_knows':[],'protagonist_knows':['identity'],'audience_believes':['normal_resolution'],
            'protagonist_believes':['normal_resolution'],'goal':goal},
        'beats':beats,'cue_links':links,'protected_lines':{'beat_0':lines[0]['text'],'beat_6':lines[-1]['text']},
        'cliffhanger':{'cue_id':'beat_6','fact':last,'payoff_of':payoff,
            'reframes_belief':'normal_resolution','unresolved':['source']},
        'continuity':{'start_state':copy.deepcopy(plan['start_state']),'end_state':copy.deepcopy(plan['end_state'])}}
    review=validate_story(treatment,lines)
    return {'schema':1,'title':plan['title'],'narration':lines,'suspense':treatment,
        'structural_review':{k:v for k,v in review.items() if k!='knowledge_timeline'}}


def draft_story(plan):
    """Select a reusable archetype from series context, never an episode number."""
    context=plan.get('story_context',{})
    character=plan['start_state']['characters']['protagonist']['name'].lower()
    archetype=context.get('archetype','delivery_trap' if 'courier' in character else 'voice_trap')
    if plan['kind']=='arrival' and archetype=='delivery_trap':
        return write_delivery(plan,context.get('strategy','withdrawal'),context)
    return write_voice_story(plan)


def realize_local(plan,draft,model):
    """Constrain fresh prose to a treatment, with one bounded critique/repair.

    A model response with only legacy radio lines uses the checked offline prose.
    A model claiming new prose must pass structure and an explicit local critique;
    subjective quality is never inferred from the structural validator alone.
    """
    contract={'principles':rules(),
        'series':plan['series_title'],'canon':plan['start_state'],'outcome':plan['end_state'],
        'treatment':draft['suspense'],'cue_skeleton':draft['narration'],
        'instructions':'Preserve IDs, roles, speakers, time windows, and protected lines. Write fresh suspenseful dialogue within each word budget. Narrator supplies context, motive or changed meaning. No generic warnings or visual inventories. Return title, exactly seven radio_lines of at most eight words each for legacy rendering, and optional dialogue cues.'}
    response=model.generate('SCREENPLAY_TREATMENT_FIRST '+json.dumps(contract))
    title=response.get('title','');radio=response.get('radio_lines',[])
    if not isinstance(title,str) or not title.strip() or len(title)>80 or not isinstance(radio,list) or len(radio)!=7 or any(not isinstance(x,str) or not x.strip() or len(x.split())>8 for x in radio):
        raise ValueError('Local model returned an invalid title/radio contract')
    candidate=response.get('dialogue')
    receipt={'source':'offline_causal_grammar','local_critic':'not_run_legacy_response'}
    if candidate is not None:
        for attempt in range(2):
            if not isinstance(candidate,list) or len(candidate)!=len(draft['narration']): raise ValueError('Local writer changed cue count')
            for line,base in zip(candidate,draft['narration']):
                if any(line.get(k)!=base[k] for k in ['id','start','end','role','speaker']): raise ValueError('Local writer changed fixed staging/timing')
                if len(line['text'].split())>max(3,int((line['end']-line['start'])*3)): raise ValueError('Local prose exceeds preliminary speech budget')
            validate_story(draft['suspense'],candidate)
            critique=model.generate('CRITIQUE_SCREENPLAY Return JSON {approved: boolean, issues: [specific editorial issues]}. Do not approve factual inventories, unnatural dialogue, unmotivated choices, leaked facts, meaningless warnings, repetitions or a disconnected cliffhanger. Evaluate all cues against treatment. '+json.dumps({'treatment':draft['suspense'],'dialogue':candidate}))
            if critique.get('approved') is True and critique.get('issues')==[]:
                receipt={'source':'local_llm_treatment_first','local_critic':'approved_by_same_model_not_human','repair_attempts':attempt};break
            if attempt: raise ValueError('Local screenplay failed bounded editorial review')
            repair=model.generate('REPAIR_SCREENPLAY Return JSON {dialogue: [...]} preserving fixed cue skeleton and protected lines. '+json.dumps({'contract':contract,'dialogue':candidate,'issues':critique.get('issues',[])}))
            candidate=repair.get('dialogue')
        draft=copy.deepcopy(draft);draft['narration']=candidate
    return draft,title,radio,receipt


def attach_story(plan,model=None):
    """Pure planning: memory is serialized in the proposed end state only.

    Existing ledger verification remains the sole authority that commits canon.
    Questions and claims keep their epistemic status; a spoken claim is not truth.
    """
    draft=draft_story(plan)
    receipt={'source':'offline_causal_grammar','human_review':'pending'}
    if model:
        draft,plan['title'],plan['radio_lines'],receipt=realize_local(plan,draft,model)
        plan['source']='local_llm'
    review=validate_story(draft['suspense'],draft['narration'])
    memory=copy.deepcopy(plan['start_state'].get('story_memory',{'history':[]}))
    memory['history'].append({'episode_uid':plan['uid'],'archetype':draft['suspense']['archetype'],
        'facts_or_claims':copy.deepcopy(draft['suspense']['facts']),
        'audience_knows':review['final_state']['audience_knows'],
        'protagonist_knows':review['final_state']['protagonist_knows'],
        'remaining_beliefs':review['final_state']['protagonist_believes'],
        'last_goal':review['final_state']['goal'],'unresolved':review['unresolved'],
        'status':'Proposed until existing verified-episode transaction commits this state'})
    plan['end_state']['story_memory']=memory
    draft['suspense']['continuity']['end_state']=copy.deepcopy(plan['end_state'])
    draft['suspense']['prior_story_memory']=copy.deepcopy(plan['start_state'].get('story_memory',{}))
    plan.update(dialogue=draft['narration'],suspense=draft['suspense'],screenwriter=receipt)
    return plan
