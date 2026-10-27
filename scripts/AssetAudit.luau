--!strict
-- Report-first safety audit for Toolbox assets. Run in Studio (Edit) on an inserted asset kept in an isolated container.
--
--   local AssetAudit = require(thisModule)
--   local report = AssetAudit.audit(root)   -- prints findings, returns the report
--   AssetAudit.strip(root)                  -- only after reading the report: removes rejects and junk
--   AssetAudit.audit(root)                  -- re-run until no "reject" findings remain
--
-- Policy: no code from the Toolbox, ever. Every LuaSourceContainer is a reject. If `root` itself is rejected, discard the asset.

export type Severity = "reject" | "warn" | "info"
export type Finding = { Severity: Severity, Path: string, Rule: string, Detail: string }
export type Report = {
	Findings: { Finding },
	AssetIds: { [string]: { string } }, -- id -> where it is referenced
	Descendants: number,
	Rejects: number,
	Warnings: number,
}

local AssetAudit = {}

local REMOTES = { "RemoteEvent", "RemoteFunction", "UnreliableRemoteEvent", "BindableEvent", "BindableFunction" }
local BEHAVIOUR = { "Tool", "ClickDetector", "ProximityPrompt", "Explosion", "Seat", "VehicleSeat" }

-- Plain-text markers that matter in script source or string values.
local SOURCE_MARKERS: { { Label: string, Pattern: string } } = {
	{ Label = "require(<number>)", Pattern = "require%s*%(%s*%d" },
	{ Label = "loadstring", Pattern = "loadstring" },
	{ Label = "getfenv/setfenv", Pattern = "[gs]etfenv" },
	{ Label = "InsertService", Pattern = "InsertService" },
	{ Label = "HttpService", Pattern = "HttpService" },
	{ Label = "MarketplaceService", Pattern = "MarketplaceService" },
	{ Label = "TeleportService", Pattern = "TeleportService" },
	{ Label = "string.char (obfuscation)", Pattern = "string%.char" },
	{ Label = "string.reverse (obfuscation)", Pattern = "string%.reverse" },
	{ Label = "decimal escapes (obfuscation)", Pattern = "\\%d%d%d" },
	{ Label = "url", Pattern = "https?://" },
}

-- Properties that reference other assets, by class.
local ASSET_PROPERTIES: { { Class: string, Props: { string } } } = {
	{ Class = "Sound", Props = { "SoundId" } },
	{ Class = "Animation", Props = { "AnimationId" } },
	{ Class = "Decal", Props = { "Texture" } }, -- Texture inherits Decal
	{ Class = "ImageLabel", Props = { "Image" } },
	{ Class = "ImageButton", Props = { "Image" } },
	{ Class = "MeshPart", Props = { "MeshId", "TextureID" } },
	{ Class = "SpecialMesh", Props = { "MeshId", "TextureId" } },
	{ Class = "ParticleEmitter", Props = { "Texture" } },
	{ Class = "Beam", Props = { "Texture" } },
	{ Class = "Trail", Props = { "Texture" } },
	{ Class = "SurfaceAppearance", Props = { "ColorMap", "NormalMap", "MetalnessMap", "RoughnessMap" } },
}

local function isHiddenCodepoint(code: number): boolean
	return (code >= 0x200B and code <= 0x200F)
		or (code >= 0x2028 and code <= 0x202E)
		or (code >= 0x2060 and code <= 0x2064)
		or code == 0xFEFF
end

local function badName(name: string): string?
	if name == "" or string.find(name, "^%s+$") then
		return "empty or whitespace-only name"
	end
	if #name > 64 then
		return "name longer than 64 characters"
	end
	if string.find(name, "%c") then
		return "name contains control characters"
	end
	local ok, hidden = pcall(function()
		for _, code in utf8.codes(name) do
			if isHiddenCodepoint(code) then
				return true
			end
		end
		return false
	end)
	if not ok then
		return "name is not valid UTF-8"
	end
	if hidden then
		return "name contains zero-width or direction-control characters"
	end
	return nil
end

local function readProperty(instance: Instance, property: string): any
	local ok, value = pcall(function()
		return (instance :: any)[property]
	end)
	return if ok then value else nil
end

local function isEmptyContainer(instance: Instance): boolean
	return (instance:IsA("Model") or instance:IsA("Folder")) and #instance:GetChildren() == 0
end

local function isInertPart(instance: Instance): boolean
	if not instance:IsA("BasePart") or instance:IsA("Terrain") then
		return false
	end
	return instance.Transparency >= 1
		and not instance.CanCollide
		and not instance.CanQuery
		and not instance.CanTouch
		and #instance:GetChildren() == 0
end

function AssetAudit.run(root: Instance): Report
	local report: Report = { Findings = {}, AssetIds = {}, Descendants = 0, Rejects = 0, Warnings = 0 }

	local function add(severity: Severity, instance: Instance, rule: string, detail: string)
		if severity == "reject" then
			report.Rejects += 1
		elseif severity == "warn" then
			report.Warnings += 1
		end
		table.insert(report.Findings, { Severity = severity, Path = instance:GetFullName(), Rule = rule, Detail = detail })
	end

	local function scanText(instance: Instance, text: string, severity: Severity, where: string)
		for _, marker in SOURCE_MARKERS do
			if string.find(text, marker.Pattern) then
				add(severity, instance, "suspicious text", marker.Label .. " in " .. where)
			end
		end
	end

	local items = root:GetDescendants()
	table.insert(items, 1, root)
	report.Descendants = #items - 1

	for _, instance in items do
		local nameProblem = badName(instance.Name)
		if nameProblem then
			add("warn", instance, "odd name", nameProblem)
		end

		if instance:IsA("LuaSourceContainer") then
			add("reject", instance, "script", instance.ClassName .. " - no Toolbox code")
			local source = readProperty(instance, "Source")
			if type(source) == "string" then
				scanText(instance, source, "info", "script source")
			end
		else
			for _, class in REMOTES do
				if instance.ClassName == class then
					add("reject", instance, "remote or bindable", class .. " has no place in a content asset")
				end
			end
			for _, class in BEHAVIOUR do
				if instance:IsA(class) then
					add("warn", instance, "behaviour instance", class .. " - confirm it is wanted")
				end
			end
		end

		if instance:IsA("StringValue") then
			scanText(instance, instance.Value, "warn", "StringValue")
		end
		for attribute, value in instance:GetAttributes() do
			if type(value) == "string" then
				scanText(instance, value, "warn", "attribute " .. attribute)
			end
		end

		for _, entry in ASSET_PROPERTIES do
			if instance:IsA(entry.Class) then
				for _, property in entry.Props do
					local value = readProperty(instance, property)
					if type(value) == "string" and value ~= "" then
						local references = report.AssetIds[value]
						if not references then
							references = {}
							report.AssetIds[value] = references
						end
						table.insert(references, instance:GetFullName() .. "." .. property)
					end
				end
			end
		end

		if isEmptyContainer(instance) then
			add("warn", instance, "empty container", "no children; strip removes it")
		elseif isInertPart(instance) then
			add("warn", instance, "inert part", "invisible, non-colliding, no children; strip removes it")
		end
	end

	return report
end

function AssetAudit.print(report: Report)
	local idCount = 0
	for _ in report.AssetIds do
		idCount += 1
	end
	print(
		string.format(
			"AssetAudit: %d instances, %d reject, %d warn, %d asset ids",
			report.Descendants,
			report.Rejects,
			report.Warnings,
			idCount
		)
	)
	for _, finding in report.Findings do
		print(string.format("[%s] %s | %s: %s", string.upper(finding.Severity), finding.Path, finding.Rule, finding.Detail))
	end
	for id, references in report.AssetIds do
		print(string.format("[ID] %s (%d use%s) e.g. %s", id, #references, if #references == 1 then "" else "s", references[1]))
	end
end

function AssetAudit.audit(root: Instance): Report
	local report = AssetAudit.run(root)
	AssetAudit.print(report)
	return report
end

-- Destroys scripts, remotes/bindables, inert parts and (repeatedly) empty containers under `root`.
-- Returns how many instances were removed. Never removes `root`; if `root` is itself rejected, discard the asset.
function AssetAudit.strip(root: Instance): number
	local removed = 0
	for _, instance in root:GetDescendants() do
		if
			instance:IsDescendantOf(root)
			and (instance:IsA("LuaSourceContainer") or table.find(REMOTES, instance.ClassName) or isInertPart(instance))
		then
			instance:Destroy()
			removed += 1
		end
	end
	repeat
		local changed = false
		for _, instance in root:GetDescendants() do
			if isEmptyContainer(instance) then
				instance:Destroy()
				removed += 1
				changed = true
			end
		end
	until not changed
	return removed
end

return AssetAudit
