--!strict
-- Visual-effect inspection for Studio MCP. Three tools, cheapest first:
--
--   lint(root)         static, instant, works in Edit: every particle must leave by Transparency, Size or Squash
--   stage() + watch()  Play: a caster sphere and a target cube to play the effect between (or a real rig playing a
--                      passed animation, and a dummy target); flags anything destroyed while still visible and
--                      emitters cut off with particles alive
--   hold()/release()   Play: snapshots and freezes the effect at a chosen second so a screenshot shows that exact
--                      frame however long the capture takes (the project's Debris cannot remove it)
--
-- Load it from a ModuleScript or through the project's HTTP file feed:
--   local Inspector = loadstring(game:GetService("HttpService"):GetAsync(url, true))()
-- Studio Edit captures omit particles, so lint in Edit and look in Play (client DataModel).

local RunService = game:GetService("RunService")

local Inspector = {}

export type Finding = { Severity: "error" | "warn", Path: string, Rule: string, Detail: string }
export type StageOptions = { Distance: number?, Origin: Vector3?, Bright: boolean?, Rig: Model?, Victim: Model?, Animation: any? }
export type View = { Zoom: number?, Focus: Vector3?, Fov: number? } -- stage:Camera framing
export type Props = { Target: boolean?, Caster: boolean?, Floor: boolean? } -- stage:Show: which stage props to show
export type Stage = {
	Folder: Folder,
	Caster: Part, -- the sphere effects start from
	Target: Part, -- the cube effects aim at
	Frame: CFrame, -- at the caster (or the rig's root), looking at the target (play effects with this)
	Rig: Model?, -- the caster rig, when staged with one
	Victim: Model?, -- the target rig, when staged with one
	Play: (self: Stage, clip: any?, speed: number?) -> AnimationTrack?, -- plays a clip on the caster rig
	Camera: (self: Stage, kind: string?, view: View?) -> CFrame,
	Show: (self: Stage, props: Props) -> (),
	Clear: (self: Stage) -> (),
}

-- A particle has left smoothly when, at the end of its life, it is transparent, tiny or squashed away.
local GONE_ALPHA = 0.95
local GONE_SIZE = 0.05 -- fraction of the emitter's largest size (and never above 0.05 studs)
local GONE_SQUASH = 1 -- |Squash| at the end of life, and at least 0.5 more than at the start. Calibrate against a held frame.
local SKIP = "InspectIgnore" -- boolean attribute: opt a deliberately hard-edged layer out (say why in a comment)

-- Value and envelope of a sequence at life fraction t.
local function at(sequence: NumberSequence, t: number): (number, number)
	local points = sequence.Keypoints
	local value, envelope = points[#points].Value, points[#points].Envelope
	if t <= points[1].Time then
		value, envelope = points[1].Value, points[1].Envelope
	else
		for index = 2, #points do
			if t <= points[index].Time then
				local a, b = points[index - 1], points[index]
				local u = (t - a.Time) / math.max(b.Time - a.Time, 1e-6)
				value, envelope = a.Value + (b.Value - a.Value) * u, a.Envelope + (b.Envelope - a.Envelope) * u
				break
			end
		end
	end
	return value, envelope
end

local function peak(sequence: NumberSequence): number
	local top = 0
	for _, point in sequence.Keypoints do
		top = math.max(top, math.abs(point.Value) + point.Envelope)
	end
	return top
end

local function relative(root: Instance, item: Instance): string
	return if item == root then root.Name else item:GetFullName():sub(#root:GetFullName() + 2)
end

-- Is the emitter invisible, tiny or squashed away at life fraction `t` (0 start, 1 end)?
local function gone(emitter: ParticleEmitter, t: number): (boolean, string)
	local alpha, alphaSpread = at(emitter.Transparency, t)
	local size, sizeSpread = at(emitter.Size, t)
	local squash = at(emitter.Squash, t)
	local squash0 = at(emitter.Squash, 0)
	local byAlpha = alpha - alphaSpread >= GONE_ALPHA
	local bySize = size + sizeSpread <= math.min(0.05, math.max(0.001, peak(emitter.Size) * GONE_SIZE)) or size + sizeSpread <= 0
	local bySquash = math.abs(squash) >= GONE_SQUASH and math.abs(squash) - math.abs(squash0) >= 0.5
	return byAlpha or bySize or bySquash,
		string.format("Transparency %.2f, Size %.2f (peak %.2f), Squash %.2f", alpha, size, peak(emitter.Size), squash)
end

-- Static pass over `root` and everything under it. Returns the findings and a one-line-per-finding text.
function Inspector.lint(root: Instance): ({ Finding }, string)
	local findings: { Finding } = {}
	local emitters = 0
	for _, item in root:GetDescendants() do
		if item ~= root and item:GetAttribute(SKIP) then
			continue
		end
		if item:IsA("ParticleEmitter") then
			emitters += 1
			local out, numbers = gone(item, 1)
			if not out then
				-- a one-shot flipbook ends on its own last frame: only the picture (endFrame) can say whether that frame is empty
				local flipbook = item.FlipbookLayout ~= Enum.ParticleFlipbookLayout.None and item.FlipbookMode == Enum.ParticleFlipbookMode.OneShot
				table.insert(findings, if flipbook
					then { Severity = "warn", Path = relative(root, item), Rule = "flipbook-exit",
						Detail = "relies on the flipbook's last frame being empty (" .. numbers .. "): confirm with Inspector.endFrame, else fade it too." } :: Finding
					else { Severity = "error", Path = relative(root, item), Rule = "no-exit",
						Detail = "particles pop out at end of life: " .. numbers .. ". Fade Transparency to 1, shrink Size to 0 or squash it away." } :: Finding)
			end
			local entered, start = gone(item, 0)
			if not entered then
				table.insert(findings, { Severity = "warn", Path = relative(root, item), Rule = "pop-in",
					Detail = "particles pop in at birth: " .. start } :: Finding)
			end
			if item.Lifetime.Max > 6 then
				table.insert(findings, { Severity = "warn", Path = relative(root, item), Rule = "long-lifetime",
					Detail = string.format("Lifetime.Max %.1f s keeps the effect alive (and its container) a long time", item.Lifetime.Max) } :: Finding)
			end
		elseif item:IsA("Trail") then
			local alpha = at(item.Transparency, 1)
			local width = at(item.WidthScale, 1)
			if alpha < GONE_ALPHA and width > 0.05 then
				table.insert(findings, { Severity = "error", Path = relative(root, item), Rule = "trail-tail",
					Detail = string.format("trail tail stays visible: Transparency %.2f, WidthScale %.2f", alpha, width) } :: Finding)
			end
		end
	end
	local lines = {}
	for _, finding in findings do
		table.insert(lines, string.format("%s %s [%s] %s", string.upper(finding.Severity), finding.Path, finding.Rule, finding.Detail))
	end
	table.insert(lines, string.format("%d emitters, %d findings", emitters, #findings))
	return findings, table.concat(lines, "\n")
end

-- Repairs what lint flags: every emitter without an exit gets a Transparency that holds its own curve until the last
-- `tail` (0.22) of the particle's life and then fades to 1. Edit-time, on a template; returns the paths it changed.
-- Check the result with lint() and a held frame, and write the template back to the project's source file.
function Inspector.fixExit(root: Instance, tail: number?): { string }
	local start = 1 - (tail or 0.22)
	local changed = {}
	local items = root:GetDescendants()
	table.insert(items, root)
	for _, item in items do
		if item:IsA("ParticleEmitter") and not item:GetAttribute(SKIP) and not gone(item, 1) then
			local keys = {}
			for _, key in item.Transparency.Keypoints do
				if key.Time < start - 1e-4 then
					table.insert(keys, NumberSequenceKeypoint.new(key.Time, key.Value, key.Envelope))
				end
			end
			if #keys == 0 then
				local first, spread = at(item.Transparency, 0)
				table.insert(keys, NumberSequenceKeypoint.new(0, first, spread))
			end
			local held, spread = at(item.Transparency, start)
			table.insert(keys, NumberSequenceKeypoint.new(start, held, spread))
			table.insert(keys, NumberSequenceKeypoint.new(1, 1, 0))
			item.Transparency = NumberSequence.new(keys)
			table.insert(changed, relative(root, item))
		end
	end
	return changed
end

-- Seconds until every emitter under `root` has stopped emitting and its last particle has died.
function Inspector.duration(root: Instance): number
	local longest = 0
	for _, item in root:GetDescendants() do
		if item:IsA("ParticleEmitter") then
			local delay = (item:GetAttribute("EmitDelay") :: number?) or 0
			local hold = (item:GetAttribute("EmitDuration") :: number?) or 0
			local scale = (item:GetAttribute("__thaw") :: number?) or item.TimeScale -- a frozen emitter keeps its real scale here
			longest = math.max(longest, delay + hold + item.Lifetime.Max / math.max(scale, 0.01))
		elseif item:IsA("Trail") then
			longest = math.max(longest, item.Lifetime)
		end
	end
	return longest
end

-- Seconds worth freezing and photographing: early, middle, the last emission, and just before the end.
function Inspector.keyTimes(root: Instance): { number }
	local total = Inspector.duration(root)
	local times = {}
	for _, fraction in { 0.08, 0.25, 0.5, 0.75, 0.93 } do
		table.insert(times, math.floor(total * fraction * 20 + 0.5) / 20)
	end
	return times
end

-- Load every texture under `root` (a template or a folder of them) before the effect is first played. A cold effect can
-- be frozen before its textures arrive and photograph as empty; preload first, or play it once to warm it.
function Inspector.preload(root: Instance)
	game:GetService("ContentProvider"):PreloadAsync({ root })
end

local staged: { AnimationTrack } = {} -- clips playing on stage rigs: hold() freezes them in the effect's frame

-- A held frame lives in this folder, outside the effect: the project's own cleanup (Debris, tweens, Destroy) cannot reach it.
local function holder(): Folder
	local existing = workspace:FindFirstChild("__VFXHold") :: Folder?
	if existing then
		return existing
	end
	local folder = Instance.new("Folder")
	folder.Name = "__VFXHold"
	folder.Parent = workspace
	return folder
end

-- Wait `seconds`, then snapshot the effect under `root` into a holder: each part is cloned bare (so its current size and
-- transparency are kept), and its emitters, lights, beams and decals are moved onto the clone and frozen (TimeScale 0).
-- The frame then stays on screen, however long the next tool call takes, until release(). Call right after playing.
function Inspector.hold(root: Instance, seconds: number)
	task.wait(seconds)
	for _, track in staged do
		if track.IsPlaying then
			track:AdjustSpeed(0) -- the staged rig keeps the pose of this exact frame
		end
	end
	local folder = holder()
	local parts: { Instance } = {}
	for _, item in root:GetDescendants() do
		if item:IsA("BasePart") then
			table.insert(parts, item)
		end
	end
	if root:IsA("BasePart") then
		table.insert(parts, root)
	end
	for _, part in parts do
		local proxy = (part :: BasePart):Clone()
		proxy:ClearAllChildren()
		proxy.Anchored = true
		proxy.Parent = folder
		for _, child in part:GetChildren() do
			if child:IsA("Attachment") or child:IsA("Light") or child:IsA("Decal") or child:IsA("Texture") or child:IsA("SurfaceGui")
				or child:IsA("ParticleEmitter") or child:IsA("Beam") or child:IsA("Trail") then -- emitters sit on parts as well as attachments
				(child :: Instance).Parent = proxy
			end
		end
	end
	for _, item in folder:GetDescendants() do
		if item:IsA("ParticleEmitter") and item:GetAttribute("__thaw") == nil then
			item:SetAttribute("__thaw", item.TimeScale)
			item.TimeScale = 0
			item.Enabled = false
		end
	end
end

-- Clear every held frame and stop the stage rigs' clips.
function Inspector.release()
	local folder = workspace:FindFirstChild("__VFXHold")
	if folder then
		folder:Destroy()
	end
	for _, track in staged do
		track:Stop(0)
	end
	table.clear(staged)
end

local function animatorOf(model: Model): Animator
	local controller: Instance? = model:FindFirstChildOfClass("Humanoid") or model:FindFirstChildOfClass("AnimationController")
	if not controller then
		local made = Instance.new("AnimationController")
		made.Parent = model
		controller = made
	end
	local animator = (controller :: Instance):FindFirstChildOfClass("Animator")
	if not animator then
		local made = Instance.new("Animator")
		made.Parent = controller
		animator = made
	end
	return animator :: Animator
end

-- A scriptless copy of `rig` standing on the floor at `spot`, facing `toward`, its root anchored. A Humanoid stands as
-- the engine stands it (R15: the root's bottom HipHeight above the floor; R6: on its legs); any other rig rests its
-- lowest body part (accessories excluded) on the floor.
local function standIn(rig: Model, spot: Vector3, toward: Vector3, parent: Instance): Model
	local archivable = rig.Archivable
	rig.Archivable = true
	local copy = rig:Clone()
	rig.Archivable = archivable
	for _, item in copy:GetDescendants() do
		if item:IsA("LuaSourceContainer") then
			item:Destroy()
		end
	end
	local root = (copy:FindFirstChild("HumanoidRootPart") or copy.PrimaryPart or copy:FindFirstChildWhichIsA("BasePart", true)) :: BasePart
	local look = root.CFrame.LookVector
	local current = CFrame.new(root.Position) * CFrame.Angles(0, math.atan2(-look.X, -look.Z), 0)
	copy:PivotTo(CFrame.lookAt(spot, Vector3.new(toward.X, spot.Y, toward.Z)) * current:Inverse() * copy:GetPivot())
	local humanoid = copy:FindFirstChildOfClass("Humanoid")
	local leg = copy:FindFirstChild("Left Leg")
	local height: number? = nil -- of the root's centre above the floor
	if humanoid and root.Name == "HumanoidRootPart" then
		if humanoid.RigType == Enum.HumanoidRigType.R15 then
			height = humanoid.HipHeight + root.Size.Y / 2
		elseif leg and leg:IsA("BasePart") then
			height = leg.Size.Y + root.Size.Y / 2
		end
	end
	if height then
		copy:PivotTo(copy:GetPivot() + Vector3.yAxis * (spot.Y + height - root.Position.Y))
	else
		local lowest = math.huge
		for _, part in copy:GetDescendants() do
			if part:IsA("BasePart") and part.Transparency < 1 and not part:FindFirstAncestorWhichIsA("Accessory") then
				local cf, half = part.CFrame, part.Size / 2
				lowest = math.min(lowest, cf.Position.Y - math.abs(cf.RightVector.Y) * half.X - math.abs(cf.UpVector.Y) * half.Y - math.abs(cf.LookVector.Y) * half.Z)
			end
		end
		if lowest < math.huge then
			copy:PivotTo(copy:GetPivot() + Vector3.yAxis * (spot.Y - lowest))
		end
	end
	root.Anchored = true
	if humanoid then
		humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	end
	copy.Parent = parent
	return copy
end

-- One emitter's particle at `fraction` of its life (0.97 by default), shown large beside the target: what its last frame
-- looks like. A particle that is still clearly visible here will vanish midair. Needs a stage; call release() afterwards.
function Inspector.endFrame(stage: Stage, emitter: ParticleEmitter, fraction: number?)
	local proxy = Instance.new("Part")
	proxy.Anchored, proxy.CanCollide, proxy.CanQuery, proxy.Transparency = true, false, false, 1
	proxy.Size, proxy.CFrame = Vector3.one, CFrame.new(stage.Target.Position + Vector3.new(0, 4, 0))
	proxy.Parent = holder()
	local attachment = Instance.new("Attachment")
	attachment.Parent = proxy
	local copy = emitter:Clone()
	copy.Enabled, copy.TimeScale = false, math.max((emitter:GetAttribute("__thaw") :: number?) or emitter.TimeScale, 0.01)
	copy.Parent = attachment
	copy:Emit(1)
	task.wait(copy.Lifetime.Max * (fraction or 0.97) / copy.TimeScale)
	copy:SetAttribute("__thaw", copy.TimeScale)
	copy.TimeScale = 0
end

-- Where did the effect land? Run it a moment after playing. Every effect part (a template's root, a piece) is tested:
--   floating   a part meant for the ground is more than `tolerance` (1.5) studs above the floor under it
--   in-body    a part sits inside a character's bounding box (an effect spawned on a head or a chest by mistake)
-- A part meant for the air (meteors, auras at chest height) opts out with the boolean attribute `Airborne`. The floor is
-- found like the game finds it: a ray down that ignores characters and effects and respects CanCollide.
function Inspector.placement(container: Instance, tolerance: number?): ({ Finding }, string)
	local limit = tolerance or 1.5
	local findings: { Finding } = {}
	local characters: { Model } = {}
	for _, descendant in workspace:GetDescendants() do
		if descendant:IsA("Humanoid") and descendant.Parent and descendant.Parent:IsA("Model") then
			table.insert(characters, descendant.Parent)
		end
	end
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.RespectCanCollide = true
	local ignore: { Instance } = { container }
	for _, character in characters do
		table.insert(ignore, character)
	end
	params.FilterDescendantsInstances = ignore
	for _, item in container:GetDescendants() do
		if item:IsA("BasePart") and not item:GetAttribute("Airborne") and item.Name ~= "Floor" then
			for _, character in characters do
				local cf, size = character:GetBoundingBox()
				local local_ = cf:PointToObjectSpace(item.Position)
				-- above the feet: a ground effect at the soles is where it belongs
				if math.abs(local_.X) <= size.X / 2 + 0.5 and local_.Y > -size.Y / 2 + 1.2 and local_.Y <= size.Y / 2 + 0.5
					and math.abs(local_.Z) <= size.Z / 2 + 0.5 then
					table.insert(findings, { Severity = "error", Path = relative(container, item), Rule = "in-body",
						Detail = "inside " .. character.Name .. "'s bounds at " .. tostring(item.Position) .. ": spawn ground effects on the floor and body effects on the right attachment" } :: Finding)
				end
			end
			local hit = workspace:Raycast(item.Position + Vector3.yAxis * 2, -Vector3.yAxis * 60, params)
			if hit and item.Position.Y - hit.Position.Y > limit and item.Transparency >= 0.95 then
				table.insert(findings, { Severity = "error", Path = relative(container, item), Rule = "floating",
					Detail = string.format("%.1f studs above the floor: ray down from the point, ignoring characters, and place it there (or mark it Airborne)", item.Position.Y - hit.Position.Y) } :: Finding)
			end
		end
	end
	local lines = {}
	for _, finding in findings do
		table.insert(lines, string.format("ERROR %s [%s] %s", finding.Path, finding.Rule, finding.Detail))
	end
	table.insert(lines, #findings .. " findings")
	return findings, table.concat(lines, "\n")
end

-- Hide (true) or restore (false) every ScreenGui in PlayerGui so popups and the HUD stay out of the captures. Client only.
function Inspector.hideUI(hide: boolean)
	local gui = game:GetService("Players").LocalPlayer:WaitForChild("PlayerGui")
	for _, screen in gui:GetChildren() do
		if screen:IsA("ScreenGui") then
			if hide and screen.Enabled then
				screen:SetAttribute("__hidden", true)
				screen.Enabled = false
			elseif not hide and screen:GetAttribute("__hidden") then
				screen:SetAttribute("__hidden", nil)
				screen.Enabled = true
			end
		end
	end
end

-- A sensible sweep for a general read of an effect: whole path, high angle, ground plan, particle detail.
Inspector.views = { { "side", 1 }, { "iso", 1 }, { "top", 1 }, { "close", 0.6 } } :: { { any } } -- { kind, zoom }

-- A dark plate with a caster sphere and a target cube `distance` studs apart, high above the map so nothing else is in view.
-- options.Rig (a character or monster Model) stands a copy at the caster instead of the sphere, so stage:Play(clip) can
-- drive it with an animation that passed AnimationInspector and the effect can be timed to its markers; options.Victim
-- stands a copy at the target instead of the cube (scale, hit height, in-body checks). options.Animation is the default clip.
function Inspector.stage(options: StageOptions?): Stage
	local settings: StageOptions = options or {}
	local distance = settings.Distance or 30
	local origin = settings.Origin or Vector3.new(0, 1000, 0)
	local folder = Instance.new("Folder")
	folder.Name = "__VFXStage"
	local function part(name: string, size: Vector3, position: Vector3, color: Color3, shape: Enum.PartType?): Part
		local p = Instance.new("Part")
		p.Name, p.Size, p.Position, p.Color = name, size, position, color
		p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
		p.Material = Enum.Material.Concrete -- matte: no sun glare on the plate
		if shape then
			p.Shape = shape
		end
		p.Parent = folder
		return p
	end
	local floor = part("Floor", Vector3.new(260, 1, 260), origin - Vector3.yAxis * 0.5, if settings.Bright then Color3.fromRGB(200, 200, 205) else Color3.fromRGB(28, 28, 34))
	floor.CanQuery, floor.CanCollide = true, true -- effects ray down to find the ground, and a character can stand on it
	local caster = part("Caster", Vector3.one * 4, origin + Vector3.yAxis * 2, Color3.fromRGB(80, 170, 255), Enum.PartType.Ball)
	local target = part("Target", Vector3.one * 4, origin + Vector3.new(0, 2, -distance), Color3.fromRGB(235, 70, 70))
	folder.Parent = workspace
	local stage = {
		Folder = folder, Caster = caster, Target = target,
		Frame = CFrame.lookAt(caster.Position, Vector3.new(target.Position.X, caster.Position.Y, target.Position.Z)),
	} :: any
	if settings.Rig then
		local rig = standIn(settings.Rig, Vector3.new(caster.Position.X, origin.Y, caster.Position.Z), target.Position, folder)
		local root = (rig:FindFirstChild("HumanoidRootPart") or rig.PrimaryPart) :: BasePart?
		caster.Transparency = 1
		stage.Rig = rig
		if root then
			stage.Frame = CFrame.lookAt(root.Position, Vector3.new(target.Position.X, root.Position.Y, target.Position.Z))
		end
	end
	if settings.Victim then
		stage.Victim = standIn(settings.Victim, Vector3.new(target.Position.X, origin.Y, target.Position.Z), caster.Position, folder)
		target.Transparency = 1
	end
	-- Plays `clip` (an Animation, an asset id, or a KeyframeSequence where it can be registered; default options.Animation)
	-- on the caster rig and returns the track. Time the effect to the clip: track:GetMarkerReachedSignal("Hit"):Wait(),
	-- then play the effect; Inspector.hold freezes the rig in the same frame as the effect.
	function stage.Play(_: Stage, clip: any?, speed: number?): AnimationTrack?
		local rig = stage.Rig :: Model?
		local source = if clip ~= nil then clip else settings.Animation
		if not rig or source == nil then
			return nil
		end
		local animation = Instance.new("Animation")
		if typeof(source) == "Instance" and (source :: Instance):IsA("Animation") then
			animation.AnimationId = (source :: Animation).AnimationId
		elseif typeof(source) == "Instance" and (source :: Instance):IsA("KeyframeSequence") then
			animation.AnimationId = game:GetService("KeyframeSequenceProvider"):RegisterKeyframeSequence(source :: KeyframeSequence)
		else
			local text = tostring(source)
			animation.AnimationId = if string.find(text, "://", 1, true) then text else "rbxassetid://" .. text
		end
		local animator = animatorOf(rig)
		for _, playing in animator:GetPlayingAnimationTracks() do
			playing:Stop(0)
		end
		local track = animator:LoadAnimation(animation)
		track.Priority = Enum.AnimationPriority.Action
		track:Play(0, 1, speed or 1)
		table.insert(staged, track)
		return track
	end
	-- Scriptable camera. kind: "side" (default, both ends in view), "iso" (high three-quarter), "top" (straight down: ground
	-- shapes), "front" (from beyond the target, looking back at the caster), "behind" (over the caster's shoulder, down
	-- the effect's path), "close" (the target, three-quarter). view.Zoom scales the distance (0.5 is twice as close, 2
	-- twice as far), view.Focus replaces the look-at point (an impact spot, a flying projectile), view.Fov the lens.
	function stage.Camera(_: Stage, kind: string?, view: View?): CFrame
		local framing: View = view or {}
		local middle = (caster.Position + target.Position) / 2
		local wide = math.max(distance * 1.1, 26)
		local look: CFrame
		if kind == "iso" then
			look = CFrame.lookAt(middle + Vector3.new(1, 0.8, 0.9).Unit * wide * 1.25, middle)
		elseif kind == "top" then
			look = CFrame.lookAt(middle + Vector3.new(0, wide * 1.15, 0.001), middle)
		elseif kind == "front" then
			look = CFrame.lookAt(target.Position + Vector3.new(0, 7, -distance * 0.5), middle)
		elseif kind == "behind" then
			look = CFrame.lookAt(caster.Position + Vector3.new(0, 7, 18), target.Position)
		elseif kind == "close" then
			look = CFrame.lookAt(target.Position + Vector3.new(12, 6, 12), target.Position)
		else
			look = CFrame.lookAt(middle + Vector3.new(wide, 8, 0), middle)
		end
		local zoom = framing.Zoom or 1
		local focus = framing.Focus or (if kind == "close" then target.Position elseif kind == "behind" then target.Position else middle)
		if framing.Focus or zoom ~= 1 then
			-- keep the preset's direction, move along it toward or away from the focus
			local from = if framing.Focus then focus + (look.Position - (if kind == "close" then target.Position else middle)) else look.Position
			local away = (from - focus)
			look = CFrame.lookAt(focus + away * zoom, focus)
		end
		-- re-asserted every frame: a game's own camera controller would otherwise take the view back
		RunService:UnbindFromRenderStep("__VFXStageCamera")
		RunService:BindToRenderStep("__VFXStageCamera", Enum.RenderPriority.Camera.Value + 1, function()
			local camera = workspace.CurrentCamera
			if camera then
				camera.CameraType = Enum.CameraType.Scriptable
				camera.CFrame = look
				camera.FieldOfView = framing.Fov or 60
			end
		end)
		return look
	end
	-- Hide or show the stage props, say `stage:Show({ Target = false })` for an unobstructed view of the effect.
	function stage.Show(_: Stage, props: Props)
		for name, prop in { Target = target, Caster = caster, Floor = folder:FindFirstChild("Floor") } :: { [string]: Instance? } do
			local visible = (props :: any)[name]
			if visible ~= nil and prop then
				(prop :: Part).Transparency = if visible then 0 else 1
			end
		end
	end
	function stage.Clear(_: Stage)
		RunService:UnbindFromRenderStep("__VFXStageCamera")
		for _, track in staged do
			track:Stop(0)
		end
		table.clear(staged)
		folder:Destroy()
		local camera = workspace.CurrentCamera
		if camera then
			camera.CameraType = Enum.CameraType.Custom
		end
	end
	return stage :: Stage
end

-- Watches `container` while an effect plays and records anything that vanishes while it can still be seen:
--   part / decal destroyed with Transparency under 0.9      light destroyed while lit
--   emitter destroyed with particles still alive            beam or trail destroyed while enabled
-- Run in Play. Call handle.Stop() after the effect's container is gone (it yields a frame, then returns findings and text).
type Record = { Path: string, Born: number, Seen: number, Enabled: number?, Visible: number, Size: number, Light: number }

function Inspector.watch(container: Instance): { Stop: () -> ({ Finding }, string) }
	local records: { [Instance]: Record } = {}
	local findings: { Finding } = {}
	local ended = false

	local function track(item: Instance)
		if item:IsA("BasePart") or item:IsA("ParticleEmitter") or item:IsA("Beam") or item:IsA("Trail") or item:IsA("Light") or item:IsA("Decal") then
			records[item] = { Path = relative(container, item), Born = os.clock(), Seen = os.clock(), Visible = 1, Size = 1, Light = 0 }
		end
	end
	local function sample(item: Instance, record: Record)
		record.Seen = os.clock()
		if item:IsA("BasePart") then
			record.Visible, record.Size = 1 - item.Transparency, item.Size.Magnitude
		elseif item:IsA("Decal") then
			record.Visible = 1 - item.Transparency
		elseif item:IsA("Light") then
			record.Light = if item.Enabled then item.Brightness else 0
		elseif item:IsA("ParticleEmitter") or item:IsA("Beam") or item:IsA("Trail") then
			if item.Enabled then
				record.Enabled = os.clock()
			end
		end
	end
	local function judge(item: Instance, record: Record)
		local now = os.clock()
		local path = record.Path -- taken while still parented: a removed item can no longer name itself
		local function add(rule: string, detail: string)
			table.insert(findings, { Severity = "error", Path = path, Rule = rule, Detail = detail } :: Finding)
		end
		if now - record.Born < 0.1 then
			return
		end
		if item:IsA("BasePart") and record.Visible > 0.1 and record.Size > 0.3 then
			add("popped", string.format("part removed while visible (Transparency %.2f, size %.1f): fade or scale it out first", 1 - record.Visible, record.Size))
		elseif item:IsA("Decal") and record.Visible > 0.1 then
			add("popped", string.format("decal removed at Transparency %.2f", 1 - record.Visible))
		elseif item:IsA("Light") and record.Light > 0.15 then
			add("popped", string.format("light removed at Brightness %.2f: tween it to 0 first", record.Light))
		elseif item:IsA("ParticleEmitter") then
			local delay = (item:GetAttribute("EmitDelay") :: number?) or 0
			local hold = (item:GetAttribute("EmitDuration") :: number?) or 0
			local emitting = record.Enabled ~= nil or ((item:GetAttribute("EmitCount") :: number?) or item.Rate) > 0
			local lastEmit = math.max(record.Born + delay + hold, record.Enabled or 0)
			local scale = (item:GetAttribute("__thaw") :: number?) or item.TimeScale
			local left = lastEmit + item.Lifetime.Max / math.max(scale, 0.01) - now
			if emitting and left > 0.1 then
				add("cut-off", string.format("emitter removed %.2f s before its last particle dies (Lifetime.Max %.2f): keep the container until then", left, item.Lifetime.Max))
			end
		elseif (item:IsA("Beam") or item:IsA("Trail")) and record.Enabled and now - record.Enabled < (if item:IsA("Trail") then item.Lifetime else 0.05) then
			add("cut-off", item.ClassName .. " removed while still drawn: disable it and wait for its fade")
		end
	end

	for _, item in container:GetDescendants() do
		track(item)
	end
	track(container)
	local added = container.DescendantAdded:Connect(track)
	local removing = container.DescendantRemoving:Connect(function(item)
		local record = records[item]
		if record and not ended then
			judge(item, record)
			records[item] = nil
		end
	end)
	local beat = RunService.Heartbeat:Connect(function()
		for item, record in records do
			sample(item, record)
		end
	end)
	local closing = container.Destroying:Connect(function()
		for item, record in records do
			judge(item, record)
		end
		records = {}
	end)

	return {
		Stop = function()
			task.wait() -- signals are deferred: let a just-destroyed container report its removals first
			ended = true
			added:Disconnect()
			removing:Disconnect()
			beat:Disconnect()
			closing:Disconnect()
			local lines = {}
			for _, finding in findings do
				table.insert(lines, string.format("ERROR %s [%s] %s", finding.Path, finding.Rule, finding.Detail))
			end
			table.insert(lines, #findings .. " findings")
			return findings, table.concat(lines, "\n")
		end,
	}
end

return Inspector
