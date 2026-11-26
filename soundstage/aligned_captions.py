"""Exact authored words, engine boundaries and bounded reading holds for any episode."""
from .captions import chunks,ass
import textwrap


def build(cues,words,duration):
    output=[]
    for cue in cues:
        selected=[w for w in words if cue['start']-.001<=(w['start']+w['end'])/2<=cue['end']+.001]
        values=chunks(cue,selected)
        # Fast function words can make a four-word flash unreadable even when
        # the full phrase has ample duration. Use a measured two-line group.
        if any(len(v['text'])/max(.01,(values[j+1]['start']-.02 if j+1<len(values) else cue['end'])-v['start'])>22 for j,v in enumerate(values)):
            values=chunks(cue,selected,max_words=8,max_chars=48)
            for value in values:value['text']=textwrap.fill(value['text'],width=26)
        for value in values:
            value.update(speaker=cue['speaker'],role=cue['role'],timing_method='synthesis_phoneme_duration_with_time_preserving_delivery')
        output.extend(values)
    for i,cue in enumerate(output):
        limit=min(duration,output[i+1]['start']-.02) if i+1<len(output) else duration-.05
        cue['end']=min(limit,max(cue['end'],cue['start']+len(cue['text'])/20))
        if cue['end']<=cue['start']: raise ValueError('Caption duration collapsed')
    if ' '.join(c['text'] for c in output).split()!=' '.join(c['text'] for c in cues).split(): raise ValueError('Caption text changed')
    if any(a['end']>b['start'] for a,b in zip(output,output[1:])): raise ValueError('Caption overlap')
    return output


def write_files(out,cues):
    def stamp(t):
        ms=round(t*1000)
        return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
    (out/'captions.srt').write_text('\n'.join(f'{i}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}\n'
        for i,c in enumerate(cues,1)),encoding='utf-8')
    (out/'captions.ass').write_text(ass(cues),encoding='utf-8-sig')
