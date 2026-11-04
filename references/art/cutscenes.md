# Cutscenes and cinematic cameras

A cutscene is a timeline: camera, clips, effects and sound keyed to one clock. Build it so any second can be reproduced, since that is the only way to check it. Effects inside it still pass [vfx.md](vfx.md); poses follow the animation route.

## Framing
- **Shots that must work on any avatar frame the body,** waist-up or wider, anchored to the root or torso. Close-ups anchored to `Head` or a hand showed an empty head under a floating crown (a headless avatar) or a wall of grey blocks; waist-up and medium shots of the same moments read on every avatar. Face close-ups are for rigs you control.
- **A low shot of something high:** a long lens from far away. 30 studs back at FOV 40 looked steeply up, and a ledge hid the figure standing on it; 70 studs back at FOV 25 matched the reference and kept the figure clear.

## Characters in a cutscene
- A character the cutscene lifts by CFrame needs Freefall disabled meanwhile ([gameplay.md](../code/gameplay.md)); its aura rides with `LockedToPart` ([vfx.md](vfx.md)).
- Start the cutscene the way the game does (its prompt, remote or UI), not by requiring its modules from `execute_luau` ([coding.md](../code/coding.md)).

## Check it frame by frame
- **One clock:** every keyed value (camera, poses, effects, text) reads the seconds since the cutscene started, never its own `task.wait` chain.
- **Hold a second for captures:** a workspace number attribute, read only when `RunService:IsStudio()`, overrides the clock and holds every keyed value at that second. `screen_capture` lands about 1.2 s after the call, so waiting for a moment and then capturing misses every fast beat; held, each frame came out exact.
- **Jump to a second:** a temporary LocalScript harness starts the cutscene from second T with its clips frozen at T, for repeatable frames and printed positions. Captures taken while effects play can time out or return stale frames.
- **Rewinding keeps what a later moment made:** held at 3.2 s, then at 0.6 s, the scene still showed an aura and eyes that first appear at 1.5 and 2.4 s. Restart the cutscene before checking an earlier moment.
- Single effects inside it: `Inspector.hold` ([vfx.md](vfx.md) section 8).
