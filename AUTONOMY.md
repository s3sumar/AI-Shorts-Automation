# Autonomous Shorts production foundation

Two complete consecutive 45-second previews are saved locally. The runner
planned/compiled the continuation, reused the existing assets, verified its
rendered endpoints against canon, and advanced story memory only after video
validation. It then created a new series concept and first-episode plan.
Nothing was pushed, uploaded to YouTube or published. Scheduled execution and
private uploads remain disabled by default.

## Deliverables

| Deliverable | Location |
| --- | --- |
| Episode 1 video | `artifacts/episode_001/episode_001_preview.mp4` |
| Episode 1 master | `artifacts/episode_001/episode_001_master.blend` |
| Episode 2, The Door That Listens | `artifacts/autonomy/series_001_e002/episode_002_preview.mp4` |
| Episode 2 master | `artifacts/autonomy/series_001_e002/episode_002_master.blend` |
| Actual continuity audit | `artifacts/autonomy/continuity_audit.json` |
| Measured benchmark | `artifacts/autonomy/series_001_e002/benchmark.json` |
| Next series, Dead Air Dispatch | `artifacts/autonomy/series_002_e001/story_plan.json` |
| Compiled next-series score | `artifacts/autonomy/series_002_e001/episode.json` |
| Persistent ledger and readable export | `state/story.sqlite3`, `state/story_memory.json` |
| Immutable state backups | `artifacts/autonomy/state_snapshots/` |
| Private upload outbox | Completed episodes' `youtube_private_upload.json` |

Both masters are 1080 frames at 24 FPS, 540 x 960. Episode 1's preview is
540 x 960 / 6 FPS / 16 samples. Episode 2's smaller preview is 360 x 640 /
6 FPS / 8 samples. Both cover 45 seconds with synthesized radio narration,
original procedural effects and captions rendered inside Blender.

## Working architecture

`autonomy/director.py` reads the bible and canon, preserves cast identity,
appearance, physical state, established facts and the unrevealed face, and
plans within a supported two-act horror grammar. The pilot season deliberately
contains two episodes: the below-zero discovery and the silent escape.
After its verified conclusion, a new bible, cast identity, premise and
environment variant are created automatically.

**The tested default director is an offline procedural story grammar, not a
language model.** It needs no API key or inference charge. An optional Ollama
adapter asks an already-installed loopback model for episode dialogue, titles
and series concepts, constrained by the same schema/canon. This session tested
the adapter with mocks; no real model was run or downloaded. Offline stories
reuse a small plot/concept library and have limited creative variety.
The optional adapter follows the documented [Ollama generation API](https://docs.ollama.com/api/generate).

`autonomy/compiler.py` maps supported high-level arrival/escape instructions
into camera shots, rig movement, lighting, floor events, doors, visibility,
captions and sound cues. Models cannot emit executable code, paths or arbitrary
object properties. `production/` provides connected characters, head/body/limb
pivots, breathing, sway, reactions, movement, silhouette steps, dolly/shake,
lighting, text and door actions. Lift 013 and a freight-lift variant share the
cab/corridor library; the latter adds enamel panels, caution bands and pipes.
The freight variant passed geometry checks and a small actual EEVEE still.
Its full new-series episode has not been rendered or narrated.

`autonomy/store.py` uses SQLite transactions. Planning reserves an episode;
failed production does not advance canon. Video verification atomically commits
the end state. Repeated run keys are idempotent, concurrent schedulers reserve
one pending episode, stale-canon commits are rejected and verified media cannot
be replaced silently. Backups are immutable and media references are portable.

`autonomy/pipeline.py` produces one bounded preview per invocation: offline
speech/effects, scene build/validation, separate render process, H.264/AAC encode
and complete MP4 decode. Nonzero render exits get at most three attempts.
Frame-plan hashes prevent mixing scenes/render settings. PNG checksums detect
truncation/corruption and damaged frames are preserved before replacement.
The limits are 270 preview frames and 1800 seconds of production per invocation.
No full-resolution 24 FPS render is automatic.

## Local operation

Requirements: Blender 5.2.3, Python 3.13 with `requirements-production.txt`,
FFmpeg with libx264/AAC, and Windows SAPI or Linux espeak-ng. Executables can be
on PATH or specified by full paths:

```powershell
python -m autonomy.pipeline status
python -m autonomy.pipeline plan --run-key my-next-run
python -m autonomy.pipeline produce --run-key my-next-run --blender blender --ffmpeg ffmpeg
python -m unittest discover -s tests -p 'test_autonomy*.py' -v
python tools/check_autonomy_workflow.py
```

The current ledger has two verified pilot episodes and a planned next-series
episode. `produce` now continues **Dead Air Dispatch**, preserving the completed
pilot. Reusing `--run-key local-continuation-002` returns the verified Episode 2
receipt, checks its file hash, and creates no extra episode. Missing media
requires restoration of its artifact rather than pretending it exists.

Use `--settings path/to/copy.json` for different production settings. The
director provider accepts `offline` or `ollama`; the model name must refer to an
already-installed local model. No remote inference provider is implemented.
Render settings accept EEVEE or CPU Cycles, including preview-only overrides.
`config/autonomy.json` keeps paid services and YouTube disabled.

On a new checkout, explicitly restore memory or run
`python -m autonomy.pipeline bootstrap`. Local bootstrap verifies Episode 1's
video against recorded provenance. Cloud bootstrap uses `--trusted-seed` only
after an explicit workflow input; it imports `config/verified_episode_001.json`
and does not claim to re-render that original episode on GitHub.

## Cloud workflow

The deployment workflow is now **manual-only**: there is no schedule and no
video-upload step. See [DEPLOYMENT.md](DEPLOYMENT.md) for the tested deployment
procedure, durable checkpoint design and local Episode 3 smoke preview.

`config/story_checkpoint.json` is reviewed, checksummed story metadata preserving
both verified pilot episodes and the planned global Episode 3. It contains no
video, SQLite database, OAuth credentials or downloaded tooling. A new runner
restores this seed once; subsequent runs restore `checkpoint/story.json` from
the dedicated `autonomy-state` Git branch. The branch is created atomically with
its first checkpoint. State history does not depend on cache eviction or artifact
retention. Existing missing/corrupt checkpoints fail closed.

The workflow reserves its run key and persists that reservation before rendering.
A final checkpoint records success or failure. GitHub content-SHA preconditions
reject stale writers, workflow concurrency serializes jobs, and validation rejects
lost episodes, changed verified evidence or broken continuity. A retry reuses the
same episode. Uploads are absent from this workflow. The job needs `contents: write`
for the state branch, while checkout credentials are not persisted. The token's
permission is repository-wide; code writes only the fixed state branch/path.

Cloud acceptance settings are deliberately small: 45 seconds, 180 x 320, 2 FPS,
4 EEVEE samples and 90 frames. The runner uses pinned Blender 5.2.3, Linux
espeak-ng, FFmpeg, Xvfb and software Mesa, with no Blender MCP dependency.
Hosted execution and actual GitHub checkpoint writes have not yet been tested.
The downloaded archive's availability was verified with an HTTP HEAD request.

Review media and SQLite recovery copies are downloadable artifacts retained for
30 days. The canonical durable record is JSON on the state branch. Deleting that
branch deliberately removes the live checkpoint; restore its history before
another dispatch. Branch-protection policies or disabled Actions write permissions
can block state storage and must be resolved before a hosted acceptance run.

## Private YouTube preparation

Each completed episode has a private-upload job. Dry-run inspection:

```powershell
python -m autonomy.youtube artifacts/autonomy/series_001_e002/youtube_private_upload.json
```

Actual execution is disabled. It requires an enabled YouTube configuration,
`YOUTUBE_UPLOAD_APPROVED=YES_PRIVATE_UPLOAD`, `--execute-private`, and OAuth
client ID/secret/refresh-token environment variables. Google client resumable
uploads hardcode private visibility, reject publication schedules and disable
subscriber notifications. Receipts persist in ignored `state/uploads/`.
Uncertain uploads are parked for reconciliation rather than duplicated.
No code path changes a video to public.

The historical optional upload adapter requires repository variable
`PRIVATE_UPLOAD_APPROVED == 'true'` and an upload request or previously approved
schedule. Secrets are `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and
`YOUTUBE_REFRESH_TOKEN`. Account consent, secret provisioning and an actual
private-upload acceptance test remain unfinished. Credentials were not searched
for or stored in this repo. Install `requirements-youtube.txt` when approved.

The adapter follows Google's [resumable upload guide](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol),
[video insertion API](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
and [offline OAuth flow](https://developers.google.com/identity/protocols/oauth2/web-server#offline).

## Measured verification and remaining work

The autonomy tests cover consecutive continuity, rollover, retries, concurrent
schedulers, failed production, stale canon, malformed model output, asset
constraints, immutable backups, portable paths, damaged PNGs and private-upload
guards/idempotence/uncertain outcomes. Remote behavior is tested with mocks.
`tools/validate_score.py` evaluated all 1080 Episode 2 frames, camera rays,
captions and actual start/end actor/door states. `tools/audit_continuity.py`
checked the **actual** videos, hashes and story ledger.
`tools/validate_seed_boundary.py` additionally measured the original Episode 1
master's final rig, shoulders, display, doors and red lighting and confirmed
that the continuation's starting canon matches those actual values. The original
local suite passed **21 tests, with zero failures, errors or skips**; deployment
adds checkpoint/recovery coverage described in DEPLOYMENT.md. Python
compilation, workflow YAML/guard checks and Git whitespace checks passed.

Episode 2's 270 frames rendered in **302.01 seconds**, including first-use shader
work. First frame: 42.72 seconds; warm median: 0.74 seconds; warm p95: 2.64
seconds. A linear 1080-frame estimate at the same preview settings is about
17.4 minutes, not a measured master render. Hosted performance is unknown.
Low samples/simple rigs and offline TTS limit visual, motion and voice quality.

Remaining: real local-model integration tests, richer story/action/environment
libraries, editorial and listening review, actual hosted checkpoint/run
acceptance, OAuth consent, an actual private-upload test, and approval before
activating paid services, scheduled cloud work or external uploads.
