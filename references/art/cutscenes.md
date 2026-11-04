# Cutscenes and cinematic cameras

A cutscene is a timeline: camera, clips, effects and sound keyed to one clock. Build it so any second can be reproduced, since that is the only way to check it. Effects inside it still pass [vfx.md](vfx.md); poses follow the animation route.

## From a reference
- **Build to its numbers:** watch it with [video.md](video.md) and build each shot to what it records: length, holds, beats, size, where the subject sits and faces, camera move and lens. Check your recording against the reference with `compare`, shot by shot, not only by timing.
- **List what is left out, and why:** a rule (all ages, any avatar) or something the cutscene cannot do yet (a focus pull, a bloom pulse). The second is a feature to raise with the user, never a silent drop.

## Framing
- **Shots that must work on any avatar frame the body,** waist-up or wider, anchored to the root or torso. Close-ups anchored to `Head` or a hand showed an empty head under a floating crown (a headless avatar) or a wall of grey blocks; waist-up and medium shots of the same moments read on every avatar. Face close-ups are for rigs you control.
- **No camera down a blocky R15 arm:** the default hand is a 0.98 x 0.32 x 1.03 slab, so a camera behind the shoulder, on the line through the fist, saw the back of the torso, and raised to head height a wall of hand. Sit the camera just above the head looking past the fist, and frame the target with an effect placed at the target (a ring around it in world space), which frames it from any camera and avatar size; never frame through the hand.
- **Particles fill a near camera:** effects sized in studs fill the frame of a camera about 8 studs away, and smoke washes it from inside. Light a character's aura after any shot whose camera sits within a few studs of the body (an over-the-shoulder shot 2 studs behind the head washed pink, and the hit after it whited out), and size each effect for the closest shot that shows it.
- **Find a wash-out by its time,** not by guessing the largest effect: line stills up against the keyed effect times. A haze blamed on expanding rings was there before the first ring fired; successive stills matched a small particle star, then swirl bursts.
- **A low shot of something high:** a long lens from far away. 30 studs back at FOV 40 looked steeply up, and a ledge hid the figure standing on it; 70 studs back at FOV 25 matched the reference and kept the figure clear.

## Characters in a cutscene
- A character the cutscene lifts by CFrame needs Freefall disabled meanwhile ([gameplay.md](../code/gameplay.md)); its aura rides with `LockedToPart` ([vfx.md](vfx.md)).
- Start the cutscene the way the game does (its prompt, remote or UI), not by requiring its modules from `execute_luau`. While you iterate, a self-contained timeline required there replays any one outcome on demand ([studio-testing.md](../code/studio-testing.md#studio-mcp-calls)).

## Check it frame by frame
- **One clock:** every keyed value (camera, poses, effects, text) reads the seconds since the cutscene started, never its own `task.wait` chain.
- **Hold a second for captures:** a workspace number attribute, read only when `RunService:IsStudio()`, overrides the clock and holds every keyed value at that second. `screen_capture` lands about 1.2 s after the call, so waiting for a moment and then capturing misses every fast beat; held, each frame came out exact.
- **Jump to a second:** a temporary LocalScript harness starts the cutscene from second T with its clips frozen at T, for repeatable frames and printed positions. Captures taken while effects play can time out or return stale frames.
- **Rewinding keeps what a later moment made:** held at 3.2 s, then at 0.6 s, the scene still showed an aura and eyes that first appear at 1.5 and 2.4 s. Restart the cutscene before checking an earlier moment.
- **A keyed value runs from the previous key that sets it,** so give every fade a hold key where it should start. A prop keyed Fade 0 at the start and Fade 1 at 1.43 s faded through its whole flight and read as a ghost before the hit; the logs and timings were all correct, and only a frame burst of the recording showed it.
- Single effects inside it: `Inspector.hold` ([vfx.md](vfx.md) section 8).
