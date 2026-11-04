# Animate R15 Like R6

"R6 like", "R6-style", "fake R6", "fake R15", "R15 R6 animation" and "R6 on R15" all mean this: the rig stays R15, and it moves the way an R6 does. Solving a limb to a target: [r6-ik.md](r6-ik.md). Roblox's own default clips: [r6-default-set.md](r6-default-set.md).

Keep the actual R15 character, hierarchy and body proportions. Make each arm and leg move as one rigid block by restricting animation to the six joints below, turning about R6's pivots. Do not substitute an R6 model or merge the visible body into six blocks.

Two helpers carry this, both speaking R6's language, with the same pivots:

- **Studio:** [scripts/R6OnR15.luau](../../scripts/R6OnR15.luau): FK, IK, clips, retargeting, checks (`--@use R6OnR15`).
- **Blender:** [scripts/r6_on_r15.py](../../scripts/r6_on_r15.py): FK and IK controls on an R15 armature, from `HttpService:JSONEncode(R6OnR15.dump(R6OnR15.map(rig)))`.

## Authoring workflow

Check for Blender MCP and test the live connection first. Attempt to author and verify the animation in Blender at **60 FPS** (`scene.render.fps = 60`, `scene.render.fps_base = 1.0`) before falling back to Roblox Studio. Repair routine connection/context errors where possible; if Blender MCP is unavailable or a real authoring blocker remains, explain the reason and continue in **Studio at 60 FPS** with the same restricted-joint policy. Do not stop solely because Blender MCP is missing.

In Studio, use a 60 FPS Animation Editor timeline or scripted keys at `Keyframe.Time = frame / 60`, then audit with `{ Fps = 60 }`. Follow the shared [Blender-first workflow](animation.md#authoring-workflow-blender-first-studio-fallback) for connection checks and fallback details. Preview GIF frame rate is independent of the 60 FPS authoring timebase.

Retargeting an existing R6 clip starts in Studio whichever path you author in: the source is there, and `retarget` reads it from the engine. `retarget`, `defaults` and `verify` step the engine by hand, which Studio allows only in **Edit**; `map`, `fk`, `reach`, `plant`, `settle` and `world` are plain math and work anywhere.

## Joint policy

Discover the target's real joints, controls, rest frames and forward direction before keying. These are standard R15 **child part/bone names**, not guaranteed control names; map them to the imported rig's controls or Motor6D/AnimationConstraint joints. A generated R15 may use AnimationConstraints; `R6OnR15.map` reads either.

| R6 part (its pose's name) | Animated R15 child | Parent |
|---|---|---|
| `Torso` (root joint) | `LowerTorso` | `HumanoidRootPart` |
| `Head` (neck) | `Head` | `UpperTorso` |
| `Left Arm`, `Right Arm` (shoulders) | `LeftUpperArm`, `RightUpperArm` | `UpperTorso` |
| `Left Leg`, `Right Leg` (hips) | `LeftUpperLeg`, `RightUpperLeg` | `LowerTorso` |

Keep these nine joints at their rest-relative **identity transform**:

- Waist: `UpperTorso`.
- Elbows/wrists: `LeftLowerArm`, `LeftHand`, `RightLowerArm`, `RightHand`.
- Knees/ankles: `LeftLowerLeg`, `LeftFoot`, `RightLowerLeg`, `RightFoot`.

Use zero pose translation, identity pose rotation and unit scale on locked joints, preserving their imported rest matrices and C0/C1. Do not reset their rest orientations or reparent them. Keep `HumanoidRootPart` stationary for in-place clips; character travel and jump height come from game movement or a separately identified preview mover.

Animate the mapped controls/pose bones, never the meshes. Do not unlock a knee or elbow to solve a posing problem.

Key the locks in every clip that moves their limb: omitting a track does not hold a joint when another animation blends underneath. An identity key at a clip's first and last keys holds it throughout; the waist has one at every key, because the arms' poses hang from it. Leave limbs a clip does not touch unkeyed, so what plays beneath keeps moving them, as R6's `toolnone` does over a walk. Poses that only carry the tree down to a limb have `Weight` 0 and override nothing. `R6OnR15.clip` and `retarget` do all of this.

## R6's pivots

R6 and R15 joints are not in the same place, so copying R6's rotations onto R15's joints gives the wrong motion. On a default R15 a raised hand lands about 0.6 studs too high, and a spread leg lifts its foot off the floor, because:

| R6 joint | Where R6 turns the block | The R15 joint |
|---|---|---|
| Root | the torso's centre | below the lower torso |
| Neck | the head's underside | about the same place |
| Shoulder | the arm's inner face, a quarter of the way down | near the top of the arm |
| Hip | the leg's **outer** face, at the torso's underside | the leg's centre |

`R6OnR15.map` measures these on the rig in front of it, and each R15 Transform is the same turn about that point (`toR15`, `fromR15`), so the R15 joint also slides a little as it turns. This is deliberate: a shoulder or hip key with a small translation is what R6's pivot looks like on an R15 joint. Slides are scaled by the limb's length, and the torso's by the legs', so a crouch that keeps R6's feet down keeps these down.

## FK

A pose is `{ [R6 part] = R6 Transform }`: the same numbers an R6 clip holds, so R6 knowledge carries over. On a shoulder or hip, turning about Z swings the limb forward (positive on the right side, negative on the left). The root joint's Z points up the body, so `CFrame.new(0, 0, -0.5)` lowers the torso.

```lua
local map = R6OnR15.map(rig)
local raise = R6OnR15.clip(map, {
	{ Frame = 0, Pose = { ["Right Arm"] = CFrame.identity } },
	{ Frame = 18, Pose = { ["Right Arm"] = CFrame.Angles(0, 0, math.rad(90)) }, Style = Enum.PoseEasingStyle.Cubic },
}, { Name = "raise", Priority = Enum.AnimationPriority.Action, Parent = game.ServerStorage })
```

**A pose that touches or points at something is IK, not FK:** a hand at the chin, on the chest or on a prop, or an arm aimed at a target. Author the point and let `R6OnR15.reach(map, limb, point, { Torso })` find the turn ([r6-ik.md](r6-ik.md)); three tries of guessed angles left a hand beside the face and an aimed arm 25 degrees off, and `reach` placed both first time.

Rotation normally supplies the motion. A translation slides the whole rigid block, which is how R6 clips imitate a bend: R6's climb slides its legs 1.5 studs. Sparse keys interpolate the R15 joint, so a limb turning far between two keys strays from R6's arc by up to about 0.1 studs; add a key where that shows. `retarget` does so by itself.

## Shape the motion

Inspect supplied frames/video ([video.md](../art/video.md)) and the existing animation family before inventing motion. Separate torso yaw, torso pitch and shoulder arcs: a circular arm gesture does not imply a body spin. Keep jump/fall bodies upright unless the reference or request calls for a tilt or turn.

- **Idle:** favor a slow weight shift, small shoulder/head lag and minimal vertical bounce. Keep both feet down unless a fidget is requested. When smoothing an approved loop, remove the unwanted accent without replacing the whole motion.
- **Walk/run:** use hip-driven leg pendulums and opposed shoulder swings, with smaller torso/head counter-motion. Reduce vertical amplitude and abrupt acceleration when asked for smoother motion. A forward run posture comes from the root/whole torso, with a partial head counter-tilt to keep looking ahead; keep the waist locked.
- **Jump:** use a compact forward-and-outward shoulder arc when that is what the reference shows. Do not turn a small circular sweep into an overhead 360-degree windmill. Review hand paths and total span from the front and side.
- **Fall:** follow the reference's held or alternating shoulder motion rather than automatically spreading both arms into a T. Keep it distinct from a new jump or body spin.
- **Held poses** (a card pose, a victory stance): plant every key's feet where the final pose puts them (`plant`), anticipation keys included, and breathe with the head only. Settling each key on its own slid the feet 0.5 to 1.4 studs, and a torso breath lifted a planted foot; planted, slides fell to 0.11 studs or less.

New motion uses sparse, deliberately eased Bezier authoring curves with controlled overlap. Loops need matching endpoint poses **and tangents**. Retain a duplicate closing key for checking/export when needed, but omit it from rendered loop playback.

## Contacts and retargeting

Calibrate studs against the actual imported rig. Work through its joint frames: child world pose = parent world pose × C0 × animated transform × inverse(C1). Do not copy Euler angles or part-center offsets between R6 and R15 without accounting for their different pivots and limb proportions: `toR15` does this.

When changing torso lean or bounce on an approved gait, preserve the feet's world paths by solving the hips in the new torso (`reach` or `plant` with `Torso`). Lock the lower-leg/foot joints throughout. A shared root-height solve seats only the lowest foot; a slow idle may need small independent hip corrections to seat both soles without sliding.

Judge in-place locomotion against backward stance travel and its measured ground speed, not stationary-foot rules. Match animation speed to character speed during integration. Check every planted sole, toe and heel for hover/penetration, and inspect shoulder/hip gaps as well as hand/head and arm/torso intersections.

## Verify and deliver

For authoring in Blender, `animate-roblox-characters` when installed supplies the authentic rig transfer and the rig-appropriate export; load it only for that ([animation.md](animation.md)). [animation.md](animation.md) supplies export and Studio inspection guidance, and this file the restricted-joint policy; generic R15 workflows must not introduce knee, elbow or waist motion.

Before delivery:

1. `R6OnR15.check(map, sequence)` must return no findings: only the six joints move, the nine locks stay at identity, and no pose names a part the rig lacks. Test the evaluated result too when controls or constraints drive the rig (`r6.check_locks` in Blender). Confirm no mesh or in-place root object has animation keys.
2. For a retarget, `R6OnR15.verify(map, rig, source, sequence)` plays both clips through the engine and reads the R15 back as R6 numbers: expect under 0.5 degrees, 0.01 studs and 0 on `Locked`.
3. Compare front and side poses/in-betweens on the actual visible R15, with `AnimationInspector.sheet`. Show its separate upper/lower limbs, hands, feet and torso segments clearly; solid diagnostic styling can otherwise make an R15 preview look like R6.
4. Audit exported KeyframeSequences with this repo's `AnimationInspector`. Set `Locomotion = true` for in-place walk/run. Exclude ground-contact rules only for genuinely airborne, swimming, climbing or seated clips. Fix errors and assess warnings without hiding them; a retarget is judged against its source's audit.
5. Verify loop seams, locked joints and blending on the exported target, in Play on the real avatar: read the joints' `Transform` through each state and the track speeds. An Edit-mode track loading successfully does not prove the gameplay path: this is how the tempo problem in [r6-default-set.md](r6-default-set.md) was found. Register clips with `RegisterKeyframeSequence` on the client to test before publishing. A height test cannot tell a planted foot from a swinging one, since a rigid leg swings through floor height: use the audit's ground speed for foot slide.
6. Render and reopen GIF previews, check timing/frame count and preserve a working-file backup. Report which checks ran and whether gameplay transitions were exercised. Check the controller's jump-to-fall timing: it can cut off a good arm arc before completion. Publishing is a separate requested step.

## Session-derived starting points

These are examples from the reviewed stock-R15 set, not universal limits. Adjust to the reference and body proportions:

- Smooth idle: three soft rocks over 7.1 seconds instead of nine; no leg-lift fidget. The revised root's vertical range was about 0.0075 studs.
- Smooth walk/run: root vertical ranges about 0.059 / 0.073 studs, reduced from 0.184 / 0.285. Run used about 14° forward torso lean with partial head counter-tilt.
- Compact jump: forward reach peaked around 0.18 seconds, opening outward by about 0.30 seconds, rather than completing a full shoulder revolution.
- Reference fall: alternating compact shoulder arcs over a 1.6-second loop, with no torso turn.

Keep approved motion and references with the working project. Do not depend on machine-specific Downloads or temporary scratch paths, and do not assume those timings, axes or amplitudes fit every avatar.
