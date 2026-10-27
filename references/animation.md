# Animation (Blender to Roblox)

## Roblox characters (R15 / R6): check for the skill first

When the task animates a Roblox character, first look for the **`animate-roblox-characters`** skill (check the available-skills list; use `find-skills` if unsure) and load it for the R15/R6 details: rig import, joint names, export format and Studio validation. If it is not available, proceed normally with the rest of this reference and the Blender rigging/animation skills.

## Non-negotiables

- **Author at 60 FPS.** Set the Blender scene to 60 fps before keying, keep keys on whole frames, and export/import at 60 so playback is smooth.
- **Proper weighted joints.** Skin with normalized weights, at most 4 influences per vertex, no stray weights on distant bones, and clean falloff at joints. Test deformation in extreme poses before animating. Use `blender-character-rigging` (heat/proxy skinning, weight rules, deformation stress tests); if no skill helps, build and verify it yourself to the same standard.
- **Clean animation.** Readable silhouette, anticipation/overshoot/settle, easing via curves (Graph Editor), no foot sliding, no jitter or gimbal flips, loops that match first and last frames, sparse keys (delete redundant keys rather than baking every frame unless needed).

## Route

- Roblox R6/R15 character actions (walk, run, idle, attacks, emotes): `animate-roblox-characters` when available (Studio-derived rigs, `.rbxanim`/FBX export, optional Studio playback validation).
- Custom skeletons and creatures: `blender-character-rigging` -> `blender-animation` (actions, NLA, baking control rigs to the export skeleton) -> `blender-export-pipelines`.
- Nothing fitting installed: search `find-skills`, then do it yourself.

## Export and verify

1. Keep the deform skeleton separate from controls; bake to it for export.
2. Import into Studio and play the animation in Edit mode on the actual rig; compare against the Blender preview.
3. Set priority (`Core`/`Idle`/`Movement`/`Action`), `Looped`, and add `KeyframeMarkers` for gameplay events (hit frames, footsteps, VFX triggers) rather than hardcoding times.
4. Check for foot sliding, pops at loop points, and mesh stretching at extremes. Report anything unverified.
