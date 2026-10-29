# VFX

Goal: an effect that is unique to the ability and reads clearly, not a remix of two presets. Hits, injuries and defeats default to the stylized effects in [no-gore.md](no-gore.md) (flashes, sparks, stars, puffs, element effects), within the experience's maturity label. Upload new textures neutral (white or grey) and tint them with `Color`; a pack's existing textures are fine by id (the project's own exclusions win).

## 1. Research before building

1. Find the project's VFX player/utility, existing templates, and VFX packs (search Workspace, ServerStorage, ReplicatedStorage, the repo's `assets/`). Read how existing effects are authored so yours plays through the same path.
2. Inspect the available textures and pack emitters: list their texture ids, flipbook layouts and original settings. Render flipbooks as contact sheets (Roblox thumbnails API) or preview them in Studio; do not pick a texture by name alone. Reference unnamed carriers by texture id.
3. Decide the beats (anticipation, release, impact, residue) and the layers per beat (core flash, body, edge, sparks, smoke/dust, light, ground mark). Give each layer its own texture, size curve and timing.

## 2. Tune the properties, do not accept defaults

For every emitter set deliberately: `Texture`, `Color` (ColorSequence), `Transparency`/`Size` (NumberSequences), `Rate` or burst count, `Lifetime`, `Speed`, `SpreadAngle`, `Acceleration`, `Drag`, `Rotation`/`RotSpeed`, `Squash`, `LightEmission`, `LightInfluence`, `Orientation`, `EmissionDirection`, `ZOffset`, `LockedToPart`, `TimeScale`, `FlipbookLayout`/`FlipbookMode`/`FlipbookFramerate`, `Shape*`. Contrast layers in size, speed and lifetime (fast thin sparks over slow soft body).

## 3. Attribute contract (burst timing)

*(default: a project with its own contract keeps it)* Each `ParticleEmitter` carries attributes; templates store `Enabled = false`.

| Attribute | Meaning |
|---|---|
| `EmitDelay` | seconds after play before this layer starts (default 0) |
| `EmitCount` | particles in the initial burst (default: the emitter's `Rate`) |
| `EmitDuration` | seconds the emitter stays `Enabled` after the burst (0 = burst only) |

Use the **project's existing player** for this (it already honours these and graphics settings). If none exists, use [scripts/ParticlePlayer.luau](../scripts/ParticlePlayer.luau), which implements the same semantics.

Count scaling: scale `EmitCount` on the client, with a **minimum of 1** for any layer whose count is above 0, so weak devices thin an effect but never delete a layer. A manual quality level gives `Value/10` (`UserSettings().GameSettings.SavedQualityLevel`). `Automatic` is the default and what most phones run, so it says nothing about the device: use the measured frame rate instead (the fallback player: 1 at 55 fps and up, down to 0.3 at 25 fps), and take the lower of the two. If the project's player treats `Automatic` as full quality, or scales without that minimum (for example passing `count * factor` straight to `Emit`), tell the user. Optional per-layer attributes the project may use: `Detail` (dropped at distance / on low settings), `FullRate`, `Tint`, `Lifetime` (template).

## 4. Smooth in, smooth out

- Every particle exits by `Transparency` -> 1, `Size` -> 0 or `Squash` at the end of its life, and enters the same way; a layer that only ends because its lifetime ran out pops out midair (checked by `Inspector.lint`, section 8).
- Fade lights (`Brightness` tween), decals, beams (`Transparency`/`Width`), trails and meshes (scale + transparency) rather than destroying them while visible.
- Teardown order: stop emitting (`Enabled = false`) -> let existing particles and tweens finish -> destroy. Do not destroy before `EmitDelay + EmitDuration + Lifetime.Max` (plus a small buffer) has passed for every emitter, and the longest fade for everything else. Compute this from the emitters rather than guessing; sustained effects expose a `Stop()` that does the same.
- Clean up on interrupt (death, unequip, cancel, player leave) with the same fade path.

## 5. Placement (where an effect spawns)

An effect that appears in the air, on a head or inside a body is a placement bug, not a style choice.

- **Never use a character's root position as a ground point.** `HumanoidRootPart` is about 3 studs above the floor and the head about 2.6 above that. A locked target position is a hip, not a floor.
- **Ground effects** (rings, cracks, pools, telegraphs): ray straight down from just above the point (4 studs, not 8 or more, so a ceiling is not hit), 40 studs long, **ignoring every character, monster, shadow, other effect and non-collidable prop** (`RaycastParams.RespectCanCollide = true`, plus an exclude list built from all of them; reuse the project's helper, for example `SkillMath.params` + `ground`). The ray must not start inside what it ignores and must not stop on a head, a drop of VFX or a decal. On a **miss, drop to the feet (point minus the hip offset), never leave it at hip height**. Lift 0.1-0.5 studs over the floor's flat dressing, and use `hit.Normal` for slopes.
- **Body effects** attach to the right part by an Attachment (a crown on the Head, a foot ring on the foot or root's floor point, a hand glow on the hand), never by a world offset from the root that drifts.
- **Air effects** (meteors, auras at chest height) declare their height from a named constant and are marked `Airborne` for the inspector.
- **Derive spawn points on the server from authoritative facts** (the target's floor point, the boss's feet) and send those; clients should not guess heights from hip positions.
- Check with `Inspector.placement(container)` (section 8): it flags `floating` parts and parts `in-body`, run with a real character standing on the stage.

## 6. Meshes

Secondary. Add a mesh only when it fits well (slash arcs, shockwave rings, cones) or as a flipbook carrier. Keep it low-poly, one material, `CanCollide/CanTouch/CanQuery = false`, `Massless`, and fade it like any other layer.

## 7. Budget and gotchas

- Set and respect a budget per cast (particles, parts, beams, lights) and per-viewer limits (distance cull, concurrent effects). Preload textures. Avoid big stacked transparent quads (overdraw). Never create instances per frame.
- `Orientation = VelocityParallel` lays the texture's width along motion, so tip-up textures go sideways; pick or rotate textures accordingly.
- Legacy `Fire`/`Smoke` objects follow the part's Y axis (sideways on rotated or cylinder parts); prefer `ParticleEmitter`.
- Additive emission (`LightEmission = 1`) can show rectangular texture backgrounds; check the texture's alpha before trusting it.
- Only the local client draws its own predicted effects; do not also replay them for that player.

## 8. Inspect (an effect is not done until it passes)

[scripts/VFXInspector.luau](../scripts/VFXInspector.luau) checks section 4: every particle leaves by fading, shrinking or squashing (never by lifetime alone), and nothing is destroyed while visible. Studio Edit captures omit particles, so **lint in Edit, look in Play** (Client DataModel; load the module as SKILL.md Scripts describes).

1. **Lint, Edit, instant:** `local findings, text = Inspector.lint(templateOrFolder)`. Fix every `ERROR` (`no-exit`, `trail-tail`): the end of life must be transparent (>= 0.95), tiny, or squashed (`|Squash|` >= 1 and 0.5 above its start; calibrate against a held frame). `Inspector.fixExit(root)` repairs them (holds the curve, fades the last 22% to 1) before you write the template back. `flipbook-exit` is a warning: a one-shot flipbook ends on its own last frame, so confirm it in step 4 or fade it anyway. A deliberately hard-edged layer opts out with the boolean attribute `InspectIgnore` and a comment saying why.
2. **Stage, Play client:** `Inspector.hideUI(true)`; `Inspector.preload(template)` (a cold effect can freeze before its textures arrive and photograph empty); `local stage = Inspector.stage()` (a **sphere caster** and a **cube target** on a dark plate high above the map). Play the effect from `stage.Caster` toward `stage.Target` through the project's player (`stage.Frame` sits at the caster, facing the target).
   - **With the real animation** (skill and attack effects): `Inspector.stage({ Rig = character, Victim = dummy, Animation = id })` stands copies in place of the sphere and cube, on the floor as the engine stands them (HipHeight). `local track = stage:Play()`, then `track:GetMarkerReachedSignal("Hit"):Wait()` and play the effect, so each layer's `EmitDelay` is judged against the real pose (the slash follows the weapon's arc, the flash lands on the impact frame). Use only a clip that passed AnimationInspector ([animation.md](animation.md) section 4), and its published id: a temporary id from `RegisterKeyframeSequence` may not load on the client. Keep the camera close, since tracks more than about 150 studs from the camera do not play.
3. **Watch:** `local watch = Inspector.watch(container)` before playing; after the container is gone, `watch.Stop()` (it yields a frame) lists `popped` (part, decal or light removed while visible) and `cut-off` (emitter, beam or trail removed with particles alive, including a container destroyed or a `Debris` lifetime that ignores `TimeScale`). Fix by fading first and destroying after `EmitDelay + EmitDuration + Lifetime.Max / TimeScale`. Run every cast of a system through it (stage the real payload) rather than one sample.
4. **Look:** take `times = Inspector.keyTimes(container)` right after playing. For each time: play a fresh copy and `Inspector.hold(container, t)`; the frame is then snapshotted out of reach of the project's `Debris`, tweens and `Destroy` (a staged rig freezes in the same frame), so capture latency does not matter and **you can move the camera and capture it as many times as you like**:
   - Camera `stage:Camera(kind, { Zoom, Focus, Fov })` (Zoom 0.5 is twice as close, 2 twice as far; Focus aims at an impact spot):

     | kind | use |
     |---|---|
     | `side` (default) | whole path, height, travel |
     | `iso` | the shape |
     | `top` | ground coverage, radius, cones and rings |
     | `front` / `behind` | from beyond the target back at the caster / down the path |
     | `close` | particle detail |

     `Inspector.views` is the ready sweep (`side`, `iso`, `top`, `close` at 0.6). `stage:Show({ Target = false, Caster = false, Floor = false })` hides the props for an unobstructed view; show them again to judge scale and aim.
   - Placement: `Inspector.placement(container)` after the effect has landed (with a real character on the stage): `floating` and `in-body` mean it spawned in the air or inside a body.
   - For one emitter's last frame: `Inspector.endFrame(stage, emitter)` then capture; particles still clearly visible there vanish midair.
5. **Clean up:** `Inspector.release()`, `stage:Clear()`, `Inspector.hideUI(false)`, delete the ModuleScript; confirm no instances, tweens or connections remain.

Capture caveat: a Studio capture can return a stale or blank frame right after you change the camera or start an effect. Wait about 6 s, and treat two identical successive captures as a stale frame, not as an empty effect; judge time-varying effects by looping them every few seconds, or from held frames. An unpublished place (PlaceId 0) may load none of the game's own textures ([ui.md](ui.md)), so inspect in a published copy. `Inspector.hold` keeps emitters and beams that sit on parts as well as on attachments.

Notes: layers whose `EmitDelay` is later than the held time fire into the frozen frame as fresh births; compute `keyTimes` before `hold` (it empties the container). The Studio MCP runs calls one at a time: start long-running work from a fixture Script and poll, rather than expecting two calls to overlap.
