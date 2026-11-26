"""Word boundaries from the exact synthesized phoneme durations, never ASR guesses."""


def phoneme_words(text, alignments, sample_rate,word_phonemes=None):
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
        if word_phonemes is not None:
            return _map_coarticulated_words(words,alignments,sample_rate,word_phonemes)
        raise ValueError(f'Engine phoneme/word mapping ambiguous: {len(words)} words / {len(groups)} groups')
    result=[{'word':word,'start':a/sample_rate,'end':b/sample_rate,'probability':1,
             'timing_source':'synthesis_phoneme_duration'} for word,(a,b) in zip(words,groups)]
    if any(w['end']<=w['start'] for w in result):
        raise ValueError('Empty engine word boundary')
    return result


def _map_coarticulated_words(words,alignments,sample_rate,word_phonemes):
    """Map reference word phonemes to the timed sentence when eSpeak joins words.

    Boundaries remain on actual synthesized phonemes. A high edit cost or a word
    without a mapped phoneme is an error; no equal-duration word guessing occurs.
    """
    ignored=set('^$.,!?;:ˈˌː')
    actual=[];cursor=0
    for p in alignments:
        length=int(p['num_samples']);phone=p['phoneme']
        if not phone.isspace() and phone not in ignored:
            actual.append((phone,cursor,cursor+length))
        cursor+=length
    reference=[(p,i) for i,phones in enumerate(word_phonemes) for p in phones if not p.isspace() and p not in ignored]
    if len(word_phonemes)!=len(words) or not reference or not actual: raise ValueError('Missing word phonemes')
    n,m=len(reference),len(actual)
    costs=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): costs[i][0]=i
    for j in range(m+1): costs[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1):
            costs[i][j]=min(costs[i-1][j-1]+(reference[i-1][0]!=actual[j-1][0]),costs[i-1][j]+1,costs[i][j-1]+1)
    ratio=costs[n][m]/max(n,m)
    if ratio>.25: raise ValueError('Sentence/word phoneme mapping too uncertain')
    mapping={i:[] for i in range(len(words))};i,j=n,m
    while i or j:
        if i and j and costs[i][j]==costs[i-1][j-1]+(reference[i-1][0]!=actual[j-1][0]):
            mapping[reference[i-1][1]].append(j-1);i-=1;j-=1
        elif i and costs[i][j]==costs[i-1][j]+1: i-=1
        else: j-=1
    result=[]
    for i,word in enumerate(words):
        indexes=mapping[i]
        if not indexes: raise ValueError('A spoken word has no mapped engine phoneme')
        start=actual[min(indexes)][1]/sample_rate;end=actual[max(indexes)][2]/sample_rate
        if end<=start: raise ValueError('Empty coarticulated word')
        result.append({'word':word,'start':start,'end':end,'probability':1,
            'timing_source':'synthesis_phoneme_boundary_mapping','phoneme_edit_ratio':ratio})
    return result
