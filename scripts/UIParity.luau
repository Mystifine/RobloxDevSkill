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
-- A line is "T|text|x,y,w,h" or "I|image|x,y,w,h" (AbsolutePosition and AbsoluteSize, rounded) for each text or image the
-- engine draws: Visible up to an enabled ScreenGui, not fully transparent, and at least partly on screen and inside every
-- ancestor that clips. Clipping follows the engine: ClipsDescendants (a ScrollingFrame clips to its window) is ignored on and
-- under a rotated GuiObject, and a CanvasGroup always clips to its box. An empty TextBox shows its placeholder; a sprite-sheet
-- image adds its rectangle to the id ("I|id@x,y,w,h|..."). Same-named children of one ScreenGui are one window. Equal hashes
-- mean equal layout and content.
-- Options:
--   Detail      window keys to list in full
--   Ignore      image ids to skip: decorations repositioned every frame (sparkles, glints)
--   Moving      attribute names: an element with a truthy one on itself or an ancestor is compared by presence only, since
--               an animated scale changes its rectangle every frame
--   KeepDigits  true keeps digits; by default they become "#", so cash, timers and counters match
--   Settle      sweep: seconds to wait after each scroll, for content that loads lazily (default 0.5)

local GuiService = game:GetService("GuiService")
local Players = game:GetService("Players")

local UIParity = {}

export type Options = {
	Detail: { string }?,
	Ignore: { string }?,
	Moving: { string }?,
	KeepDigits: boolean?,
	Settle: number?,
}

type Context = { Options: Options, Ignore: { [string]: boolean }, Moving: { string }, Low: Vector2, High: Vector2 }

local MAX_SWEEP_STEPS = 500 -- a canvas that keeps growing (an endless feed) stops here

local function hash(lines: { string }): string
	local h = 7
	for _, line in lines do
		for i = 1, #line do
			h = (h * 131 + string.byte(line, i)) % 2147483647 -- stays exact in a double
		end
	end
	return string.format("%08x", h)
end

-- one call's settings, and the whole screen in GUI coordinates (AbsolutePosition counts from below the top-bar inset)
local function context(options: Options?): Context
	local opts: Options = options or {}
	local ignore: { [string]: boolean } = {}
	for _, id in (opts.Ignore or {}) :: { string } do
		ignore[id] = true
	end
	local inset = GuiService:GetGuiInset()
	local viewport = (workspace.CurrentCamera :: Camera).ViewportSize
	return { Options = opts, Ignore = ignore, Moving = (opts.Moving or {}) :: { string }, Low = -inset, High = viewport - inset }
end

-- what a text or image shows ("T|..." or "I|..."), or nil when it shows nothing
local function content(node: Instance, ctx: Context): string?
	if node:IsA("TextLabel") or node:IsA("TextButton") or node:IsA("TextBox") then
		local o = node :: any
		local text: string = o.Text
		if text == "" and node:IsA("TextBox") then
			text = node.PlaceholderText
		end
		if text == "" or o.TextTransparency >= 1 or o.MaxVisibleGraphemes == 0 then
			return nil
		end
		return "T|" .. (if ctx.Options.KeepDigits then text else (string.gsub(text, "%d", "#")))
	elseif node:IsA("ImageLabel") or node:IsA("ImageButton") then
		local o = node :: any
		local image: string = o.Image
		if image == "" or o.ImageTransparency >= 1 or ctx.Ignore[image] then
			return nil
		end
		local size: Vector2 = o.ImageRectSize
		if size.X > 0 and size.Y > 0 then
			local offset: Vector2 = o.ImageRectOffset
			return string.format("I|%s@%d,%d,%d,%d", image, offset.X, offset.Y, size.X, size.Y)
		end
		return "I|" .. image
	end
	return nil
end

local function tagged(item: Instance, names: { string }): boolean
	for _, name in names do
		if item:GetAttribute(name) then
			return true
		end
	end
	return false
end

-- Walks from `node` up to its ScreenGui: whether the engine draws it at all (Visible all the way up, the ScreenGui enabled,
-- no CanvasGroup faded out), whether it or an ancestor carries a Moving attribute, and the window it can be drawn in (the
-- screen cut down by every ancestor that clips).
local function place(node: Instance, ctx: Context): (boolean, boolean, Vector2, Vector2)
	local low, high = ctx.Low, ctx.High
	local chain: { GuiObject } = {}
	local moving = false
	local current: Instance? = node
	while current and not current:IsA("LayerCollector") do
		if current:IsA("GuiObject") then
			if not current.Visible or (current:IsA("CanvasGroup") and current.GroupTransparency >= 1) then
				return false, false, low, high
			end
			table.insert(chain, current)
		end
		moving = moving or tagged(current, ctx.Moving)
		current = current.Parent
	end
	local layer = current :: LayerCollector?
	if not layer or not layer:IsA("ScreenGui") or not layer.Enabled then
		return false, false, low, high
	end
	moving = moving or tagged(layer, ctx.Moving)
	local rotated = false
	for i = #chain, 2, -1 do -- top down; chain[1] is the node itself, which clips only its children
		local frame = chain[i]
		rotated = rotated or frame.Rotation ~= 0
		if frame:IsA("CanvasGroup") or (frame.ClipsDescendants and not rotated) then
			local size = if frame:IsA("ScrollingFrame") then frame.AbsoluteWindowSize else frame.AbsoluteSize
			low = low:Max(frame.AbsolutePosition)
			high = high:Min(frame.AbsolutePosition + size)
		end
	end
	return true, moving, low, high
end

-- every text and image under `root` (itself included) that shows, as sorted lines
local function collect(root: Instance, ctx: Context): { string }
	local lines = {}
	local nodes = root:GetDescendants()
	table.insert(nodes, root)
	for _, node in nodes do
		local key = content(node, ctx)
		if key then
			local shows, moving, low, high = place(node, ctx)
			local o = node :: GuiObject
			local p, s = o.AbsolutePosition, o.AbsoluteSize
			if shows and s.X > 0 and s.Y > 0 and p.X < high.X and p.Y < high.Y and p.X + s.X > low.X and p.Y + s.Y > low.Y then
				local rect = if moving
					then "~"
					else string.format("%d,%d,%d,%d", math.round(p.X), math.round(p.Y), math.round(s.X), math.round(s.Y))
				table.insert(lines, key .. "|" .. rect)
			end
		end
	end
	table.sort(lines)
	return lines
end

function UIParity.fingerprint(options: Options?): string
	local ctx = context(options)
	local gui = (Players.LocalPlayer :: Player):WaitForChild("PlayerGui")
	local viewport = (workspace.CurrentCamera :: Camera).ViewportSize
	local detail: { [string]: boolean } = {}
	for _, key in (ctx.Options.Detail or {}) :: { string } do
		detail[key] = true
	end
	local windows: { [string]: { string } } = {}
	for _, screen in gui:GetChildren() do
		if screen:IsA("ScreenGui") and screen.Enabled then
			for _, top in screen:GetChildren() do
				local key = screen.Name .. "/" .. top.Name
				local list = windows[key] or {}
				windows[key] = list
				for _, line in collect(top, ctx) do
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

-- Scrolls `frame` (a ScrollingFrame in a ScreenGui) from top to bottom one window height at a time (yields) and fingerprints
-- what shows inside it at each step, following a canvas that grows as it loads; puts the canvas back where it was, also when
-- something fails.
function UIParity.sweep(frame: ScrollingFrame, options: Options?): string
	assert(typeof(frame) == "Instance" and frame:IsA("ScrollingFrame"), "UIParity.sweep: expected a ScrollingFrame")
	local layer = frame:FindFirstAncestorWhichIsA("LayerCollector")
	assert(layer and layer:IsA("ScreenGui"), "UIParity.sweep: the ScrollingFrame must be in a ScreenGui")
	local ctx = context(options)
	local settle = ctx.Options.Settle or 0.5
	local start = frame.CanvasPosition
	local ok, result = pcall(function(): string
		local out = {}
		local y = 0
		for _ = 1, MAX_SWEEP_STEPS do
			local at = math.min(y, math.max(0, frame.AbsoluteCanvasSize.Y - frame.AbsoluteWindowSize.Y))
			frame.CanvasPosition = Vector2.new(start.X, at)
			task.wait(settle)
			local lines = collect(frame, ctx)
			table.insert(out, string.format("%d %d %s", at, #lines, hash(lines)))
			if at >= math.max(0, frame.AbsoluteCanvasSize.Y - frame.AbsoluteWindowSize.Y) then
				return table.concat(out, "\n")
			end
			y = at + math.max(frame.AbsoluteWindowSize.Y, 50)
		end
		table.insert(out, string.format("stopped after %d steps: the canvas kept growing", MAX_SWEEP_STEPS))
		return table.concat(out, "\n")
	end)
	frame.CanvasPosition = start
	if not ok then
		error(result, 0)
	end
	return result
end

return UIParity
