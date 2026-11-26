# Automation status ? November 26, 2026

The creative development pipeline now reaches a real Blender MP4, with durable
retry/resume state and private-upload preparation. It is not a finished public
YouTube production service. Live AI credentials and YouTube OAuth are absent
both locally and in the repository Actions secrets; professional visual/acting
review remains incomplete. Daily scheduling and public/paid services stay off.

## What now runs

`autonomy.creative_service` reserves one script, produces voice/captions, builds
an original supported world, sequences typed performances and cameras, renders
frames, encodes H.264/AAC with subtitles and fully decodes the video. The service
then verifies script/input-memory/video hashes and atomically advances its own
creative ledger. Run keys are idempotent; failed reservations keep the same
script; snapshots restore pending/verified episodes and editorial provenance.
The protected pilot ledger and `checkpoint/story.json` are never written by it.

Three original low-cost blockout adapters exist: royal prison record office,
lunar greenhouse and map workshop. They have explicit prop bindings, connected
mannequin characters, breathing/head/hand performances, word-timed mouth motion,
scene-specific lighting, per-shot cameras and simple reveal events. Unknown
assets/settings and unsupported multi-world cuts remain blocked. The director
can create unlimited text concepts, but new visual worlds still need adapters.

The existing detailed elevator assets/previews are preserved. Blockout quality
is visibly simpler and must not be described as matching the reference film.
Facial acting, hands, phoneme lip sync, richer assets, physical interactions and
human storytelling/visual/listening approval remain production-quality work.

## Actual new media

All paths below are relative to the repository root.

| Deliverable | Path |
| --- | --- |
| The King's Mercy, complete 45-second preview | artifacts/production_completion_20261126/kings_mercy_v4/creative_episode_preview.mp4 |
| The Mapmaker's Rain, complete 45-second preview | artifacts/production_completion_20261126/mapmakers_rain_v3/creative_episode_preview.mp4 |
| The Last Greenhouse, complete 45-second preview | artifacts/production_completion_20261126/last_greenhouse/creative_episode_preview.mp4 |
| Native 720x1280 / 24 FPS, four-second probe | artifacts/production_completion_20261126/native_720_probe/native_720p24_4seconds.mp4 |
| Revised Episode 3 audio ending "I ordered you." | artifacts/audio_previews/episode3_ordered_20261126/dialogue_and_sound_preview.mp3 |

The full development videos are 180x320 at 2 FPS with complete 45-second audio,
subtitles, all seven shots and saved 1080-frame/24-FPS Blender masters. They are
sampled diagnostic movies, not smooth native final episodes. Each folder has
scene/media validation, individual voice takes, stems, captions, render timings
and a disabled/private upload job. No authored example is represented as an AI
writing test. The new Episode 3 audio preserves the earlier A/B versions and
canonical checkpoint; existing videos did not silently receive its soundtrack.

Prison rendering measured about 52 seconds for 90 frames locally. Native 720p
rendering measured 131.25 seconds for 96 real frames: about 1.37 seconds/frame.
A linear full-episode estimate is 24.6 minutes at the same local blockout settings,
not a completed native-HD episode or a GitHub CPU benchmark. This simpler style
cannot be fairly compared as an equal-quality optimization of the old detailed
cloud scene. No expensive full native-HD episode render was started.

Actual end-to-end state verification used the rendered prison MP4: reserve,
verified hash-bound commit, repeated commit without another episode, checksum
snapshot, restoration and a private-upload dry run. It advanced only an isolated
artifact-directory test ledger to development Episode 2. Canonical local/cloud
Episode 1/2/3 state was not advanced by this benchmark/test.

## Operations

```powershell
python tools/automation_doctor.py
python -m autonomy.creative_service plan --development --state artifacts/my_run/ledger.sqlite3 --run-key trial-1 --approved-example examples/creative/creative_kings_mercy
python -m autonomy.creative_service produce --development --state artifacts/my_run/ledger.sqlite3 --run-key trial-1 --out artifacts/my_run/media --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --ffmpeg "<your FFmpeg executable>"
```

For live AI, omit `--approved-example`, provide an original `--brief`, and configure
`OPENROUTER_API_KEY` in your environment. Missing credentials stop; there is no
hidden fallback. Use a fresh output revision after any partial render or changed
scene. `autonomy.creative_media --reuse-audio <prior audio folder>` reuses verified
raw takes even from a partial revision. Original audio is never truncated.
Measured pacing adjustments respect the authored window, next cue and tail limit.
Fast caption groups can use two lines with engine-derived timing; unreadable
captions stop before rendering. Successful technical verification remains
`quality_status: NOT_READY` until the actual production-quality gate is satisfied.

## Cloud

`.github/workflows/creative_production.yml` is manual-only. It supports `live_ai`
or explicitly labeled `authored_demo`. It restores the separate development
checkpoint, reserves/persists a script before rendering, downloads pinned local
voices and checksum-verified Blender 5.2.3, builds/decodes the MP4, then persists
success or failure. State lives at `checkpoint/creative_development.json` on
`autonomy-state`; the protected legacy checkpoint path is unchanged. Missing
state requires explicit initialization; optimistic SHA checks and regression
checks prevent overwrites. A real subsequent cloud retry must recover the pending
script rather than asking a model to invent a competitor.

The cloud workflow uses standard `ubuntu-24.04`; this repository is public, so
standard public-runner compute is free under the documented GitHub rules. The
artifact is small, compressed and retained one day. No paid runner, provider,
YouTube upload, schedule or billing option is enabled. Actions is enabled and the
repository initially had approximately 22 MB of live artifacts in its listing.
Account billing-usage endpoints were unavailable; no billing settings were changed.
Cloud execution results, if run, are recorded separately in the completion report.

The API writer/critic workflow and existing production workflows remain available.
The production pause is respected by the canonical service. Development mode
cannot use the canonical state directory. Upload outboxes default to private,
unapproved and not-ready; the existing uploader requires configured OAuth and
an explicit private-upload execution gate. No remote YouTube test can pass until
the owner connects that account. Account consent cannot be replaced by code.

## Remaining external and quality requirements

1. Configure a free OpenRouter API key for a genuine live writer/critic test.
2. Configure YouTube OAuth client ID, secret and refresh token; verify private
   upload idempotency with a real authorized account before enabling it daily.
3. Approve and improve visual/acting quality beyond development blockouts, then
   test complete native production-quality media. Do not weaken the readiness
   gate to manufacture a passing result.
4. Activate unattended daily production only after those prerequisites work.

Full provider/story-writing details remain in CREATIVE_DIRECTOR.md; older handoff
files and dated reports describe earlier milestones and are retained as history.

Local final validation: 156 tests ran; 155 passed and one optional generated-audio fixture skipped. Regression testing exposed an unclosed SQLite inspection handle on Windows; explicit connection closing fixed it, and the clean-source suite passed afterward. New tests cover legacy-ledger protection, durable editorial provenance, tail timing and fast-caption readability. The source scan found no generated media or credentials among deployment candidates.
