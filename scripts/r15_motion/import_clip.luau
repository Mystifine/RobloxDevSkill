--@use AnimationInspector
--# selene: allow(undefined_variable) -- (the --@use line above makes it a local)
-- Makes one baked clip a KeyframeSequence (pipeline.py fills in CLIP, and runs this in Studio, Edit mode), audits it on a
-- real R15, checks by forward kinematics that Roblox plays exactly what Blender baked, and leaves it in ServerStorage.R15ClipImports so
-- the pipeline can read its bytes in pieces (a reply over about 100k characters is cut short).
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")
local ServerStorage = game:GetService("ServerStorage")

local CLIP = HttpService:JSONDecode([==[__CLIP__]==])

local PARENTS = {
	LowerTorso = "HumanoidRootPart",
	UpperTorso = "LowerTorso",
	Head = "UpperTorso",
	LeftUpperArm = "UpperTorso",
	LeftLowerArm = "LeftUpperArm",
	LeftHand = "LeftLowerArm",
	RightUpperArm = "UpperTorso",
	RightLowerArm = "RightUpperArm",
	RightHand = "RightLowerArm",
	LeftUpperLeg = "LowerTorso",
	LeftLowerLeg = "LeftUpperLeg",
	LeftFoot = "LeftLowerLeg",
	RightUpperLeg = "LowerTorso",
	RightLowerLeg = "RightUpperLeg",
	RightFoot = "RightLowerLeg",
}

local B64 = {}
for i, c in string.split("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", "") do
	B64[string.byte(c)] = i - 1
end
local function decode(text: string): buffer
	local length = #text // 4 * 3
	if string.sub(text, -1) == "=" then
		length -= if string.sub(text, -2, -2) == "=" then 2 else 1
	end
	local out = buffer.create(length)
	local at = 0
	for i = 1, #text, 4 do
		local a, b, c, d = string.byte(text, i, i + 3)
		local n = bit32.lshift(B64[a], 18) + bit32.lshift(B64[b], 12) + bit32.lshift(B64[c] or 0, 6) + (B64[d] or 0)
		if at < length then
			buffer.writeu8(out, at, bit32.band(bit32.rshift(n, 16), 255))
		end
		if at + 1 < length then
			buffer.writeu8(out, at + 1, bit32.band(bit32.rshift(n, 8), 255))
		end
		if at + 2 < length then
			buffer.writeu8(out, at + 2, bit32.band(n, 255))
		end
		at += 3
	end
	return out
end

-- frame -> { joint -> CFrame }
local byFrame: { [number]: { [string]: CFrame } } = {}
local frames = {}
for joint, data in CLIP.Joints do
	local raw = decode(data.D)
	local count = data.N
	local hasOffset = data.O
	local at = 0
	for _ = 1, count do
		local frame = buffer.readu16(raw, at)
		local qx = buffer.readi16(raw, at + 2) / 32767
		local qy = buffer.readi16(raw, at + 4) / 32767
		local qz = buffer.readi16(raw, at + 6) / 32767
		local qw = buffer.readi16(raw, at + 8) / 32767
		at += 10
		local px, py, pz = 0, 0, 0
		if hasOffset then
			px = buffer.readi16(raw, at) / 4096
			py = buffer.readi16(raw, at + 2) / 4096
			pz = buffer.readi16(raw, at + 4) / 4096
			at += 6
		end
		local row = byFrame[frame]
		if not row then
			row = {}
			byFrame[frame] = row
			table.insert(frames, frame)
		end
		row[joint] = CFrame.new(px, py, pz, qx, qy, qz, qw)
	end
end
table.sort(frames)

local sequence = Instance.new("KeyframeSequence")
sequence.Name = CLIP.Name
sequence.Loop = CLIP.Loop
sequence.Priority = Enum.AnimationPriority[CLIP.Priority]

local poses = 0
for index, frame in frames do
	local joints = byFrame[frame]
	local key = Instance.new("Keyframe")
	key.Time = frame / CLIP.Fps
	local made: { [string]: Instance } = {}
	local function ensure(name: string): Instance
		local existing = made[name]
		if existing then
			return existing
		end
		local parent = PARENTS[name]
		local holder = if parent then ensure(parent) else key
		local item = Instance.new("Pose")
		item.Name = name
		item.CFrame = joints[name] or CFrame.identity
		item.Weight = if joints[name] then 1 else 0 -- (one that only carries the tree down to a limb overrides nothing)
		item.EasingStyle = Enum.PoseEasingStyle.Linear
		item.EasingDirection = Enum.PoseEasingDirection.In
		item.Parent = holder
		made[name] = item
		poses += 1
		return item
	end
	for name in joints do
		ensure(name)
	end
	for _, marker in CLIP.Markers do
		if marker[2] == frame then
			local m = Instance.new("KeyframeMarker")
			m.Name = marker[1]
			key:AddMarker(m)
		end
	end
	key.Parent = sequence
	if index % 150 == 0 then
		task.wait()
	end
end

for _, old in workspace:GetChildren() do
	if old.Name == "ClipImportRig" then
		old:Destroy()
	end
end
local rig = Players:CreateHumanoidModelFromDescription(Instance.new("HumanoidDescription"), Enum.HumanoidRigType.R15)
rig.Name = "ClipImportRig"
local animate = rig:FindFirstChild("Animate")
if animate then
	animate:Destroy()
end
rig:PivotTo(CFrame.new(0, 200, 0))
rig.Parent = workspace
local humanoid = rig:FindFirstChildOfClass("Humanoid") :: Humanoid
humanoid:BuildRigFromAttachments()
for _, part in rig:GetDescendants() do
	if part:IsA("BasePart") then
		part.Anchored = true
	end
end

-- The audit
local audit = CLIP.Audit or {}
local report = AnimationInspector.audit(rig, sequence, {
	Fps = CLIP.Fps,
	Looped = CLIP.Loop,
	Locomotion = audit.Locomotion,
	Ignore = CLIP.Ignore,
	Feet = audit.Feet,
})

-- Round trip: the rig posed by Roblox at each checked frame against Blender's forward kinematics
local animator = humanoid:FindFirstChildOfClass("Animator") :: Animator
if not animator then
	animator = Instance.new("Animator")
	animator.Parent = humanoid
end
local animation = Instance.new("Animation")
animation.AnimationId = KeyframeSequenceProvider:RegisterKeyframeSequence(sequence)
local track = animator:LoadAnimation(animation)
track.Looped = false
track:Play(0)
track:AdjustSpeed(0)
local joints = {}
for _, item in rig:GetDescendants() do
	if item:IsA("AnimationConstraint") and item.Attachment0 and item.Attachment1 then
		joints[(item.Attachment1.Parent :: Instance).Name] = item
	elseif item:IsA("Motor6D") and item.Part1 then
		joints[item.Part1.Name] = item
	end
end
local function solve(name: string, cache): CFrame
	if cache[name] then
		return cache[name]
	end
	local joint = joints[name]
	local result
	if not joint then
		result = CFrame.identity
	elseif joint:IsA("AnimationConstraint") then
		local parent = solve((joint.Attachment0.Parent :: Instance).Name, cache)
		result = parent * joint.Attachment0.CFrame * joint.Transform * joint.Attachment1.CFrame:Inverse()
	else
		local parent = solve((joint.Part0 :: Instance).Name, cache)
		result = parent * joint.C0 * joint.Transform * joint.C1:Inverse()
	end
	cache[name] = result
	return result
end
local worst, worstAt = 0, ""
for _, check in CLIP.Check or {} do
	track.TimePosition = check.F / CLIP.Fps
	animator:StepAnimations(0.0001)
	local cache = {}
	for name, at in check.P do
		local here = solve(name, cache).Position
		local gap = (here - Vector3.new(at[1], at[2], at[3])).Magnitude
		if gap > worst then
			worst, worstAt = gap, string.format("%s at frame %d", name, check.F)
		end
	end
end
track:Stop(0)
track:Destroy()
animation:Destroy()
rig:Destroy()

local folder = ServerStorage:FindFirstChild("R15ClipImports") or Instance.new("Folder")
folder.Name = "R15ClipImports"
folder.Parent = ServerStorage
local old = folder:FindFirstChild(CLIP.Name)
if old then
	old:Destroy()
end
sequence.Parent = folder

return HttpService:JSONEncode({
	Audit = report.Text,
	Keyframes = #frames,
	Poses = poses,
	Worst = worst,
	WorstAt = worstAt,
})
