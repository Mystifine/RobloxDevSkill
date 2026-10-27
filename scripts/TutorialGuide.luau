--!strict
-- Tutorial guidance templates (client). Small, reusable pointers; use the ONE that fits the target, never all at once:
--
--   local Guide = require(thisModule)
--   local spot = Guide.spotlight(screenGui)      -- ScreenGui with IgnoreGuiInset = true
--   spot.Focus(button)                           -- a GuiObject, or a Rect in screen pixels; dark everywhere else
--   spot.Focus(Guide.screenRect(chest))          -- a 3D Model/BasePart: the focus box is its projected bounds
--   spot.Clear()                                 -- lights the screen again; spot.Destroy() removes it
--   local stopArrow = Guide.arrow(chest)         -- bobbing arrow floating above a 3D target
--   local stopBeam = Guide.beam(gatePosition, nil, nil, { gateModel })  -- beam from the character, raised off the floor
--   local unlock = Guide.lock({ shopGui, offersGui }, { Enum.KeyCode.G })  -- hide the HUD the lesson does not use and
--                                                -- sink the keys it forbids; call unlock() on finish, skip and leave
--   local release = Guide.lookAt(chest.Position, 1.5)  -- camera assist for a key reveal; returns the camera early
--
-- Each returns a function (or handle) that fully cleans up; keep it and call it when the step ends. Steps complete on the
-- player's action, not on a Next button. Colours, textures and timings are parameters: match the project's UI style.

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local StarterGui = game:GetService("StarterGui")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local Guide = {}

local DIM = Color3.new(0, 0, 0)
local FLOOR_LIFT = 1.5 -- studs a beam stays above the floor at both ends: never digging into it
local resetToken = 0

-- The reset button callback errors until the CoreGui is ready, so retry briefly; a later call supersedes an earlier one
local function setReset(enabled: boolean)
	resetToken += 1
	local token = resetToken
	task.spawn(function()
		for _ = 1, 15 do
			if token ~= resetToken or pcall(StarterGui.SetCore, StarterGui, "ResetButtonCallback", enabled) then
				return
			end
			task.wait(0.3)
		end
	end)
end

local function camera(): Camera
	return workspace.CurrentCamera :: Camera
end

-- The screen rectangle (pixels) a 3D target's bounds cover, or nil while it is behind the camera
function Guide.screenRect(target: Instance, padding: number?): Rect?
	local cframe, size
	if target:IsA("Model") then
		cframe, size = target:GetBoundingBox()
	elseif target:IsA("BasePart") then
		cframe, size = target.CFrame, target.Size
	else
		return nil
	end
	local low, high = Vector2.new(math.huge, math.huge), Vector2.new(-math.huge, -math.huge)
	for x = -1, 1, 2 do
		for y = -1, 1, 2 do
			for z = -1, 1, 2 do
				local point = (camera():WorldToViewportPoint(cframe:PointToWorldSpace(size / 2 * Vector3.new(x, y, z))))
				if point.Z <= 0 then
					return nil
				end
				low = Vector2.new(math.min(low.X, point.X), math.min(low.Y, point.Y))
				high = Vector2.new(math.max(high.X, point.X), math.max(high.Y, point.Y))
			end
		end
	end
	local pad = padding or 12
	return Rect.new(low - Vector2.one * pad, high + Vector2.one * pad)
end

-- A dark screen with a rounded hole: a frame the size of the hole whose UIStroke is so thick it runs off every edge of the
-- screen (the stroke is the dark). Four invisible sinks around the hole stop input everywhere except on the target.
function Guide.spotlight(screen: ScreenGui, darkness: number?)
	local hole = Instance.new("Frame")
	hole.Name = "SpotlightHole"
	hole.BackgroundTransparency = 1
	hole.Visible = false
	hole.Parent = screen
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 18)
	corner.Parent = hole
	local stroke = Instance.new("UIStroke")
	stroke.Color, stroke.Transparency = DIM, darkness or 0.35
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Parent = hole
	local sinks = {}
	for index = 1, 4 do
		local sink = Instance.new("Frame")
		sink.Name = "SpotlightSink" .. index
		sink.BackgroundTransparency, sink.Active, sink.Visible = 1, true, false
		sink.Parent = screen
		sinks[index] = sink
	end
	local handle = {}
	function handle.Focus(target: GuiObject | Rect?, padding: number?)
		local rect: Rect? = if typeof(target) == "Rect" then target
			elseif target then Rect.new(target.AbsolutePosition, target.AbsolutePosition + target.AbsoluteSize) else nil
		if not rect then
			handle.Clear()
			return
		end
		local pad = padding or 10
		local min, max = rect.Min - Vector2.one * pad, rect.Max + Vector2.one * pad
		local view = screen.AbsoluteSize
		stroke.Thickness = math.max(view.X, view.Y) * 1.5
		hole.Visible = true
		TweenService:Create(hole, TweenInfo.new(0.25, Enum.EasingStyle.Quad), {
			Position = UDim2.fromOffset(min.X, min.Y), Size = UDim2.fromOffset(max.X - min.X, max.Y - min.Y),
		}):Play()
		local rects = { -- above, below, left, right of the hole
			{ 0, 0, view.X, min.Y }, { 0, max.Y, view.X, view.Y - max.Y },
			{ 0, min.Y, min.X, max.Y - min.Y }, { max.X, min.Y, view.X - max.X, max.Y - min.Y },
		}
		for index, sink in sinks do
			local r = rects[index]
			sink.Position, sink.Size, sink.Visible = UDim2.fromOffset(r[1], r[2]), UDim2.fromOffset(math.max(0, r[3]), math.max(0, r[4])), true
		end
	end
	function handle.Clear()
		hole.Visible = false
		for _, sink in sinks do
			sink.Visible = false
		end
	end
	function handle.Destroy()
		hole:Destroy()
		for _, sink in sinks do
			sink:Destroy()
		end
	end
	return handle
end

-- A bobbing arrow above a 3D target (Model or BasePart), seen through walls, small and clear of its top
function Guide.arrow(target: Instance, text: string?, color: Color3?): () -> ()
	local part = if target:IsA("Model") then target.PrimaryPart or target:FindFirstChildWhichIsA("BasePart") else target
	local gui = Instance.new("BillboardGui")
	gui.Adornee, gui.AlwaysOnTop, gui.Size = part :: BasePart, true, UDim2.fromOffset(60, 60)
	gui.StudsOffsetWorldSpace = Vector3.new(0, (part :: BasePart).Size.Y / 2 + 3, 0)
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency, label.Size = 1, UDim2.fromScale(1, 1)
	label.Text, label.TextScaled, label.TextColor3 = text or "▼", true, color or Color3.fromRGB(255, 205, 70)
	label.Font = Enum.Font.GothamBlack
	label.Parent = gui
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	local bob = RunService.Heartbeat:Connect(function()
		label.Position = UDim2.fromOffset(0, math.sin(os.clock() * 6) * 6) -- about a hertz, a few pixels
	end)
	return function()
		bob:Disconnect()
		gui:Destroy()
	end
end

-- A beam from the character to `goal` (a point), both ends FLOOR_LIFT above the floor so it never digs in; fades at both
-- ends. Pass a chevron `texture` to animate flow. `ignore` lists what the floor ray must skip besides the character (the
-- target model). Returns the stop function.
function Guide.beam(goal: Vector3, color: Color3?, texture: string?, ignore: { Instance }?): () -> ()
	local player = Players.LocalPlayer
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not root or not humanoid then
		return function() end
	end
	local params = RaycastParams.new()
	params.FilterType, params.RespectCanCollide = Enum.RaycastFilterType.Exclude, true
	local skipped = { character }
	for _, item in ignore or {} do
		table.insert(skipped, item)
	end
	params.FilterDescendantsInstances = skipped
	local ground = workspace:Raycast(goal + Vector3.yAxis * 4, -Vector3.yAxis * 40, params)
	local anchor = Instance.new("Part")
	anchor.Anchored, anchor.CanCollide, anchor.CanQuery, anchor.CanTouch, anchor.Transparency = true, false, false, false, 1
	anchor.Size, anchor.Position = Vector3.one, (if ground then ground.Position else goal) + Vector3.yAxis * FLOOR_LIFT
	anchor.Parent = workspace
	local far = Instance.new("Attachment")
	far.Parent = anchor
	local near = Instance.new("Attachment")
	near.Position = Vector3.new(0, FLOOR_LIFT - (humanoid.HipHeight + root.Size.Y / 2), 0) -- the same height over the floor
	near.Parent = root
	local beam = Instance.new("Beam")
	beam.Attachment0, beam.Attachment1 = near, far
	beam.FaceCamera, beam.Segments, beam.Width0, beam.Width1 = true, 24, 1.2, 1.2
	beam.Color = ColorSequence.new(color or Color3.fromRGB(90, 190, 255))
	beam.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.1, 0.2),
		NumberSequenceKeypoint.new(0.9, 0.2), NumberSequenceKeypoint.new(1, 1),
	}) -- the fades need the segments: a two-keypoint beam draws nothing
	if texture then
		beam.Texture, beam.TextureMode, beam.TextureLength, beam.TextureSpeed = texture, Enum.TextureMode.Static, 3, 1.5
	end
	beam.Parent = anchor
	return function()
		near:Destroy()
		anchor:Destroy()
	end
end

-- Camera assist for a key reveal: turns the camera to look at `point`, holds it, and hands control back (also if you call
-- the returned function early, e.g. on skip). Never use it during movement lessons.
function Guide.lookAt(point: Vector3, hold: number?): () -> ()
	local cam = camera()
	local previous = cam.CameraType
	cam.CameraType = Enum.CameraType.Scriptable
	local tween = TweenService:Create(cam, TweenInfo.new(0.6, Enum.EasingStyle.Quad), { CFrame = CFrame.lookAt(cam.CFrame.Position, point) })
	tween:Play()
	local done = false
	local function release()
		if not done then
			done = true
			tween:Cancel()
			cam.CameraType = previous
		end
	end
	task.delay(0.6 + (hold or 1.5), release)
	return release
end

-- Hides every GuiObject/ScreenGui in `hide`, sinks `keys` and disables the reset button while a lesson runs; the returned
-- function restores all three. The server must still refuse out-of-order requests and keep the player alive: this is the
-- client half of an enforced tutorial. Keep the lock state out of the save (leaving mid-tutorial resets the run).
function Guide.lock(hide: { Instance }, keys: { Enum.KeyCode }?): () -> ()
	local restore = {}
	for _, item in hide do
		if item:IsA("ScreenGui") then
			table.insert(restore, { item, "Enabled", item.Enabled })
			item.Enabled = false
		elseif item:IsA("GuiObject") then
			table.insert(restore, { item, "Visible", item.Visible })
			item.Visible = false
		end
	end
	setReset(false)
	if keys and #keys > 0 then
		ContextActionService:BindActionAtPriority("TutorialLock", function()
			return Enum.ContextActionResult.Sink
		end, false, Enum.ContextActionPriority.High.Value, table.unpack(keys))
	end
	return function()
		ContextActionService:UnbindAction("TutorialLock")
		setReset(true)
		for _, entry in restore do
			if (entry[1] :: Instance).Parent then
				(entry[1] :: any)[entry[2] :: string] = entry[3]
			end
		end
	end
end

return Guide
