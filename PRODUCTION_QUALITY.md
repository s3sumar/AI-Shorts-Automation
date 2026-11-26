# Episode 3: quality first, automation second

## Implemented multi-voice audio (2026-11-21)

The implemented cast replaces the one-voice workaround for opt-in audio
production. The current playable audio-only preview is
`artifacts/audio_previews/episode3_multivoice_v3/dialogue_and_sound_preview.mp3`;
its exact-length master is `audio/episode_mix.wav` in that same directory.
It contains the complete 45-second writing revision in
`episodes/episode_003_dialogue.json`, with 13 individual delivered line WAVs,
three speaker stems, ambience/effects stems and aligned SRT/ASS captions.
Existing 3D previews retain their previous audio; no new animation was rendered.

The writing pass establishes the impossible delivery status and her wish to get
home, replaces obvious speed commentary with a cancellation attempt, explains
the sealed floor and preserves the recipient/delivery double meaning for the
last line. It is an editorial audio revision; story canon has not been updated.

| Role | Stable identity | Local model |
| --- | --- | --- |
| Narrator | `john_storyteller_v1` | John medium |
| Main character | `lj_character_v1` | LJ Speech high |
| Figure | `norman_figure_v1` | Norman medium |

These are three distinct voice models, not one voice with different labels.
Their model/config SHA-256 hashes and repository revisions are pinned in
`config/voice_cast_local.json`. The model cards document public-domain datasets:
[John](https://huggingface.co/rhasspy/piper-voices/blob/e9c8a39444359388adaa94255becb37a5a2b8e51/en/en_US/john/medium/MODEL_CARD),
[LJ Speech](https://huggingface.co/rhasspy/piper-voices/blob/6b9cfaacb4fb2e02a9621227e3c1a48bec9710c3/en/en_US/ljspeech/high/MODEL_CARD),
and [Norman](https://huggingface.co/rhasspy/piper-voices/blob/e9c8a39444359388adaa94255becb37a5a2b8e51/en/en_US/norman/medium/MODEL_CARD).
Model cards and provenance stay beside the ignored downloaded models. Piper is
an optional GPL runtime dependency, not vendored project code. These voices run
locally on CPU and can run on Linux; they do not require Windows SAPI or a live
Blender MCP session. The old SAPI/single-narrator development path is preserved.

### Delivery, timing and mixing

Each line chooses a role and a bounded `emotion` profile: storytelling, uneasy,
afraid, desperate, terrified, resolute or unsettling. Profiles control generated
pace, phrase pauses, subtle time-preserving pitch adjustment, gain and optional
small amplitude tremor. The figure also receives restrained filtering/delay.
These are real applied signal/synthesis controls, but Piper is not an emotional
acting model. A `terrified` label does not certify believable fear; naturalness
and character performance still require listening review.

Every line has its own raw take, delivered WAV, exact voice identity, word/phrase
timings, delivery receipt and checksums. Matching takes are reused. A changed
script/voice/style cannot silently reuse a different take. Speech overruns fail
with a measured error rather than cutting off words. The figure's first slot was
widened after a measured overrun, preserving its performance and final pause.

Word boundaries come from the synthesized phoneme durations, not a guessed
transcript. Where the phonemizer joins words, a constrained per-word phoneme
mapping uses those same timed phonemes; high edit cost or unmappable words fail.
This fixed the `was a` boundary case. Captions retain the exact authored words,
speaker metadata and bounded reading holds. Balanced three/three-word splitting
fixed the refusal caption's reading speed. Pronunciation and final boundary
quality still need listening review, especially after pitch processing.

Dialogue is centered in a stereo 48 kHz mix. Environmental effects follow the
score's animation cues; other environments can supply explicit `sound_events`.
Ambience/effects duck under actual speech. The written mix measures −16.07 LUFS,
−1.50 dBTP and 6.3 LU loudness range; measured speech-over-bed margin is about
31.1 dB. The WAV contains exactly 45 seconds. MP3 and WAV fully decode without
errors. All 13 lines fit and all 24 subtitle chunks pass the 22-character/second
reading-speed limit, with no ASR fallback phrases.

### Reuse and autonomous pipeline integration

`soundstage/voice_contract.py` validates dialogue and freezes model identities;
`soundstage/casting.py` renders the cast. New series store a voice lock in their
bible and pass it to future episode plans. The existing courier series has a
source-controlled voice-only lock in `config/series_voice_casts.json`; this is
not an episode checkpoint. Changed model/config hashes or role assignments
require explicit recasting. Supporting roles can be added with their own pinned
voices. A character need not speak in every episode just because it is cast.

The director now produces role-tagged dialogue or accepts validated dialogue
from an already installed local model. The offline dialogue remains a baseline
for the supported lift story grammar; it is not an unlimited story writer or a
guarantee of publication-quality prose. Compiler settings select the feature:

```json
"audio": {"mode": "cast", "cast_settings": "config/voice_cast_local.json"}
```

`config/multivoice_preview.json` supplies that opt-in configuration. Compilation
normalizes speakers to stable character IDs. The existing `prepare_audio.py`,
generated caption update, audio resume and quality-evidence path accept the
cast. Each used voice still needs human identity approval for release readiness.
Planning/production remain paused; the new profile does not bypass that pause,
enable uploads or advance existing story checkpoints.

The manual production workflow has an optional `audio_profile: cast` choice
(default remains legacy). That path checks the pause before downloading any
voices or restoring/reserving state, installs `requirements-voice-cast.txt`,
verifies pinned assets and the FFmpeg pitch filter, then uses the cast settings.
It has not been dispatched or tested on a hosted runner in this task.

For a fresh machine, install the production and voice-cast requirements;
install FFmpeg with the `rubberband` filter. Explicitly download free voices:

```text
python tools/setup_voice_cast.py
python tools/preview_dialogue.py --score <compiled-score.json> --script <role-script.json> --out artifacts/audio_previews/<fresh-revision> --ffmpeg <ffmpeg-executable>
```

Synthesis never downloads models, contacts paid services or creates cloud jobs.
Audio previews do not load Blender. Tests cover voice locks across two planned
episodes, compiler integration, changed identities, invalid dialogue, timing,
subtitle text, coarticulation and non-elevator environmental sound events.
The production entry point also resumed the actual completed mix without
changing its hash. This feature is locally tested; no new cloud voice run or
public upload has been performed.

The following sections retain the earlier one-voice audition history.

Episode 3 remains the fixed benchmark. No additional episode was generated and
no working scene, video or story checkpoint was replaced. The old production
preview is **NOT READY**, even though its render/continuity checks passed.
The quality experiments did not schedule production, upload to YouTube or use
paid services. Generated media and downloaded models are local-only artifacts.

`config/production_standards.json` pauses episode planning and
production until owner approval to resume. Status/bootstrap remain available;
fixed Episode 3 audio and visual benchmark tools remain usable. This policy also
applies to GitHub Actions after deployment: manual production exits before
reserving another episode until the owner explicitly approves unpausing.
The latest story draft and three excerpt results are in
[EPISODE_3_SCRIPT_REVIEW.md](EPISODE_3_SCRIPT_REVIEW.md). The audition results
below describe the earlier November 14 audio revision.

## Listen before choosing a narrator

The comparison uses the same four phrases for all approaches, level matched to
approximately -16 LUFS. These are candidates, not approved professional voices.

| Approach | Actual sample | Strengths and limitations | Cost |
| --- | --- | --- | --- |
| A: plain installed Windows David | `artifacts/production_upgrade/episode3_v2/samples/A_plain_sapi_listen.wav` | Reference with no directed pauses; useful control, not the recommended final voice. Windows-only. | No API fee on this machine. |
| B: directed Windows David | `artifacts/production_upgrade/episode3_v2/samples/B_directed_sapi_listen.wav` | SSML emphasis, slower delivery and explicit clause pauses. SAPI expressiveness remains limited. Windows-only. | No API fee on this machine. |
| C: local neural LJ Speech | `artifacts/production_upgrade/episode3_v2/samples/C_local_neural_listen.wav` | Neural candidate with timed phrasing and stable model identity. Neutral audiobook voice; Piper does not provide reliable emotional direction just because an intention is written in the script. Requires listening approval. Cross-platform CPU inference. | No API fee; local/cloud compute and storage still have costs or limits. |

The sample text is: “The lift is empty. So who said her name? The doors are
opening. Someone is waiting.” Pauses and delivery rate intentionally differ.
The samples are not a blind comparison with equal timing; they compare practical
delivery approaches. No real person was impersonated or cloned for this task.

Piper 1.8.0 and its approximately 114 MB voice model were downloaded into ignored
`artifacts/` directories. The runtime is GPL-3.0-or-later; it is not vendored.
The [voice model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD)
documents public-domain LJ Speech training data and training from scratch.
Piper's [commercial-use notes](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md)
list this voice's dataset chain as public domain. Model revision/checksum are
pinned in `config/narrator_candidate.json`; the downloaded model card and file
hashes are saved in `artifacts/audio_models/ljspeech_high/provenance.json`.
The source voice is 22.05 kHz; a 48 kHz delivery mix does not add voice bandwidth.

### Paid alternatives evaluated, not used

[ElevenLabs' API price page](https://elevenlabs.io/pricing/api), checked for the November 14 comparison, listed
v3/v4 TTS at **US$0.08 per 1,000 characters**, with expressive/audio-tag features.
Those capabilities make it a candidate for a paid audition; vendor descriptions
are not an independent listening comparison. The revised script has 274
characters: arithmetic usage would be about $0.0219 per take, $0.66 for 30
single takes, or $1.97 for three takes per day for 30 days. **These figures are
not an all-inclusive subscription quote.** Plan eligibility, credits, minimums,
commercial rights, retries and taxes must be checked before purchase.
[Creative plan pricing](https://elevenlabs.io/pricing) lists Starter at $6/month
after its introductory offer and Creator at $22/month. Do not assume those
plans and API usage prices are interchangeable.

OpenAI's [GPT-4o mini TTS model page](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)
was also checked: it is marked deprecated and lists token-based pricing. No
new integration or obsolete per-minute estimate was assumed. A supported
replacement and actual account pricing need review before a paid audition.
No OpenAI/ElevenLabs API call, subscription, key search or purchase was made.
Unknown/paid providers fail closed in the current narration adapter.

## Sound design and mixing

`soundstage/` implements narrator identity/caching, separate stereo stems and
reusable original procedural categories: environment, footstep, movement,
mechanical, doors, radio, alarm, impact, transition and cliffhanger.

Door travel follows the authored door aperture keys (29.5–35.5 seconds in this
episode). Impact follows its 26-second animation key. Footstep anchors follow
the passenger's step keys and antagonist root landing keys; this is authored
key timing, not collision/contact simulation. No unlicensed recordings or music
were downloaded. Every cue records its category, gain and animation anchor.

Dialogue stays centered. Ambience ducks by 12 dB and effects by 8 dB with smooth
attack/release. Source words are never truncated or crudely time-compressed to
fit a window. Actual phrase durations drive subtitles and overrun checks.
Two-pass FFmpeg loudness normalization is followed by measurement of the written
audio, with bounded correction and peak limiting if a short dramatic clip misses
its target. This verification caught and corrected an initial short-clip mismatch.

Measured final candidate:

| Item | Integrated loudness | True peak | Other evidence |
| --- | ---: | ---: | --- |
| Original cloud Episode 3 MP4 | -26.73 LUFS | -0.32 dBTP | Mono, 24 kHz; fails new standards. |
| Revised full 45-second mix | -15.82 LUFS | -1.50 dBTP | Stereo, 48 kHz; 14.7 LU loudness range. |
| Revised encoded comparison clip | -16.13 LUFS | -1.77 dBTP | Stereo, 48 kHz; no clipped/nonfinite samples or unexpected long silence. |

Measured speech-over-bed margin was 30.46 dB during active speech. All eight
lines fit their allocated windows. The opening hook finishes at approximately
1.60 seconds. The mix takes about 26.6 seconds locally including synthesis and
normalization; an integration run also verified the existing `prepare_audio.py`
entrypoint and an unchanged-audio resume after timed caption updates.

The current 14.7 LU dynamic range still needs phone/headphone listening review.
`audio/phone_simulation.wav` is mono with 150–7000 Hz bandwidth. It is **not**
a physical phone test. No physical headphone or phone listening was claimed.

## Episode 3 revision and visual costs

The draft script adds a hook, a short recap of the ground-floor escape, a
message linking the new courier story, and a personal cliffhanger. The new
message connection and narrator identity require editorial approval; story
memory was not rewritten to make them canon.

Final review files:

```text
artifacts/production_upgrade/episode3_v2/comparison/episode3_before_after_12s.mp4
artifacts/production_upgrade/episode3_v2/comparison/episode3_upgraded_6s_720p24.mp4
artifacts/production_upgrade/episode3_v2/audio/episode_mix.wav
artifacts/production_upgrade/episode3_v2/audio/phone_simulation.wav
artifacts/production_upgrade/episode3_v2/comparison/production_quality_gate_final.json
artifacts/production_upgrade/episode3_v2/benchmark_and_costs.json
```

The comparison plays **six seconds before, then six seconds after**. It uses
the same native animated image sequence, so it compares audio/script/captions
without changing the shot performance. Both parts are level matched. The
upgraded six-second clip uses 144 distinct native Blender frames at 720 x 1280
and 24 FPS. This is a development preview, not a publication master or an upscale
of the 2 FPS preview. Existing rendered frames were reused to avoid a needless
expensive render.

Five **genuine 1080 x 1920, 32-sample** local probes also passed exposure/framing
checks: 22.80 seconds of rendering, 7.17 seconds for the first frame and a warm
median of 3.99 seconds/frame. Data is in
`artifacts/quality/production_1080p_probes/benchmark.json`. A simple 1080-frame
extrapolation is **about 72 minutes on this local machine**, not a measured full
episode or a cloud/GPU service benchmark. The main renderer retains the
character materials, blue/red lighting and native camera/character motion.
Fine shadow grain, simple rigs and facial details remain visible limitations.

### Realistic daily-production budget

- Local neural narration and original effects: $0 API usage; allow roughly half
  a minute of measured local audio processing per episode, plus review/retakes.
- Standard public-repository Actions compute is
  [free under GitHub's standard-runner policy](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job).
  Hosted 1080p speed, execution limits and artifact capacity still need testing.
  The old 6-minute low-resolution cloud run is not a full-quality cost estimate.
- A paid expressive voice needs an approved plan/account budget; use the
  character-count arithmetic above as a usage estimate, not the complete invoice.
- As an explicitly **unbenchmarked scenario**, GitHub lists eligible Linux GPU
  runners at [$0.052/minute](https://docs.github.com/en/billing/reference/actions-runner-pricing).
  If a future measured GPU job takes 30–90 minutes, that is $1.56–$4.68 per
  episode, or $46.80–$140.40 for 30 episodes, before plan/tax/storage costs.
  These runners require eligible organization/enterprise plans and are not a
  drop-in free upgrade for this personal repository. No GPU runner was purchased.
- Listening/editorial review time is still required and is not included in
  those dollar figures. Fully unattended professional-quality publishing has
  not been demonstrated.

## Production gate and automation integration

`quality/production_gate.py` checks 1080 x 1920 minimum, 24/30 FPS, frame counts,
native contiguous render provenance, unexpected duplicates in moving shots,
audio format/loudness/true peak/clipping, narration presence/timing, readable
captions, assets and scene continuity. It also requires media-hash-bound human
reviews for voice naturalness, story connection, pacing, visual appeal, phone
listening and headphone listening. A stale review cannot approve changed media.
Even a fully reviewed READY video cannot publish while the public-publishing
policy remains disabled. Existing YouTube code still supports private only.

The new clip correctly fails readiness for its development resolution/duration
and unapproved voice identity, with all six human reviews pending. “Technically
verified” in the story ledger does not mean publication-ready.

The final suite passed **50 tests** with no failures. Coverage includes paid-call
blocking, source-frame cadence/resolution, duplicates, stale reviews, loudness,
clipping, caption synchronization, generation pause, deterministic effects and
an actual FFmpeg normalization test. Full before/after videos decode, the new
clip has 144 unique source frames and constant 24 FPS timestamps, and the cloud
checkpoint and original Episode 3 video checksums are unchanged. Synthetic foley
realism and voice expressiveness remain listening-review questions, not solved
by those checks.

The advanced audio path is opt-in in existing settings:

```json
"audio": {"mode": "cinematic", "narrator_settings": "config/narrator_candidate.json"}
```

Install `requirements-audio.txt` alongside existing production requirements and
run `python tools/setup_local_narrator.py` to download the pinned free voice.
Synthesis itself never downloads models or contacts paid providers. The existing
prepare/build/render/encode runner accepts the new stereo mix, updates generated
caption timing, measures readiness and carries NOT_READY into upload jobs.
Legacy development behavior remains available. Model/voice changes invalidate
caches; matching retries reuse measured audio without replacing working takes.

Human review starts with `config/human_review.example.json`. Fill the exact video
SHA-256, reviewer and only checks actually performed. The runner reads
`human_quality_review.json` from an episode's output directory. For an existing
review clip, `tools/review_production_quality.py` accepts `--video`, `--gate`,
`--human-review`, `--out` and `--ffmpeg`, rechecks the actual media, and returns
exit code 2 for NOT_READY. A voice must also be explicitly approved in its
narrator settings. No tool automatically fills human approvals.

Keep the generation pause, uploads and schedules disabled. Before any release:
choose/approve a voice after listening, review story edits and mix dynamics,
perform real phone/headphone review, fix remaining art-direction issues, then
benchmark/render a full native 1080p master and rerun the gate. No new cloud run
is authorized merely by deploying these source changes.


## Treatment-first suspense writer and Episode 3 writing comparison

The director now builds a causal treatment before writing spoken cues. The
versioned policy is `config/storytelling_principles.json`; `autonomy/suspense.py`
tracks separate audience/protagonist knowledge, beliefs and the immediate goal
through ordered revelation, decision, consequence and belief-change events.
Every cue has a purpose and a beat. Choices cannot use unknown information or
unstated beliefs; consequences must follow their originating choices. Structural
checks reject premature protected reveals, an unplanted payoff, an unrelated
open mystery, unsupported narrator purposes, broken timing and changed staging.
These are declared information states and intended reveal times, not automatic
semantic understanding or proof of good writing. Actual audio word times remain
in the audio manifest and subtitle files.

`autonomy/screenwriter.py` provides withdrawal and verification strategies for a
delivery trap, plus a borrowed-voice arrival / silent-escape archetype. Selection
uses series context and supported scene grammar, never an Episode 3 number.
New plans serialize their treatment, cast and proposed narrative memory. The
next episode receives prior observations/claims, beliefs and open questions;
a delivery-trap successor explicitly recalls the human-delivery claim. The
existing verified-media transaction still controls whether a proposed end state
becomes canon. This work did not reserve or commit any production episode.
Existing plans and stored checkpoints are not migrated or rewritten.

With an explicitly configured, installed loopback local model, the same
screenwriter sends the complete treatment, canon, policy and fixed cue skeleton
before prose generation. New dialogue then receives one bounded critique/repair
cycle, with identity, protected-line, staging and preliminary speech-budget
checks. A response supplying only legacy radio lines uses the structural offline
realization for multi-voice dialogue. The optional local-model protocol was
exercised with scripted test doubles; no installed creative LLM was run here.
Offline writing is a bounded grammar with finite variations. It does not promise
unlimited original plots or professional editorial quality for arbitrary series.
The compiler uses the new spoken script and treatment in the existing opt-in
cast audio profile. Legacy audio compatibility and production pause remain.

Review sources are `episodes/episode_003_story_a.json` and
`episodes/episode_003_story_b.json`, with corresponding timestamped `.txt` files.
Both preserve the accepted opening and "You're the delivery." They keep the
same physical beginning/end, faceless figure and retained parcel; neither is a
replacement production checkpoint. A attempts cancellation, then refuses a
handoff. B seeks a recipient name, tests the apparent recipient and receives an
answer to her own final question. Narrator passages establish her reasonable
expectation, why silence matters, and when finishing the job gives way to escape.
The planned speech-free reveal holds are 29.3-33.6 seconds (A) and 28.8-31.3 (B).

Actual local audio-only previews, both 45 seconds, are kept in ignored folder
`artifacts/audio_previews/episode3_writing_comparison/`:

| Version | Playable files | Lines | Measured loudness | True peak | Max caption CPS |
| --- | --- | --- | --- | --- | --- |
| A: cancellation | Episode3_A.mp3 / Episode3_A.wav | 11 | -16.04 LUFS | -1.50 dBTP | 20.70 |
| B: verification | Episode3_B.mp3 / Episode3_B.wav | 12 | -16.06 LUFS | -1.50 dBTP | 20.00 |

Both use the existing John/LJ/Norman cast, per-line delivery, original environment
sound, ducking, engine-derived subtitles and no caption fallbacks. All words fit
inside their allotted speech windows, both WAV and MP3 decode to exactly 45
seconds, and the final MP3s decode without errors. Signature- and checksum-based
raw-take reuse preserves identity, text, phrases and delivery controls across cue
indices. Processing revision 2 adds linear peak headroom rather than hard
clipping a transient; completed prior previews are preserved. Audio testing
caught a transient peak failure, an overlong request and captions above 22 CPS;
headroom, cue length, wording and pacing changes resolved them without cutting
spoken words. The repeated pause/phrase and final reveal takes were reused.

Validation: 106 clean-source tests ran outside OneDrive: 105 passed, one skipped
because the optional generated Episode 1 audio fixture is not exported. This
includes 17 new suspense/cache/headroom tests and the existing continuity,
checkpoint, cast and upload safety coverage. The first in-place suite encountered
an intermittent OneDrive WinError 5 on an existing temporary atomic JSON rename;
the independent clean-source run passed. The manual-workflow checker and source
security/deployment scanner passed. Media checks and full comparison receipts are
in `comparison_validation.json` beside the final audio. The prior accepted audio
and Episode 3 Blender scene hashes still match; local story state matches the
preserved seed and the remote autonomy-state checkpoint blob is unchanged.

Remaining review: free TTS pacing/pitch/tremor is not dramatic acting; listening,
pronunciation and editorial approval remain pending. No new visuals were rendered
or retimed to these alternate scripts. The structural checker trusts declared
semantic links and cannot replace human judgment. No cloud run, model download,
paid inference, upload, schedule activation, commit or push was performed.
