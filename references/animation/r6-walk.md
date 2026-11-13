# R6 walks and runs

A walk or run in R6's style, on an R6 rig or on R15 through [r6-on-r15.md](r6-on-r15.md). Measured on four R6 walks that read well and on Roblox's own, each sampled 60 times a second through `Animator:StepAnimations` and compared by its Fourier terms at the stride's frequency.

## The shape

The body moves, not only the limbs. Roblox's own R6 walk moves only its limbs: a 0.67 s stride, legs swinging 55 to 60 degrees each way, no lean, bob or roll, a one-sided twist of 2 degrees, a foot lifting 0.75 studs. The four that read well:

| | Measured |
|---|---|
| Stride (two steps) | 0.76 to 1.0 s at 1x |
| Legs | 25 to 45 degrees each way, from the hip |
| Arms | 18 to 53 degrees each way against the legs (0.75 to 1.2 of their swing), held 4 to 10 out from the body |
| Torso | leaning 3 to 8 degrees from the root (the waist locked); twisting 2.5 to 5.5 each way once a stride, the forward arm's shoulder leading, peaking just after each foot lands; rolling 2 or less |
| Bob | 0.085 to 0.13 studs at twice the stride alone, lowest as each front foot lands, highest passing |
| Head | turned against the torso so the gaze holds level and ahead: the best two take 70 to 97 percent of the twist and most of the lean off it. Take it all by default *(default)* |
| Halves | mirrored |
| Keys | Linear and dense (30 to 65 a second), or about 10 a second for a snappy, toy-like walk |

## Tempo and feet

- **Rigid R6 legs skate.** The planted feet travel back 4 to 10 studs a second at 1x (Roblox's 13.3), 30 to 70 percent of the ground at WalkSpeed 16. Widening or quickening the swing to lock them is the stiff default's look.
- **Judge the tempo at the game's playback rate.** Animate plays an R6 walk at WalkSpeed / 14.5 (2.2x at 32). Pick the cycle for that cadence and say the skate it leaves.
- **Smooth a grounded rigid-leg body height** to harmonics 0 and 2 of the loop, not each frame's ground pass, which corners at every footfall.
- **Ground the body on the leg blocks' lowest corners,** not the foot points: a tilted 1-stud-deep block reaches 0.5 sin(angle) lower (heel at landing, toe at push-off). Smoothed as above, the body dipped 0.084 studs at each landing, inside good walks' 0.085 to 0.13 at contact; on the ankle targets it bobbed 0.27, lowest mid-step.
- **Plant each foot at the ground's speed** (run-cycle key poses, the feet's targets exported for `plantFeet`) only when the user asks for real steps on a fast run over R15 legs.

## A reference to match

When a walk reads stiff or waddles, measure the reference the user names (a dummy's AnimSaves) instead of hand-keying sines. Pose a copy at 60 Hz (a stopped track, `TimePosition`, `Animator:StepAnimations`); read each limb's swing and spread in the torso's frame, the torso's lean, twist, roll and offset from the root, and the head against the torso; then each channel's mean and first two harmonics against one leg's phase. That table, not stills, says what the reference does.

## Checking

Audit with `Locomotion = true` ([animation.md](animation.md)). On an R6 rig the `stride` warning starts at 50 percent and a planted sink is an error past 0.25 studs: the five R6 walks measured vary 26 to 44 percent and sink up to 0.19. The report's ground speed is the no-slide rate; on R6, pick the cadence instead. Judge the walk in motion, at the game's playback rate.
