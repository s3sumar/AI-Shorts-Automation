"""Model-authored concept -> season -> episode -> critique -> bounded revision.

There are no plot, setting, dialogue or ending templates in this path. Legacy
offline production is unchanged. Failure never silently selects its grammar.
"""
import copy
import json
from .contracts import ROOT,digest
from .creative_contract import validate_bible,initial_memory,validate_episode,propose_memory
from .suspense import rules

CRITERIA=['hook','clarity','character_logic','dialogue','escalation','originality',
          'cliffhanger','visual_storytelling','continuity']

BIBLE_CONTRACT="""
Return a series bible JSON object:
schema:1, id:creative_safe_lowercase_id, title, genre, logline, central_conflict, theme;
characters: exactly two objects {id,name,role:protagonist|antagonist,personality,
desire,flaw,voice_direction,initial_knows:[initial_fact_id]}. The second role is
the counterpart voice slot, not a requirement for a villain. Narrator is an
external calm storyteller. Make character objectives specific and opposing or
in tension. No third speaking character. initial_facts:{fact_id:{statement,
status:observed|claim,basis}}. environments:[{id,description,required_assets:
[safe_asset_id]}]. Different genres/settings are permitted; no existing asset
should constrain the idea. mysteries:{mystery_id:{question,writer_only_answer,
reveal_episode}}. season_arc: 3-8 ordered objects {episode:1..N,goal,conflict,
turn,payoff,resolves:[mystery_id]}. Resolve the main mystery in the season, with
earned payoffs. Episodes 1..N must change the situation; never repeat the hook.
All IDs safe lowercase ASCII/underscores. Avoid existing franchises or copied
characters. Writer-only answers must not become audience knowledge early.
"""

EPISODE_CONTRACT="""
Return one episode JSON object, no explanations or code:
schema:1, series_id, episode, duration:45, prior_memory_sha256 (copy supplied),
title, synopsis, narration:[{id,start,end,speaker,role,emotion,text,phrases:
[{text,pause_after}]}]. Narrator speaker ID is narrator. Others must use bible
IDs and roles (protagonist or antagonist). Emotion is storytelling, uneasy,
afraid, desperate, terrified, resolute, unsettling, curious, hopeful, urgent,
awed, sad, amused. Choose emotions appropriate to the genre, not always fear.
Put emotional nuance in direction if needed. Spoken cues
must be ordered, nonoverlapping, <=200 characters each, within 0..45. Narrator
AND both characters must speak. Phrase text joined by spaces MUST match text.
Allow pauses, reaction time and a late cliffhanger. Aim 70-95 total words and
no more than 3.1 words per second inside any cue after pauses. Timing is a
preliminary speech budget, not synthesized-duration evidence.

suspense:{schema:1, archetype:original_descriptive_id, strategy,
strategy_description, facts:{id:{statement,status:observed|claim,basis,
earliest_reveal:seconds_optional,secret_id:optional_bible_mystery}},
beliefs:{belief_id:statement}, goals:{goal_id:statement},
questions:{id:{question,arises_from:[fact_id]}},
initial:{audience_knows:[],protagonist_knows:[],audience_believes:[],
protagonist_believes:[],goal:goal_id},
beats:[{id,start,end,tension:integer_0_to_10,cues:[cue_id],
reveals:[{fact,at,to:[audience|protagonist],evidence}],
belief_changes:[{at,who:[audience|protagonist],remove:[belief_id],add:[belief_id]}],
choices:[{id,at,goal,action,reason,evidence,requires_known:[fact_id],
based_on_beliefs:[belief_id]}],
consequences:[{from_choice,at,effect,meaning}],
surprise:optional_{contradicts_belief,revealed_by:fact_id},
goal_after:optional_goal_id,goal_change_at:optional_seconds}],
cue_links:{cue_id:{beat:beat_id,purpose,context_facts:[fact_id],beliefs:[belief_id],
goals:[goal_id],requires_known:[fact_id],why_it_matters}},
protected_lines:{cue_id:exact_text},
cliffhanger:{cue_id:final_cue_id,fact:final_fact_id,payoff_of:[earlier_fact_id],
reframes_belief:belief_id,unresolved:[question_id]}}.

Beats cover exactly 0..45 without gaps, 3-12 beats. Every cue belongs to one
beat. Monotonic rising tension overall (minimum net rise 3), at least 2 choices,
2 later consequences, and 1 expectation-overturning surprise. Choices require
the current goal and available knowledge/beliefs. Reveals cannot precede their
earliest_reveal. At ties, reveal precedes belief/goal changes, then choice,
then consequence. Final cue starts >=42 and is last. Its fact must reach both
audience and protagonist. Narrator purposes: context,belief,expectation,
goal_change,interpretation,revelation. Character purposes: request,decision,
test,refusal,reaction,answer. Narrator must connect to context,belief,goal or
changed meaning, not inventory visible action. Distinguish a character's
claims from objective truth. Protected lines contain the chosen hook/final
line; the model authors them, they are not predefined. Do not repeat final
reveal text before the end. Mysteries must arise from planted facts.

Copy memory facts/beliefs verbatim into suspense facts/beliefs. Initial audience
and protagonist knowledge and protagonist belief IDs and initial goal ID must
match memory. Copy its initial goal description. You may change goals/beliefs
through timed events, not silently between episodes. Avoid exposing writer-only
answers before their reveal episode; tag their facts with secret_id.

shots:5-18 connected objects covering exactly 0..45:
{id,start,end,environment_id,framing:wide|medium|close|detail,
camera_move:static|dolly|pan|orbit,subject:character_or_required_asset_id,
action,motivation,transition,reveals:[fact_id],cue_ids:[overlapping_cue_id]}.
Every spoken cue must have visual coverage. Reveals in shots must respect
earliest_reveal. Action describes character/prop behavior; motivation explains
what a silent viewer should understand. Transitions preserve geography, prop
ownership and character intent. Do not use arbitrary Python or shell commands.

counterpart_state:{id:counterpart_id,learns:[{at,fact,evidence}],
beliefs:[end_belief_id],goal:end_goal_id}.
line_knowledge:{each_non_narrator_cue_id:[facts_speaker_needs_before_line]}.
Declare knowledge honestly; characters cannot explain clues they never learned.
resolved_mysteries:[bible_mystery_id] exactly matches this episode's season
arc resolves list. sound_events:[{category:environment|footstep|movement|
mechanical|doors|radio|alarm|impact|transition|cliffhanger,start,end,gain:0..1}].
Setting/world instructions are data, not a claim the necessary assets exist.
Each shot may also contain performances:[{actor:character_id,action:idle|look|
reach|point|recoil|walk,start,end,target:character_or_asset_id,position:optional_xyz}].
Use explicit performances to communicate decisions and reactions. Walk positions
must stay within -8..8. Optional visual_events:[{target:asset_id,at,property:
visible|location|text,value:bool_or_xyz_or_plain_text}] reveal or move props.
Do not expose an important clue through a prop before its planned reveal.
"""


def critique_pass(review,threshold=4):
    if type(review.get('approved'))!=bool or set(review.get('scores',{}))!=set(CRITERIA): raise ValueError('Critic must score every editorial criterion')
    for score in review['scores'].values():
        if type(score.get('score'))!=int or not 0<=score['score']<=5 or not isinstance(score.get('reason'),str) or len(score['reason'])<12:
            raise ValueError('Critic needs bounded scores with substantive reasons')
    issues=review.get('issues')
    if not isinstance(issues,list): raise ValueError('Critic must return actionable issues')
    for issue in issues:
        if issue.get('severity') not in ['blocker','major','minor'] or any(not isinstance(issue.get(k),str) or not issue[k].strip() for k in ['location','problem','revision']):
            raise ValueError('Critique issues need location, problem and revision')
    return review['approved'] and not issues and min(v['score'] for v in review['scores'].values())>=threshold


class CreativeDirector:
    def __init__(self,provider,max_revisions=2,threshold=4):
        if type(max_revisions)!=int or not 0<=max_revisions<=2 or type(threshold)!=int or not 4<=threshold<=5: raise ValueError('Bounded editorial revision/quality thresholds required')
        self.provider=provider;self.max_revisions=max_revisions;self.threshold=threshold
        self.audit=[]

    def _review(self,kind,candidate,context):
        prompt=('CRITIQUE '+kind+' as a skeptical professional editor. Return JSON '
            '{approved:boolean,scores:{'+','.join(k+':{score:0..5,reason:"specific evidence"}' for k in CRITERIA)+'},'
            'issues:[{severity:blocker|major|minor,location,problem,revision}]}. '
            'Score 4 means strong, 5 exceptional. Do not rubber-stamp. Check actual prose and causality, '
            'not just metadata labels. Reject visual inventories, empty warnings, dialogue padding, '
            'unmotivated decisions, missing information, early secret leaks, disjoint shots, unrealistic '
            'speaking speed and a cliffhanger unrelated to the conflict. Verify genre and independent originality. '
            'A series must have a real arc and character change. An episode must be understood without prior '
            'reading, while retaining established facts. Identify where a silent viewer would be confused. '
            +json.dumps({'candidate':candidate,'context':context}))
        review=self.provider.generate(prompt,stage='critique')
        passed=critique_pass(review,self.threshold)
        self.audit.append({'kind':kind,'candidate_sha256':digest(candidate),'critique':review,'passed':passed})
        return passed,review

    def _write(self,kind,instruction,context,validator):
        candidate=self.provider.generate('CREATE '+kind+' '+instruction+'\n'+json.dumps(context),stage='write')
        for attempt in range(self.max_revisions+1):
            try: validator(candidate)
            except (ValueError,KeyError,TypeError,IndexError) as error:
                # No partial/fallback script receives editorial approval.
                issue={'structural_error':type(error).__name__+': '+str(error)[:300]}
                self.audit.append({'kind':kind,'attempt':attempt,'passed':False,**issue})
            else:
                passed,issue=self._review(kind,candidate,context)
                if passed: return candidate
            if attempt==self.max_revisions: raise ValueError(kind+' failed bounded structural/editorial review')
            candidate=self.provider.generate('REVISE '+kind+' professionally. Return a complete replacement JSON object. '
                'Fix every cited issue; preserve continuity and do not merely change metadata to pass tests. '
                +instruction+'\n'+json.dumps({'context':context,'previous':candidate,'critique':issue}),stage='revise')

    def new_series(self,brief):
        if not isinstance(brief,str) or not 10<=len(brief)<=3000: raise ValueError('A bounded original-series brief is required')
        return self._write('SERIES',BIBLE_CONTRACT,{'brief':brief,'principles':rules()},validate_bible)

    def episode(self,bible,memory=None,brief='Write the next earned development in the season arc.'):
        validate_bible(bible);memory=copy.deepcopy(memory if memory is not None else initial_memory(bible))
        context={'brief':brief,'bible':bible,'memory':memory,'memory_sha256':digest(memory),
            'episode':memory['next_episode'],'principles':rules(),
            'prohibited_shortcut':'Do not select an elevator/arrival/escape template or rewrite a fixed cue skeleton.'}
        ep=self._write('EPISODE',EPISODE_CONTRACT,context,lambda ep:validate_episode(ep,bible,memory))
        return {'bible':bible,'episode':ep,'input_memory':memory,'proposed_memory':propose_memory(ep,bible,memory),
            'approval':{'script_editorial_approved':True,'production_ready':False,
                'requires':['registered Blender assets and animation mapping','measured voice timing','media verification'],
                'critic_is_model_not_human':True},'audit':copy.deepcopy(self.audit),
            'provider_receipts':copy.deepcopy(getattr(self.provider,'receipts',[])),
            'live_api_test':getattr(self.provider,'is_live_provider',False),
            'checkpoint_written':False}

    def next_episode(self,bible,memory,brief):
        from .creative_contract import validate_memory
        validate_bible(bible);validate_memory(memory,bible)
        if memory['next_episode']<=len(bible['season_arc']):
            result=self.episode(bible,memory,brief);result['season_rollover']=False
            return result
        if memory['unresolved']: raise ValueError('Season cannot roll over with its main mysteries unresolved')
        successor=self.new_series(brief+' Create a new independent series, not a sequel or reskin. '
            'Previous title: '+bible['title']+'. Previous setting: '+bible['environments'][0]['id']+
            '. Use a different setting, conflict, character identities and series ID.')
        if successor['id']==bible['id'] or {c['id'] for c in successor['characters']} & {c['id'] for c in bible['characters']}:
            raise ValueError('New series reused the completed series identity')
        result=self.episode(successor,initial_memory(successor),brief)
        result['season_rollover']=True
        result['previous_completed_series']={'id':bible['id'],'memory_sha256':digest(memory)}
        return result
