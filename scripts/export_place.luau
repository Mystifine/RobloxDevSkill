--!strict
-- Writes every Script, LocalScript and ModuleScript in a saved place file to <out>/<DataModel path><suffix> (Lune,
-- outside Studio): the legacy code of a game being converted (references/rojo-project.md), byte for byte, without
-- passing it through Studio or an agent's context. Suffixes: .server.luau, .client.luau, .luau. Two siblings with one
-- name get ~2, ~3 suffixes.
-- Usage: lune run export_place.luau <place.rbxl or .rbxlx> <out folder>

local fs = require("@lune/fs")
local process = require("@lune/process")
local roblox = require("@lune/roblox")

local placePath, outDir = process.args[1], process.args[2]
assert(placePath and outDir, "usage: lune run export_place.luau <place.rbxl or .rbxlx> <out folder>")
local game = roblox.deserializePlace(fs.readFile(placePath))

local SUFFIX = { Script = ".server.luau", LocalScript = ".client.luau", ModuleScript = ".luau" }

-- a name Windows, macOS and Linux all accept
local function safe(name: string): string
	local clean = string.gsub(name, '[<>:"/\\|%?%*%c]', "_")
	clean = string.gsub(clean, "[%. ]+$", "_")
	return if clean == "" then "_" else clean
end

local used: { [string]: boolean } = {}
local made: { [string]: boolean } = {}
local count, bytes = 0, 0
for _, item in game:GetDescendants() do
	local suffix = SUFFIX[item.ClassName]
	if suffix then
		local parts = {}
		local node: any = item
		while node and node ~= game do
			table.insert(parts, 1, safe(node.Name))
			node = node.Parent
		end
		local folder = outDir .. "/" .. table.concat(parts, "/", 1, #parts - 1)
		if not made[folder] then
			fs.writeDir(folder)
			made[folder] = true
		end
		local base = outDir .. "/" .. table.concat(parts, "/")
		local path, n = base .. suffix, 1
		while used[string.lower(path)] do -- case-insensitive file systems
			n += 1
			path = base .. "~" .. n .. suffix
		end
		used[string.lower(path)] = true
		local source = (item :: any).Source
		fs.writeFile(path, source)
		count += 1
		bytes += #source
	end
end
print(string.format("%d scripts, %d bytes -> %s", count, bytes, outDir))
