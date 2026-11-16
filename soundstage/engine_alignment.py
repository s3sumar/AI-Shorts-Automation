"""Word boundaries from the exact synthesized phoneme durations, never ASR guesses."""


def phoneme_words(text, alignments, sample_rate):
    cursor=0
    groups=[]
    active=None
    for item in alignments:
        phoneme=item['phoneme']
        length=int(item['num_samples'])
        if length<0:
            raise ValueError('Negative phoneme duration')
        if phoneme.isspace() or phoneme in '^$.,!?;:':
            if active:
                groups.append(active);active=None
        else:
            if active is None: active=[cursor,cursor+length]
            else: active[1]=cursor+length
        cursor+=length
    if active: groups.append(active)
    words=text.split()
    if len(words)!=len(groups):
        raise ValueError(f'Engine phoneme/word mapping ambiguous: {len(words)} words / {len(groups)} groups')
    result=[{'word':word,'start':a/sample_rate,'end':b/sample_rate,'probability':1,
             'timing_source':'synthesis_phoneme_duration'} for word,(a,b) in zip(words,groups)]
    if any(w['end']<=w['start'] for w in result):
        raise ValueError('Empty engine word boundary')
    return result
