# Episode 3: quality first, automation second

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
