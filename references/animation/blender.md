# Animating in Blender

The whole Blender side of a clip, with [animation.md](animation.md) for the rules every clip keeps and its Studio check. Scripts: [blender_anim.py](../../scripts/blender_anim.py) (any rig, in Blender), [r6_rig.py](../../scripts/r6_rig.py) (the R6 rig), [gif_preview.py](../../scripts/gif_preview.py), [clip_import.py](../../scripts/clip_import.py) with `ClipImport` (into Studio). Their headers give every option.

## The rig

Animate the target's own rig: one built from its Studio numbers, a pinned premade rig, or the user's export. Never a guessed humanoid or a box proxy. Do the rigging, posing and keying yourself; ask the user only for what needs them (a download, a plugin click, an API key).

| The clip | Rig in Blender | Out | Into Studio |
|---|---|---|---|
| An R6 game's, or fake R6 on R15 ([r6-on-r15.md](r6-on-r15.md)) | Aeresei's R6 IK + FK V2.22: `python scripts/r6_rig.py fetch`, then `copy OUT.blend` | `r6.export`: `.rbxanim` + `.json` | `clip_import.py rbxanim`, `--r15` for fake R6 |
| Realistic R15 | the real R15 dumped from Studio ([r15-motion.md](r15-motion.md)) | its pipeline | `pipeline.py import` |
| Bones: creatures, custom skeletons ([custom-creatures.md](../rigs/custom-creatures.md)) | the rig as built | `ba.deltas`: world deltas a sample | `clip_import.py deltas` |
| The user's avatar, any Motor6D rig | exported by Cautioned's Studio plugin [Blender Animations (ultimate edition)](https://create.roblox.com/store/asset/16708835782/Blender-Animations-ultimate-edition) (a user click), read by `bpy.ops.object.rbxanims_importmodel` then `rbxanims_genrig` | `.rbxanim` (`rbxanims_bake_file`) | `clip_import.py rbxanim --rig` |

## Set up

- **The connection is a Python call:** `ba.session()` through Blender MCP reports the file, unsaved changes, background mode and the frame rate. Author in the user's open Blender so they can watch. Never close it, and never change a file with unsaved changes: ask, or work on a copy (a headless Blender suits scripted builds and tests, `find_blender.py`). Render in the one process, never a process a frame.
- **The R6 rig:** `fetch` checks each file's size and SHA-256 (the rig's `.blend` and `.rbxm` from its author's DevForum attachments, Cautioned's add-on 2.6.3 from its GitHub release; `--from DIR` takes copies already on disk). Animate a `copy`, never the master. Open it with Python auto-run off (never Allow Execution), then `r6.check()`: its controls, body and five embedded scripts at their pinned hashes. The controls drive the body through constraints; `r6.activate()` runs the scripts only for their panels. `r6.addon()` registers the exporter from the hash-checked zip, or uses the user's install.
- **The add-on's online parts stay off:** OAuth, asset access, auto-connect. Its live-sync server listens on localhost: start it only for a transfer and stop it after.
- **Any other `.blend` from outside:** open with auto-run off and read its text blocks, drivers and handlers before running anything ([assets.md](../safety/assets.md)).

## The R6 rig

- **Controls:** `LowerTorso-FK` (location x right, y up, z back; quaternion, yaw about its y), `Head`, `RightShoulder` and `LeftShoulder` (FK arms), `LeftLeg-IK` and `RightLeg-IK` (location x right, y forward, z lift; turning about z). `MasterControl`, poles, grab points and `LookToPoint` stay put unless a clip needs them. `InternalArmature`, the Motor6D rig the exporter bakes, follows. The rig faces +Y, the floor is z = 0, 1 unit is 1 stud.
- **Pose arms by direction,** in the torso's frame: `r6.aim(bone, arm, held)` for an arm holding something (at rest the arm hangs and the item points forward, as R6's grip holds a sword); `r6.swing(bone, arm)` for a free arm, the shortest swing from hanging (a fixed roll reference flipped an arm 51 degrees in one frame as it swung through it); `r6.arc(a, b, s)` for a cut: the rigid arm and item turning about one axis through the shoulder, the item trailing (leading on a rising cut).
- **The legs are rigid.** The IK targets stay on the floor, but the legs cannot shorten, so a crouch sinks the soles 0.2 to 0.5 studs (the audit warns `sinks`). An R6 game's clip runs `r6.ground(arm)` on each pose before keying it, with no action assigned. For fake R6 the targets are what count: `r6.export` writes them a frame and `plantFeet` reaches the R15's legs for them.
- **A step lifts the body or swings the leg far:** a rigid leg swung 25 degrees raises its foot 0.19 studs, which AnimationInspector reads as a sliding foot (0.92 studs on an R6, in a test).

## Work in steps

1. **Brief:** type and gameplay purpose, feel, loop or one-shot (walks, runs and idles loop; attacks, jumps and most emotes do not), 60 fps, length, markers, in place. Measure whatever the user supplied first (a clip, a video, a dummy's AnimSaves): keys a second, amplitudes, which joints move.
2. **Key poses before keys:** contact, down, passing and up for locomotion; anticipation, action or impact, follow-through and recovery for a one-shot. For each: the hips and the weight-bearing side, the torso's lean, twist and counter-turn, the legs and planted foot, the arm arcs, the head, the front and side read. Say the brief and poses in one short message, then work; ask only what the request leaves open.
3. **Block** a pose or body group a call with `ba.key(arm, frame, {name: changes})`, Constant: torso and hips, then legs and contacts, arms, head. Names come from `ba.inspect()`. Never key a mesh. Quaternion keys from any other code go on the previous key's side, as `key` and `polish` put them: Blender blends the four channels separately, and a key on the far side (negative w after positive) swung a tongue through a large turn and 2 studs into the floor.
4. **Review each batch:** `ba.review(arm, folder, label)` renders front and side; look at both. When the image and the numbers disagree, the image wins. Front: base of support, centre of mass over it, hip and shoulder counter-angle, asymmetry, negative space, limb separation, silhouette. Side: lean, spine curve, heel and toe contact, knee direction, arm arc, head leading or dragging, weight on the ground.
5. **`ba.audit(arm, stage='BLOCKING', loop=..., contacts=...)`**, then **polish:** `ba.polish(arm, sharp=(frames...))` turns every key Bezier, auto-clamped, with VECTOR handles at the sharp frames. Make a coil's release and a strike's middle key sharp so the whip is an even sweep: with only its end key sharp a swing accelerates into it, and fast swings peaked at 52 to 59 degrees a frame; sharp release and middle keys, and a frame more on long windups, held every clip to 42-43 with the hit still at 0.13 to 0.25 s. Offset secondary motion (the torso leads, the arm follows a frame or two later, the head holds the target, the hips settle), clear plateaus and wobble, and review in-betweens, not only keys.
6. **`ba.audit(arm, loop=(start, end) or False, contacts={...} or False)`** until it returns no errors, then export, preview, and run the Studio check ([animation.md](animation.md) section 4), which `clip_import.py` does.

What AI animation gets wrong: robotic timing; planted feet sliding; parts flying apart; keyed meshes; default or sparse Linear curves; weight with no support under it; motion too subtle for a Roblox camera; symmetric, lifeless poses; a loop that hitches (a held or doubled seam frame, mismatched tangents); helpers, cameras, lights or other actions exported.

## The audit

`ba.audit` samples the evaluated rig, constraints included, and measures the armature that is exported (the R6 rig's `InternalArmature`). FINAL needs `loop` and `contacts` stated, so no check is skipped by leaving it out.

| Finding | Means | Fix |
|---|---|---|
| `Constant keys left` | blocking was not polished | `polish` |
| `Linear keys more than 3 frames apart` | mechanical motion | Bezier, or a key every 1 to 3 frames: an R6 animator's dense Linear string reads well |
| `turns N degrees in one 60 fps frame` | over 43 a 1/60 s frame; AnimationInspector errors at 45 in Studio | spread the turn over another frame; make the key before it sharp |
| `pops` | 15 degrees or more and 4 times every frame within two of it | a flip or missing key: quaternion keys (`key` keeps each on its previous key's side), or add a key |
| `loop seam` | the end pose misses the start by over 0.0001 units, 0.1 degrees or 0.0001 scale, or the slopes differ by over 0.001 a frame | `polish(loop=(start, end))` |
| `slides` | a planted contact (a bone's head and tail, or an object) drifts over 0.02 studs within its frames | key the IK target still |
| `sinks` (warning) | a visible sole below the floor (the R6 rig's legs by default) | `r6.ground`; fake R6: `plantFeet` |
| `animated meshes` | a mesh, not the armature, holds keys | key the armature |

Contacts name planted controls or bones with their frame spans, such as `{'LeftLeg-IK': [[0, 40]]}`. In-place locomotion moves its feet on purpose: pass `contacts=False` and let AnimationInspector judge the stride. Pass `studs=` for a rig not at 1 unit a stud.

## Into Studio

- **`.rbxanim`:** `r6.export(arm, path, action, markers={'Hit': frame}, loop=...)` bakes a key every frame from `InternalArmature` (the exporter marks holds Constant) and writes the sidecar: markers in seconds, loop, fps and the IK targets a frame. `channels={'Flick': ('RightShoulder', 'flick')}` adds a held weapon's flick (a keyed custom property), and `parts=('Torso', 'Head', 'Left Arm', 'Right Arm')` makes an upper-body layer: the exporter bakes every part, and only these are imported.
- **`python scripts/clip_import.py rbxanim CLIPS... --r15 ServerStorage.Rig`** (or `--rig` for an R6 game; `--held WeaponGrip --tip Tip` for a held weapon) builds each clip on the game's own rig, carries fake R6 over at every frame and plants its feet, sets markers, checks the joint policy, audits, and saves `clips/<name>.rbxm` (upload: `upload_asset.py --type Animation`) and `<name>.audit.txt`. Without a rig path it uses a default HumanoidDescription's body, which is not the game's.
- **Bone rigs:** `ba.deltas(arm, path, action, markers=..., loop=...)`, then `clip_import.py deltas FILE --rig ServerStorage.Creature --feet A,B --soles`. It finds the axis map by laying the rest heads on the imported bones; a fit over 0.05 studs means a different rig.
- **A bone named like a mesh object** (Body, Door) comes back from the Open Cloud importer as that MeshPart on a Motor6D, not a Bone. `ClipImport.deltas` poses it as the joint, at `Part0.CFrame * C0`; or rename the bone.
- **Feet whose joint sits above the sole** (a creature's ankle bones): `--soles`, or AnimationInspector's `Soles` option directly. Without it `float` read every planted paw as hovering 1.8 studs, and no slide was measured.
- **Studio's own FBX importer:** `ba.export_fbx(arm, path, action)` writes one action and the deform bones, baked a sample a frame, no leaf bones, with `roblox_rig`'s axes. Its import into Studio is a manual step that has not been tested here.

## Preview

After export, `ba.preview(arm, folder, name, start, end, step=2, exclude_last=<looped>)` renders one fixed three-quarter-front view (the R6 rig's camera (6.8, 8.8, 4.8) on (0, 0, 2.55) at scale 6.4; other rigs framed on the clip's bounds), then `python scripts/gif_preview.py FOLDER OUT.gif --glob 'name_*.png' --fps 30` encodes and verifies it. Deliver a GIF with every clip keyed in Blender *(default)*, after looking at it: it supplements the audits and the Studio sheet, never replaces them.
