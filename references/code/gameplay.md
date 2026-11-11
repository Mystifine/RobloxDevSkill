# Gameplay systems (physics, ownership, NPCs, animation playback)

## Physics

- **Movers are constraints** ([mover constraints](https://create.roblox.com/docs/physics/mover-constraints)): `LinearVelocity` (a steady speed along a direction, a line or a plane), `AngularVelocity`, `AlignPosition` and `AlignOrientation` (pull toward a target or another attachment), `VectorForce` and `Torque` (constant), `LineForce`. `BodyVelocity`, `BodyPosition`, `BodyGyro`, `BodyForce`, `BodyThrust` and `RocketPropulsion` are deprecated: convert them when you touch them (the page maps each one).
- **One-off pushes:** set `AssemblyLinearVelocity` / `AssemblyAngularVelocity`, or `BasePart:ApplyImpulse`, from the side that owns the assembly.
- **A part's height is not its `Size.Y`:** pads and rings are often cylinders lying on their side. Its world height is `|RightVector.Y| * Size.X + |UpVector.Y| * Size.Y + |LookVector.Y| * Size.Z`. A 0.6 x 9 x 9 pad on its side, read by `Size.Y`, stood every character 4.5 studs up, and looked plausible in screenshots: print the numbers.
- **Collisions:** `PhysicsService:RegisterCollisionGroup` and `CollisionGroupSetCollidable`, then `BasePart.CollisionGroup`. Decor gets `CanCollide`, `CanTouch` and `CanQuery` off, which is cheaper than a group.
- **Network ownership.** An unanchored assembly is simulated by its network owner, and the server hands assemblies near a player to that player's client by default, which can then move them anywhere. NPCs, projectiles, loot and anything authoritative: `SetNetworkOwner(nil)` on an unanchored part of the assembly. A player's own vehicle: `SetNetworkOwner(player)` for responsive driving, with the server checking speed and position. Anchored parts are never owned. Security rules: [coding.md](coding.md).

## NPC movement

- `PathfindingService:CreatePath({ AgentRadius = 2, AgentHeight = 5, AgentCanJump = true, AgentCanClimb = false, WaypointSpacing = 4, Costs = {} })` lists the defaults: size them to the NPC ([pathfinding](https://create.roblox.com/docs/characters/pathfinding)).
- `path:ComputeAsync(from, to)` inside `pcall`, then require `path.Status == Enum.PathStatus.Success`. It fails past 3,000 studs of straight-line distance or 20,000 nodes, so long trips go in legs.
- Walk waypoint by waypoint; a waypoint whose `Action` is `Enum.PathWaypointAction.Jump` sets the Humanoid jumping. `path.Blocked` gives the blocked waypoint's index: recompute only when it is ahead of the NPC.
- `PathfindingModifier` labels with matching `Costs` entries (`math.huge` forbids an area, a high cost makes it a last resort, `PassThrough` lets paths cross a door); `PathfindingLink` connects two attachments for boats, teleporters and ladders.
- `Humanoid:MoveTo` gives up after 8 seconds and `MoveToFinished` fires with `false`: re-issue it every few seconds on long walks (the Humanoid reference's sample refreshes every 6 s), or move per waypoint.
- **An NPC with no Humanoid** (the default rig, [rigs.md](../rigs/rigs.md)) has no `MoveTo`: compute the path the same way and move its anchored root along the waypoints by CFrame, facing the way it goes, its centre `RootHeight` above the floor (raycast for it), with the walk clip playing.
- NPCs belong to the server (network owner nil), share one update loop ([coding.md](coding.md)), and idle when no player is near.

## Bot opponents

- **A bot that steers the result** (an assisted win, a match kept close) plans over the moves still legal, never from a fixed script of round results: where moves are spent or limited, a scripted lose, win, win meets a player choice it has no legal answer to. A bounded minimax on the server, over every remaining player choice with at least one legal reply to each, kept the planned result on all 22,752 paths of a three-round card game with no 3-0; varying which close sequence it prefers stops matches looking alike. A choice the bot has already shown the player stays as shown.

## Playing animations in game

- **Load each animation once per Animator (the Humanoid's, or the AnimationController's) and keep the track.** Calling `animator:LoadAnimation(animation)` on every use piles up tracks until Roblox warns, and the old ones keep their memory.
- The local player's character animates from the client (it replicates); NPCs animate from the server. A client may also play a cosmetic clip on a server-owned NPC's Animator: it shows on that client only, at full weight.
- **An anchored character moved by CFrame** (its owner's client lifting it for a pose or cutscene) goes to Freefall at once and stays there after it is back on the floor, until unanchored, so the fall clip plays under every later pose; holding a movement key on an anchored root does not start the walk. Disable Freefall while it is moved (`Humanoid:SetStateEnabled(Enum.HumanoidStateType.Freefall, false)`), then `ChangeState(Enum.HumanoidStateType.Running)` and enable it again.
- **A character anchored mid-run or mid-jump** keeps its speed on the root (50 studs/s on one). `ChangeState(Running)` fires nothing when the state is already Running, and `Landed` then `Running` reports that stale speed, so Animate plays the walk; stopping the walk track by hand leaves no animation at all. Zero the root's `AssemblyLinearVelocity` first, then `ChangeState(Enum.HumanoidStateType.Landed)`, then `Running`, and the idle plays. Keep Freefall and Jumping disabled while it is held there.
- `track:Play(fadeTime, weight, speed)`. Priorities, low to high: `Core`, `Idle`, `Movement`, `Action`, then `Action2` to `Action4`. Time gameplay to `track:GetMarkerReachedSignal("Hit")`, never to `task.wait` guesses ([animation.md](../animation/animation.md)).
- Stop tracks with the same fade on death, unequip and teardown, through the project's maid.
