# Animation (Blender to Roblox)

## Rig-only scope

For a modeling task that includes an animation-ready rig, first follow [rigs.md](../rigs/rigs.md) and its standard/custom route. Use representative poses or a short diagnostic motion to verify deformation before baking and after importing the rig into Studio. This does not require a full idle/walk/attack set, gameplay code or publication of diagnostic clips. The full clip authoring, inspection and publishing workflow below applies when production animations are part of the task. Custom creatures use anatomy-appropriate skeletons, not automatically R6/R15.

For **R6-like motion on an R15 rig** ("R6 like", "fake R6", "fake R15", "R15 R6 animation", "R6 on R15"), first read [r6-on-r15.md](r6-on-r15.md). A project whose default animations are already R6-like gets R6-like clips too, unless the user says otherwise *(default)*. It defines the six moving joints and nine locked joints, FK and IK that behave like R6's, rigid-limb retargeting, Roblox's default R6 set rebuilt for R15, and motion/preview checks. Use the toolchain below with that joint policy; do not introduce normal articulated R15 knees, elbows or waist movement.

## Roblox characters (R15 / R6)

For **realistic R15 motion written from code**, with no plugin (dump the rig through Studio MCP, bake in Blender, import and audit back), read [r15-motion.md](r15-motion.md).

Load the **`animate-roblox-characters`** skill only for what it adds: moving an authentic rig into Blender and exporting from it (rig import, joint names, export format, Blender-side audits). It costs about 13,000 tokens with its required references, so a clip written in Studio does not load it. Where it differs, this reference wins: 60 FPS rather than its 30 FPS default, and the Studio fallback below when Blender is unavailable. If it is not installed, proceed with the rest of this reference and the Blender rigging/animation skills. Either way, section 4 is the check on the real Roblox rig.

## Authoring workflow: Blender first, Studio fallback

1. **Check Blender MCP first.** Discover the available Blender tools and test Python execution in the connected interactive Blender session. Confirm that the intended rig is accessible; having Blender open or an MCP tool listed is not proof that the connection works.
2. **Attempt to animate in Blender at 60 FPS.** Set `scene.render.fps = 60` and `scene.render.fps_base = 1.0` before keying. Inspect the rig, then author and verify an initial pose or motion batch through MCP. Resolve routine connection, context or rig-mapping errors before abandoning that path; do not skip straight to Studio when Blender authoring is available.
3. **Fall back to Roblox Studio at 60 FPS** if Blender MCP is unavailable, cannot connect to a usable interactive session, or an actual authoring blocker remains after a reasonable repair attempt. State what failed and continue in Studio rather than stopping solely because Blender MCP is missing. Use the actual target rig and retain the same motion brief, joint restrictions and validation requirements. The companion Blender skill supplies rig/export guidance; its Blender-only workflow must not prevent this Studio fallback.
4. **Keep the Studio authoring grid at 60 FPS.** Set the Animation Editor timeline to 60 FPS when using the editor. For scripted KeyframeSequences, place keys at `Keyframe.Time = frame / 60` and audit with `{ Fps = 60 }`. Preserve durations, loop seams and this timebase through import/export. This is the animation authoring rate, not a guarantee of viewport or game rendering speed; a 30 FPS GIF can still preview a 60 FPS clip.

## 1. Non-negotiables

- **Author at 60 FPS** *(default)*: scene at that rate before keying, keys on whole frames, export/import at the same rate.
- **Proper weighted joints.** Normalized weights, at most 4 influences per vertex, no stray weights on distant bones, clean falloff. Test deformation in extreme poses before animating (`blender-character-rigging`).
- **Clean animation.** Readable silhouette, anticipation/overshoot/settle, eased curves, no foot sliding, no jitter or flips, loops whose last frame meets the first, sparse keys rather than a bake of every frame unless needed.
- **A strike is driven by the whole body** *(default)*: a windup (fist or weapon back, hips and chest coiled away, weight back), a short charge (a sink at the top of the coil), a release of about 0.06 s (hips and chest whip through, weight drops forward, the back heel peels) and a dead stop on impact. Fifteen eased punches read as dancing and 36 fast jabs on a still body as shaking arms: speed alone does not make a hit read. Fewer heavy blows beat many light ones; quicken them through a sequence, and switch off follow-through lag and idle sway while they run.
- **Feet meet the ground exactly.** A foot that is meant to touch the ground (stance, landing, stomp, idle) sits on the in-game floor, where the HumanoidRootPart's bottom minus HipHeight puts it (with no Humanoid, `RootHeight` below the root's centre), within 0.05 studs while planted. It never hovers above the floor, and no heel or toe sinks through it. Pose against that floor height, not by eye.

## 2. Route

- R6-like animation on R15, under any of its names: [r6-on-r15.md](r6-on-r15.md) for its joint policy, [r6-ik.md](r6-ik.md) for FK and IK, [r6-default-set.md](r6-default-set.md) for the default clips, then the Roblox character toolchain below.
- Roblox R6/R15 actions (walk, run, idle, attacks, emotes): this reference; `animate-roblox-characters` for Blender rig transfer and export.
- Custom skeletons and creatures: `blender-character-rigging` -> `blender-animation` (actions, NLA, baking control rigs to the export skeleton) -> `blender-export-pipelines`.
- Nothing fitting installed: search `find-skills`, then do it yourself.
- A video of the motion to match: [video.md](../art/video.md); its `burst` gives the timing in frames.

## 3. Export, set up, publish

1. Keep the deform skeleton separate from controls; bake to it for export. Import into Studio as a KeyframeSequence on the actual rig. A rig scripted from `Players:CreateHumanoidModelFromDescription` has AnimationConstraint joints (15, with 14 BallSocketConstraints) and no Motor6D, even before it is parented: forward kinematics that walks Motor6Ds finds nothing ([rigs.md](../rigs/rigs.md)); `R6OnR15.map` and AnimationInspector read both.
2. Set priority (`Core`/`Idle`/`Movement`/`Action`), `Looped`, and `KeyframeMarkers` for gameplay events (hit frames, footsteps, VFX triggers) instead of hardcoded times.
3. To read an existing clip, `Clone` what `KeyframeSequenceProvider:GetKeyframeSequenceAsync` returns before changing it, and never `Destroy` it: it is cached and shared, and destroying it leaves that id empty for the rest of the Studio session (`AnimationClipProvider:GetAnimationClipAsync` still reads it). `Animator:StepAnimations` runs only in Edit.
4. Pass section 4, then publish to the **group that owns the experience** (the project's cloud API key with that group as creator, or Studio publishing to that group; [uploading.md](../safety/uploading.md)). An animation plays only in experiences owned by its creator. Republishing makes a new id.

## 4. Inspect (a clip is not done until it passes)

[scripts/AnimationInspector.luau](../../scripts/AnimationInspector.luau) poses a scriptless copy of the rig at exact times in **Edit** mode and measures it by forward kinematics (Motor6D, AnimationConstraint or Bones), so results do not depend on frame rate or capture latency, and the rig itself is never changed. Load it as SKILL.md (Scripts) describes. Calibrated in Studio: Roblox's own R15 idle, walk, run and point clips give 0 errors (a few warnings, such as off-grid keys and a skating run), and each planted defect is caught.

1. **Audit (instant, text):** `return Anim.audit(rig, clip, { Markers = { "Hit" } }).Text`. `clip` is the editable KeyframeSequence (preferred: keys and markers are readable), an Animation or an id. Options: `Fps` (key grid, default 60), `Feet`, `Tip` (default `RightGripAttachment`), `Markers` (ones the clip must have; the first is synced to the tip), `Ignore` (rule names), `Looped`, `Locomotion` (`true` measures backward stance phases, `false` enforces stationary slide checks; omitted: infer), `Hinges` (custom `{ Upper, Lower, Bend }`, hinged on the upper part's X axis: `"back"` flexes with a negative turn like R15 knees, `"front"` with a positive one like elbows). Fix every ERROR; judge each WARN. The `Motion` sparkline shows timing: wind-up, peak, holds, with `^` under markers.

   | Rule | Means | Fix |
   |---|---|---|
   | `rest-only` | the rig never left its rest pose: the clip did not apply, so every other result is void (cannot be ignored) | check the id, its owner and the pose names |
   | `unmatched` | error: the clip moves none of the rig's parts; warn: posed names the rig lacks, whose motion is dropped (fine for extra finger or face bones) | rename the poses to the rig's parts |
   | `pop` | one frame turns 15°+ and 4x more than every frame within two of it, or 45°+ in one 60 fps frame (or jumps 0.4+ studs) | an Euler flip or a missing key: re-key with quaternions or add a key. A strike hidden under flash frames still gives its joints 4+ frames with an out ease and moves only the root in one frame: snaps over 2-6 frames popped by 45-87°, and the same poses over 4-16 frames passed and still finished inside the flash |
   | `seam`, `seam-speed` | a loop's last frame misses the first (over 1° / 0.05 studs); with smooth easing, its speed changes across the seam | `closeLoop(sequence)`; match the curve tangents |
   | `slide` | a planted foot drifts over 0.05 studs in a stationary clip | lock planted feet (IK) |
   | `stride` | in-place locomotion: a planted foot's backward speed varies over 25% | keep contact speed even; play the clip at `WalkSpeed / GroundSpeed` (in the report) |
   | `float` | a planted foot hovers over 0.05 studs above the floor, or a still foot rests 0.15 to 0.6 studs up without touching; error when still feet never touch the floor at all | lower the root or the leg onto the floor; `Ignore` it only for a foot lifted or a clip airborne on purpose |
   | `clip` | a planted foot sinks over 0.05 studs into the floor, or its toe or heel dips over 0.1 (measured at the sole's `FootAttachment` and the corners of a sole 0.35 of the foot's length and 0.45 of its width from it, so a foot tipped onto its edge counts as touching) | raise it; pivot rolls on the toe or heel, not the ankle |
   | `end-offset` | a one-shot ends with the body over 0.5 studs from its start; the root does not follow, so it snaps back | move the character in code, or `Ignore` it for death and knockback clips |
   | `hyperextend` | a knee or elbow bends over 5° the wrong way | fix the pole target or IK |
   | `grid` | keys between frames | `snapKeys(sequence, fps)` |
   | `easing` | keys over 3 frames apart and mostly Linear: mechanical | Cubic/CubicV2 on key poses, add breakdowns |
   | `marker`, `hit-sync` | a required marker is missing, or sits over 0.1 s from the tip's fastest moment, so the effect and damage land early or late | `setMarker(sequence, "Hit", report.Tip.Fastest)` |

2. **Look (one capture):** `return Anim.sheet(rig, clip, options).Legend`, then `screen_capture` with the `camera_position` and `look_at_position` the legend gives. The sheet narrows the lens but never moves the editor camera, because a parked camera made captures come back blank. It yields 0.75 s for redraw before returning (`CaptureDelay`, bounded 0..5 s); recapture if a slow viewport still shows the preceding sheet. The rows show the side view (line of action, lean, arcs in depth) and the front view (balance, symmetry, width). The columns are the start, end, markers, peak and stillest key poses, and the last column is the peak pose with paths from blue (start) to red (end). A planted foot is a black dot that stays one dot; a smear means it slides. The legend maps each column to its time. Options: `Times`, `Count` (8), `Views` (`side`, `front`, `back`, `three`), `Trails`, `Dark`, `Fov`. Judge whether the poses read as silhouettes, the action has anticipation, the arcs are smooth, and nothing clips through the body.
3. **Repair and repeat:** `closeLoop`, `snapKeys` and `setMarker` edit the KeyframeSequence in place; bigger fixes go back to Blender. Audit again until there are 0 errors and look again, then publish.
4. **Clean up:** `Anim.clear()` removes the sheet and restores the camera's field of view.

A clip that passes can drive VFX timing: stage it on the real rig in place of the caster sphere ([vfx.md](../art/vfx.md) section 8). Playing clips in game (loading tracks once, priorities, who plays them): [gameplay.md](../code/gameplay.md).
