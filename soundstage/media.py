import json
import re
import subprocess
import wave
import shutil
from pathlib import Path
import numpy as np

SR=48000


def read(path,ffmpeg,sr=SR):
    result=subprocess.run([ffmpeg,'-v','error','-i',str(path),'-f','f32le','-ac','2','-ar',str(sr),'-'],capture_output=True,check=True)
    return np.frombuffer(result.stdout,dtype='<f4').reshape(-1,2).astype(np.float64)


def write(path,data,sr=SR):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    data=np.asarray(data)
    if data.ndim==1:
        data=data[:,None]
    with wave.open(str(path),'wb') as stream:
        stream.setparams((data.shape[1],2,sr,0,'NONE','not compressed'))
        stream.writeframes((np.clip(data,-.9999,.9999)*32767).astype('<i2').tobytes())


def measure(path,ffmpeg):
    result=subprocess.run([ffmpeg,'-hide_banner','-i',str(path),'-af','loudnorm=I=-16:TP=-1.5:LRA=8:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    values=json.loads(re.findall(r'\{[^{}]+\}',result.stderr,re.S)[-1])
    return {k:float(values[k]) for k in ['input_i','input_tp','input_lra','input_thresh','target_offset']}


def normalize(source,destination,ffmpeg):
    first=measure(source,ffmpeg)
    args='loudnorm=I=-16:TP=-1.5:LRA=8:linear=true:print_format=json'+''.join([
        ':measured_I='+str(first['input_i']),':measured_TP='+str(first['input_tp']),
        ':measured_LRA='+str(first['input_lra']),':measured_thresh='+str(first['input_thresh']),
        ':offset='+str(first['target_offset'])])
    result=subprocess.run([ffmpeg,'-hide_banner','-y','-i',str(source),'-af',args,'-ar',str(SR),
        '-ac','2','-c:a','pcm_s24le',str(destination)],capture_output=True,text=True,check=True)
    Path(destination).with_suffix('.loudnorm.log').write_text(result.stderr,encoding='utf-8')
    # Short dramatic clips can disagree with loudnorm's own output statistics.
    # Verify the written samples and make bounded, measured corrections.
    current=Path(destination)
    actual=measure(current,ffmpeg)
    for i in range(4):
        if abs(actual['input_i']+16)<=.4 and actual['input_tp']<=-1.0:
            break
        delta=max(-6,min(6,-16-actual['input_i']))
        refined=Path(destination).with_name(Path(destination).stem+f'_refine_{i}.wav')
        limit=10**(-1.8/20)
        subprocess.run([ffmpeg,'-v','error','-y','-i',str(current),'-af',
            f'volume={delta}dB,alimiter=limit={limit}:level=false:attack=5:release=100',
            '-ar',str(SR),'-ac','2','-c:a','pcm_s24le',str(refined)],check=True)
        actual=measure(refined,ffmpeg)
        current=refined
    if current!=Path(destination):
        shutil.copyfile(current,destination)
    if not abs(actual['input_i']+16)<=1 or actual['input_tp']>-1.0:
        raise ValueError('Measured loudness/true peak still fails after bounded correction')
    return actual
