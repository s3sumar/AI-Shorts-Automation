# Manual autonomous cloud deployment

The deployable project includes the reusable Blender asset, compiler, offline
director, audio tools, validation, checkpoint recovery, workflow and tests.
No Blender MCP session or personal computer is needed by the hosted runner.
No paid inference API, daily schedule or video upload is enabled.

## State and episode numbering

`config/story_checkpoint.json` is an intentional source configuration: a
checksummed, portable story checkpoint reviewed against the local ledger and
the original delivery hashes. It preserves verified global Episodes 1 and 2,
their immutable continuity/evidence, run reservations and the planned global
Episode 3. It contains story metadata, not generated media or a local database.

The pilot season ends after Episode 2. Global Episode 3 is **Dead Air Dispatch:
The Undelivered Signal**, series_002_e001. Its new cast and freight-lift setting
are the planned season transition. Episode 1/2 canon remains intact; the new
series starts from its own recorded initial state.

The local acceptance render used a separate restored ledger and output directory.
It did not advance the working/deployment ledger. The first cloud dispatch still
reserves global Episode 3, never starts again at Episode 1.

## Durable cloud checkpoints

`tools/cloud_checkpoint.py` uses the GitHub REST API to store
`checkpoint/story.json` on **autonomy-state**, a dedicated Git branch. This is
versioned storage rather than an evictable cache. Initialization creates the
branch and its first complete checkpoint atomically from the dispatched source
commit. Later writes require the content SHA obtained at recovery/save time.
Conflicting writes fail rather than overwrite newer state. The implementation
follows GitHub's [contents API](https://docs.github.com/en/rest/repos/contents)
and [Git references API](https://docs.github.com/en/rest/git/refs).

Each manual run:

1. Tests the checkout and restores durable state, or the reviewed seed on the
   very first run. Existing missing/corrupt state fails closed.
2. Reserves `github-${GITHUB_RUN_ID}` and saves the reservation before rendering.
3. Builds and validates one episode, renders at most 90 preview frames, encodes
   H.264/AAC and fully decodes the video before advancing canon.
4. Saves the verified result or failed reservation, including on production
   failure. Always exports logs and downloadable review/recovery artifacts.

Rerunning the same GitHub run reuses its key. A new run after a failure resumes
the pending episode. Verified episodes and their media hashes are immutable.
There is no cloud upload step, so no videos can be uploaded by this workflow.

The job's `GITHUB_TOKEN` needs `contents: write` to maintain the state branch.
That GitHub permission is repository-wide; the implementation writes only the
fixed state branch/path. Checkout uses `persist-credentials: false`. No personal
access token or OAuth secret is needed. Branch protection may require a repository
policy adjustment. An API failure before reservation persistence stops production.

Recovery artifacts are retained for 30 days, while state-branch commits remain
until deliberately deleted. If the state branch is deleted, restore it before
dispatching again. A job interrupted before its final checkpoint may rerender
the same reserved episode; it cannot advance to a duplicate episode or upload.
If a verified run is retried on a fresh runner and its video is absent, the
runner refuses regeneration and asks for artifact recovery. Automatic media
artifact rehydration is not implemented.

## Local acceptance evidence

- 29 unit tests pass with zero failures/errors/skips in the working checkout.
- A clean source checkout runs the same suite: 28 pass and the existing generated
  Episode 1 audio check skips because local media is intentionally excluded.
  That audio check passes in the working checkout; cloud production validates
  the newly generated narration before committing its result.
- Eight added tests cover restored Episode 3 numbering, corrupt checkpoints,
  immutable restore, durable recovery, failed-run reservation reuse, stale-writer
  rejection, missing checkpoint failure, regression protection and manual guards.
- An initial test exposed an unclosed read-only SQLite connection on Windows;
  explicit connection closing fixed it and the suite passed afterward.
- Both completed pilot MP4s remain unchanged and fully decode.
- Episode 3's separate test produces a complete 45-second **108 x 192, 2 FPS**
  smoke preview with offline narration, procedural effects and captions. Its
  scene passes all 1080 master-frame checks; 90 preview frames render in **38.96
  seconds** on this local machine. This is not a hosted-run benchmark.
- Its saved shot plan has 11 shots. Repeating its run key returns the verified
  receipt without rendering or reserving another episode.
- The required Blender asset opens in Blender 5.2.3 with no unpacked external
  images, sounds, fonts or linked libraries.
- Workflow YAML/ordering/disabled-publication guards, Python syntax, credential
  pattern checks and Git whitespace checks pass.

Local evidence (ignored by Git):

```text
artifacts/deployment/final_unit_tests.log
artifacts/deployment/asset_check.log
artifacts/deployment/episode3_local/media/series_002_e001/episode_003_preview.mp4
artifacts/deployment/episode3_local/media/series_002_e001/episode_003_master.blend
artifacts/deployment/episode3_local/media/series_002_e001/episode.json
artifacts/deployment/episode3_local/media/series_002_e001/story_plan.json
artifacts/deployment/episode3_local/media/series_002_e001/scene_validation.json
artifacts/deployment/episode3_local/media/series_002_e001/video_validation.json
```

## First hosted acceptance run

After owner approval, push the reviewed local commit to `origin/main`, then
manually run **Autonomous Shorts Production** in Actions. The CLI equivalent is:

```sh
gh workflow run autonomous_production.yml --ref main
```

This dispatch can consume GitHub Actions allowance; it has not been performed
locally. The workflow is manual-only, has a 40-minute job timeout, and uses
`config/cloud_preview.json`: 180 x 320, 2 FPS, 4 samples, 90 frames, offline
speech and software EEVEE. Download `shorts-production-<run-id>-<attempt>` and
inspect the Actions summary. Confirm global Episode 3 and the autonomy-state
checkpoint before considering any later production activation.

## Limits and deployment review

The actual hosted Linux/Mesa/espeak combination and real GitHub checkpoint API
writes remain untested until an approved dispatch. Repository policy must allow
Actions and state-branch writes; runner allowance must be available. The Blender
archive URL returned HTTP 200 locally. No special API keys are required.

The tested story director is a limited offline procedural grammar. Real Ollama
generation and real private YouTube uploads remain separate acceptance tasks.
Full 24 FPS final-quality renders and editorial/listening review remain unfinished.

Commit source/configuration/workflows/tests/documentation and only the required
`assets/elevator_template.blend` binary. Exclude artifacts, MP4/WAV files, local
SQLite state, downloaded tools, tokens and credentials. `tools/review_deployment.py
--staged` checks the staged bytes for these exclusions and credential patterns.
No secret scan can prove absence of every possible secret; the automated scan
is combined with the source/configuration review.
