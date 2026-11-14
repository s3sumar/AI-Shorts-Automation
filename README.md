ï»¿# AI Shorts Automation â€” Below Zero

The autonomous foundation and two consecutive episode previews are now available.
See [AUTONOMY.md](AUTONOMY.md) for the director, persistent memory, production
runner, next-series plan, benchmark, cloud workflow and private-upload preparation.
Scheduled execution and uploading remain disabled.
See [DEPLOYMENT.md](DEPLOYMENT.md) for the manual cloud test, durable state
through Episode 2, and the completed local Episode 3 smoke preview.

Episode 001, **The Floor Below Zero**, is a 45-second vertical horror episode.
The master has **1080 frames at 24 FPS, 540 x 960**. Its practical review video
samples the entire timeline at **6 FPS** and includes original sound design,
locally synthesized radio narration and captions rendered inside Blender.

## Local deliverables

- `artifacts/episode_001/episode_001_master.blend`
- `artifacts/episode_001/episode_001_preview.mp4`
- `artifacts/episode_001/scene_validation.json`
- `artifacts/episode_001/video_validation.json`
- `artifacts/episode_001/captions.srt`
- `artifacts/episode_001/narration.md`
- `artifacts/episode_001/audio/audio_manifest.json`
- `EPISODE_001_REPORT.md` â€” implementation, verification and limitations

The original scene, earlier ten-second version and fallback workflow are preserved.
Pre-task snapshots are under `artifacts/backups/`. Generated media and downloaded
local tools are ignored by Git. `assets/elevator_template.blend` is a required,
small, self-contained source asset and must accompany the scripts in a checkout.

## Run the production template

Requirements: Blender **5.2.3**, Python with NumPy, and FFmpeg with `libx264` + AAC.
Put the executables on PATH or supply their full paths:

```powershell
python tools/produce_episode.py --config episodes/episode_001.json --blender blender --ffmpeg ffmpeg
```

The command prepares audio, builds a separate master, evaluates the complete
master animation, renders a sampled preview, checks every PNG, encodes MP4 and
decodes the complete MP4 to test it. Existing generated masters are protected;
use `--rebuild-generated` to revise one. That option preserves a master snapshot.
Changed scene files automatically move stale preview frames into `revisions/`
instead of mixing different versions when resuming a render.

The default is EEVEE with screen-space reflections. `--engine CYCLES` selects a
slower CPU renderer. The master uses 32 EEVEE samples and the preview uses 16.
`ENABLE_REFLECTIONS=0` disables screen tracing for constrained graphics contexts.
This pipeline renders a preview only; no full 24 FPS production render starts
automatically. It never uploads a video or modifies a remote repository.

For separate steps:

```powershell
python tools/prepare_audio.py
blender --background --factory-startup --python-exit-code 1 --python story_scene.py --python tests/validate_episode.py
blender --background artifacts/episode_001/episode_001_master.blend --python-exit-code 1 --python tools/render_episode.py
python tools/encode_episode.py
python -m unittest discover -s tests -p test_episode_data.py -v
```

Rebuilding an existing generated output with `story_scene.py` directly requires
`ALLOW_REBUILD=1`. The one-command wrapper manages this via `--rebuild-generated`.
Output and config paths resolve relative to this repository, not the shell CWD.

## Reuse and extend

`episodes/episode_001.json` contains story data: camera shots and lenses,
countdown events, rig movement keys in seconds, facial reactions, breathing,
sway, door timing, lighting, caption windows, sound cues and continuity notes.
Edit that data instead of adding per-episode branches to the Blender builder.

`production/common.py` supplies geometry, materials, animation, text and lighting
primitives. `production/characters.py` builds the recurring connected passenger
and faceless antagonist. `production/episode.py` appends the existing elevator
asset, extends the corridor, assembles characters and sequences the episode.
All episode animation actions have meaningful names and fake users. Their
existing slots are associated with the corresponding objects and node trees.
The shadow head has an empty facial-effects socket for future episodes.

This is a reusable **elevator** production template. The autonomous layer adds
constrained story planning, continuity memory, season rollover and cloud
orchestration. Arbitrary environments, richer model-driven storytelling and
remote deployment still require further work; see AUTONOMY.md.

## Sound

Effects are generated with deterministic procedural synthesis: hum, rumble,
beeps, radio noise, flicker clicks, knocks, impact, sliding doors, drone, footstep
and the final sting. They use no downloaded sound recordings. Local narration
uses installed Windows SAPI (Microsoft David in this build); Linux uses
`espeak-ng` when installed. The audio manifest records what was generated and
which voices are missing. The scene packs the finished WAV for portability.

Narration caching checks the exact text, so a changed script cannot silently
reuse an old line. Captions have their own safe camera-space backing and are
included even when FFmpeg lacks subtitle filters. An SRT is also supplied.

## GitHub Actions

`.github/workflows/dynamic_render.yml` is manual-only and accepts episode and
engine choices. It pins Blender 5.2.3, generates sound locally, validates the
scene, renders PNGs, encodes H.264/AAC, decodes the result and uploads review
artifacts. EEVEE runs under Xvfb with Mesa software graphics; CPU Cycles is an
optional slower fallback. Cloud previews disable screen reflections.

The updated Linux workflow has been reviewed locally but has **not** been run
on GitHub; remote download availability and cloud performance remain unverified.
No push or workflow dispatch was performed. `render.yml` is unchanged.

Episode 002 keeps its existing eight-second schema-1 behavior through
`legacy_story_scene.py` and `tests/validate_scene.py`. It is not a newly authored
45-second sequel. Existing ten-second tools and their checks remain separate.
