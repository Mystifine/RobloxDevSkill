--!strict
-- UI bounds audit: nothing leaks out of the box it belongs in. Run it on a mounted UI (Edit mount, or live in Play on the
-- client) at the phone size first, then tablet and desktop:
--
--   local UIBounds = require(thisModule)
--   local findings, text = UIBounds.audit(frame)      -- every visible GuiObject under `frame`
--   print(text)
--
-- Rules (a stroke is drawn OUTSIDE its frame, so a bar's outline adds its thickness on every side):
--   outside-parent  a child, with its own outline, reaches past its parent's edge
--   on-border       an element touches, or comes within 2 px of, another frame's outline (the gold rim, the card border)
--   corner          a child's corner pokes out of its parent's rounded (UICorner) corner
--   outside-root    anything reaches past `frame` itself
-- Deliberate overlaps (a badge on a card's corner, a glow, a shine) opt out with the boolean attribute `AllowBleed`
-- on that element, and the design reason goes in a comment. Scrolling content is skipped: it is meant to leave its frame.
-- Not judged: rotated elements, and taste. Compare screenshots against the design as well.

local UIBounds = {}

export type Finding = { Rule: string, Path: string, Detail: string }

local SLACK = 0.75 -- pixels of tolerance for rounding
local MARGIN = 2 -- pixels content keeps clear of another frame's outline: flush against it still reads as leaking

local function visible(item: Instance, root: Instance): boolean
	local current: Instance? = item
	while current and current ~= root do
		if current:IsA("GuiObject") and not current.Visible then
			return false
		end
		current = current.Parent
	end
	return true
end

-- Thickness of the outline a frame-like object draws around itself (0 for text outlines, hidden or transparent strokes)
local function outline(item: GuiObject): number
	if item:IsA("TextLabel") or item:IsA("TextButton") or item:IsA("TextBox") then
		return 0
	end
	local stroke = item:FindFirstChildOfClass("UIStroke")
	if stroke and stroke.Enabled and stroke.Transparency < 0.95 then
		return stroke.Thickness
	end
	return 0
end

local function rect(item: GuiObject, grow: number): (Vector2, Vector2)
	return item.AbsolutePosition - Vector2.one * grow, item.AbsolutePosition + item.AbsoluteSize + Vector2.one * grow
end

local function cornerRadius(item: GuiObject): number
	local corner = item:FindFirstChildOfClass("UICorner")
	if not corner then
		return 0
	end
	local short = math.min(item.AbsoluteSize.X, item.AbsoluteSize.Y)
	return math.min(corner.CornerRadius.Scale * short + corner.CornerRadius.Offset, short / 2)
end

local function name(root: Instance, item: Instance): string
	local full = item:GetFullName()
	local base = root:GetFullName()
	return if full:sub(1, #base) == base then full:sub(#base + 2) else full
end

-- Is `a` drawn over `b`? Compare the two branches under their common ancestor: higher ZIndex, else later sibling.
local function drawnAbove(a: GuiObject, b: GuiObject): boolean
	local chain: { [Instance]: boolean } = {}
	local cursor: Instance? = b
	while cursor do
		chain[cursor] = true
		cursor = cursor.Parent
	end
	local branchA: Instance = a
	while branchA.Parent and not chain[branchA.Parent] do
		branchA = branchA.Parent
	end
	local common = branchA.Parent
	local branchB: Instance = b
	while branchB.Parent and branchB.Parent ~= common do
		branchB = branchB.Parent
	end
	local za = if branchA:IsA("GuiObject") then branchA.ZIndex else 0
	local zb = if branchB:IsA("GuiObject") then branchB.ZIndex else 0
	if za ~= zb or not common then
		return za > zb
	end
	local siblings = common:GetChildren()
	return (table.find(siblings, branchA) or 0) > (table.find(siblings, branchB) or 0)
end

local function related(a: Instance, b: Instance): boolean
	return a == b or a:IsDescendantOf(b) or b:IsDescendantOf(a)
end

function UIBounds.audit(root: GuiBase2d, options: { Ignore: { string }? }?): ({ Finding }, string)
	local ignore = (options and options.Ignore) or {}
	local findings: { Finding } = {}
	local function add(rule: string, item: Instance, detail: string)
		table.insert(findings, { Rule = rule, Path = name(root, item), Detail = detail })
	end
	local items: { GuiObject } = {}
	for _, item in root:GetDescendants() do
		if item:IsA("GuiObject") and visible(item, root) and not item:GetAttribute("AllowBleed") and not table.find(ignore, item.Name)
			and item.AbsoluteSize.X > 0 and item.AbsoluteSize.Y > 0 and item.Rotation % 180 == 0 then
			table.insert(items, item)
		end
	end
	local rootLow, rootHigh = root.AbsolutePosition, root.AbsolutePosition + root.AbsoluteSize
	for _, item in items do
		local grow = outline(item)
		local low, high = rect(item, grow)
		local parent = item.Parent
		-- scrolling content is allowed to leave its frame
		local scrolled = false
		local walker: Instance? = item.Parent
		while walker and walker ~= root do
			if walker:IsA("ScrollingFrame") then
				scrolled = true
				break
			end
			walker = walker.Parent
		end
		if low.X < rootLow.X - SLACK or low.Y < rootLow.Y - SLACK or high.X > rootHigh.X + SLACK or high.Y > rootHigh.Y + SLACK then
			if not scrolled then
				add("outside-root", item, string.format("reaches %.1f px past the root", math.max(rootLow.X - low.X, rootLow.Y - low.Y, high.X - rootHigh.X, high.Y - rootHigh.Y)))
			end
		end
		if parent and parent:IsA("GuiObject") and parent ~= root and not scrolled and not parent:IsA("ScrollingFrame") then
			local plow, phigh = rect(parent, 0)
			local over = math.max(plow.X - low.X, plow.Y - low.Y, high.X - phigh.X, high.Y - phigh.Y)
			if over > SLACK then
				add("outside-parent", item, string.format("%.1f px past %s (outline %.1f included)", over, parent.Name, grow))
			end
			local radius = cornerRadius(parent)
			local flat = item:IsA("TextLabel") or item:IsA("TextButton") or item:IsA("TextBox") or item:IsA("ImageLabel") or item:IsA("ImageButton")
				or (item.BackgroundTransparency >= 0.95 and grow == 0) -- an invisible layout box draws no corner
			if radius > 2 and over <= SLACK and not flat then
				-- the child's corners against the parent's rounded corners; a rounded child's corner is pulled in along the diagonal
				local pull = (cornerRadius(item) + grow) * (1 - 0.7071)
				local centre = (plow + phigh) / 2
				for _, corner in { Vector2.new(low.X, low.Y), Vector2.new(high.X, low.Y), Vector2.new(low.X, high.Y), Vector2.new(high.X, high.Y) } do
					local left, top = corner.X < centre.X, corner.Y < centre.Y
					local point = corner + Vector2.new(if left then pull else -pull, if top then pull else -pull)
					local cx = if left then plow.X + radius else phigh.X - radius
					local cy = if top then plow.Y + radius else phigh.Y - radius
					local inCorner = (if left then point.X < cx else point.X > cx) and (if top then point.Y < cy else point.Y > cy)
					if inCorner and (point - Vector2.new(cx, cy)).Magnitude > radius + SLACK then
						add("corner", item, string.format("a corner is %.1f px outside %s's rounded corner", (point - Vector2.new(cx, cy)).Magnitude - radius, parent.Name))
						break
					end
				end
			end
		end
	end
	-- an element that touches another frame's outline band (not its own ancestor or descendant)
	for _, frame in items do
		local thickness = outline(frame)
		if thickness > 0 then
			local innerLow, innerHigh = frame.AbsolutePosition, frame.AbsolutePosition + frame.AbsoluteSize
			local outerLow, outerHigh = innerLow - Vector2.one * thickness, innerHigh + Vector2.one * thickness
			for _, other in items do
				-- only elements in the frame's own container: a separate window that happens to overlap is not a leak
				if not related(other, frame) and frame.Parent ~= nil and other:IsDescendantOf(frame.Parent) then
					local grow = outline(other)
					local low, high = rect(other, grow)
					local crosses = low.X < outerHigh.X - SLACK and high.X > outerLow.X + SLACK and low.Y < outerHigh.Y - SLACK and high.Y > outerLow.Y + SLACK
					-- inside the frame itself is fine; the band is what is left between the frame and its outline
					local insideFrame = low.X >= innerLow.X + MARGIN - SLACK and low.Y >= innerLow.Y + MARGIN - SLACK and high.X <= innerHigh.X - MARGIN + SLACK and high.Y <= innerHigh.Y - MARGIN + SLACK
					local clear = high.X <= innerLow.X or low.X >= innerHigh.X or high.Y <= innerLow.Y or low.Y >= innerHigh.Y
					local text = other:IsA("TextLabel") or other:IsA("TextButton") or other:IsA("TextBox")
					local solid = not text and (other.BackgroundTransparency < 0.95 or other:IsA("ImageLabel") or other:IsA("ImageButton"))
					-- only what is drawn above the frame can cover its outline: a drop shadow or backdrop is behind it
					local above = drawnAbove(other, frame)
					if crosses and solid and above and not insideFrame and not clear then
						add("on-border", other, string.format("touches %s's %.1f px outline", frame.Name, thickness))
					end
				end
			end
		end
	end
	local lines = {}
	for _, finding in findings do
		table.insert(lines, string.format("%s %s: %s", string.upper(finding.Rule), finding.Path, finding.Detail))
	end
	table.insert(lines, string.format("%d GuiObjects checked, %d findings", #items, #findings))
	return findings, table.concat(lines, "\n")
end

return UIBounds
