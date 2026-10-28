# Animation (Blender to Roblox)

## Roblox characters (R15 / R6): check for the skill first

When the task animates a Roblox character, first look for the **`animate-roblox-characters`** skill (check the available-skills list; use `find-skills` if unsure) and load it for the R15/R6 details: rig import, joint names, export format and Blender-side audits. If it is not available, proceed with the rest of this reference and the Blender rigging/animation skills. Either way, section 4 is the check on the real Roblox rig.

## 1. Non-negotiables

- **Author at 60 FPS** *(default)*: scene at that rate before keying, keys on whole frames, export/import at the same rate.
- **Proper weighted joints.** Normalized weights, at most 4 influences per vertex, no stray weights on distant bones, clean falloff. Test deformation in extreme poses before animating (`blender-character-rigging`).
- **Clean animation.** Readable silhouette, anticipation/overshoot/settle, eased curves, no foot sliding, no jitter or flips, loops whose last frame meets the first, sparse keys rather than a bake of every frame unless needed.
- **Feet meet the ground exactly.** A foot that is meant to touch the ground (stance, landing, stomp, idle) sits on the in-game floor, where the HumanoidRootPart's bottom minus HipHeight puts it, within 0.05 studs while planted. It never hovers above the floor, and no heel or toe sinks through it. Pose against that floor height, not by eye.

## 2. Route

- Roblox R6/R15 actions (walk, run, idle, attacks, emotes): `animate-roblox-characters` when available.
- Custom skeletons and creatures: `blender-character-rigging` -> `blender-animation` (actions, NLA, baking control rigs to the export skeleton) -> `blender-export-pipelines`.
- Nothing fitting installed: search `find-skills`, then do it yourself.

## 3. Export, set up, publish

1. Keep the deform skeleton separate from controls; bake to it for export. Import into Studio as a KeyframeSequence on the actual rig.
2. Set priority (`Core`/`Idle`/`Movement`/`Action`), `Looped`, and `KeyframeMarkers` for gameplay events (hit frames, footsteps, VFX triggers) instead of hardcoded times.
3. Pass section 4, then publish to the **group that owns the experience** (the group key, or Studio publishing to that group; [assets.md](assets.md), Uploading). An animation plays only in experiences owned by its creator. Republishing makes a new id.

## 4. Inspect (a clip is not done until it passes)

[scripts/AnimationInspector.luau](../scripts/AnimationInspector.luau) poses a scriptless copy of the rig at exact times in **Edit** mode and measures it by forward kinematics (Motor6D, AnimationConstraint or Bones), so results do not depend on frame rate or capture latency, and the rig itself is never changed. Load it as SKILL.md (Scripts) describes. Calibrated in Studio: Roblox's own R15 idle, walk, run and point clips give 0 errors (a few warnings, such as off-grid keys and a skating run), and each planted defect is caught.

1. **Audit (instant, text):** `return Anim.audit(rig, clip, { Markers = { "Hit" } }).Text`. `clip` is the editable KeyframeSequence (preferred: keys and markers are readable), an Animation or an id. Options: `Fps` (key grid, default 60), `Feet`, `Tip` (default `RightGripAttachment`), `Markers` (ones the clip must have; the first is synced to the tip), `Ignore` (rule names), `Looped`, `Hinges` (custom `{ Upper, Lower, Bend }`, hinged on the upper part's X axis: `"back"` flexes with a negative turn like R15 knees, `"front"` with a positive one like elbows). Fix every ERROR; judge each WARN. The `Motion` sparkline shows timing: wind-up, peak, holds, with `^` under markers.

   | Rule | Means | Fix |
   |---|---|---|
   | `rest-only` | the rig never left its rest pose: the clip did not apply, so every other result is void (cannot be ignored) | check the id, its owner and the pose names |
   | `unmatched` | error: the clip moves none of the rig's parts; warn: posed names the rig lacks, whose motion is dropped (fine for extra finger or face bones) | rename the poses to the rig's parts |
   | `pop` | one frame turns 15°+ and 4x more than every frame within two of it, or 45°+ in one 60 fps frame (or jumps 0.4+ studs) | an Euler flip or a missing key: re-key with quaternions or add a key |
   | `seam`, `seam-speed` | a loop's last frame misses the first (over 1° / 0.05 studs); with smooth easing, its speed changes across the seam | `closeLoop(sequence)`; match the curve tangents |
   | `slide` | a planted foot drifts over 0.05 studs in a stationary clip | lock planted feet (IK) |
   | `stride` | in-place locomotion: a planted foot's backward speed varies over 25% | keep contact speed even; play the clip at `WalkSpeed / GroundSpeed` (in the report) |
   | `float` | a planted foot hovers over 0.05 studs above the floor, or a still foot rests 0.15 to 0.6 studs up without touching; error when still feet never touch the floor at all | lower the root or the leg onto the floor; `Ignore` it only for a foot lifted or a clip airborne on purpose |
   | `clip` | a planted foot sinks over 0.05 studs into the floor, or its toe or heel dips over 0.1 (measured at the sole's `FootAttachment` and toe and heel points) | raise it; pivot rolls on the toe or heel, not the ankle |
   | `end-offset` | a one-shot ends with the body over 0.5 studs from its start; the root does not follow, so it snaps back | move the character in code, or `Ignore` it for death and knockback clips |
   | `hyperextend` | a knee or elbow bends over 5° the wrong way | fix the pole target or IK |
   | `grid` | keys between frames | `snapKeys(sequence, fps)` |
   | `easing` | keys over 3 frames apart and mostly Linear: mechanical | Cubic/CubicV2 on key poses, add breakdowns |
   | `marker`, `hit-sync` | a required marker is missing, or sits over 0.1 s from the tip's fastest moment, so the effect and damage land early or late | `setMarker(sequence, "Hit", report.Tip.Fastest)` |

2. **Look (one capture):** `return Anim.sheet(rig, clip, options).Legend`, then `screen_capture` with the `camera_position` and `look_at_position` the legend gives. The sheet narrows the lens but never moves the editor camera, because a parked camera made captures come back blank. The rows show the side view (line of action, lean, arcs in depth) and the front view (balance, symmetry, width). The columns are the start, end, markers, peak and stillest key poses, and the last column is the peak pose with paths from blue (start) to red (end). A planted foot is a black dot that stays one dot; a smear means it slides. The legend maps each column to its time. Options: `Times`, `Count` (8), `Views` (`side`, `front`, `back`, `three`), `Trails`, `Dark`, `Fov`. Judge whether the poses read as silhouettes, the action has anticipation, the arcs are smooth, and nothing clips through the body.
3. **Repair and repeat:** `closeLoop`, `snapKeys` and `setMarker` edit the KeyframeSequence in place; bigger fixes go back to Blender. Audit again until there are 0 errors and look again, then publish.
4. **Clean up:** `Anim.clear()` removes the sheet and restores the camera's field of view.

A clip that passes can drive VFX timing: stage it on the real rig in place of the caster sphere ([vfx.md](vfx.md) section 8).
