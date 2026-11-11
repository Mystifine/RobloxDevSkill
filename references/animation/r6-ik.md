# R6-like IK on R15

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
- **A free arm aimed by direction** (nothing in its hand to set the roll) turns by the shortest swing from hanging: pass its rest as `From`, or `r6.swing` on the R6 rig ([blender.md](blender.md#the-r6-rig)). A fixed roll reference flips the arm over as it swings through that reference.
- Check the second return value of `reach`: a miss means the target is out of reach for this slide, not that the limb got there.
- **Do not use Studio's Animation Editor IK or an ordinary chain** on these clips: they solve through elbows and knees (an `IKControl` down the whole arm bent the elbow 24 degrees). Use `reach` instead.

**In Blender,** `r6.add_controls(armature, roles)` adds them as bones and the R15 bones follow:

- FK: `R6_Torso`, `R6_Head`, `R6_Arm.L/.R`, `R6_Leg.L/.R`, each at its R6 pivot. Rotate to turn, move to slide.
- IK: `R6_Arm_IK.L/.R`, `R6_Leg_IK.L/.R`, `R6_Head_IK`, on the root so a planted foot stays planted. `ik` blends FK (0) to IK (1) and can be keyed; `slide` goes from aiming only (0) to reaching (1).
- `r6.pose_r6` poses from R6 numbers; `r6.bake(armature, start, end)` keys the 15 R15 bones for the exporter; `r6.edit` returns to the controls; `r6.check_locks` must return `[]`.
- Keep the imported rig's names and metadata (`names=` maps them), and calibrate `space=` to the rig. The controls are checked against Studio's numbers on a replica from `roblox_rig`; confirm the export on your rig's own exporter.

**In game,** call `reach` each frame in `RunService.Stepped` and write `map.Joints[map.Roles[limb].Joint].Item.Transform = R6OnR15.toR15(map, limb, transform)`, passing `Torso` if the torso is animating. This keeps R6's pivot and has no joint limits; `Slide = 0` keeps the limb on its pivot. `IKControl` also works with `Type = LookAt`, `ChainRoot` the upper limb and `EndEffector` an attachment on that same part, at the tip, facing along the limb: the elbow stays locked and the limb attached, but R15's ball-socket limits stop it short of some aims (0.83 alignment on a target ahead of the chest). `Type = Position` on that chain reaches by tearing the limb off its joint: do not use it.
