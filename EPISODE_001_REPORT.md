# Episode 001 — The Floor Below Zero

This report records the Episode 1 milestone. The later autonomous production
milestone is documented in [AUTONOMY.md](AUTONOMY.md).

Implemented in Blender 5.2.3 LTS. The master is 1080 frames at 24 FPS, portrait
540 x 960. The playable preview covers the entire 45 seconds at a practical
6 FPS. It contains seven original radio lines, an original synthesized sound
mix, cinematic captions, 11 camera shots and a cut-to-black cliffhanger.

## Protection and inspection

The current live scene was inspected and backed up before changes to
`artifacts/backups/pre_episode001_20261109_231107.blend`.
`artifacts/episode_001/current_scene_inspection.json` records objects, materials,
lights, actions and all action keyframe coordinates. The inspected scene had
48 objects and 19 actions. Existing scripts, episode 001 configuration, README,
Git ignore rules and dynamic workflow were copied to
`artifacts/backups/repository_pre_episode001/`.

Neither the original `first_scene.blend` nor the earlier ten-second
`elevator_suspense_10s.blend` was overwritten. The prior episode builder is
preserved verbatim as `legacy_story_scene.py`. Episode 002 still uses that
builder. `render.yml` retains its original SHA-256:
`ECCF3D805068AACBF651EDF1EDEB21824AE7ADBDFFD2E989CBB2D783F1548358`.
No remote push, publication or GitHub workflow dispatch was performed.

## Implemented story and systems

- The passenger settles inside the established elevator, breathes, looks up,
  sways under acceleration, reacts to impact, turns toward the doors, steps
  backward and freezes. Connected shoulder, elbow, hand, pelvis, knee and shoe
  meshes replace the floating limbs. Hip and shoulder pivots animate rigid
  connected limbs without simulation or a costly deformation rig.
- Floor text progresses through every integer from 13 to 0, increasingly fast,
  then glitches before showing -1. Each readable number lasts at least three
  preview frames. Font bodies are separate objects with stepped visibility
  actions; this works without unsupported animated font-body strings.
- Camera-bound timeline markers provide an opening wide, indicator close-ups,
  an uneasy medium, bounded acceleration shake, wrong-floor close-up, impact
  reaction, wide door reveal, an over-the-shoulder shot, silhouette shot and
  final slow push before black. Primary subjects and captions were checked
  against the active camera, not just a user viewport.
- Overhead lamps and visible fluorescent emission flicker together. Power
  fails after impact, then red emergency lighting returns. A real doorway
  opens onto a deeper corridor with ribs, guide lights and limited cool light.
  Brushed steel, graphite reflections, trim, controls and radio grille extend
  the existing environment asset.
- The antagonist is a reusable connected faceless humanoid with matte cloth,
  tapered coat, independent head and body pivots, articulated hips and one slow
  step. Its empty facial-effects socket allows later additions without giving
  this episode a detailed face.
- JSON separates story timing from assembly. Geometry/material helpers,
  character constructors, shot selection, reactions, lighting, displays,
  doors, movement, captions and sound cues are reusable modules and controls.
  The final master retains 73 named episode actions using fake users.
- Windows SAPI generated seven radio lines with Microsoft David. Their timing
  fits the authored caption windows without cutting words. All mechanical and
  atmospheric effects were synthesized locally with deterministic noise and
  oscillators; no external sound recordings were used. `audio_manifest.json`
  records the source, cue timing, durations and peak. The 45-second PCM mix is
  packed in the master and encoded as AAC in the preview. Linux automation can
  generate a different offline voice with espeak-ng.

## Verification evidence

`tests/validate_episode.py` reopened/evaluated the episode under the actual
Blender 5.2.3 LTS runtime. All 1080 master frames passed: active shot assignment,
exact countdown visibility, finite transforms and primary-subject framing.
Representative per-shot rays checked geometry occlusion; complete antagonist
head bounds were checked in the final two shots. Caption bounds stay inside
the safe viewing area. Additional assertions cover blue arrival, blackout,
red return, door travel, recoil, shadow forward travel, hip movement, connected
hierarchy, retained actions, packed sound and final camera. Evidence:
`artifacts/episode_001/scene_validation.json`.

Twelve EEVEE still renders were inspected, covering 1, 6, 9.5, 21.9, 24.5,
26.3, 28, 32, 36, 39, 42 and 44 seconds. These are half-resolution diagnostic
renders. The final preview is rendered separately at 540 x 960 with 16 samples.
The final saved master keeps 32 EEVEE samples and 24 FPS.

`tests/test_episode_data.py` passed five checks: countdown order/speed and
preview readability, complete shot coverage, narration/caption alignment,
generated audio duration and levels, and the unchanged fallback workflow.
Python compilation and `git diff --check` passed. The schema-1 Episode 002
builder and its full 96-frame validation also passed without rendering.
An additional CPU Cycles smoke render passed at frame 937, 108 x 192,
four samples, taking 1.45 seconds locally. This tests the CPU render path,
not full-resolution cloud throughput.

`tools/encode_episode.py` verifies the complete PNG sequence, encodes H.264/AAC,
checks MP4 dimensions, sample count, rate and duration, and decodes the entire
video through FFmpeg. Evidence is written to `video_validation.json`,
`ffmpeg_encode.log`, `ffmpeg_decode.log` and `render_metadata.json`.

**Final preview verification passed:** 270 H.264 frames, 6 FPS, 540 x 960,
exactly 45.0 seconds of video, AAC sound track, 4,108,861 bytes. Every frame
decoded successfully with no FFmpeg error output. The final review render
uses 16 EEVEE samples; it completed after the resume described below.
Representative final-resolution preview frames were also visually inspected.

Resolved issues found during work: initial antagonist shots cropped the head;
they were widened and retested. Initial ray assertions treated a nose/eye or
the empty center between font strokes as an obstacle; the checks now recognize
those expected surfaces. Windows speech was denied inside the sandbox and
succeeded after the authorized unsandboxed retry. The installed CapCut FFmpeg
lacked libx264; a project-local FFmpeg distribution supplied it. The initial
speech-window fit was too short for two lines; the authored timings were
extended and the audio tests now reject that mismatch.

One 16-sample EEVEE preview pass encountered a native
`EXCEPTION_ACCESS_VIOLATION` at `GPU_texture_extend_mode` after frame 38.
The earlier complete 8-sample preview remained valid. The interactive viewport
was switched to solid mode and the higher-sample render resumed in a fresh
background process from its saved plan. The local one-command runner now uses
separate build/validation and render processes with at most three render
attempts; frame-plan hashes prevent cross-version resume. This does not claim
to fix the underlying Blender/graphics-driver bug.

## Remaining limitations

- The full 24 FPS master sequence has not been rendered; the complete review
  preview samples it at 6 FPS. Fine motion and flicker are less smooth in that
  preview. Low EEVEE samples can show soft-shadow noise and screen-reflection
  artifacts. No expensive high-resolution production render was started.
- The installed voice is an offline synthetic radio voice, not a directed
  studio performance. Linux espeak-ng will sound different. Audio generation
  and levels were tested programmatically; no claim of a listening review is
  made.
- Shot rays and framing checks do not prove every pixel is free from all
  possible intersections. Movement uses simple pivots and connected meshes,
  without full-body IK or motion capture. The opening is an interior settling
  movement rather than an exterior hallway entrance shot.
- The new GitHub workflow was reviewed locally; Linux/Xvfb execution, remote
  Blender archive availability and cloud timing have not been tested on a
  hosted runner. CPU Cycles may exceed the preview budget on slower runners.
- The system currently supports this elevator template. It does not invent
  arbitrary environments or episodes, maintain a persistent continuity store,
  schedule daily jobs, perform automatic editorial/audio review or upload to
  YouTube. Those components, a larger asset/action library and publishing
  authorization are still needed for autonomous daily production.
