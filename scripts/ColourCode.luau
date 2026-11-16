--!strict
-- Review colours for captures (SKILL.md, Make images readable): parts that are hard to tell apart in a screenshot (left from
-- right, a limb's segments, one piece of a build from the next) take flat colours for the shot, then get their own back.
--
--   body(name)               a body part's review colour from its Roblox name (R6 "Left Arm", R15 "LeftUpperArm"), or nil
--   apply(target, options)   recolours a model's parts, or a list of parts, for a capture; returns { Legend, Restore }
--
-- The character's right is warm (arm red, leg yellow), its left cool (leg cyan, arm blue), the torso green and the head
-- magenta: six hues 60 degrees apart, which stay apart after shading (a yellow head beside an orange leg merged in a render).
-- A limb's segments step down the same hue: upper full, lower dark, hand or foot pale. Clothing, textures, surface appearances
-- and decals other than the face are taken off while coded, so the colours show. Other parts (a weapon, hair, a build's pieces)
-- take hues a golden angle apart (Others = "hues", the default when no body part is found) or light grey ("grey", the default
-- on a body, so nothing else wears a limb's colour), or keep theirs ("keep"). Recolour a copy where you can: AnimationInspector.sheet
-- takes `Recolour = ColourCode.apply` and codes only its posed copies.

local ColourCode = {}

export type Options = { Others: string? } -- "hues", "grey" or "keep"
export type Handle = { Legend: { { Name: string, Colour: string } }, Restore: () -> () }

local HUES = { RightArm = 0, RightLeg = 1 / 6, Torso = 2 / 6, LeftLeg = 3 / 6, LeftArm = 4 / 6, Head = 5 / 6 }
local SEGMENTS: { [string]: { any } } = {
	Arm = { "Arm", 1 }, UpperArm = { "Arm", 1 }, LowerArm = { "Arm", 2 }, Hand = { "Arm", 3 },
	Leg = { "Leg", 1 }, UpperLeg = { "Leg", 1 }, LowerLeg = { "Leg", 2 }, Foot = { "Leg", 3 },
	Torso = { "Torso", 1 }, UpperTorso = { "Torso", 1 }, LowerTorso = { "Torso", 2 }, Head = { "Head", 1 },
}
local GREY = Color3.fromRGB(215, 215, 220)
local GOLDEN = 0.618034

function ColourCode.body(name: string): Color3?
	local side, rest = string.match(name, "^(Left) ?(.*)$")
	if not side then
		side, rest = string.match(name, "^(Right) ?(.*)$")
	end
	local segment = SEGMENTS[rest or name]
	if not segment then
		return nil
	end
	local hue = HUES[(side or "") .. segment[1]]
	if not hue then
		return nil
	end
	local step = segment[2]
	return Color3.fromHSV(hue, if step == 3 then 0.5 else 0.85, if step == 2 then 0.6 else 0.92)
end

local function hex(colour: Color3): string
	return string.format("#%02X%02X%02X", math.round(colour.R * 255), math.round(colour.G * 255), math.round(colour.B * 255))
end

function ColourCode.apply(target: Instance | { BasePart }, options: Options?): Handle
	local parts: { BasePart } = {}
	local hidden: { Instance } = {}
	if typeof(target) == "Instance" then
		if target:IsA("BasePart") then
			table.insert(parts, target)
		end
		for _, item in target:GetDescendants() do
			if item:IsA("BasePart") then
				table.insert(parts, item)
			elseif item:IsA("Clothing") or item:IsA("ShirtGraphic") or item:IsA("SurfaceAppearance")
				or (item:IsA("Decal") and item.Name ~= "face") then
				table.insert(hidden, item)
			end
		end
	else
		parts = table.clone(target :: { BasePart })
	end
	local anyBody = false
	for _, part in parts do
		if ColourCode.body(part.Name) then
			anyBody = true
			break
		end
	end
	local others = (options and options.Others) or (if anyBody then "grey" else "hues")
	local saved: { { Part: BasePart, Color: Color3, Material: Enum.Material, Texture: string? } } = {}
	local legend: { { Name: string, Colour: string } } = {}
	local index = 0
	for _, part in parts do
		local colour = ColourCode.body(part.Name)
		if not colour and others ~= "keep" then
			if others == "hues" then
				index += 1
				colour = Color3.fromHSV((index * GOLDEN) % 1, 0.75, 0.9)
			else
				colour = GREY
			end
		end
		if colour then
			local texture = if part:IsA("MeshPart") then part.TextureID else nil
			table.insert(saved, { Part = part, Color = part.Color, Material = part.Material, Texture = texture })
			part.Color, part.Material = colour, Enum.Material.SmoothPlastic
			if part:IsA("MeshPart") then
				part.TextureID = ""
			end
			table.insert(legend, { Name = part.Name, Colour = hex(colour) })
		end
	end
	local parents: { Instance? } = {}
	for i, item in hidden do
		parents[i] = item.Parent
		item.Parent = nil
	end
	table.sort(legend, function(a, b)
		return a.Name < b.Name
	end)
	local restored = false
	return {
		Legend = legend,
		Restore = function()
			if restored then
				return
			end
			restored = true
			for _, entry in saved do
				entry.Part.Color, entry.Part.Material = entry.Color, entry.Material
				if entry.Texture and entry.Part:IsA("MeshPart") then
					entry.Part.TextureID = entry.Texture
				end
			end
			for i, item in hidden do
				item.Parent = parents[i]
			end
		end,
	}
end

return ColourCode
