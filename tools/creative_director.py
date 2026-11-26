"""Cloud-safe creative review only: never touches production Memory or Blender."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomy.contracts import digest,write_json
from autonomy.creative import CreativeDirector
from autonomy.creative_provider import from_config,ProviderError
from autonomy.creative_compile import compile_creative
from autonomy.creative_contract import initial_memory,validate_bible,validate_memory


def run(args):
    out=args.out.resolve()
    if not out.is_relative_to((ROOT/'artifacts').resolve()): raise ValueError('Use an isolated artifacts output folder')
    if out.exists(): raise FileExistsError('Preserve previous creative runs; choose a new output directory')
    out.mkdir(parents=True)
    provider=from_config(args.settings)
    settings=provider.settings
    director=CreativeDirector(provider,settings.get('max_revisions',2),settings.get('approval_threshold',4))
    try:
        if bool(args.bible)!=bool(args.memory): raise ValueError('Continuing episodes require both bible and memory')
        bible=json.loads(args.bible.read_text()) if args.bible else director.new_series(args.brief)
        validate_bible(bible)
        memory=json.loads(args.memory.read_text()) if args.memory else initial_memory(bible)
        validate_memory(memory,bible)
        result=director.next_episode(bible,memory,args.brief)
        bible=result['bible'];memory=result['input_memory']
        write_json(out/'series_bible.json',bible)
        write_json(out/'input_memory.json',memory)
        from autonomy.creative_memory import pack
        write_json(out/'input_checkpoint_unchanged.json',pack(bible,memory))
        compiled=compile_creative(result['episode'],bible,memory)
        write_json(out/'review_result.json',result)
        write_json(out/'episode.json',result['episode'])
        write_json(out/'proposed_memory_NOT_COMMITTED.json',result['proposed_memory'])
        write_json(out/'audio_score.json',compiled['audio_score'])
        write_json(out/'blender_storyboard.json',compiled['blender_storyboard'])
        rows=[bible['title']+' / '+result['episode']['title'],bible['genre'],
              'Planned 45-second timing; no TTS or render performed.','']
        for line in result['episode']['narration']:
            rows.append(f'{line["start"]:05.2f}-{line["end"]:05.2f} {line["speaker"]} ({line["emotion"]})\n{line["text"]}\n')
        (out/'script.txt').write_text('\n'.join(rows),encoding='utf-8')
        write_json(out/'run_status.json',{'status':'editorial_review_passed','live_model':True,
            'script_sha256':digest(result['episode']),'renderable':compiled['blender_storyboard']['readiness']['renderable'],
            'provider_calls':provider.calls,'production_checkpoint_written':False,'paid_services_enabled':False,
            'render_started':False,'youtube_upload_started':False})
        print(json.dumps({'out':str(out),'status':'script_editorial_review_passed','checkpoint_written':False}))
    except Exception as error:
        # Provider errors are sanitized by the provider. Do not write arbitrary raw network exceptions.
        detail=str(error)[:500] if isinstance(error,(ProviderError,ValueError,KeyError)) else type(error).__name__
        write_json(out/'run_status.json',{'status':'blocked' if isinstance(error,ProviderError) else 'failed',
            'error':detail,'provider_calls':provider.calls,'production_checkpoint_written':False,
            'render_started':False,'paid_services_enabled':False})
        print('CREATIVE REVIEW STOPPED: '+detail,file=sys.stderr)
        raise SystemExit(2) from None
    finally:
        write_json(out/'editorial_audit.json',director.audit)
        write_json(out/'provider_receipts.json',provider.receipts)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--settings',type=Path,default=ROOT/'config/creative_director.json')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--brief',required=True)
    parser.add_argument('--bible',type=Path)
    parser.add_argument('--memory',type=Path)
    run(parser.parse_args())
