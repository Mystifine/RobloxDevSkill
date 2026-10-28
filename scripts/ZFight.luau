--!nonstrict
-- Z-fighting check and fix for Studio builds. Two visible faces that look the same way, lie in the same plane and
-- overlap fight over the same pixels and flicker in game. In Studio only exact coincidence fights (a 0.002-stud gap was
-- already clean at 1500 studs); moving a face 0.03 studs out also covers renderers with a coarser depth buffer.
--
--   audit(root)    report only: every visible fighting face pair (an overlap buried inside an opaque part is skipped),
--                  and every two decals or textures that share a face and a ZIndex (they flicker the same way)
--   settle(root)   fix: of two fighting faces, the one whose part is thinner behind it (a plate, a trim, an overlay)
--                  moves 0.03 studs out by growing its part on that side, so nothing else of the part shifts and no gap
--                  opens; between equals, the later one. Tied decals get distinct ZIndex. Repeats until nothing moves;
--                  running it twice moves nothing.
--
-- Analyses Parts (blocks, cylinder ends), WedgeParts and CornerWedgeParts. MeshParts, unions and terrain are not.
-- Load: loadstring(game:GetService("HttpService"):GetAsync(url, true))(), or a temporary ModuleScript. Edit mode.

local ZFight = {}

ZFight.SETTLE = {
	tol = .015, -- faces closer than this along their normal are fighting
	sep = .03, -- ... and are moved this far apart
	max = .24, -- a face never moves further than this
	window = .3, -- faces within this of each other are weighed against one another
	minArea = .02, -- overlaps smaller than this, or thinner than minWidth, are left alone
	minWidth = .02,
	skew = .12, -- planes that part by more than this across their overlap cross: an edge, not a fight
	skewArea = 4, -- faces a hair off parallel are only weighed where they overlap this much,
	skewWidth = .5, -- this wide (the slivers along the seams of a terrain are left alone)
	passes = 8,
}

local V3, CF = Vector3.new, CFrame.new
local pi, cos, sin = math.pi, math.cos, math.sin
local DISC = 20 -- sides of the polygon standing in for a cylinder's end
local CELL = 16 -- cell of the grid used to tell whether a point is buried
local REGION = 128 -- faces are compared region by region (see addFace)

local function polyArea(p)
	local s, n = 0, #p
	local x0, y0 = p[n - 1], p[n]
	for i = 1, n, 2 do
		local x1, y1 = p[i], p[i + 1]
		s += x0 * y1 - x1 * y0
		x0, y0 = x1, y1
	end
	return s / 2
end

--- Intersection of two convex counter-clockwise polygons (flat arrays of x, y).
local function clipPoly(subject, clipper)
	local out = subject
	local n = #clipper
	for i = 1, n, 2 do
		local m = #out
		if m == 0 then
			return out
		end
		local ax, ay = clipper[i], clipper[i + 1]
		local j = if i + 2 > n then 1 else i + 2
		local ex, ey = clipper[j] - ax, clipper[j + 1] - ay
		local inp = out
		out = {}
		local k = 0
		local px, py = inp[m - 1], inp[m]
		local sp = ex * (py - ay) - ey * (px - ax)
		for q = 1, m, 2 do
			local qx, qy = inp[q], inp[q + 1]
			local sq = ex * (qy - ay) - ey * (qx - ax)
			if sq >= 0 then
				if sp < 0 then
					local t = sp / (sp - sq)
					out[k + 1], out[k + 2] = px + (qx - px) * t, py + (qy - py) * t
					k += 2
				end
				out[k + 1], out[k + 2] = qx, qy
				k += 2
			elseif sp >= 0 then
				local t = sp / (sp - sq)
				out[k + 1], out[k + 2] = px + (qx - px) * t, py + (qy - py) * t
				k += 2
			end
			px, py, sp = qx, qy, sq
		end
	end
	return out
end

--- Whether point p (in the pass's frame) is inside the solid of a part. The solid is taken a touch larger than it is,
--- so that a point on the seam between two parts counts as inside them.
local function insidePart(r, p)
	local l = r.cf:PointToObjectSpace(p)
	local x, y, z = l.X, l.Y, l.Z
	local s = r.size
	local hx, hy, hz = s.X / 2, s.Y / 2, s.Z / 2
	local e = -.002
	local shape = r.shape
	if shape == "Ball" then
		local radius = math.min(hx, hy, hz) - e
		return x * x + y * y + z * z <= radius * radius
	end
	if math.abs(x) > hx - e or math.abs(y) > hy - e or math.abs(z) > hz - e then
		return false
	end
	if shape == "Cylinder" then
		local radius = math.min(hy, hz) - e
		return y * y + z * z <= radius * radius
	elseif shape == "Wedge" then
		return (y + hy) / s.Y <= (z + hz) / s.Z - e
	elseif shape == "CornerWedge" then
		local f = (y + hy) / s.Y
		return f <= (x + hx) / s.X - e and f <= (hz - z) / s.Z - e
	end
	return true
end

local function cellKey(ix, iy, iz)
	return ((ix + 4096) * 8192 + (iy + 4096)) * 8192 + (iz + 4096)
end

--- One pass over the model. Returns how many faces it moved and how many it could not; with `dry`, moves nothing and
--- returns the visible fighting pairs instead.
local function settlePass(root, touched, dry)
	local S = ZFight.SETTLE
	local floor, abs, huge = math.floor, math.abs, math.huge
	local minW = S.minWidth
	local SEARCH = S.window * 2 -- how far apart two planes' offsets may be for their faces to be compared

	-- the visible parts, in the order they were built, in a frame near them (so the arithmetic stays exact far from
	-- the place origin)
	local recs = {}
	local origin
	for _, inst in root:GetDescendants() do
		if inst:IsA("BasePart") and inst.Transparency < 1 then
			local shape = if inst:IsA("WedgePart") then "Wedge"
				elseif inst:IsA("CornerWedgePart") then "CornerWedge"
				elseif inst:IsA("Part") then inst.Shape.Name
				else nil
			if shape then
				if not origin then
					local p = inst.CFrame.Position
					origin = V3(floor(p.X), floor(p.Y), floor(p.Z))
				end
				recs[#recs + 1] = { inst = inst, i = #recs + 1, shape = shape, cf = inst.CFrame - origin, size = inst.Size, opaque = inst.Transparency <= .02 }
			end
		end
	end

	-- opaque parts by the grid cells they touch: a pair of faces buried inside one of them cannot be seen
	local cells, big = {}, {}
	for _, r in recs do
		if r.opaque then
			local cf, s = r.cf, r.size
			local p, ax, ay, az = cf.Position, cf.XVector, cf.YVector, cf.ZVector
			local hx, hy, hz = s.X / 2, s.Y / 2, s.Z / 2
			local e = V3(abs(ax.X) * hx + abs(ay.X) * hy + abs(az.X) * hz, abs(ax.Y) * hx + abs(ay.Y) * hy + abs(az.Y) * hz, abs(ax.Z) * hx + abs(ay.Z) * hy + abs(az.Z) * hz)
			local lo, hi = p - e, p + e
			r.lo, r.hi = lo, hi
			local x0, y0, z0 = floor(lo.X / CELL), floor(lo.Y / CELL), floor(lo.Z / CELL)
			local x1, y1, z1 = floor(hi.X / CELL), floor(hi.Y / CELL), floor(hi.Z / CELL)
			if (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1) > 2000 then
				big[#big + 1] = r
			else
				for ix = x0, x1 do
					for iy = y0, y1 do
						for iz = z0, z1 do
							local key = cellKey(ix, iy, iz)
							local list = cells[key]
							if not list then
								list = {}
								cells[key] = list
							end
							list[#list + 1] = r
						end
					end
				end
			end
		end
	end
	local function buried(p, ra, rb)
		local x, y, z = p.X, p.Y, p.Z
		local list = cells[cellKey(floor(x / CELL), floor(y / CELL), floor(z / CELL))]
		for _ = 1, 2 do
			if list then
				for _, r in list do
					if r ~= ra and r ~= rb then
						local lo, hi = r.lo, r.hi
						if x >= lo.X and x <= hi.X and y >= lo.Y and y <= hi.Y and z >= lo.Z and z <= hi.Z and insidePart(r, p) then
							return true
						end
					end
				end
			end
			list = big
		end
		return false
	end

	-- The flat faces of every part, grouped by the way they look and by their plane. k1 is the side of the part
	-- (1..6: +X -X +Y -Y +Z -Z) that grows to move the face out; a slope moves out by lengthening its foot (k1) and
	-- raising its top (k2), by f1 and f2 studs for each stud it moves.
	local faces = {}
	local groups, groupList, coarse = {}, {}, {}
	local function groupKey(x, y, z)
		return ((x + 1000) * 2001 + (y + 1000)) * 2001 + (z + 1000)
	end
	--- The group of faces looking along n: normals are rounded to a thousandth, and one that falls right beside a
	--- rounding boundary also looks in the group across it, so that two parts turned the same way are never split.
	local function groupFor(n)
		local x, y, z = n.X * 1000, n.Y * 1000, n.Z * 1000
		local rx, ry, rz = math.round(x), math.round(y), math.round(z)
		local key = groupKey(rx, ry, rz)
		local g = groups[key]
		if g then
			return g
		end
		local ox = if abs(abs(x - rx) - .5) < .02 then (if x > rx then 1 else -1) else 0
		local oy = if abs(abs(y - ry) - .5) < .02 then (if y > ry then 1 else -1) else 0
		local oz = if abs(abs(z - rz) - .5) < .02 then (if z > rz then 1 else -1) else 0
		if ox ~= 0 or oy ~= 0 or oz ~= 0 then
			for ix = 0, abs(ox) do
				for iy = 0, abs(oy) do
					for iz = 0, abs(oz) do
						local other = groups[groupKey(rx + ix * ox, ry + iy * oy, rz + iz * oz)]
						if other and other.n:Dot(n) > .9999995 then
							return other
						end
					end
				end
			end
		end
		local rn = V3(rx, ry, rz).Unit
		local ax, ay, az = abs(rn.X), abs(rn.Y), abs(rn.Z)
		local ref = if ax <= ay and ax <= az then Vector3.xAxis elseif ay <= az then Vector3.yAxis else Vector3.zAxis
		local u = rn:Cross(ref).Unit
		g = { n = n, u = u, v = rn:Cross(u), w = rn, regions = {}, id = #groupList + 1 }
		groups[key] = g
		groupList[g.id] = g
		local ckey = groupKey(math.round(n.X * 100), math.round(n.Y * 100), math.round(n.Z * 100))
		local list = coarse[ckey]
		if not list then
			list = {}
			coarse[ckey] = list
		end
		list[#list + 1] = g
		return g
	end
	local function addFace(r, depth, n, verts, k1, f1, k2, f2)
		local g = groupFor(n)
		local u, v = g.u, g.v
		local poly = table.create(#verts * 2)
		local u0, u1, v0, v1 = huge, -huge, huge, -huge
		for i, p in verts do
			local a, b = p:Dot(u), p:Dot(v)
			poly[i * 2 - 1], poly[i * 2] = a, b
			u0, u1, v0, v1 = math.min(u0, a), math.max(u1, a), math.min(v0, b), math.max(v1, b)
		end
		if polyArea(poly) < 0 then
			local m = #poly
			for i = 1, m // 2, 2 do
				local j = m - i
				poly[i], poly[i + 1], poly[j], poly[j + 1] = poly[j], poly[j + 1], poly[i], poly[i + 1]
			end
		end
		local f = { r = r, depth = depth, n = n, d = n:Dot(verts[1]), g = g, poly = poly, u0 = u0, u1 = u1, v0 = v0, v1 = v1, seq = #faces + 1, k1 = k1, f1 = f1 or 1, k2 = k2, f2 = f2 }
		faces[#faces + 1] = f
		-- Faces are sorted by the offset of their plane, to find the ones lying in nearly the same plane. Two faces that
		-- are a hair off parallel have offsets that drift apart with distance from where they are measured, so they are
		-- measured from the middle of each region the face reaches into, and compared region by region.
		local lo, hi = verts[1], verts[1]
		for i = 2, #verts do
			lo, hi = lo:Min(verts[i]), hi:Max(verts[i])
		end
		f.lo, f.hi = lo, hi
		for ix = floor((lo.X - SEARCH) / REGION), floor((hi.X + SEARCH) / REGION) do
			for iy = floor((lo.Y - SEARCH) / REGION), floor((hi.Y + SEARCH) / REGION) do
				for iz = floor((lo.Z - SEARCH) / REGION), floor((hi.Z + SEARCH) / REGION) do
					local key = cellKey(ix, iy, iz)
					local region = g.regions[key]
					if not region then
						region = { centre = V3(ix + .5, iy + .5, iz + .5) * REGION, buckets = {}, all = {} }
						g.regions[key] = region
					end
					local bk = floor((f.d - n:Dot(region.centre)) / SEARCH)
					local list = region.buckets[bk]
					if not list then
						list = {}
						region.buckets[bk] = list
					end
					list[#list + 1] = f
					region.all[#region.all + 1] = f
				end
			end
		end
	end
	for _, r in recs do
		local cf, s, shape = r.cf, r.size, r.shape
		local sx, sy, sz = s.X, s.Y, s.Z
		local hx, hy, hz = sx / 2, sy / 2, sz / 2
		local X, Y, Z = cf.XVector, cf.YVector, cf.ZVector
		if shape == "Block" then
			addFace(r, sx, X, { cf * V3(hx, -hy, -hz), cf * V3(hx, hy, -hz), cf * V3(hx, hy, hz), cf * V3(hx, -hy, hz) }, 1)
			addFace(r, sx, -X, { cf * V3(-hx, -hy, -hz), cf * V3(-hx, hy, -hz), cf * V3(-hx, hy, hz), cf * V3(-hx, -hy, hz) }, 2)
			addFace(r, sy, Y, { cf * V3(-hx, hy, -hz), cf * V3(hx, hy, -hz), cf * V3(hx, hy, hz), cf * V3(-hx, hy, hz) }, 3)
			addFace(r, sy, -Y, { cf * V3(-hx, -hy, -hz), cf * V3(hx, -hy, -hz), cf * V3(hx, -hy, hz), cf * V3(-hx, -hy, hz) }, 4)
			addFace(r, sz, Z, { cf * V3(-hx, -hy, hz), cf * V3(hx, -hy, hz), cf * V3(hx, hy, hz), cf * V3(-hx, hy, hz) }, 5)
			addFace(r, sz, -Z, { cf * V3(-hx, -hy, -hz), cf * V3(hx, -hy, -hz), cf * V3(hx, hy, -hz), cf * V3(-hx, hy, -hz) }, 6)
		elseif shape == "Cylinder" then
			local radius = math.min(hy, hz)
			for _, sign in { 1, -1 } do
				local ring = table.create(DISC)
				for k = 1, DISC do
					local a = 2 * pi * k / DISC
					ring[k] = cf * V3(sign * hx, cos(a) * radius, sin(a) * radius)
				end
				addFace(r, sx, X * sign, ring, if sign > 0 then 1 else 2)
			end
		elseif shape == "Wedge" then
			local len = math.sqrt(sy * sy + sz * sz)
			addFace(r, sx, X, { cf * V3(hx, -hy, -hz), cf * V3(hx, -hy, hz), cf * V3(hx, hy, hz) }, 1)
			addFace(r, sx, -X, { cf * V3(-hx, -hy, -hz), cf * V3(-hx, -hy, hz), cf * V3(-hx, hy, hz) }, 2)
			addFace(r, sy, -Y, { cf * V3(-hx, -hy, -hz), cf * V3(hx, -hy, -hz), cf * V3(hx, -hy, hz), cf * V3(-hx, -hy, hz) }, 4)
			addFace(r, sz, Z, { cf * V3(-hx, -hy, hz), cf * V3(hx, -hy, hz), cf * V3(hx, hy, hz), cf * V3(-hx, hy, hz) }, 5)
			addFace(r, sy * sz / len, cf:VectorToWorldSpace(V3(0, sz, -sy).Unit),
				{ cf * V3(-hx, -hy, -hz), cf * V3(hx, -hy, -hz), cf * V3(hx, hy, hz), cf * V3(-hx, hy, hz) }, 6, len / sy, 3, len / sz)
		elseif shape == "CornerWedge" then
			local apex = cf * V3(hx, hy, -hz)
			local lenX, lenZ = math.sqrt(sx * sx + sy * sy), math.sqrt(sz * sz + sy * sy)
			addFace(r, sy, -Y, { cf * V3(-hx, -hy, -hz), cf * V3(hx, -hy, -hz), cf * V3(hx, -hy, hz), cf * V3(-hx, -hy, hz) }, 4)
			addFace(r, sx, X, { cf * V3(hx, -hy, -hz), cf * V3(hx, -hy, hz), apex }, 1)
			addFace(r, sz, -Z, { cf * V3(-hx, -hy, -hz), cf * V3(hx, -hy, -hz), apex }, 6)
			addFace(r, sx * sy / lenX, cf:VectorToWorldSpace(V3(-sy, sx, 0).Unit),
				{ cf * V3(-hx, -hy, -hz), cf * V3(-hx, -hy, hz), apex }, 2, lenX / sy, 3, lenX / sx)
			addFace(r, sy * sz / lenZ, cf:VectorToWorldSpace(V3(0, sz, sy).Unit),
				{ cf * V3(-hx, -hy, hz), cf * V3(hx, -hy, hz), apex }, 5, lenZ / sy, 3, lenZ / sz)
		end
	end
	task.wait()

	-- pairs of faces of different parts that look the same way, lie within the window of each other and overlap
	local linked = {}
	local function link(a, b, info)
		local nb = a.nb
		if not nb then
			nb = {}
			a.nb, a.ni = nb, {}
			linked[#linked + 1] = a
		end
		nb[#nb + 1] = b
		a.ni[#nb] = info
	end
	--- Links faces fa and fb if their overlap (polyB is the outline of fb in the u, v of group g, like fa.poly) is big
	--- enough and their planes come within the window of each other there. Records how far the plane of fa is in front
	--- of the plane of fb across the overlap: lo at least, hi at most. The two normals differ at least by float noise,
	--- so the offsets of the planes from the origin cannot be compared instead.
	local function weigh(fa, fb, g, polyB, minArea, minWidth)
		local inter = clipPoly(fa.poly, polyB)
		if #inter < 6 then
			return
		end
		local area = polyArea(inter)
		if area < minArea then
			return
		end
		local x0, x1, y0, y1 = huge, -huge, huge, -huge
		for k = 1, #inter, 2 do
			x0, x1, y0, y1 = math.min(x0, inter[k]), math.max(x1, inter[k]), math.min(y0, inter[k + 1]), math.max(y1, inter[k + 1])
		end
		local w, h = x1 - x0, y1 - y0
		if math.min(w, h) < minWidth or area / (2 * (w + h)) < minWidth / 4 then
			return
		end
		local u, v = g.u, g.v
		local na, nb = fa.n, fb.n
		local wa, wb = g.w:Dot(na), g.w:Dot(nb)
		local lo, hi = huge, -huge
		for k = 1, #inter, 2 do
			local base = u * inter[k] + v * inter[k + 1]
			local ahead = (fa.d - na:Dot(base)) / wa - (fb.d - nb:Dot(base)) / wb
			lo, hi = math.min(lo, ahead), math.max(hi, ahead)
		end
		if lo < S.window and hi > -S.window and hi - lo <= S.skew then
			local info = { inter = inter, area = area, g = g, a = fa, b = fb, lo = lo, hi = hi }
			link(fa, fb, info)
			link(fb, fa, info)
		end
	end
	local byU = function(p, q)
		return p.u0 < q.u0
	end
	local tried = {}
	for _, g in groups do
		for _, region in g.regions do
			local centre = region.centre
			for bk, list in region.buckets do
				local other = region.buckets[bk + 1]
				if #list + (if other then #other else 0) >= 2 then
					local items = table.clone(list)
					if other then
						table.move(other, 1, #other, #items + 1, items)
					end
					for i, f in items do
						f.here = i <= #list -- in this bucket, not the next
						f.off = f.d - f.n:Dot(centre)
					end
					table.sort(items, byU)
					local count = #items
					for i = 1, count - 1 do
						local fa = items[i]
						local reach = fa.u1 - minW
						for j = i + 1, count do
							local fb = items[j]
							if fb.u0 >= reach then
								break
							end
							if (fa.here or fb.here) and fa.r ~= fb.r and fb.v0 < fa.v1 - minW and fa.v0 < fb.v1 - minW
								and abs(fa.off - fb.off) < SEARCH then
								local pair = math.min(fa.seq, fb.seq) * 4194304 + math.max(fa.seq, fb.seq)
								if not tried[pair] then
									tried[pair] = true
									weigh(fa, fb, g, fb.poly, S.minArea, minW)
								end
							end
						end
					end
				end
			end
		end
	end
	task.wait()

	-- Faces a fraction of a degree off parallel fall into different groups, and fight all the same wherever their planes
	-- cross (a cap laid on a slope it almost matches). Groups that look nearly the same way are compared too, region by
	-- region, for overlaps big enough to see.
	local function outlineIn(f, g)
		local fg, p = f.g, f.poly
		local wn = fg.w:Dot(f.n)
		local out = table.create(#p)
		for i = 1, #p, 2 do
			local base = fg.u * p[i] + fg.v * p[i + 1]
			local at = base + fg.w * ((f.d - f.n:Dot(base)) / wn)
			out[i], out[i + 1] = at:Dot(g.u), at:Dot(g.v)
		end
		if polyArea(out) < 0 then
			local m = #out
			for i = 1, m // 2, 2 do
				local j = m - i
				out[i], out[i + 1], out[j], out[j + 1] = out[j], out[j + 1], out[i], out[i + 1]
			end
		end
		return out
	end
	local pad = S.window
	for _, g1 in groupList do
		local n1 = g1.n
		local cx, cy, cz = math.round(n1.X * 100), math.round(n1.Y * 100), math.round(n1.Z * 100)
		for ix = cx - 1, cx + 1 do
			for iy = cy - 1, cy + 1 do
				for iz = cz - 1, cz + 1 do
					for _, g2 in coarse[groupKey(ix, iy, iz)] or {} do
						if g2.id > g1.id and n1:Dot(g2.n) > .99996 then
							for key, r1 in g1.regions do
								local r2 = g2.regions[key]
								if r2 then
									-- each face of the smaller lot against the faces of the larger whose planes pass near it
									local few, many = r1, r2
									if #few.all > #many.all then
										few, many = many, few
									end
									local centre = many.centre
									for _, fa in few.all do
										local b0 = floor((fa.d - fa.n:Dot(centre)) / SEARCH)
										for bk = b0 - 3, b0 + 3 do
											for _, fb in many.buckets[bk] or {} do
												local alo, ahi, blo, bhi = fa.lo, fa.hi, fb.lo, fb.hi
												if fa.r ~= fb.r and alo.X - pad < bhi.X and blo.X - pad < ahi.X and alo.Y - pad < bhi.Y
													and blo.Y - pad < ahi.Y and alo.Z - pad < bhi.Z and blo.Z - pad < ahi.Z then
													local pair = math.min(fa.seq, fb.seq) * 4194304 + math.max(fa.seq, fb.seq)
													if not tried[pair] then
														tried[pair] = true
														weigh(fa, fb, fa.g, outlineIn(fb, fa.g), S.skewArea, S.skewWidth)
													end
												end
											end
										end
									end
								end
							end
						end
					end
				end
			end
		end
	end
	task.wait()

	--- Whether the overlap of two faces can be seen: a point of it, just outside the faces, is not inside an opaque part.
	local function exposed(info)
		local known = info.exposed
		if known == nil then
			local inter = info.inter
			local m = #inter
			local cx, cy = 0, 0
			for k = 1, m, 2 do
				cx += inter[k]
				cy += inter[k + 1]
			end
			cx, cy = cx / (m / 2), cy / (m / 2)
			-- u, v and w are square to the rounded normal of the group, the faces to their own: a point with given u, v
			-- coordinates is brought onto the plane of a face by going along w
			local fa, fb, g = info.a, info.b, info.g
			local u, v, w = g.u, g.v, g.w
			local na, nb = fa.n, fb.n
			local wa, wb = w:Dot(na), w:Dot(nb)
			-- the middle of the overlap, and points two thirds of the way to eight corners spread round its edge
			local corners = m / 2
			known = false
			for i = 0, math.min(corners, 8) do
				local x, y = cx, cy
				if i > 0 then
					local k = (if corners > 8 then math.floor((i - 1) * corners / 8) else i - 1) * 2 + 1
					x, y = (cx + 2 * inter[k]) / 3, (cy + 2 * inter[k + 1]) / 3
				end
				local base = u * x + v * y
				local out = math.max((fa.d - na:Dot(base)) / wa, (fb.d - nb:Dot(base)) / wb) + .012
				if not buried(base + w * out, fa.r, fb.r) then
					known = true
					info.at = base + w * ((fa.d - na:Dot(base)) / wa) + origin -- a visible point of the fight, in world space
					break
				end
			end
			info.exposed = known
		end
		return known
	end

	local tol, sep, clear = S.tol, S.sep, S.sep - .004
	if dry then
		local found = {}
		for _, f in linked do
			for k in f.nb do
				local info = f.ni[k]
				if info.a == f and info.lo < tol and info.hi > -tol and exposed(info) then
					found[#found + 1] = info
				end
			end
		end
		return found
	end

	-- Thick parts stay where they are. Thinner ones (plates, trims, overlays) and, between equals, the ones built later
	-- move out in front of whatever they were fighting.
	table.sort(linked, function(p, q)
		if p.depth ~= q.depth then
			return p.depth > q.depth
		elseif p.r.i ~= q.r.i then
			return p.r.i < q.r.i
		end
		return p.seq < q.seq
	end)
	local moved, stuck = 0, 0
	local least, most, cands = {}, {}, {}
	for _, f in linked do
		local nb, ni = f.nb, f.ni
		-- least[k] .. most[k]: how far this face is in front of its k-th neighbour across their overlap, where that
		-- neighbour has been placed
		local fighting = false
		for k, o in nb do
			local out = o.out
			if out then
				local info = ni[k]
				local lo, hi = info.lo, info.hi
				if info.a ~= f then
					lo, hi = -hi, -lo
				end
				lo, hi = lo - out, hi - out
				least[k], most[k] = lo, hi
				if not fighting and lo < tol and hi > -tol and exposed(info) then
					fighting = true
				end
			else
				least[k] = false
			end
		end
		local g = 0
		if fighting then
			table.clear(cands)
			for k = 1, #nb do
				local lo = least[k]
				if lo and sep - lo > 0 then
					cands[#cands + 1] = sep - lo
				end
			end
			table.sort(cands)
			g = nil
			for _, c in cands do
				if c > S.max then
					break
				end
				local ok = true
				for k = 1, #nb do
					local lo = least[k]
					if lo and lo + c < clear and most[k] + c > -clear and exposed(ni[k]) then
						ok = false
						break
					end
				end
				if ok then
					g = c
					break
				end
			end
			if not g then
				stuck += 1
				g = 0
			end
		end
		f.out = g
		if g > 0 then
			moved += 1
			local grow = f.r.grow
			if not grow then
				grow = { 0, 0, 0, 0, 0, 0 }
				f.r.grow = grow
			end
			grow[f.k1] = math.max(grow[f.k1], g * f.f1)
			if f.k2 then
				grow[f.k2] = math.max(grow[f.k2], g * f.f2)
			end
		end
	end

	-- a face moves by growing its part on that side, never by shifting the part: its other faces stay where they are
	for _, r in recs do
		local grow = r.grow
		if grow then
			local inst = r.inst
			local s = inst.Size
			inst.Size = V3(s.X + grow[1] + grow[2], s.Y + grow[3] + grow[4], s.Z + grow[5] + grow[6])
			inst.CFrame *= CF((grow[1] - grow[2]) / 2, (grow[3] - grow[4]) / 2, (grow[5] - grow[6]) / 2)
			touched[inst] = true
		end
	end
	return moved, stuck
end

-- Decals and textures on the same face of the same part with the same ZIndex, both visible: they flicker too.
local function decalTies(root)
	local ties = {}
	local parts = root:GetDescendants()
	if root:IsA("BasePart") then
		table.insert(parts, root)
	end
	for _, part in parts do
		if part:IsA("BasePart") then
			local seen = {}
			for _, child in part:GetChildren() do
				if child:IsA("Decal") and child.Transparency < 1 then -- Texture is a Decal
					local key = child.Face.Name .. "/" .. child.ZIndex
					if seen[key] then
						table.insert(ties, { part = part, first = seen[key], second = child })
					else
						seen[key] = child
					end
				end
			end
		end
	end
	return ties
end

local function relative(root, item)
	return if item == root then root.Name else item:GetFullName():sub(#root:GetFullName() + 2)
end

-- How a fighting pair shows: two different surfaces flicker; one surface on a textured material shimmers (each part
-- tiles its texture from its own origin); one smooth surface looks unchanged. settle() fixes all three.
local SMOOTH = { SmoothPlastic = true, Neon = true, Glass = true, ForceField = true }
local RANK = { flicker = 1, shimmer = 2, hidden = 3 }
local function look(a, b)
	if a.Color ~= b.Color or a.Material ~= b.Material or a.MaterialVariant ~= b.MaterialVariant or math.abs(a.Transparency - b.Transparency) > 1e-3 then
		return "flicker"
	end
	return if SMOOTH[a.Material.Name] then "hidden" else "shimmer"
end

--- Lists what flickers under `root` without changing anything. Returns the count, a text report (visible flicker
--- first, largest overlaps first) and the pairs ({ A, B, Area, At, Look } for faces; { A, B, Face } for decals).
function ZFight.audit(root: Instance, limit: number?)
	local fights = settlePass(root, {}, true)
	local counts = { flicker = 0, shimmer = 0, hidden = 0 }
	for _, info in fights do
		info.look = look(info.a.r.inst, info.b.r.inst)
		counts[info.look] += 1
	end
	table.sort(fights, function(p, q)
		if p.look ~= q.look then
			return RANK[p.look] < RANK[q.look]
		end
		return p.area > q.area
	end)
	local ties = decalTies(root)
	local lines, pairs = {}, {}
	for index, info in fights do
		local a, b = info.a.r.inst, info.b.r.inst
		table.insert(pairs, { A = a, B = b, Area = info.area, At = info.at, Look = info.look })
		if index <= (limit or 15) then
			table.insert(lines, string.format("%s %s <-> %s: %.2f studs² at (%.1f, %.1f, %.1f)", string.upper(info.look), relative(root, a), relative(root, b),
				info.area, info.at.X, info.at.Y, info.at.Z))
		end
	end
	if #fights > (limit or 15) then
		table.insert(lines, string.format("... %d more face pairs", #fights - (limit or 15)))
	end
	for _, tie in ties do
		table.insert(pairs, { A = tie.first, B = tie.second, Face = tie.first.Face })
		table.insert(lines, string.format("DECAL %s and %s share the %s face at ZIndex %d", relative(root, tie.first), relative(root, tie.second),
			tie.first.Face.Name, tie.first.ZIndex))
	end
	table.insert(lines, string.format("%d fighting face pairs (%d flicker, %d shimmer, %d hidden), %d decal ties%s", #fights, counts.flicker, counts.shimmer,
		counts.hidden, #ties, if #fights + #ties > 0 then ": ZFight.settle(root), then audit again" else ""))
	return #fights + #ties, table.concat(lines, "\n"), pairs
end

--- Rids `root` of z-fighting (see the header). Returns { parts, faces, passes, stuck, decals }: the parts and faces it
--- moved, the faces it had to leave fighting because moving them would have taken more than SETTLE.max, and the decals
--- it renumbered. Edit-time; write the result back to the project's source if the model is generated.
function ZFight.settle(root: Instance)
	local touched = {}
	local faces, stuck, passes = 0, 0, 0
	for pass = 1, ZFight.SETTLE.passes do
		passes = pass
		local moved
		moved, stuck = settlePass(root, touched, false)
		faces += moved
		task.wait()
		if moved == 0 then
			break
		end
	end
	local parts = 0
	for _ in touched do
		parts += 1
	end
	local decals = 0
	for _, tie in decalTies(root) do
		local top = 0
		for _, child in tie.part:GetChildren() do
			if child:IsA("Decal") and child.Face == tie.second.Face then
				top = math.max(top, child.ZIndex)
			end
		end
		tie.second.ZIndex = top + 1
		decals += 1
	end
	return { parts = parts, faces = faces, passes = passes, stuck = stuck, decals = decals }
end

return ZFight
