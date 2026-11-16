# Hit effects: attacks, slashes and impacts

For an attack's effects (auto attacks, weapon swings, abilities, specials), on top of [vfx.md](vfx.md). Damage and the target's reaction land on the clip's `Hit` marker: [gameplay.md](../code/gameplay.md).

## Weight

- **Scale an impact to the attack's weight** *(default)*. A basic or auto attack is light and short: one glint or small hit flash, a cut aligned to the blade's travel, a few sparks thrown along it, gone in under 0.2 s; no dark core, shock ring, bloom, floor crack or finisher. The heavy layers (a big blast, a dark core, rings racing out, floor marks, a light, hit-stop, residue) belong to specials and ultimates. Basics that shared a special's layer stack (fire blasts, a dark core, a 1.7x finisher every third hit, floor cracks and rings lasting 0.4-1.2 s) read as too drastic and too long; a separate small hit for basics fixed it without touching the specials.
- **A light hit is built from single small layers,** not a trimmed heavy template: a pack's hit templates were white in every layer, 6 to 30 studs across and living 1.5 to 4.4 s, so trimming layers past 0.6 s still left a big white particle lingering, reported three times. Before reusing a template at a smaller role, list each layer's lifetime (`Lifetime.Max / TimeScale`), largest `Size` and colour.
- **An ability always plays its effects.** With nothing in reach it plays them at a point ahead (past the landing point for a dash), dropping only the impact and the camera jolt and keeping the movement: placed only at the hit point, a whiff drew nothing.

## Cuts and slashes

- **A cut line is two tapered camera-facing beams,** end to middle to end (widths 0, w, 0; `FaceCamera`), drawn across in about 0.035 s and thinned to nothing by 0.17 s: one crisp cut from the gameplay and side cameras. A flare squashed into a line went hair-thin and tens of studs long.
- **Trace a melee slash from the clip's blade, sampled offline,** not a `Trail` or a pack arc placed on the target. Fast cuts cross 8 studs between two 60 fps frames (up to 581 studs/s), so a per-frame Trail draws straight facets, and camera-facing arcs with a random spin read as random. Sample the grip and tip in root space at 120 to 240 Hz (`Animator:StepAnimations` plus forward kinematics), then draw a chain of Beams along a spline timed by `AnimationTrack.TimePosition`: it follows the blade exactly, hit-stop included. Taper the tail by position so it ends in a point.
- **A thrown slash or slash arc** *(default)* is a crescent mesh whose plane contains its flight, its thick edge (a teardrop section) leading toward the target and its horns trailing, in one orientation the whole way: from the caster's side it reads as a thick line of force. Seen face-on (a flat crescent turned to the camera or to face its flight) it read as a half moon with its weight to one side and was sent back. A swing trace left in the air takes the same orientation.
- **Cut marks a blade leaves on a target** keep only the crescent's bright edge and core, shallow (about 0.55 of its depth): with a thrown slash's dark trailing body, rows of them seen from three quarters read as claws.
