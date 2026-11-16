# Reference analysis and original directing revision — 2026-11-15

The supplied screen recording is a useful benchmark for readable storytelling,
editing and selective animation. It does not establish that our current voice,
acting or finished episodes match its quality. The revised test remains NOT_READY.

## Evidence and limits

The input is `Screen Recording 2026-11-15 173128.mp4`, SHA-256
`a1e602dcf0d41ea84e1b249f9a52400c5eb51224686a8c399ea6fdf5ca9ec42a`.
It contains 75.833 seconds of 1908×1078, approximately 30 FPS desktop capture.
The embedded portrait film was inspected separately at crop x398/y139/480×852;
browser UI and comments were excluded. Capture dimensions and frame rate do not
prove the original video's resolution or animation sampling rate. It begins
mid-sentence, so the original opening hook cannot be judged from this file.

Frame inspection shows stylized, relatively simple figures and environments,
alternating wide staging, facial reactions and important-object inserts. Cool
interiors contrast with warm practical light. Captions use short phrases and
selective emphasis. These are transferable production principles; their plot,
characters, dialogue, graphics, voice and music are not reusable assets.

Local CPU ASR estimated 198 words, about 157 words per recorded minute, with a
median interword pause above 150 ms of about 560 ms. Transcription errors and the
partial recording make these approximate. This is timing analysis, not a
listening assessment of voice naturalness, emotional delivery or music quality.
The capture measures roughly −40.4 LUFS / −20.6 dBTP; capture gain makes that an
unsuitable mastering target. Our mix target remains −16 LUFS with peak headroom.

About 66% of adjacent cropped frames have low measured image change (normalized
mean difference below .002). Holds, limited motion and fades can all cause this;
it is not proof of the original animation FPS. The useful lesson is that
purposeful motion, composition and edit timing can carry suspense economically.
Private analysis files, transcript, extracted audio and model downloads stay in
ignored `artifacts/reference_analysis/20261115` and tooling/model directories.
None is fed into production as footage, sound, dialogue or a voice sample.

## Applied to our own story

- `production/directing.py` supplies an opt-in arrival-episode directing pass.
  Compiler settings `directing.profile: original_lift_v1` enable it; existing
  cloud settings retain their prior behavior. The pass replaces one 13.5-second
  display insert with display, parcel and listening-reaction coverage. The
  45-second score has 15 contiguous shots, with display inserts no longer than
  four seconds. This is a project-specific rule, not a universal editing rule.
- The courier's head turn now shares rotation with the torso. An early glance
  adds anticipation; facial details sit closer to the head surface. Existing
  starting/ending character and story states are retained.
- An original delivery parcel and radio status light make the narration's
  evidence and silence visible. Radio sound and light share authored timing.
  Blue/red elevator lighting and the existing silhouette reveal remain our own.
- `config/episode3_director_v3.json` is a noncanonical narration draft: 13 short
  lines, 71 words over 45 seconds, with deliberately reserved reveal holds.
  It adds a parcel clue for editorial review, without changing the story ledger.
  We do not force the benchmark's speech rate onto a different story.
- `soundstage/captions.py` preserves authored words and produces short chunks
  with our ivory/cyan treatment. Optional local ASR must match the authored
  tokens and pass timing/confidence checks. Otherwise it uses measured phrase
  timing and records a review requirement; it never substitutes invented words.
  Actual output: 22 chunks, with 8 of 15 spoken phrases falling back. Word timing
  is therefore not fully verified. Touching chunk boundaries are clamped to
  prevent overlapping captions.
- `config/cinematic_reference_profile.json` records general guidance and
  originality constraints. It contains no copied script. Story-continuity,
  camera/visibility checks and the existing human quality gate remain separate.

## Actual test outputs

All paths below are relative to the repository:

| Output | Location |
| --- | --- |
| Playable original five-second test | `artifacts/reference_director/episode3_v3/preview/original_director_v3_720p24.mp4` |
| New 45-second Blender master | `artifacts/reference_director/episode3_v3/director_source.blend` |
| Full revised 45-second audio | `artifacts/reference_director/episode3_v3/audio/episode_mix.wav` |
| Scene validation | `artifacts/reference_director/episode3_v3/scene_validation.json` |
| Video validation | `artifacts/reference_director/episode3_v3/preview/validation.json` |
| Caption uncertainty report | `artifacts/reference_director/episode3_v3/alignment/word_alignment.json` |
| Preservation and final test evidence | `artifacts/reference_director/episode3_v3/HANDOFF.json` |

The video covers seconds 14.5–19.5 of our revised episode. It is native
720×1280, constant 24 FPS, with 120 separately rendered source frames, H.264/AAC,
stereo 48 kHz audio and burned-in captions. Full FFmpeg decoding passed. Rendering
at 16 samples took 172.74 seconds in total, median 1.37 seconds/frame locally;
encoding, analysis, synthesis and scene setup are additional costs. This is a
two-shot local test, not proof of 45-second cloud throughput. Do not extrapolate
these two shots as a measured whole-episode cloud runtime.

Blender 5.2.3 LTS validated all 1,080 scene frames, 29 checks, 203 objects and 94
reusable actions. Five representative 720p probes were rendered. The camera,
display sequence, framing, ray visibility and canonical endpoint checks passed.
The complete revised audio measures −16.00 LUFS / −1.50 dBTP, with no narration
overruns. Representative composed frames were visually inspected. Technical
checks cannot approve dramatic performance or narrative appeal.

## Reproduction and remaining work

The safe experiment entry points are `tools/reference_director_pass.py`,
`tools/align_local_captions.py` and `tools/render_director_preview.py` (use
`--help` for paths). The first accepts only an isolated experiment directory
and refuses to replace completed scene/config files. Caption alignment is an
optional local tool, not enabled in the unattended cloud workflow. Its free
CPU dependency is listed in `requirements-analysis.txt`; local Piper setup is
documented in `PRODUCTION_QUALITY.md`. These tools need local Blender/FFmpeg
executables, not a live MCP connection. No benchmark dispatch was made to GitHub.

The candidate Piper voice is not human-approved and has limited emotional
control. Its 22.05 kHz source is mixed to 48 kHz without claiming new source
detail. Hand gripping, facial expression and subtle body weight remain simple;
the prop is attached rather than physically gripped. Some fine material noise
remains at practical render settings. Caption fallback phrases require listening
review. This turn rendered five seconds, not a complete revised 45-second MP4.
The full new scene/audio exist, but the complete film still needs editorial and
listening review, corrected timings and a later full-length render when warranted.

No original working scene/video was replaced, no story checkpoint was advanced,
no Episode 4 was generated, and no push, publishing, scheduling, paid API call
or additional cloud production run was performed.
