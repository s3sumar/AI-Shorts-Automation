"""Audience/protagonist information states and causal suspense validation.

This checks declared narrative structure. It cannot prove that prose is moving,
or infer every semantic contradiction; optional local critique and human review
remain separate from these mechanical checks.
"""
import copy
import json
import re
from pathlib import Path
from soundstage.voice_contract import validate_dialogue

ROOT=Path(__file__).resolve().parents[1]


def rules(): return json.loads((ROOT/'config/storytelling_principles.json').read_text())


def validate_story(model,lines,duration=45):
    validate_dialogue(lines,duration)
    policy=rules()
    facts=model['facts'];beliefs=model['beliefs'];goals=model['goals'];beats=model['beats']
    if not isinstance(facts,dict) or not facts or not all(isinstance(v.get('statement'),str) and v['statement'].strip() for v in facts.values()):
        raise ValueError('Named fact statements required')
    if not 3<=len(beats)<=policy['maximum_beats']: raise ValueError('Bounded narrative beat sequence required')
    by_id={line['id']:line for line in lines}
    if len(by_id)!=len(lines): raise ValueError('Unique dialogue cue IDs required')
    if set(model['cue_links'])!=set(by_id): raise ValueError('Every spoken cue needs a narrative purpose')
    coverage=[cue for beat in beats for cue in beat['cues']]
    if len(coverage)!=len(set(coverage)) or set(coverage)!=set(by_id): raise ValueError('Every cue must belong to exactly one beat')
    if len({b['id'] for b in beats})!=len(beats): raise ValueError('Unique beat IDs required')
    questions=model['questions']
    for question in questions.values():
        if not question.get('question') or not question.get('arises_from') or not set(question['arises_from'])<=set(facts):
            raise ValueError('Mysteries must be connected to named facts')
    initial=model['initial']
    for key in ['audience_knows','protagonist_knows']:
        if not set(initial[key])<=set(facts): raise ValueError('Unknown initial knowledge')
    for key in ['audience_believes','protagonist_believes']:
        if not set(initial[key])<=set(beliefs): raise ValueError('Unknown initial belief')
    if initial['goal'] not in goals: raise ValueError('Initial immediate goal required')
    events=[];choices={};consequences=[];surprises=0;last=0;tension=[]
    for beat in beats:
        if not last==beat['start']<beat['end']<=duration: raise ValueError('Beat timeline gap or overlap')
        last=beat['end'];tension.append(beat['tension'])
        if not isinstance(beat['tension'],int) or not 0<=beat['tension']<=10: raise ValueError('Invalid suspense level')
        for cue_id in beat['cues']:
            if cue_id not in by_id: raise ValueError('Unknown cue in beat')
            cue=by_id[cue_id]
            if not beat['start']<=cue['start']<cue['end']<=beat['end']: raise ValueError('Dialogue falls outside its beat')
            if model['cue_links'][cue_id]['beat']!=beat['id']: raise ValueError('Wrong cue-to-beat link')
        for reveal in beat.get('reveals',[]):
            if reveal['fact'] not in facts or not beat['start']<=reveal['at']<=beat['end']: raise ValueError('Invalid revelation')
            if reveal['at']<facts[reveal['fact']].get('earliest_reveal',0): raise ValueError('Premature protected reveal')
            if not reveal.get('evidence'): raise ValueError('A revelation needs spoken/visual/sound evidence')
            if not reveal.get('to') or not set(reveal['to'])<={'audience','protagonist'}: raise ValueError('Invalid knowledge recipient')
            events.append((reveal['at'],0,'reveal',reveal))
        for change in beat.get('belief_changes',[]):
            if not set(change.get('add',[])+change.get('remove',[]))<=set(beliefs): raise ValueError('Unknown changed belief')
            events.append((change['at'],1,'belief',change))
        for choice in beat.get('choices',[]):
            if choice['id'] in choices or choice['goal'] not in goals: raise ValueError('Duplicate choice or unknown goal')
            if not choice.get('action') or not choice.get('reason') or not choice.get('evidence'): raise ValueError('Choice requires action, reason and realization')
            choices[choice['id']]=choice
            events.append((choice['at'],2,'choice',choice))
        for consequence in beat.get('consequences',[]):
            if not consequence.get('effect') or not consequence.get('meaning'): raise ValueError('Consequence must change the situation')
            consequences.append(consequence)
            events.append((consequence['at'],3,'consequence',consequence))
        if beat.get('surprise'):
            surprise=beat['surprise']
            if surprise['contradicts_belief'] not in beliefs or surprise['revealed_by'] not in facts:
                raise ValueError('A surprise must overturn an expectation with evidence')
            surprises+=1
        if 'goal_after' in beat:
            if beat['goal_after'] not in goals: raise ValueError('Unknown new goal')
            at=beat.get('goal_change_at',beat['end'])
            if not beat['start']<=at<=beat['end']: raise ValueError('Goal change falls outside its beat')
            events.append((at,1,'goal',beat['goal_after']))
        for collection in ['belief_changes','choices','consequences']:
            for event in beat.get(collection,[]):
                if not beat['start']<=event['at']<=beat['end']: raise ValueError('Narrative event falls outside its beat')
    if last!=duration: raise ValueError('Narrative beats must cover the full duration')
    if len(choices)<policy['minimum_choices'] or len(consequences)<policy['minimum_choice_consequences']:
        raise ValueError('Story needs choices with consequences')
    for consequence in consequences:
        source=choices.get(consequence['from_choice'])
        if not source or consequence['at']<source['at']: raise ValueError('Consequence precedes or invents its choice')
    if surprises<policy['minimum_surprises']: raise ValueError('No meaningful reversal of an expectation')
    if tension[-1]<tension[0]+policy['minimum_tension_rise'] or any(b<a for a,b in zip(tension,tension[1:])):
        raise ValueError('Suspense progression does not escalate')
    state=copy.deepcopy(initial);timeline=[]
    for at,priority,kind,event in sorted(events,key=lambda e:(e[0],e[1])):
        before=copy.deepcopy(state)
        if kind=='reveal':
            for who in event['to']:
                key=who+'_knows'
                if event['fact'] not in state[key]: state[key].append(event['fact'])
        elif kind=='belief':
            for who in event.get('who',['protagonist']):
                key=who+'_believes'
                state[key]=[b for b in state[key] if b not in event.get('remove',[])]+[b for b in event.get('add',[]) if b not in state[key]]
        elif kind=='choice':
            if not set(event.get('requires_known',[]))<=set(state['protagonist_knows']): raise ValueError('Character choice uses unavailable knowledge')
            if not set(event.get('based_on_beliefs',[]))<=set(state['protagonist_believes']): raise ValueError('Character choice uses an unstated belief')
            if event['goal']!=state['goal']: raise ValueError('Choice is disconnected from the current goal')
        elif kind=='goal': state['goal']=event
        timeline.append({'at':at,'kind':kind,'before':before,'after':copy.deepcopy(state)})
    for cue_id,link in model['cue_links'].items():
        cue=by_id[cue_id]
        role=cue.get('role',cue['speaker'])
        purposes=policy['narrator_purposes'] if role=='narrator' else policy['character_purposes']
        if link['purpose'] not in purposes or not link.get('why_it_matters'): raise ValueError('Line has no supported story purpose')
        if not set(link.get('beliefs',[]))<=set(beliefs) or not set(link.get('goals',[]))<=set(goals): raise ValueError('Cue references unknown beliefs or goals')
        if role=='narrator' and not any(link.get(key) for key in ['context_facts','beliefs','goals','changes_meaning_of']):
            raise ValueError('Narrator only describes visible action')
        if not set(link.get('communicates',[])+link.get('requires_known',[])+link.get('context_facts',[])+link.get('changes_meaning_of',[]))<=set(facts):
            raise ValueError('Cue references unknown facts')
        knowledge=set(initial['protagonist_knows'])
        for t,_,kind,event in sorted(events,key=lambda e:(e[0],e[1])):
            if t>cue['start']: break
            if kind=='reveal' and 'protagonist' in event['to']: knowledge.add(event['fact'])
        if role=='protagonist' and not set(link.get('requires_known',[]))<=knowledge: raise ValueError('Dialogue leaks character knowledge')
    cliff=model['cliffhanger']
    if cliff['cue_id'] not in by_id or cliff['fact'] not in facts: raise ValueError('Cliffhanger needs an actual final cue and fact')
    if not cliff.get('payoff_of') or not set(cliff['payoff_of'])<=set(facts): raise ValueError('Cliffhanger has no planted clue')
    if not cliff.get('unresolved') or not set(cliff['unresolved'])<=set(questions): raise ValueError('Cliffhanger has no specific open question')
    if not cliff.get('reframes_belief') or cliff['reframes_belief'] not in beliefs: raise ValueError('Cliffhanger changes no interpretation')
    final=by_id[cliff['cue_id']]
    if final!=lines[-1] or final['start']<duration-3: raise ValueError('Cliffhanger is not reserved for the ending')
    planted=set(initial['audience_knows'])
    for at,_,kind,event in events:
        if kind=='reveal' and at<final['start'] and 'audience' in event['to']: planted.add(event['fact'])
    if not set(cliff['payoff_of'])<=planted: raise ValueError('Cliffhanger payoff was not planted for the audience')
    if not any(set(questions[q]['arises_from']) & set(cliff['payoff_of']+[cliff['fact']]) for q in cliff['unresolved']): raise ValueError('Open mystery is disconnected from the cliffhanger')
    protected=model.get('protected_lines',{})
    for cue_id,text in protected.items():
        if by_id.get(cue_id,{}).get('text')!=text: raise ValueError('A protected story line was altered')
    for line in lines[:-1]:
        if final['text'].lower().rstrip('.!?') in line['text'].lower(): raise ValueError('Final reveal appears early')
    if cliff['fact'] not in state['audience_knows'] or cliff['fact'] not in state['protagonist_knows']:
        raise ValueError('Cliffhanger was never revealed to both audience and character')
    return {'passed':True,'choices':len(choices),'consequences':len(consequences),'surprises':surprises,
            'knowledge_timeline':timeline,'final_state':state,'unresolved':{key:questions[key]['question'] for key in cliff['unresolved']},
            'scope':'Declared knowledge/causality/timing checks; semantic and dramatic quality still require review'}
