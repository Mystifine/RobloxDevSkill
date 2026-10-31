---
name: animate-r15-like-r6
description: Animate an R15 Roblox rig with stiff R6-style motion by moving only its root, neck, shoulders and hips. Use for fake-R6 locomotion, jumps, falls and emotes on R15; not for actual R6 rigs or normally articulated R15 animation.
---

# Animate R15 Like R6

Keep the actual R15 character, hierarchy and body proportions. Make each arm and leg move as one rigid unit by restricting animation to the six joints below. Do not substitute an R6 model or merge the visible body into six blocks.

## Authoring workflow

Check for Blender MCP and test the live connection first. Attempt to author and verify the animation in Blender at **60 FPS** (`scene.render.fps = 60`, `scene.render.fps_base = 1.0`) before falling back to Roblox Studio. Repair routine connection/context errors where possible; if Blender MCP is unavailable or a real authoring blocker remains, explain the reason and continue in **Studio at 60 FPS** with the same restricted-joint policy. Do not stop solely because Blender MCP is missing.

In Studio, use a 60 FPS Animation Editor timeline or scripted keys at `Keyframe.Time = frame / 60`, then audit with `{ Fps = 60 }`. Follow the shared [Blender-first workflow](../../references/animation.md#authoring-workflow-blender-first-studio-fallback) for connection checks and fallback details. Preview GIF frame rate is independent of the 60 FPS authoring timebase.

## Joint policy

Discover the target's real joints, controls, rest frames and forward direction before keying. These are standard R15 **child part/bone names**, not guaranteed control names; map them to the imported rig's controls or Motor6D/AnimationConstraint joints.

| R6 role | Animated R15 child | Parent |
|---|---|---|
| Root / whole torso | `LowerTorso` | `HumanoidRootPart` |
| Neck | `Head` | `UpperTorso` |
| Left / right shoulder | `LeftUpperArm`, `RightUpperArm` | `UpperTorso` |
| Left / right hip | `LeftUpperLeg`, `RightUpperLeg` | `LowerTorso` |

Keep these nine joints at their rest-relative **identity transform**:

- Waist: `UpperTorso`.
- Elbows/wrists: `LeftLowerArm`, `LeftHand`, `RightLowerArm`, `RightHand`.
- Knees/ankles: `LeftLowerLeg`, `LeftFoot`, `RightLowerLeg`, `RightFoot`.

Use zero pose translation, identity pose rotation and unit scale on locked joints, preserving their imported rest matrices and C0/C1. Do not reset their rest orientations or reparent them. Keep `HumanoidRootPart` stationary for in-place clips; character travel and jump height come from game movement or a separately identified preview mover.

Animate the mapped controls/pose bones, never the meshes. Rotation normally supplies the motion. Small shoulder/hip translations are useful when the reference shifts rigid limb blocks: an R6 clip can imitate a knee by moving the entire leg upward. Retarget that position as well as its rotation when needed, then check contact and attachment gaps. Do not unlock a knee or elbow to solve a posing problem.

For a full-body clip, explicitly key or otherwise enforce all nine locked joints throughout playback. Omitting their tracks does not guarantee a lock when another animation is blended underneath. Preserve the pose hierarchy and intentional identity-pose weights on export; verify the result with the actual animation controller.

## Shape the motion

Inspect supplied frames/video and the existing animation family before inventing motion. Separate torso yaw, torso pitch and shoulder arcs: a circular arm gesture does not imply a body spin. Keep jump/fall bodies upright unless the reference or request calls for a tilt or turn.

- **Idle:** favor a slow weight shift, small shoulder/head lag and minimal vertical bounce. Keep both feet down unless a fidget is requested. When smoothing an approved loop, remove the unwanted accent without replacing the whole motion.
- **Walk/run:** use hip-driven leg pendulums and opposed shoulder swings, with smaller torso/head counter-motion. Reduce vertical amplitude and abrupt acceleration when asked for smoother motion. A forward run posture comes from the root/whole torso, with a partial head counter-tilt to keep looking ahead; keep the waist locked.
- **Jump:** use a compact forward-and-outward shoulder arc when that is what the reference shows. Do not turn a small circular sweep into an overhead 360-degree windmill. Review hand paths and total span from the front and side.
- **Fall:** follow the reference's held or alternating shoulder motion rather than automatically spreading both arms into a T. Keep it distinct from a new jump or body spin.

Use sparse, deliberately eased Bezier authoring curves with controlled overlap. Loops need matching endpoint poses **and tangents**. Retain a duplicate closing key for checking/export when needed, but omit it from rendered loop playback.

## Contacts and retargeting

Calibrate studs against the actual imported rig. Work through its joint frames: child world pose = parent world pose × C0 × animated transform × inverse(C1). Do not copy Euler angles or part-center offsets between R6 and R15 without accounting for their different pivots and limb proportions.

When changing torso lean or bounce on an approved gait, preserve the feet's world paths by solving compensating hip transforms in the new parent frame. Lock the lower-leg/foot joints throughout. A shared root-height solve seats only the lowest foot; a slow idle may need small independent hip corrections to seat both soles without sliding.

Judge in-place locomotion against backward stance travel and its measured ground speed, not stationary-foot rules. Match animation speed to character speed during integration. Check every planted sole, toe and heel for hover/penetration, and inspect shoulder/hip gaps as well as hand/head and arm/torso intersections.

## Verify and deliver

Use the installed `animate-roblox-characters` skill when available for authentic rig transfer, Blender authoring and the rig-appropriate export workflow. In this repository, [animation.md](../../references/animation.md) supplies export and Studio inspection guidance. This skill supplies the restricted-joint policy; generic R15 workflows must not introduce knee, elbow or waist motion.

Before delivery:

1. Confirm that only the six allowed joint transforms vary, all nine locked joints remain at identity, and no mesh or in-place root object has animation keys. Test the evaluated result too when controls or constraints drive the rig.
2. Compare front and side poses/in-betweens on the actual visible R15. Show its separate upper/lower limbs, hands, feet and torso segments clearly; solid diagnostic styling can otherwise make an R15 preview look like R6.
3. Audit exported KeyframeSequences with this repo's `AnimationInspector`. Set `Locomotion = true` for in-place walk/run. Exclude ground-contact rules only for genuinely airborne, swimming, climbing or seated clips. Fix errors and assess warnings without hiding them.
4. Verify loop seams, locked joints and blending on the exported target. An Edit-mode track loading successfully does not prove that the engine evaluated its joints; distinguish Edit-time FK audit from Play-mode playback.
5. Render and reopen GIF previews, check timing/frame count and preserve a working-file backup. Report which checks ran and whether gameplay transitions were exercised. Check the controller's jump-to-fall timing: it can cut off a good arm arc before completion. Publishing is a separate requested step.

## Session-derived starting points

These are examples from the reviewed stock-R15 set, not universal limits. Adjust to the reference and body proportions:

- Smooth idle: three soft rocks over 7.1 seconds instead of nine; no leg-lift fidget. The revised root's vertical range was about 0.0075 studs.
- Smooth walk/run: root vertical ranges about 0.059 / 0.073 studs, reduced from 0.184 / 0.285. Run used about 14° forward torso lean with partial head counter-tilt.
- Compact jump: forward reach peaked around 0.18 seconds, opening outward by about 0.30 seconds, rather than completing a full shoulder revolution.
- Reference fall: alternating compact shoulder arcs over a 1.6-second loop, with no torso turn.

Keep approved motion and references with the working project. Do not depend on machine-specific Downloads or temporary scratch paths, and do not assume those timings, axes or amplitudes fit every avatar.
