--!strict
-- UI parity: a short fingerprint of everything visible on screen, per window, so a port can be compared with the original game
-- at the same viewport and state without dumping thousands of elements. Client, during Play (load as a temporary ModuleScript,
-- SKILL.md Scripts); run the same calls in both copies:
--
--   local UIParity = require(module)
--   UIParity.fingerprint()                              -- "viewport WxH", then "<ScreenGui>/<child> <count> <hash>" per window
--   UIParity.fingerprint({ Detail = { "Hud/Shop" } })   -- plus every line of those windows, to see what differs
--   UIParity.sweep(scrollingFrame)                      -- "<canvas y> <count> <hash>" per window-height step, top to bottom
--
-- A line is "T|text|x,y,w,h" or "I|image|x,y,w,h" for each visible text or image inside the viewport (AbsolutePosition and
-- AbsoluteSize, rounded). Same-named children of one ScreenGui are one window. Equal hashes mean equal layout and content.
-- Options:
--   Detail  window keys to list in full
--   Ignore  image ids to skip: decorations repositioned every frame (sparkles, glints)
--   Moving  attribute names: an element with one of them on itself or an ancestor is compared by presence only, since an
--           animated scale changes its rectangle every frame
--   Digits  false keeps digits (by default they become "#", so cash, timers and counters match)
--   Settle  sweep: seconds to wait after each scroll, for content that loads lazily (default 0.5)

local Players = game:GetService("Players")

local UIParity = {}

export type Options = {
	Detail: { string }?,
	Ignore: { string }?,
	Moving: { string }?,
	Digits: boolean?,
	Settle: number?,
}

local function hash(lines: { string }): string
	local h = 7
	for _, line in lines do
		for i = 1, #line do
			h = (h * 131 + string.byte(line, i)) % 2147483647 -- stays exact in a double
		end
	end
	return string.format("%08x", h)
end

local function shown(node: Instance, gui: Instance): boolean
	local current: Instance? = node
	while current and current ~= gui do
		if current:IsA("GuiObject") and not current.Visible then
			return false
		end
		if current:IsA("LayerCollector") and not current.Enabled then
			return false
		end
		current = current.Parent
	end
	return true
end

local function moving(node: Instance, gui: Instance, names: { string }): boolean
	local current: Instance? = node
	while current and current ~= gui do
		for _, name in names do
			if current:GetAttribute(name) then
				return true
			end
		end
		current = current.Parent
	end
	return false
end

-- every visible text and image under `root` inside `clip` (min, max), as sorted lines
local function collect(root: Instance, gui: Instance, clip: { Vector2 }, options: Options): { string }
	local ignore: { [string]: boolean } = {}
	for _, id in options.Ignore or {} do
		ignore[id] = true
	end
	local names = options.Moving or {}
	local lines = {}
	local nodes = root:GetDescendants()
	table.insert(nodes, root)
	for _, node in nodes do
		if not node:IsA("GuiObject") then
			continue
		end
		local o = node :: any
		local p, s = o.AbsolutePosition, o.AbsoluteSize
		if s.X <= 0 or s.Y <= 0 or p.X + s.X <= clip[1].X or p.Y + s.Y <= clip[1].Y or p.X >= clip[2].X or p.Y >= clip[2].Y then
			continue
		end
		local key: string? = nil
		if (o:IsA("TextLabel") or o:IsA("TextButton") or o:IsA("TextBox")) and o.Text ~= "" and o.TextTransparency < 1 then
			key = "T|" .. (if options.Digits == false then o.Text else (string.gsub(o.Text, "%d", "#")))
		elseif (o:IsA("ImageLabel") or o:IsA("ImageButton")) and o.Image ~= "" and o.ImageTransparency < 1 and not ignore[o.Image] then
			key = "I|" .. o.Image
		end
		if key and shown(node, gui) then
			local rect = if #names > 0 and moving(node, gui, names)
				then "~"
				else string.format("%d,%d,%d,%d", math.round(p.X), math.round(p.Y), math.round(s.X), math.round(s.Y))
			table.insert(lines, key .. "|" .. rect)
		end
	end
	table.sort(lines)
	return lines
end

function UIParity.fingerprint(options: Options?): string
	local opts: Options = options or {}
	local gui = (Players.LocalPlayer :: Player):WaitForChild("PlayerGui")
	local viewport = (workspace.CurrentCamera :: Camera).ViewportSize
	local clip = { Vector2.zero, viewport }
	local detail: { [string]: boolean } = {}
	for _, key in opts.Detail or {} do
		detail[key] = true
	end
	local windows: { [string]: { string } } = {}
	for _, screen in gui:GetChildren() do
		if screen:IsA("ScreenGui") and screen.Enabled then
			for _, top in screen:GetChildren() do
				local key = screen.Name .. "/" .. top.Name
				local list = windows[key] or {}
				windows[key] = list
				for _, line in collect(top, gui, clip, opts) do
					table.insert(list, line)
				end
			end
		end
	end
	local keys = {}
	for key, list in windows do
		if #list > 0 then
			table.insert(keys, key)
		end
	end
	table.sort(keys)
	local out = { string.format("viewport %dx%d", viewport.X, viewport.Y) }
	for _, key in keys do
		local list = windows[key]
		table.sort(list)
		table.insert(out, string.format("%s %d %s", key, #list, hash(list)))
		if detail[key] then
			for _, line in list do
				table.insert(out, "  " .. line)
			end
		end
	end
	return table.concat(out, "\n")
end

-- Scrolls `frame` from top to bottom one window height at a time (yields) and fingerprints what shows inside it at each step;
-- puts the canvas back where it was.
function UIParity.sweep(frame: ScrollingFrame, options: Options?): string
	local opts: Options = options or {}
	local gui = (Players.LocalPlayer :: Player):WaitForChild("PlayerGui")
	local start = frame.CanvasPosition
	local maxY = math.max(0, frame.AbsoluteCanvasSize.Y - frame.AbsoluteWindowSize.Y)
	local step = math.max(frame.AbsoluteWindowSize.Y, 50)
	local clip = { frame.AbsolutePosition, frame.AbsolutePosition + frame.AbsoluteWindowSize }
	local out = {}
	local y = 0
	while true do
		local at = math.min(y, maxY)
		frame.CanvasPosition = Vector2.new(start.X, at)
		task.wait(opts.Settle or 0.5)
		local lines = collect(frame, gui, clip, opts)
		table.insert(out, string.format("%d %d %s", at, #lines, hash(lines)))
		if at >= maxY then
			break
		end
		y += step
	end
	frame.CanvasPosition = start
	return table.concat(out, "\n")
end

return UIParity
