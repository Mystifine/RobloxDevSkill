--@use VFXInspector
-- Run through studio_mcp.py in Edit mode: VFXInspector.lint's zoffset-tie rule and Inspector.layer, on a temporary
-- part of emitters. Creates and destroys its own instances.
-- selene: allow(undefined_variable)
local Inspector = VFXInspector
local HttpService = game:GetService("HttpService")
local temporary = {}
local results = {}
local function check(ok, label)
	assert(ok, label)
	table.insert(results, label)
end
-- An emitter that leaves smoothly, so only the rule under test can fire.
local function emitter(parent, name, zOffset, lightEmission)
	local item = Instance.new("ParticleEmitter")
	item.Name = name
	item.ZOffset = zOffset
	item.LightEmission = lightEmission
	item.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.5, 0), NumberSequenceKeypoint.new(1, 1) })
	item.Enabled = false
	item.Parent = parent
	return item
end
local function rules(root)
	local count = {}
	for _, finding in (Inspector.lint(root)) do
		count[finding.Rule] = (count[finding.Rule] or 0) + 1
	end
	return count
end

local ok, failure = pcall(function()
	local folder = Instance.new("Folder")
	folder.Name = "VFXInspectorSpec"
	table.insert(temporary, folder)
	local host = Instance.new("Part")
	host.Parent = folder
	local spark = emitter(host, "Sparks", 0, 1)
	local core = emitter(host, "CoreFlash", 0, 0.5)
	local smoke = emitter(host, "Smoke", 0, 0)
	local ring = emitter(host, "Ring", 0.1, 0)
	emitter(host, "GlowA", 0.5, 1)
	emitter(host, "GlowB", 0.5, 1)
	local other = Instance.new("Part")
	other.Parent = folder
	emitter(other, "Dust", 0, 0)

	check((rules(folder)["zoffset-tie"] or 0) == 1, "one tie found: additive-only ties and emitters on another host are left alone")
	check(#Inspector.layer(folder) == 2, "layer moves all but the back layer of the tie")
	check(rules(folder)["zoffset-tie"] == nil, "no tie is left")
	check(smoke.ZOffset == 0 and smoke.ZOffset < core.ZOffset and core.ZOffset < spark.ZOffset, "smoke behind cores behind sparks")
	-- (ZOffset is stored as a float32, so 0.1 reads back a hair off)
	check(spark.ZOffset < ring.ZOffset and math.abs(ring.ZOffset - 0.1) < 1e-6, "the ring set in front stays in front, unmoved")

	local top = Instance.new("Part")
	top.Parent = folder
	local mist = emitter(top, "Mist", 2, 0)
	local shard = emitter(top, "Shards", 2, 0)
	Inspector.layer(folder)
	check(mist.ZOffset == 2 and math.abs(shard.ZOffset - 2.02) < 1e-6, "a tie at the top spreads by 0.02")

	local ignored = emitter(other, "Haze", 0, 0)
	ignored:SetAttribute("InspectIgnore", true)
	check(rules(folder)["zoffset-tie"] == nil, "an InspectIgnore emitter takes no part in ties")
end)
for _, item in temporary do
	item:Destroy()
end
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
