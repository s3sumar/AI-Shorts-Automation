# Model-authored creative direction

November 26 update: see AUTOMATION_STATUS.md for the now-working development media
service, three blockout scene adapters and durable CreativeStore. The dated sections
below retain the November 21 writing milestone; claims of an empty asset registry
or missing development-media commits are superseded by the November 26 update.
Live AI and YouTube credentials are still absent.


Status: implemented locally; hosted creative generation is blocked by a missing
`OPENROUTER_API_KEY`. No inference, rendering, production reservation, checkpoint
advance, upload, schedule activation, commit or push was performed for this work.
Provider research and the anonymous public model catalogue were checked on
2026-11-21. The three review scripts are assistant-authored originals, not outputs
from a live provider test. Protocol test doubles do not establish creative quality.

## What changed

The old `autonomy/screenwriter.py` selects an arrival/escape plot and cue skeleton
before asking a local model to realize prose. It remains available for compatibility.
The new `autonomy/creative.py` path has no concept list, plot realization, fixed
setting, dialogue template or predetermined ending. The writer model authors a
series bible, characters, central conflict, writer-only mysteries and a three-to-eight
part season arc. It then authors the episode events, dialogue, information-state
treatment and shot plan from that bible and the accepted input memory.

A separate configured critic model evaluates hook, clarity, character logic,
dialogue, escalation, originality, cliffhanger, visual storytelling and continuity.
Every score needs evidence and every issue needs a location and actionable revision.
All scores must reach 4/5 with no outstanding issues. Structural failures or a weak
critique cause at most two replacement drafts and fresh critique. Failure stops
review; it never silently uses the old procedural generator. Model approval is
editorial evidence, not a guarantee or a substitute for human judgment.

`autonomy/creative_contract.py` validates stable identities, 45-second time budgets,
dialogue roles/emotions/phrasing, world facts versus claims, initial audience and
character knowledge/beliefs/goals, information acquisition, choices/consequences,
protected late reveals, season resolutions and complete timed visual coverage.
Counterpart knowledge is also tracked so the second character is not omniscient.
Entire dialogue repeats are rejected. Statements from the past cannot silently be
rewritten; writer-only secrets have scheduled release episodes. A model can still
mislabel a semantic fact or paraphrase a secret; the critic and human review must
catch errors beyond the declared structure.

Proposed memory preserves observations/claims, audience knowledge and beliefs,
character knowledge/beliefs/goals, unresolved mysteries, episode summaries,
script hashes and the frozen three-voice cast. A complete season can request a
new model-authored series rather than selecting a fixed concept. Accepted memory
can be packed into a checksum-protected portable checkpoint. Review writes only
`proposed_memory_NOT_COMMITTED.json`; it has no authority to update production.
There is intentionally no new automatic production-memory commit path yet: that
requires registered worlds, measured audio, verified media and the same explicit
integration/review discipline as the working production ledger.

The original `state/story.sqlite3` and durable `checkpoint/story.json` remain
separate and unchanged. Creative series use the `creative_` namespace. Optional
read-only recovery uses `checkpoint/creative/<creative_id>.json` on the existing
`autonomy-state` branch, and stops on missing/corrupt state. No such new branch
checkpoint was installed during this task; an accepted input must be seeded by
an approved deployment before cloud continuation of that series can be tested.

## Provider assessment

| Option | Unattended Actions suitability | Cost and practical constraints | Decision |
| --- | --- | --- | --- |
| OpenRouter pinned free models | Standard HTTPS calls with one repository secret; no laptop or GPU | Free variants are rate-limited (normally 50 requests/day before funded-account increases). Availability can change. | Implemented free-only adapter. |
| Gemini 3.8 Flash | Hosted API with an AI Studio key; no laptop | Official pricing lists a free tier. Paid standard rates through 2026-12-31 are $0.75/M input and $3.75/M output including thinking. Account quota and billing tier matter. | Strong alternative to evaluate with a key; adapter not implemented. |
| Groq GPT-OSS 120B / Qwen3.8 27B | Hosted API with a Groq key | Published free limits include 8K tokens/minute for these models; the full writing contract plus a long structured draft may need compact/chunked requests. | Candidate for a later measured comparison; adapter not implemented. |
| Ollama on a laptop | Requires that host to remain on | No inference fee, but cannot meet the laptop-off requirement. Large capable models are impractical on standard CPU Actions runners. | Existing local adapter preserved; not the cloud recommendation. |
| GitHub Models | Unavailable | GitHub retired the catalogue and inference service on 2026-07-30. | Do not deploy older GitHub Models recipes. |

Sources: [OpenRouter free-model terms](https://openrouter.ai/collections/free-models/),
[provider price routing](https://openrouter.ai/docs/guides/routing/provider-selection),
[Gemini pricing](https://aistudio.google.com/docs/pricing),
[Groq limits](https://console.groq.com/docs/rate-limits),
[GitHub Models retirement](https://github.blog/changelog/2026-07-30-github-models-is-now-retired/).

The checked public catalogue currently lists the configured writer
`google/gemma-4-31b-it:free` (262,144 context, JSON response support) and critic
`baidu/ernie-5.5-flash-preview:free` (1,024,000 context, JSON support), both with
zero prompt/completion pricing. They are capable-model candidates, not measured
creative-quality winners. Selecting two models avoids a writer merely endorsing
its own output, but does not guarantee critical independence or good taste.

`autonomy/creative_provider.py` rechecks the pinned model catalogue before every
inference, rejects nonzero prices and non-free IDs, sends maximum prompt,
completion and request prices of zero, disables provider fallback, requires JSON,
checks response model/finish/cost, and caps the entire process at 16 inference
attempts and 10,000 output tokens per response. A retry after 429/502/503 is bounded
and consumes the request budget. Authentication bodies/headers are not logged;
receipts record stage, model, hashes, elapsed time and usage. A price or capacity
change stops the run instead of selecting a paid replacement. Free quota is
shared with other account usage; failed attempts can count against it.

For scale only, at the cited Gemini paid rates, an entire multi-call writing job
using a combined 20K input and 6K output tokens would cost about $0.038, excluding
any extra tools, retries or other costs. This is arithmetic, not a measured job
cost, and does not authorize or enable billing. No paid adapter is enabled.

## Pipeline and cloud entry points

The new production-module entry point is an isolated review lane:

```powershell
python -m autonomy.pipeline creative-review --creative-brief "An original historical conspiracy about a costly act of loyalty" --review-out artifacts/creative_review/my_first_run
```

Set `OPENROUTER_API_KEY` locally through your own environment, or add it as a
GitHub Actions repository secret. Do not put a credential in a JSON file, commit,
workflow input, chat or script. No API keys were available in this session, and
no application/Git credentials were repurposed for inference.

For continuation, supply `--creative-bible` and `--creative-memory` containing
accepted state. Reusing an output folder is refused. The separate CLI
`tools/creative_director.py` provides equivalent `--bible`/`--memory` options.
Outputs include the bible, full episode, editorial audit, provider receipts,
unchanged input checkpoint, proposed memory, readable script, audio score and
Blender storyboard. Failures retain a status report and stop with exit code 2.

`.github/workflows/creative_writing_review.yml` is manual-only, read-only repository
access, Ubuntu/Python 3.13, no Blender/MCP/GPU, a 25-minute job limit and downloadable
review artifacts. It can recover an explicitly selected existing creative series
from the accepted state branch. It cannot write checkpoints or upload videos.
No extra hosted service is needed beyond the configured inference API and GitHub
Actions allowance. The workflow has not been pushed or executed; Actions quota
and real inference behavior still need a first authorized cloud acceptance test.

## Render/audio integration and remaining limits

`autonomy/creative_compile.py` emits real `soundstage.prepare`-compatible cast
scores, including line-level text, emotional delivery, phrase pauses and explicit
sound events. The same model identities stay frozen in creative memory. New
curious/hopeful/urgent/awed/sad/amused delivery profiles support genres beyond
fear; existing voice models and delivery profiles are preserved. These are bounded
pacing/pitch/gain controls, not trained human acting.

The companion storyboard carries 24 FPS, 720x1280 framing, connected shots,
camera moves, character/prop actions, narrative intent and asset requirements.
It is structured visual intent, not arbitrary Blender code or a tested new-world
animation compiler. `config/creative_assets.json` is deliberately empty. Missing
worlds/characters/props keep rendering blocked; a medieval prison or fantasy town
is never silently rendered as an elevator. New environment assets and action/rig
adapters remain to be built and verified. Actual speech durations, subtitle
alignment, visual continuity and production quality must pass after synthesis
and rendering are explicitly authorized. The existing lift pipeline is preserved.

## Original 45-second review scripts and critical comparison

All three are source review examples in `examples/creative/`, with timestamped
scripts, complete bibles/season arcs, structured episodes, input-memory fixtures
and provenance notes. They never enter the runtime model prompt or a fallback.
Timings are writing budgets; no audio or animation was generated for these scripts.

1. **The King's Mercy ? historical conspiracy.** Ivo buys his sister a pardon,
   finds an empty cell, then breaks a royal seal to discover the destination.
   "She's been sold. The ship leaves tonight." is both an answer and a new urgent
   objective. Strongest of the three: the audience understands his goal, his risk
   and the significance of the discovery with very little world explanation.
   Sera must visibly choose to help rather than simply recite records. The word
   "bought" should be staged as a corrupt official fee/bribe, not a modern legal
   service; the watch bell must clearly follow the broken seal.
2. **The Mapmaker's Rain ? community fantasy.** Nia brings water to dry wells,
   discovers that a river destroys the bridge, and fails to erase the flood.
   New handwriting points toward her home: "That's my mother's handwriting."
   Best emotional/visual potential. Her earlier loss to a river gives the rescue
   choice meaning. The mother's pen/map relationship and the effect of erasing
   must be legible on screen; otherwise the ending risks looking like an arbitrary
   second magical rule. Her recognition is evidence, not proof her mother is alive.
3. **The Last Greenhouse ? ecological science fiction.** Mara delays burning the
   last tree, tests its synchronized respiration and disconnects a suspected
   sensor link. Her body still responds. "It isn't copying you. It's breathing
   for you." reframes the tree from threat to possible life support. Strong bodily
   stakes, but the highest explanatory burden and the weakest causal proof of
   the three. Habitat's final line is tagged as a claim, not established medical
   truth. The difference between a suit data link and a breathing supply must be
   explicit in the visual design; otherwise the experiment will feel inconclusive.

These are this assistant's editorial judgments, not a live provider benchmark or
human listening approval. A real writer/critic run must still prove that the new
path can deliver equally clear, fresh results without these authored examples.

## Actual verification

The public free-model catalogue request succeeded and verified the selected IDs,
zero prices, context and JSON support. Both direct and production-module creative
CLI attempts stopped before inference because `OPENROUTER_API_KEY` was absent:
zero hosted creative requests, zero paid calls. There is no successful live model
script or real model critique to report. Detailed statuses and the catalogue are
kept locally under `artifacts/creative_director_review/`.

Offline tests exercise generation/revision contracts, two-model routing,
knowledge/goal/secret continuity, voice identity, proposed memory and checksum
recovery, stale/replayed episodes, timing/shot coverage, failed critiques,
season rollover, free-only price guards, bounded retries, response truncation,
credential redaction, and isolation from the production ledger. Those tests use
explicit doubles and source fixtures. See `clean_source_tests.log` in that local
review folder for the full regression result. Required next configuration is the
free-provider API key; deployment also requires approval to push this source and
manually run the review workflow. Production/new-world rendering remains gated.

Final clean-source regression: 138 tests ran; 137 passed and one optional generated-audio fixture was skipped. All 32 creative tests also passed alone in a fresh source export with no artifacts/models/tools, matching the new cloud workflow test selection. Source/deployment scan passed with 156 candidate files and no detected secrets or generated media. Existing production-workflow checks passed. File hashes and local/remote production checkpoint checks passed. Casting for new character identities still needs review; the initial bank remains the existing three free voices.
