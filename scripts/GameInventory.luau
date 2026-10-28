--!strict
-- Game inventory for converting a Studio game into a Rojo project (Studio MCP, Edit mode). Use it before, during and
-- after the migration (references/rojo-project.md):
--
--   scripts(roots?)        every Script, LocalScript and ModuleScript: path, class, run context, lines, and what its
--                          source touches (requires, remotes, DataStores, tags, products, attributes)
--   markdown(entries)      those entries as rows for docs/migration.md
--   content(roots?)        non-script instances per service by class, to compare before and after the switch to Rojo
--   export(first, budget)  a batch of { Path, Class, Source } of at most `budget` characters (small games; a large
--                          game's sources come out of its saved file with export_place.luau instead)
--   leftovers(managed)     scripts outside the Rojo-managed instances after the switch (expected: none)
--
-- The source scan is pattern matching, so treat it as a checklist to confirm by reading, not as a parser.
-- Load: loadstring(game:GetService("HttpService"):GetAsync(url, true))(), or a temporary ModuleScript.

local Inventory = {}

local SERVICES = { "Workspace", "ReplicatedFirst", "ReplicatedStorage", "ServerScriptService", "ServerStorage", "StarterGui",
	"StarterPack", "StarterPlayer", "Lighting", "SoundService", "Teams", "TextChatService", "MaterialService" }

export type Entry = {
	Path: string,
	Class: string,
	RunContext: string,
	Enabled: boolean,
	Lines: number,
	Requires: { string },
	Remotes: { string }, -- remote instances in the place that the source names
	Network: { string }, -- remote calls and handlers it uses (FireServer, OnServerEvent, ...), even on remotes made at runtime
	DataStores: { string }, -- store names, or the expression that builds one
	Tags: { string },
	Products: { string },
	Attributes: { string },
}

local function roots(list: { Instance }?): { Instance }
	if list then
		return list
	end
	local found = {}
	for _, name in SERVICES do
		local ok, service = pcall(game.GetService, game, name)
		if ok and service then
			table.insert(found, service)
		end
	end
	return found
end

local function sorted(set: { [string]: boolean }): { string }
	local list = {}
	for key in set do
		table.insert(list, key)
	end
	table.sort(list)
	return list
end

local function collect(source: string, patterns: { string }): { string }
	local set = {}
	for _, pattern in patterns do
		for match in string.gmatch(source, pattern) do
			set[match] = true
		end
	end
	return sorted(set)
end

-- The argument of every call to one of `names` (Lua patterns), with balanced parentheses: a string literal unquoted,
-- anything else as written (a computed store name), at most 80 characters.
local function calls(source: string, names: { string }): { string }
	local set = {}
	for _, name in names do
		for args in string.gmatch(source, name .. "%s*(%b())") do
			local inner = (string.match(string.gsub(string.sub(args, 2, -2), "%s+", " "), "^%s*(.-)%s*$")) :: string
			-- a literal name, alone or as the first argument (GetProfileStore("PlayerData", template))
			local text = string.match(inner, '^"([^"]*)"%s*$') or string.match(inner, "^'([^']*)'%s*$")
				or string.match(inner, '^"([^"]*)"%s*,') or string.match(inner, "^'([^']*)'%s*,") or inner
			if text == "" then
				text = "(no name)"
			end
			set[if #text > 80 then string.sub(text, 1, 77) .. "..." else text] = true
		end
	end
	return sorted(set)
end

local function property(item: Instance, name: string): any
	local ok, value = pcall(function()
		return (item :: any)[name]
	end)
	return if ok then value else nil
end

local function each(list: { Instance }?, visit: (Instance) -> ())
	for _, root in roots(list) do
		for _, item in root:GetDescendants() do
			visit(item)
		end
	end
end

-- Every script under the roots (default: the services a game keeps content in).
function Inventory.scripts(list: { Instance }?): { Entry }
	local remoteNames = {}
	each(list, function(item)
		if item:IsA("RemoteEvent") or item:IsA("RemoteFunction") or item:IsA("UnreliableRemoteEvent") or item:IsA("BindableEvent") or item:IsA("BindableFunction") then
			remoteNames[item.Name] = true
		end
	end)
	local entries: { Entry } = {}
	each(list, function(item)
		if not item:IsA("LuaSourceContainer") then
			return
		end
		local source = (property(item, "Source") :: string?) or ""
		local remotes = {}
		for name in remoteNames do
			if string.find(source, name, 1, true) then
				table.insert(remotes, name)
			end
		end
		table.sort(remotes)
		local context = property(item, "RunContext")
		local _, newlines = string.gsub(source, "\n", "")
		table.insert(entries, {
			Path = item:GetFullName(),
			Class = item.ClassName,
			RunContext = if typeof(context) == "EnumItem" then context.Name else "",
			Enabled = property(item, "Enabled") ~= false,
			Lines = if source == "" then 0 else newlines + 1,
			Requires = calls(source, { "%f[%w_]require" }),
			Remotes = remotes,
			Network = collect(source, { ":(FireServer)%s*%(", ":(FireClient)%s*%(", ":(FireAllClients)%s*%(", ":(InvokeServer)%s*%(", ":(InvokeClient)%s*%(",
				"%.(OnServerEvent)", "%.(OnClientEvent)", "%.(OnServerInvoke)", "%.(OnClientInvoke)" }),
			-- DataStoreService and the common wrappers (ProfileService, ProfileStore, DataStore2)
			DataStores = calls(source, { "GetDataStore", "GetOrderedDataStore", "GetGlobalDataStore", "GetProfileStore", "ProfileStore%.New", "%f[%w_]DataStore2", "%f[%w_]DataStore2%.Combine" }),
			Tags = collect(source, { "GetTagged%s*%(%s*[\"']([^\"']+)", "GetInstanceAddedSignal%s*%(%s*[\"']([^\"']+)", "AddTag%s*%([^,]+,%s*[\"']([^\"']+)",
				"HasTag%s*%([^,]+,%s*[\"']([^\"']+)", ":AddTag%s*%(%s*[\"']([^\"']+)", ":HasTag%s*%(%s*[\"']([^\"']+)" }),
			Products = collect(source, { "(ProcessReceipt)", "Prompt%a*Purchase%s*%([^,]+,%s*(%d+)", "UserOwnsGamePassAsync%s*%([^,]+,%s*(%d+)" }),
			Attributes = collect(source, { "GetAttribute%s*%(%s*[\"']([^\"']+)", "SetAttribute%s*%(%s*[\"']([^\"']+)" }),
		})
	end)
	return entries
end

-- The entries as markdown table rows: legacy path, class, lines, what it touches, and empty New home / Status columns.
function Inventory.markdown(entries: { Entry }): string
	local lines = { "| Legacy path | Class | Lines | Touches | New home | Status |", "|---|---|---|---|---|---|" }
	for _, entry in entries do
		local touches = {}
		for label, list in { requires = entry.Requires, remotes = entry.Remotes, network = entry.Network, stores = entry.DataStores,
			tags = entry.Tags, products = entry.Products, attributes = entry.Attributes } :: { [string]: { string } } do
			if #list > 0 then
				table.insert(touches, label .. ": " .. table.concat(list, ", ", 1, math.min(#list, 20)) .. (if #list > 20 then string.format(" (+%d more)", #list - 20) else ""))
			end
		end
		table.sort(touches)
		local requiresId = false
		for _, required in entry.Requires do
			requiresId = requiresId or string.match(required, "^%d+$") ~= nil
		end
		table.insert(lines, string.format("| %s | %s%s | %d | %s |  |  |", entry.Path, entry.Class,
			(if entry.Enabled then "" else ", disabled") .. (if requiresId then ", REQUIRES AN ASSET ID" else ""),
			entry.Lines, (string.gsub(table.concat(touches, "; "), "|", "/"))))
	end
	return table.concat(lines, "\n")
end

-- Non-script instances under each root, by class: { [rootName] = { Total = n, Classes = { [class] = n } } }, and a text
-- summary. Take it before the switch and again after; the counts must match.
function Inventory.content(list: { Instance }?): ({ [string]: { Total: number, Classes: { [string]: number } } }, string)
	local result = {}
	local lines = {}
	for _, root in roots(list) do
		local classes, total = {}, 0
		for _, item in root:GetDescendants() do
			if not item:IsA("LuaSourceContainer") then
				classes[item.ClassName] = (classes[item.ClassName] or 0) + 1
				total += 1
			end
		end
		result[root.Name] = { Total = total, Classes = classes }
		table.insert(lines, string.format("%s: %d", root.Name, total))
	end
	return result, table.concat(lines, ", ")
end

-- Sources in a stable order, `budget` characters at a time (default 150,000): call with the returned Next until it is nil.
function Inventory.export(first: number?, budget: number?): { Items: { { Path: string, Class: string, Source: string } }, Next: number?, Total: number }
	local all: { LuaSourceContainer } = {}
	each(nil, function(item)
		if item:IsA("LuaSourceContainer") then
			table.insert(all, item)
		end
	end)
	local items: { { Path: string, Class: string, Source: string } }, used, index = {}, 0, first or 1
	local limit = budget or 150000
	while index <= #all do
		local item = all[index]
		local source = (property(item, "Source") :: string?) or ""
		if #items > 0 and used + #source > limit then
			break
		end
		table.insert(items, { Path = item:GetFullName(), Class = item.ClassName, Source = source })
		used += #source
		index += 1
	end
	return { Items = items, Next = if index <= #all then index else nil, Total = #all }
end

-- Scripts that are not inside any of the `managed` instances (the folders and scripts Rojo maps). After the switch,
-- every script should be Rojo's; anything listed here was missed or is a leftover legacy copy.
function Inventory.leftovers(managed: { Instance }, list: { Instance }?): { string }
	local found = {}
	each(list, function(item)
		if item:IsA("LuaSourceContainer") then
			for _, owner in managed do
				if item == owner or item:IsDescendantOf(owner) then
					return
				end
			end
			table.insert(found, item:GetFullName())
		end
	end)
	table.sort(found)
	return found
end

return Inventory
