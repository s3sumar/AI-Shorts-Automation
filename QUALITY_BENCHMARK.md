# Cinematic quality and performance benchmark

This benchmark is separate from production. It uses the fixed global Episode 3
plan in the reviewed seed, creates disposable scenes under `artifacts/quality`,
and never reserves episodes, writes SQLite story memory or updates the durable
cloud checkpoint. The autonomous production workflow and original assets are
unchanged. No daily scheduling or video upload is added.

## Existing cloud measurements

The successful Episode 3 run took **379 seconds**. Its 90 EEVEE frames at
180 x 320, 2 FPS, 4 samples took **309.31 seconds**, or **81.6%** of job execution.
The cold frame took 21.27 seconds; warm median was 3.26 seconds. Encoding took
about 1.4 seconds. Even the final black shot cost about 2.57 seconds per frame.
These measurements identify rendering and per-frame overhead as the bottleneck,
not narration, encoding or state storage. They do not isolate individual GPU
kernel costs; shadow/setup costs remain an inference until further profiling.

At those *original small-preview settings*, 1080 frames were estimated at about
58.3 minutes. That already exceeds the production runner's 30-minute invocation
budget. 720p has 16 times as many pixels and 24 FPS requires 12 times as many
frames as the preview, but multiplying both ratios is not a valid performance
prediction: substantial work is independent of resolution.

Actual per-camera cloud data is saved in
`artifacts/quality/cloud_baseline_analysis.json`.

## Opt-in balanced profile

`quality/profile.py` applies changes only in a disposable Blender process:

- Bake static bevel/weighted-normal modifiers once. The exact evaluated meshes,
  animated rig transforms, character identities and source assets are preserved.
- Keep overhead/key and rim shadows; stop computing shadows for the face fill
  and corridor depth wash. Use a moderate shadow resolution scale of 0.75 and
  avoid sub-centimeter shadow-map detail.
- Keep ray tracing and depth of field off. Preserve authored metal roughness,
  AgX color management, blue/red colors, lens settings and smooth camera paths.
- Increase sampling from 4 to 16 for the HD tests. Apply a conservative spatial
  FFmpeg denoise before adding clean subtitles. This does not create path-traced
  reflections or eliminate every shadow/noise artifact.

Blender describes the sampling/quality tradeoff in its
[EEVEE sampling documentation](https://docs.blender.org/manual/en/latest/render/eevee/render_settings/sampling.html).
The first matched local five-frame probes measured 10.65 seconds before and
8.29 seconds after optimization, about 22% less render time. These are local
measurements, not hosted Linux results.

## Native and efficient alternatives

The ten-second test covers master seconds 26–36: impact/reaction, red-light
recovery, head turn, opening doors and a silhouette reveal across three shots.
It reuses the original packed narration/effects mix when a saved source is given.
Without a source, it builds the fixed plan and synthesizes offline audio, which
is how the prepared cloud workflow runs independently of the laptop.

**Native:** 720 x 1280, 24 FPS, 240 distinct Blender frames. This is actual native
animation, not a low-FPS video in a 24 FPS container.

**Hybrid:** render slow movements at 12 FPS; retain 24 FPS for impacts, rapid
lighting changes and short transition segments. Interpolate each segment to
24 FPS using FFmpeg motion compensation. Never interpolate across camera cuts,
floor-number changes or blackout boundaries. Reuse one plate for the full
black cliffhanger shot. Composite subtitles afterward so optical flow cannot
warp text. A full episode uses **609 source frames instead of 1080**; the demo
uses **156 instead of 240**.

The reconstruction uses FFmpeg's documented
[minterpolate and padding filters](https://ffmpeg.org/ffmpeg-filters.html#minterpolate).
It can produce edge/occlusion artifacts and cannot be promised equivalent to
native animation. Native impacts and separate caption composition mitigate
specific problems. SSIM is a diagnostic, not proof of perceived smoothness.

An early visual review caught duplicate subtitles because Blender re-evaluated
animated hide flags. The renderer now disconnects caption visibility animation
in memory and asserts captions stay hidden, then FFmpeg adds exactly one layer.
Earlier intermediate examples are retained locally; use the final outputs below.

## Reproduction

Requirements are the existing production dependencies, Blender 5.2.3 and FFmpeg
with libx264, AAC, libass, hqdn3d and minterpolate. No model API is used.

```sh
python tools/benchmark_quality.py --mode native --profile balanced --samples 16 --out artifacts/quality/native_720p24 --blender blender --ffmpeg ffmpeg
python tools/benchmark_quality.py --mode hybrid --profile balanced --samples 16 --out artifacts/quality/hybrid_720p24 --blender blender --ffmpeg ffmpeg
python tools/report_quality.py --ffmpeg ffmpeg
```

Pass `--source path/to/episode_003_master.blend` to reuse a completed scene.
Outputs refuse mixing source/profile/renderer versions. A repeated run can reuse
validated PNGs and retain their original measured render times. The reported
process wall time is that invocation only; summed frame times are accumulated
measurements. The local benchmark encountered overlapping obsolete/new renderer
processes during caption repair; the obsolete process was stopped. Warm medians
and explicit environment labels should be used rather than treating its total
wall time as a controlled cloud comparison.

Local final outputs:

```text
artifacts/quality/native_final_720p24/quality_native_720p24.mp4
artifacts/quality/hybrid_final_720p24/quality_hybrid_720p24.mp4
artifacts/quality/baseline_final_180p/baseline_180p24_container.mp4
artifacts/quality/COMPARISON.md
artifacts/quality/quality_comparison.json
artifacts/quality/final_unit_tests.log
artifacts/quality/state_preservation.json
```

The final **local** ten-second measurements are:

| Mode | Source frames | Render time | Composition/decode time |
| --- | ---: | ---: | ---: |
| 180 x 320 baseline, 2 FPS source | 20 | 10.41 s | 0.86 s |
| 720 x 1280 native 24 FPS | 240 | 394.10 s | 12.23 s |
| 720 x 1280 hybrid 24 FPS output | 156 | 209.21 s | 34.32 s |

Native warm median was 1.19 s/frame; hybrid warm median was 1.21 s/frame.
The native total includes the local overlapping-process interruption described
above, so the total-time ratio is not a controlled speedup measurement. Both
videos have exactly 240 output frames, ten seconds, non-silent audio, one caption
layer, and pass full decoding. Hybrid/native video SSIM is **0.990878**. Matched
profile still SSIM ranges from 0.9839 to 0.9950; these metrics are not perceptual
guarantees. Fine shadow grain and simple character rigs remain visible limits.

The source-independent build path also passed: it generated offline narration,
built a new fixed-plan scene, validated all 1080 master frames, and rendered five
720p probes without reading a local episode master or using Blender MCP. The
complete local unit suite passes **36 tests**. A listening/editorial review and
actual hosted HD acceptance remain separate from these automated checks.

The baseline file is explicitly a 24 FPS *container* duplicating its 2 FPS
source frames. It is provided for matching clip comparison, not claimed as
24 FPS animation.

## Checks and current deployment boundary

The renderer checks shot-camera bindings, subject framing, character visibility,
finite/nonnegative light settings, representative image exposure, expected
blackouts, source checksum immutability and starting/ending character transforms.
Every encoded MP4 is probed for dimensions, exact frame count and duration,
audio presence and full decoding. Tests also cover cut separation, fast-event
sampling, plate reuse and read-only cloud permissions.

The prepared `.github/workflows/quality_benchmark.yml` is manual-only and has
**contents: read**. It has no checkpoint writer, upload-to-service step, secrets
or schedule. A public-repository guard prevents running it after a change to
private visibility. It runs the low-resolution baseline, matched 720p probes, native
and hybrid ten-second tests, then saves downloadable videos and diagnostics.
Its job is capped at 90 minutes; native rendering is capped at 40 minutes and
hybrid rendering at 30 minutes. Expired budgets fail and retain diagnostics.

**The quality workflow has not been run in GitHub Actions.** Deploying this
manual workflow does not dispatch a render. A cloud-rendered HD MP4, actual
HD cloud timing and confirmation that a complete 45-second HD episode fits the
free runner/budget remain outstanding. Local feasibility estimates must not be
reported as cloud measurements. A full 45-second HD render has deliberately
not been started without that calibration.

A later explicit instruction can authorize running **Cinematic Quality Benchmark**
once. Keep scheduling and publishing disabled; a source-code push does not
authorize an additional cloud run.
