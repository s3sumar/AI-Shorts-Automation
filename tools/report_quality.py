"""Summarize measured benchmarks and clearly separate cloud extrapolations."""
import argparse
import json
import re
import subprocess
import math
import array
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=ROOT/'artifacts/quality')
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args()
    root=a.root.resolve()
    rows=[]
    for file in sorted(root.glob('*/benchmark.json')):
        if file.parent.name in ['native_720p24','baseline_180p','hybrid_720p24']:
            replacement=file.parent.with_name(file.parent.name.replace('_720p24','_final_720p24').replace('_180p','_final_180p'))
            if (replacement/'benchmark.json').exists():
                continue
        row=json.loads(file.read_text())
        row['case']=file.parent.name
        rows.append(row)
    comparisons=[]
    for i in range(5):
        original=root/'probe_original'/f'part_{i:03d}/frame_0001.png'
        optimized=root/'probe_balanced'/f'part_{i:03d}/frame_0001.png'
        if original.exists() and optimized.exists():
            result=subprocess.run([a.ffmpeg,'-hide_banner','-i',str(original),'-i',str(optimized),
                '-lavfi','ssim','-f','null','-'],capture_output=True,text=True,check=True)
            score=float(re.search(r'All:([0-9.]+)',result.stderr).group(1))
            comparisons.append({'probe':i,'ssim':score})
    native=root/'native_final_720p24/quality_native_720p24.mp4'
    hybrid=root/'hybrid_final_720p24/quality_hybrid_720p24.mp4'
    if not native.exists():
        native=root/'native_720p24/quality_native_720p24.mp4'
    if not hybrid.exists():
        hybrid=root/'hybrid_720p24/quality_hybrid_720p24.mp4'
    flow=None
    if native.exists() and hybrid.exists():
        result=subprocess.run([a.ffmpeg,'-hide_banner','-i',str(native),'-i',str(hybrid),
            '-lavfi','ssim','-an','-f','null','-'],capture_output=True,text=True,check=True,timeout=180)
        (root/'hybrid_ssim.log').write_text(result.stderr)
        flow=float(re.search(r'All:([0-9.]+)',result.stderr).group(1))
    audio=None
    if native.exists():
        decoded=subprocess.run([a.ffmpeg,'-v','error','-i',str(native),'-vn','-ac','1','-ar','24000',
                                '-f','f32le','-'],capture_output=True,check=True)
        samples=array.array('f')
        samples.frombytes(decoded.stdout)
        rms=math.sqrt(sum(v*v for v in samples)/len(samples))
        peak=max(abs(v) for v in samples)
        assert rms>.005 and math.isfinite(peak),'Silent or invalid audio'
        audio={'rms':rms,'peak':peak,'sample_count':len(samples),'silent':False}
    report={'measurements':rows,'profile_probe_similarity':comparisons,'hybrid_vs_native_ssim':flow,
            'ssim_caveat':'Structural similarity does not prove absence of motion/occlusion artifacts or cinematic quality.',
            'cloud_720p_measured':any(r.get('execution_environment')=='github_actions' and r['resolution']==[720,1280] for r in rows),
            'checkpoint_advanced':False,'native_audio_check':audio}
    (root/'quality_comparison.json').write_text(json.dumps(report,indent=2))
    lines=['# Measured quality benchmark','','Environment labels distinguish actual cloud runs from local measurements.',
           '','| Case | Environment | Resolution | Source frames | Samples | Render seconds | Composition seconds |',
           '|---|---|---|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["case"]} | {r.get("execution_environment","local")} | {r["resolution"][0]} x {r["resolution"][1]} | {r["rendered_frames"]} | {r["samples"]} | {r["render_seconds"]:.2f} | {r.get("composition_seconds",0):.2f} |')
    lines+=['','Profile SSIM probes: '+', '.join(f'{v["ssim"]:.4f}' for v in comparisons),
            '','Hybrid versus native video SSIM: '+str(flow),'',report['ssim_caveat'],
            '','Cloud 720p measured: '+str(report['cloud_720p_measured'])+'. No story checkpoint writes.']
    (root/'COMPARISON.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='measurements'},indent=2))


if __name__=='__main__':
    main()
