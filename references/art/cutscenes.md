# Cutscenes and cinematic cameras

A cutscene is a timeline: camera, clips, effects and sound keyed to one clock. Build it so any second can be reproduced, since that is the only way to check it. Effects inside it still pass [vfx.md](vfx.md); poses follow the animation route.

## From a reference
- **Build to its numbers:** watch it with [video.md](video.md) and build each shot to what it records: length, holds, beats, size, where the subject sits and faces, camera move and lens. Check your recording against the reference with `compare`, shot by shot, not only by timing.
- **List what is left out, and why:** a rule (all ages, any avatar) or something the cutscene cannot do yet (a focus pull, a bloom pulse). The second is a feature to raise with the user, never a silent drop.
- **An object the reference is known by** (a weapon, a creature) that the project lacks: build it (weapons at the gear budget, [gear.md](../rigs/gear.md)) or ask at the start. Listed as left out at the end, the shots, pose and timing had to be reworked around it.
- **A fast strike has no visible travel** *(default)*: a 0.8 s dash down a 28-stud lane, true to its reference's timing, read as a slow slide. Move the body in one frame under two to six flash frames, then show what the speed left behind (a line in the air, the floor erupting along the path, a skid).

## Framing
- **Shots that must work on any avatar frame the body,** waist-up or wider, anchored to the root or torso. Close-ups anchored to `Head` or a hand showed an empty head under a floating crown (a headless avatar) or a wall of grey blocks; waist-up and medium shots of the same moments read on every avatar. Face close-ups are for rigs you control.
- **No camera down a blocky R15 arm:** the default hand is a 0.98 x 0.32 x 1.03 slab, so a camera behind the shoulder, on the line through the fist, saw the back of the torso, and raised to head height a wall of hand. Reframe around what the avatar can show first. When a shot over the hand is truly wanted, show an unattached stand-in hand of Parts in the camera's frame each frame, with the real arm, head and accessories at `LocalTransparencyModifier` 1 for that window: it frames the same on any avatar. Place it by reading the posed parts' positions and solving the offset that puts the target on the camera's ray at a set depth; hand-tuned offsets missed repeatedly.
- **Particles fill a near camera:** effects sized in studs fill the frame of a camera about 8 studs away, and smoke washes it from inside. Light a character's aura after any shot whose camera sits within a few studs of the body (an over-the-shoulder shot 2 studs behind the head washed pink, and the hit after it whited out), and size each effect for the closest shot that shows it. Size a prop for the closest camera that shows it, the moment it leaves a hand included: an orb near full size 0.1 s after launch filled half a shot 7 studs away, and keyed as a small spark until the next cut it read.
- **Find a wash-out by its time,** not by guessing the largest effect: line stills up against the keyed effect times. A haze blamed on expanding rings was there before the first ring fired; successive stills matched a small particle star, then swirl bursts.
- **A low shot of something high:** a long lens from far away. 30 studs back at FOV 40 looked steeply up, and a ledge hid the figure standing on it; 70 studs back at FOV 25 matched the reference and kept the figure clear.
- **A black or solid card inside a 3D scene:** a grade cannot black out the picture and keep particles glowing. A hollow box of black Neon parts round the camera (Neon is unlit, so it reads pure black) with the particles inside, far from the stage so nobody else sees it.
- **Grading a sky to a colour it lacks:** [environment.md](environment.md), Post-processing.

## Characters in a cutscene
- A character the cutscene lifts by CFrame needs Freefall disabled meanwhile ([gameplay.md](../code/gameplay.md)); its aura rides with `LockedToPart` ([vfx.md](vfx.md)).
- Start the cutscene the way the game does (its prompt, remote or UI), not by requiring its modules from `execute_luau`. While you iterate, a self-contained timeline required there replays any one outcome on demand ([studio-testing.md](../code/studio-testing.md#studio-mcp-calls)).
- **No added body details by default** *(default)*: temporary fingers or glowing eyes built to match a reference's close-ups were removed as not needed, so offer them as a choice. When fingers are wanted, build them from Parts (SmoothPlastic, the avatar's colours): a skinned mesh hand worked and was turned down as unsuited to Roblox avatars.
- **A held prop rides a Weld** from the hand to the prop's primary part, with `C1` its `PivotOffset` and `C0` keyed per beat: an anchored prop placed every frame trails an animated hand by one frame.

## Captions
- **Caption every spoken line** of a speech-led cutscene *(default)*, not only those the reference shows. Word times: [video.md](video.md).
- **The weight follows the voice** *(default)*: heavy for a line shouted or declared, calm for one said quietly. A stamp on a quiet line read as too aggressive, and a fading subtitle on a big one as too light. Judge the whole scene's delivery, not only its big line.
- **Heavy:** each word lands on its time; the key word on a row of its own at about 2.3 times the size, slammed from about 2.6 times with an accelerating ease, stamped just below size and back, white for a frame before its colour, with a bright copy bursting outward, a jolt of the line and a camera shake. Start one slam ahead of the voice. Merely scaling a bold word up read as light and bouncy.
- **Calm:** a lighter weight in its own case, low in the picture, each word fading up over about 0.5 s; the key word only a little larger, in colour. Let a line clear in about 0.2 s when the next follows at once, since both sit in the same place.

## Check it frame by frame
- **One clock:** every keyed value (camera, poses, effects, text) reads the seconds since the cutscene started, never its own `task.wait` chain.
- **Hold a second for captures:** a workspace number attribute, read only when `RunService:IsStudio()`, overrides the clock and holds every keyed value at that second. `screen_capture` lands about 1.2 s after the call, so waiting for a moment and then capturing misses every fast beat; held, each frame came out exact.
- **Jump to a second:** a temporary LocalScript harness starts the cutscene from second T with its clips frozen at T, for repeatable frames and printed positions. Captures taken while effects play can time out or return stale frames. Wait for `track.Length > 0` before setting `TimePosition`: set sooner on a new clip, it froze at 0. Stop the previous run fully before the next, since an overlapping stop can clear state they share, such as captions.
- **A harness that needs the game's own modules** (its state, its UI) runs as a LocalScript: [studio-testing.md](../code/studio-testing.md).
- **Rewinding keeps what a later moment made:** held at 3.2 s, then at 0.6 s, the scene still showed an aura and eyes that first appear at 1.5 and 2.4 s. Restart the cutscene before checking an earlier moment.
- **A keyed value runs from the previous key that sets it,** so give every fade a hold key where it should start. A prop keyed Fade 0 at the start and Fade 1 at 1.43 s faded through its whole flight and read as a ghost before the hit; the logs and timings were all correct, and only a frame burst of the recording showed it.
- Single effects inside it: `Inspector.hold` ([vfx.md](vfx.md) section 8).
