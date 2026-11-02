---
name: animate-r15-like-r6
description: R6-like animation on a real R15 rig. Use whenever a request says "R6 like", "R6-style", "fake R6", "fake R15", "R15 R6 animation" or "R6 on R15", or wants stiff limbs moving only at the root, neck, shoulders and hips; for FK or IK on R15 that behaves like R6's; and for Roblox's default R6 clips (idle, walk, jump, fall, climb, sit, tools, emotes, dances) on R15. Not for actual R6 rigs or normally articulated R15 animation.
---

# Animate R15 Like R6

People call this "R6 like", "R6-style", "fake R6", "fake R15", "R15 R6 animation" or "R6 on R15". They all mean this: the rig stays R15, and it moves the way an R6 does.

Keep the actual R15 character, hierarchy and body proportions. Make each arm and leg move as one rigid block by restricting animation to the six joints below, turning about R6's pivots. Do not substitute an R6 model or merge the visible body into six blocks.

Two helpers carry this, both speaking R6's language, with the same pivots:

- **Studio:** [scripts/R6OnR15.luau](../../scripts/R6OnR15.luau): FK, IK, clips, retargeting, checks. Load it as the dispatcher's Scripts section describes (`--@use R6OnR15`).
- **Blender:** [scripts/r6_on_r15.py](../../scripts/r6_on_r15.py): FK and IK controls on an R15 armature, from `HttpService:JSONEncode(R6OnR15.dump(R6OnR15.map(rig)))`.

## Authoring workflow

Check for Blender MCP and test the live connection first. Attempt to author and verify the animation in Blender at **60 FPS** (`scene.render.fps = 60`, `scene.render.fps_base = 1.0`) before falling back to Roblox Studio. Repair routine connection/context errors where possible; if Blender MCP is unavailable or a real authoring blocker remains, explain the reason and continue in **Studio at 60 FPS** with the same restricted-joint policy. Do not stop solely because Blender MCP is missing.

In Studio, use a 60 FPS Animation Editor timeline or scripted keys at `Keyframe.Time = frame / 60`, then audit with `{ Fps = 60 }`. Follow the shared [Blender-first workflow](../../references/animation.md#authoring-workflow-blender-first-studio-fallback) for connection checks and fallback details. Preview GIF frame rate is independent of the 60 FPS authoring timebase.

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

Rotation normally supplies the motion. A translation slides the whole rigid block, which is how R6 clips imitate a bend: R6's climb slides its legs 1.5 studs. Sparse keys interpolate the R15 joint, so a limb turning far between two keys strays from R6's arc by up to about 0.1 studs; add a key where that shows. `retarget` does so by itself.

## IK

An R6 limb has one joint and no bend, so its IK is an aim, then a slide along the limb for the distance an aim cannot cover, which is how R6's own clips reach. There is no pole target, because nothing bends.

| Call | Solves |
|---|---|
| `R6OnR15.reach(map, limb, point, options)` | a limb's Transform, its tip on `point` (in the root's space). Returns the Transform, how far the tip stopped from the point, and the slide used |
| `R6OnR15.reach(map, "Head", point)` | the head looking at `point` |
| `R6OnR15.plant(map, leg, at, options)` | a leg with its foot's lowest corner on the floor over `at`'s x and z |
| `R6OnR15.settle(map, pose, legs)` | body IK: the torso moved straight up or down so the lowest of `legs` meets the floor |

Options: `Torso` (the torso's Transform in this pose: always pass it when the torso moves), `From` (the limb's FK Transform: the swing is the smallest from it, so FK sets the roll), `Twist` (radians about the limb), `Tip` (another point on the limb, such as a heel), `Slide` (the furthest it may slide; `0` only aims; defaults 1 for arms and 1.6 for legs, as far as R6's stock clips go), `Floor`.

- The results are ordinary R6 Transforms, so **blend FK and IK** with `fk:Lerp(ik, weight)` and key them with `clip`.
- A rigid foot tips with its leg, so it rests on a corner, not flat. That is R6's look; do not unlock an ankle for it.
- A shared `settle` seats one foot; `plant` the other for both.
- Check the second return value of `reach`: a miss means the target is out of reach for this slide, not that the limb got there.
- **Do not use Studio's Animation Editor IK or an ordinary chain** on these clips: they solve through elbows and knees (an `IKControl` down the whole arm bent the elbow 24 degrees). Use `reach` instead.

**In Blender,** `r6.add_controls(armature, roles)` adds them as bones and the R15 bones follow:

- FK: `R6_Torso`, `R6_Head`, `R6_Arm.L/.R`, `R6_Leg.L/.R`, each at its R6 pivot. Rotate to turn, move to slide.
- IK: `R6_Arm_IK.L/.R`, `R6_Leg_IK.L/.R`, `R6_Head_IK`, on the root so a planted foot stays planted. `ik` blends FK (0) to IK (1) and can be keyed; `slide` goes from aiming only (0) to reaching (1).
- `r6.pose_r6` poses from R6 numbers; `r6.bake(armature, start, end)` keys the 15 R15 bones for the exporter; `r6.edit` returns to the controls; `r6.check_locks` must return `[]`.
- Keep the imported rig's names and metadata (`names=` maps them), and calibrate `space=` to the rig. The controls are checked against Studio's numbers on a replica from `roblox_rig`; confirm the export on your rig's own exporter.

**In game,** call `reach` each frame in `RunService.Stepped` and write `map.Joints[map.Roles[limb].Joint].Item.Transform = R6OnR15.toR15(map, limb, transform)`, passing `Torso` if the torso is animating. This keeps R6's pivot and has no joint limits; `Slide = 0` keeps the limb on its pivot. `IKControl` also works with `Type = LookAt`, `ChainRoot` the upper limb and `EndEffector` an attachment on that same part, at the tip, facing along the limb: the elbow stays locked and the limb attached, but R15's ball-socket limits stop it short of some aims (0.83 alignment on a target ahead of the chest). `Type = Position` on that chain reaches by tearing the limb off its joint: do not use it.

## Roblox's default R6 set

`R6OnR15.DEFAULTS` lists all 23 clips from the R6 `Animate` script, and [assets/r6-on-r15/R6OnR15Animations.rbxm](../../assets/r6-on-r15/R6OnR15Animations.rbxm) holds them built, as KeyframeSequences on classic R15 proportions (`BodyTypeScale` and `ProportionScale` 0: HipHeight 2, the same leg length as R6). Insert the file into ServerStorage in Studio, or rebuild:

```lua
R6OnR15.defaults(R6OnR15.map(rig), folder)  -- Edit only; a few seconds; pass your game's own proportions
```

| Group | Clips |
|---|---|
| Locomotion | `idle` (weight 9), `idle2` (weight 1), `walk` (also the run: R6 has no run clip), `jump`, `fall`, `climb`, `sit` |
| Tools | `toolnone`, `toolslash` (only the right arm and torso, so a walk keeps playing beneath), `toollunge` (full body) |
| Emotes | `wave`, `point`, `laugh`, `cheer`, `dance1`, `dance2`, `dance3`, each dance with `b` and `c` variants |

- **The motion comes from R6's own clips,** sampled from the engine at 60 FPS, then thinned to the keys the curve needs, so nothing about Roblox's easing or partly keyed joints is guessed. Linear interpolation is correct here: it is what the sources hold. Loops close on their first pose, which removes the seam a few R6 clips have.
- **Proportions:** a clip fits the rig it was built on. On another R15 the turns are identical and joint positions differ by up to about 0.13 studs on the far-sliding clips (`climb`, `cheer`). Rebuild for an exact fit. `R6OnR15.map(character)` reads a player's real avatar in Play; a default `HumanoidDescription` (HipHeight 2.19) is not the same body as a game's classic R15 (HipHeight 2).
- **In a game:** publish to the group that owns the experience ([animation.md](../../references/animation.md), section 3), then `R6OnR15.wire(animate, ids)` on a copy of the R15 `Animate` in StarterCharacterScripts, in Edit. R6's own `Animate` cannot run on R15, since it waits for `Torso`.
- **Tempo:** R15's `Animate` is tuned to its own clips, which plays R6's walk about 13% fast and its climb 2.4 times too fast. `wire` retunes its source to R6's `speed / 14.5` and `speed / 12`, and reports any line it cannot find in a customized script; `R6Tempo = false` leaves the source alone. Swimming uses the walk and idle, as R6 does.
- **Inherited quirks:** the audit finds what the originals do. R6's walk sinks a foot 0.16 studs, its dances slide feet, `sit` and `toollunge` lift both feet. A finding the R6 source also has is fidelity, not a bug; compare `AnimationInspector.audit` on both. To clean a contact, rework that clip with `plant` and `settle`, and say that it no longer matches the original.

## Shape the motion

Inspect supplied frames/video and the existing animation family before inventing motion. Separate torso yaw, torso pitch and shoulder arcs: a circular arm gesture does not imply a body spin. Keep jump/fall bodies upright unless the reference or request calls for a tilt or turn.

- **Idle:** favor a slow weight shift, small shoulder/head lag and minimal vertical bounce. Keep both feet down unless a fidget is requested. When smoothing an approved loop, remove the unwanted accent without replacing the whole motion.
- **Walk/run:** use hip-driven leg pendulums and opposed shoulder swings, with smaller torso/head counter-motion. Reduce vertical amplitude and abrupt acceleration when asked for smoother motion. A forward run posture comes from the root/whole torso, with a partial head counter-tilt to keep looking ahead; keep the waist locked.
- **Jump:** use a compact forward-and-outward shoulder arc when that is what the reference shows. Do not turn a small circular sweep into an overhead 360-degree windmill. Review hand paths and total span from the front and side.
- **Fall:** follow the reference's held or alternating shoulder motion rather than automatically spreading both arms into a T. Keep it distinct from a new jump or body spin.

New motion uses sparse, deliberately eased Bezier authoring curves with controlled overlap. Loops need matching endpoint poses **and tangents**. Retain a duplicate closing key for checking/export when needed, but omit it from rendered loop playback.

## Contacts and retargeting

Calibrate studs against the actual imported rig. Work through its joint frames: child world pose = parent world pose × C0 × animated transform × inverse(C1). Do not copy Euler angles or part-center offsets between R6 and R15 without accounting for their different pivots and limb proportions: `toR15` does this.

When changing torso lean or bounce on an approved gait, preserve the feet's world paths by solving the hips in the new torso (`reach` or `plant` with `Torso`). Lock the lower-leg/foot joints throughout. A shared root-height solve seats only the lowest foot; a slow idle may need small independent hip corrections to seat both soles without sliding.

Judge in-place locomotion against backward stance travel and its measured ground speed, not stationary-foot rules. Match animation speed to character speed during integration. Check every planted sole, toe and heel for hover/penetration, and inspect shoulder/hip gaps as well as hand/head and arm/torso intersections.

## Verify and deliver

Use the installed `animate-roblox-characters` skill when available for authentic rig transfer, Blender authoring and the rig-appropriate export workflow. In this repository, [animation.md](../../references/animation.md) supplies export and Studio inspection guidance. This skill supplies the restricted-joint policy; generic R15 workflows must not introduce knee, elbow or waist motion.

Before delivery:

1. `R6OnR15.check(map, sequence)` must return no findings: only the six joints move, the nine locks stay at identity, and no pose names a part the rig lacks. Test the evaluated result too when controls or constraints drive the rig (`r6.check_locks` in Blender). Confirm no mesh or in-place root object has animation keys.
2. For a retarget, `R6OnR15.verify(map, rig, source, sequence)` plays both clips through the engine and reads the R15 back as R6 numbers: expect under 0.5 degrees, 0.01 studs and 0 on `Locked`.
3. Compare front and side poses/in-betweens on the actual visible R15, with `AnimationInspector.sheet`. Show its separate upper/lower limbs, hands, feet and torso segments clearly; solid diagnostic styling can otherwise make an R15 preview look like R6.
4. Audit exported KeyframeSequences with this repo's `AnimationInspector`. Set `Locomotion = true` for in-place walk/run. Exclude ground-contact rules only for genuinely airborne, swimming, climbing or seated clips. Fix errors and assess warnings without hiding them; a retarget is judged against its source's audit.
5. Verify loop seams, locked joints and blending on the exported target, in Play on the real avatar: read the joints' `Transform` through each state and the track speeds. An Edit-mode track loading successfully does not prove the gameplay path: this is how the tempo problem above was found. Register clips with `RegisterKeyframeSequence` on the client to test before publishing. A height test cannot tell a planted foot from a swinging one, since a rigid leg swings through floor height: use the audit's ground speed for foot slide.
6. Render and reopen GIF previews, check timing/frame count and preserve a working-file backup. Report which checks ran and whether gameplay transitions were exercised. Check the controller's jump-to-fall timing: it can cut off a good arm arc before completion. Publishing is a separate requested step.

## Session-derived starting points

These are examples from the reviewed stock-R15 set, not universal limits. Adjust to the reference and body proportions:

- Smooth idle: three soft rocks over 7.1 seconds instead of nine; no leg-lift fidget. The revised root's vertical range was about 0.0075 studs.
- Smooth walk/run: root vertical ranges about 0.059 / 0.073 studs, reduced from 0.184 / 0.285. Run used about 14° forward torso lean with partial head counter-tilt.
- Compact jump: forward reach peaked around 0.18 seconds, opening outward by about 0.30 seconds, rather than completing a full shoulder revolution.
- Reference fall: alternating compact shoulder arcs over a 1.6-second loop, with no torso turn.

Keep approved motion and references with the working project. Do not depend on machine-specific Downloads or temporary scratch paths, and do not assume those timings, axes or amplitudes fit every avatar.
