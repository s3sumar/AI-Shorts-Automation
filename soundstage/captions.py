"""Short phrase captions with explicit, auditable timing confidence."""
import re
import textwrap


def token(value):
    return re.sub(r'[^a-z0-9]','',value.lower())


def chunks(cue,words,max_words=4,max_chars=30):
    expected=cue['text'].split()
    if [token(v) for v in expected]!=[token(w['word']) for w in words]:
        raise ValueError('Alignment does not preserve the authored spoken words')
    if not words or any(w['end']<=w['start'] or w['start']<cue['start']-.2 or w['end']>cue['end']+.25 for w in words):
        raise ValueError('Invalid spoken word timing')
    if any(w.get('probability',1)<.65 for w in words):
        raise ValueError('Low-confidence word alignment needs review')
    if any(a['end']>b['start']+.06 for a,b in zip(words,words[1:])):
        raise ValueError('Overlapping word alignment')
    output=[]; group=[]
    for text,w in zip(expected,words):
        proposed=' '.join([x[0] for x in group]+[text])
        if group and (len(group)>=max_words or len(proposed)>max_chars):
            output.append(group);group=[]
        group.append((text,w))
    if group: output.append(group)
    if (len(output)>1 and len(output[-1])<len(output[-2])-1
            and len(' '.join([output[-2][-1][0]]+[v[0] for v in output[-1]]))<=max_chars):
        output[-1].insert(0,output[-2].pop())
    cues=[]
    for group in output:
        start=max(cue['start'],group[0][1]['start']);end=min(cue['end'],group[-1][1]['end']+.06)
        if end<=start: raise ValueError('Word cue falls outside its phrase')
        cues.append({'start':start,'end':end,
                     'text':' '.join(w[0] for w in group),'timing_method':'local_asr_word_alignment'})
    for a,b in zip(cues,cues[1:]):
        a['end']=min(a['end'],b['start']-.01)
        if a['end']<=a['start']: raise ValueError('Aligned chunks overlap')
    return cues


def align_phrases(cues,words):
    output=[]; fallback=[]
    for cue in cues:
        selected=[w for w in words if cue['start']-.10<=(w['start']+w['end'])/2<=cue['end']+.10]
        try:
            output.extend(chunks(cue,selected))
        except ValueError as error:
            output.append(dict(cue,text='\n'.join(textwrap.wrap(cue['text'],30)),timing_method='measured_phrase_fallback'))
            fallback.append({'start':cue['start'],'reason':str(error)})
    return {'captions':output,'fallback_phrases':fallback,'all_words_verified':not fallback,
            'requires_human_timing_review':True}


def ass(cues,accent_words=('name','delivered','sealed','waiting','sender')):
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,62,&H00EFF5F5,&H00F4E38D,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,80,110,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    def stamp(t):
        cs=round(t*100)
        return f'{cs//360000:01d}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'
    rows=[]
    for cue in cues:
        text=cue['text'].replace('\\','').replace('{','(').replace('}',')').replace('\n',r'\N')
        words=text.split()
        highlighted=False
        for i,w in enumerate(words):
            if not highlighted and token(w) in accent_words:
                words[i]=r'{\c&H F4E38D&}'.replace(' ','')+w+r'{\r}'
                highlighted=True
        rows.append(f'Dialogue: 0,{stamp(cue["start"])},{stamp(cue["end"])},Default,,0,0,0,,'+ ' '.join(words))
    return header+'\n'.join(rows)+'\n'
