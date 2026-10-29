--!strict
-- Client. Fallback attribute-driven particle player; prefer the project's own player when it has one.
--
-- Per ParticleEmitter (templates store Enabled = false):
--   EmitDelay    seconds after play before the layer starts   (default 0)
--   EmitCount    particles in the initial burst                (default: the emitter's Rate)
--   EmitDuration seconds the emitter stays Enabled afterwards  (default 0 = burst only)
--
-- Counts are scaled on the client by the lower of two factors, with a minimum of 1 for any layer whose count is above 0,
-- so weak devices thin an effect without deleting a layer: a manual graphics level gives level/10, and the measured frame
-- rate gives 1 at 55 fps or more down to 0.3 at 25 fps or less. Automatic, the default and what most phones run, says
-- nothing about the device, so for it the frame rate decides alone.
--
--   local lifetime = ParticlePlayer.play(effectRoot)         -- seconds until the last particle has faded
--   ParticlePlayer.playAndClean(effectRoot)                  -- plays, then destroys the root once everything is done

local RunService = game:GetService("RunService")

type Entry = {
	Start: number,
	Count: number,
	Delay: number,
	Duration: number,
	EmitTime: number?,
}

local ParticlePlayer = {}

local active: { [ParticleEmitter]: Entry } = {}
local connection: RBXScriptConnection? = nil

local FULL_FPS, FLOOR_FPS, FLOOR = 55, 25, 0.3
local frameTime = 1 / 60 -- smoothed seconds per frame, sampled from the first play on
local sampler: RBXScriptConnection? = nil

local function sample(dt: number)
	-- a single hitch (a load, a GC pause) moves the average only a little
	frameTime += (math.min(dt, 0.25) - frameTime) * 0.05
end

local function qualityFactor(): number
	local level = UserSettings().GameSettings.SavedQualityLevel
	local manual = if level == Enum.SavedQualitySetting.Automatic then 1 else level.Value / 10
	local fps = 1 / frameTime
	local measured = math.clamp(FLOOR + (fps - FLOOR_FPS) / (FULL_FPS - FLOOR_FPS) * (1 - FLOOR), FLOOR, 1)
	return math.min(manual, measured)
end

-- Scales a burst count by graphics quality, keeping at least 1 particle for any non-zero layer.
function ParticlePlayer.scaleCount(count: number): number
	if count <= 0 then
		return 0
	end
	return math.max(1, math.round(count * qualityFactor()))
end

local function step()
	local now = os.clock()
	for emitter, entry in active do
		if emitter.Parent == nil then
			active[emitter] = nil
		elseif entry.EmitTime == nil then
			if now - entry.Start >= entry.Delay then
				emitter:Emit(ParticlePlayer.scaleCount(entry.Count))
				if entry.Duration > 0 then
					entry.EmitTime = now
					emitter.Enabled = true
				else
					active[emitter] = nil
				end
			end
		elseif now - entry.EmitTime >= entry.Duration then
			emitter.Enabled = false
			active[emitter] = nil
		end
	end
	if next(active) == nil and connection then
		connection:Disconnect()
		connection = nil
	end
end

-- Starts every emitter under `root` (and `root` itself). Returns how long until the last particle has faded.
function ParticlePlayer.play(root: Instance): number
	assert(RunService:IsClient(), "ParticlePlayer.play can only be called on the client.")
	if sampler == nil then
		sampler = RunService.Heartbeat:Connect(sample) -- one cheap connection for the session
	end
	local now = os.clock()
	local longest = 0
	local function start(emitter: ParticleEmitter)
		local delay = emitter:GetAttribute("EmitDelay")
		local duration = emitter:GetAttribute("EmitDuration")
		local count = emitter:GetAttribute("EmitCount")
		local entry: Entry = {
			Start = now,
			Count = if type(count) == "number" then count else emitter.Rate,
			Delay = if type(delay) == "number" then delay else 0,
			Duration = if type(duration) == "number" then duration else 0,
		}
		emitter.Enabled = false -- reset any prior in-flight state
		active[emitter] = entry
		longest = math.max(longest, entry.Delay + entry.Duration + emitter.Lifetime.Max)
	end
	if root:IsA("ParticleEmitter") then
		start(root)
	end
	for _, descendant in root:GetDescendants() do
		if descendant:IsA("ParticleEmitter") then
			start(descendant)
		end
	end
	if connection == nil and next(active) ~= nil then
		connection = RunService.Heartbeat:Connect(step)
	end
	return longest
end

-- Stops emission under `root` immediately; particles already alive finish fading.
function ParticlePlayer.stop(root: Instance)
	for _, descendant in root:GetDescendants() do
		if descendant:IsA("ParticleEmitter") then
			descendant.Enabled = false
			active[descendant] = nil
		end
	end
end

-- Plays `root`, then destroys it once every delay, burst, duration and particle lifetime has finished (plus `buffer`).
function ParticlePlayer.playAndClean(root: Instance, buffer: number?): number
	local lifetime = ParticlePlayer.play(root) + (buffer or 0.1)
	task.delay(lifetime, function()
		if root.Parent then
			root:Destroy()
		end
	end)
	return lifetime
end

return ParticlePlayer
