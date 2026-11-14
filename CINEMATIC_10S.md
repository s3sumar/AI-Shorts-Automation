# Elevator: Floor -1

The live Blender scene was backed up before editing:
`artifacts/backups/first_scene_backup_20261109_221732.blend` (185,737 bytes).
The original `C:/Users/Shakeel/Documents/AI_Shorts/first_scene.blend` was not saved over.

Output: `artifacts/cinematic_elevator_10s/elevator_suspense_10s.blend`.
240 frames at 24 FPS; 540 x 960 portrait; active camera `Cinematic portrait camera`.
The output is open in the MCP-connected Blender at frame 1.

| Frames | Story beat |
| --- | --- |
| 1–46 | Cold blue arrival, floor 13, slow camera dolly |
| 47–93 | Short power failures, fluorescent emission and light color drift toward red |
| 104 | Floor indicator switches discretely to -1 |
| 116–144 | Independent head turn and raised eyebrows |
| 155–210 | Doors slide into pockets, revealing the dark figure in a recessed corridor |
| 178–216 | Passenger recoils and raises arms |
| 210–240 | Hold the silhouette reveal as the camera eases forward |

`cinematic_elevator_10s.py` upgrades the original scene (or its backup), with
15 named actions retained using fake users. Existing action slots remain associated
with their objects/data; the actions can be retimed or duplicated in Blender.
The builder requires the original object names and is intentionally guarded against
running again on an already upgraded scene or overwriting its output.
It is a separate builder from the existing episode pipeline; existing workflows,
episode configurations and uncommitted changes were preserved.

CPU rendering uses Cycles, 24 samples, denoising, four maximum bounces, no volumes,
no simulations and no external assets. The steel has subtle procedural bump,
beveled frame details and a reflective graphite floor. Depth of field is disabled
to keep the indicator and distant silhouette readable at low sample counts.

Validation was run in a separate background Blender **5.2.3 LTS** process, reopening
the saved file, with six CPU threads:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background 'artifacts/cinematic_elevator_10s/elevator_suspense_10s.blend' --threads 6 --python-exit-code 1 --python tests/validate_cinematic_10s.py -- --render-previews
```

Exit code: **0**. All checks passed. Every frame was evaluated for finite transforms,
stable active camera, exact display visibility and camera framing of the head and
indicator. Checks also cover blue/intermediate/red lighting, the power failure,
head independence, recoil, arm reaction, door travel and camera continuity.
Camera rays hit the closed door at frame 1 and the silhouette hood at frame 240.
The largest per-frame camera movement was 0.00634 scene units.

Four actual CPU Cycles PNG renders were visually reviewed:

| Frame | Preview | Seconds |
| --- | --- | --- |
| 1 | `preview_0001.png` | 8.110 |
| 83 | `preview_0083.png` | 7.682 |
| 144 | `preview_0144.png` | 3.812 |
| 240 | `preview_0240.png` | 7.087 |

Previews are 270 x 480 at 16 samples. JSON evidence is in
`artifacts/cinematic_elevator_10s/validation.json`. The preview process did not
save its lower render settings into the final blend; live inspection confirmed
the final file uses CPU Cycles, 24 samples and 100% resolution.

Limitations: the complete 240-frame sequence has not been rendered or encoded;
no sound, music or final editing pass is included. Cloud execution and full-resolution
render time have not been tested. Low sample counts may produce temporal denoising
variation or reflection noise. The retained character and newly modeled figure are
simple stylized meshes, not production character rigs. The corridor recess is a
stylized cool backlight rather than volumetric fog. No GitHub push was performed.
