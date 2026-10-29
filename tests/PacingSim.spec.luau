--!strict
-- Specs for scripts/PacingSim.luau. Run them all with: lune run tests/run.luau
local PacingSim = require("../scripts/PacingSim")

local failures, checks = 0, 0
local function check(ok: boolean, message: string)
	checks += 1
	if not ok then
		failures += 1
		print("FAIL: " .. message)
	end
end
local function near(a: number?, b: number, tolerance: number): boolean
	return a ~= nil and math.abs(a - b) <= tolerance * math.max(1, math.abs(b))
end
local function has(text: string, part: string): boolean
	return string.find(text, part, 1, true) ~= nil
end

-- 1. Cost ladders against brute force
for _, case in { { 10, 1.15 }, { 3, 1.07 }, { 100, 2 }, { 7, 1 }, { 0.5, 1.5 } } do
	local base, growth = case[1], case[2]
	for from = 0, 30, 5 do
		local sum = 0
		for to = from, from + 40 do
			check(near(PacingSim.totalCost(base, growth, from, to), sum, 1e-9), `totalCost {base} {growth} {from} {to}`)
			sum += PacingSim.cost(base, growth, to)
		end
	end
	for level = 0, 20, 4 do
		for _, budget in { 0, base * 0.5, base, base * 10, base * 1234.5, base * 98765.4321 } do
			local brute, total = 0, 0
			while total + PacingSim.cost(base, growth, level + brute) <= budget do
				total += PacingSim.cost(base, growth, level + brute)
				brute += 1
			end
			local got = PacingSim.affordable(base, growth, level, budget)
			check(got == brute, `affordable {base} {growth} {level} {budget}: {got}, brute force {brute}`)
		end
		-- an exact boundary buys exactly that many levels
		local exact = PacingSim.totalCost(base, growth, level, level + 17)
		check(PacingSim.affordable(base, growth, level, exact) == 17, `affordable at the exact boundary {base} {growth}`)
	end
end
check(PacingSim.affordable(10, 1.15, 0, math.huge) == math.huge, "an infinite budget buys everything")
check(not pcall(PacingSim.affordable, 10, 1.15, 0, 0 / 0), "a NaN budget is rejected")

-- 2. Chance arithmetic
check(PacingSim.rollsFor(600, 0.5) == 416, "median rolls for 1 in 600 is 416")
check(PacingSim.rollsFor(600, 0.9) == 1381, "p90 rolls for 1 in 600 is 1381")
check(PacingSim.rollsFor(600, 0.5, 2) == 208, "luck x2 halves the median")
check(PacingSim.hitShare(600, 416) >= 0.5 and PacingSim.hitShare(600, 415) < 0.5, "hitShare agrees with rollsFor")
check(PacingSim.rollsFor(10, 0.5, 20) == 1, "certain with enough luck")
check(PacingSim.rollsFor(10, 0) == 0 and PacingSim.rollsFor(10, 1) == math.huge, "share edges")
check(near(1 - PacingSim.hitShare(100000, 100000), math.exp(-1), 1e-4), "37% still miss after N rolls")
check(near(1 - PacingSim.hitShare(100000, 300000), math.exp(-3), 1e-4), "5% still miss after 3N rolls")
check(PacingSim.chance(1000, 5) == 0.005, "luck multiplies the chance")

-- 3. Durations
check(PacingSim.duration(40) == "40 s", "seconds: " .. PacingSim.duration(40))
check(PacingSim.duration(390) == "6.5 min", "short minutes: " .. PacingSim.duration(390))
check(PacingSim.duration(2100) == "35 min", "minutes: " .. PacingSim.duration(2100))
check(PacingSim.duration(11520) == "3.2 h", "hours: " .. PacingSim.duration(11520))
check(PacingSim.duration(3600 * 1234) == "1,234 h", "many hours: " .. PacingSim.duration(3600 * 1234))
check(PacingSim.duration(math.huge) == "never", "never")

-- 4. Simulation timing
local function constant(target: number?): PacingSim.Model
	return {
		init = function()
			return { cash = 0 }
		end,
		income = function()
			return 10
		end,
		milestones = {
			{
				name = "6000 cash",
				target = target,
				reached = function(s: PacingSim.State)
					return s.cash >= 6000
				end,
			},
		},
		sessionMinutes = 20,
		sessionsPerDay = 2,
		days = 1,
	}
end
local one = PacingSim.simulate(constant(10))
local first = one.milestones[1]
check(near(first.minutes, 10, 1e-9) and first.day == 1 and first.session == 1, "constant income reaches 6000 at 10 min")
check(#one.sessions == 2 and near(one.sessions[2].balance, 24000, 1e-9), "full horizon without early stop")
check(has(PacingSim.report(one), "on target"), "on target verdict")
check(has(PacingSim.report(PacingSim.simulate(constant(5))), "slow"), "slow verdict")
check(has(PacingSim.report(PacingSim.simulate(constant(20))), "fast"), "fast verdict")

local away = PacingSim.simulate({
	init = function()
		return { cash = 0 }
	end,
	income = function()
		return 10
	end,
	milestones = {
		{
			name = "24001 cash",
			target = 5,
			reached = function(s: PacingSim.State)
				return s.cash >= 24001
			end,
		},
		{
			name = "never",
			target = 5,
			reached = function()
				return false
			end,
		},
	},
	sessionMinutes = 10,
	sessionsPerDay = 2,
	days = 1,
	offline = { rate = 0.5, capHours = 1 },
})
-- session 1 earns 6000; 11 h 50 min away is capped at 1 h: +18000; the first second of session 2 adds the last 10
check(near(away.milestones[1].minutes, 10 + 1 / 60, 1e-9) and away.milestones[1].session == 2, "offline earnings")
check(away.milestones[2].minutes == nil and has(PacingSim.report(away), "not reached"), "a milestone never reached")

local grown = PacingSim.simulate({
	init = function()
		return { cash = 0, crop = 0 }
	end,
	income = function()
		return 0
	end,
	away = function(s: PacingSim.State, seconds: number)
		s.crop += seconds
	end,
	milestones = {
		{
			name = "crop grown",
			reached = function(s: PacingSim.State)
				return s.crop >= 3600
			end,
		},
	},
	sessionMinutes = 5,
	sessionsPerDay = 4,
	days = 1,
})
check(grown.milestones[1].session == 2 and near(grown.milestones[1].minutes, 5, 1e-9), "away rules run between sessions")

-- 5. Policies: A costs 10 for +1 income, B costs 15 for +3; income starts at 1
local function trade(policy: string, list: { PacingSim.Buy }, cash: number): PacingSim.Run
	return PacingSim.simulate({
		init = function()
			return { cash = cash, a = 0, b = 0 }
		end,
		income = function(s: PacingSim.State)
			return 1 + s.a + 3 * s.b
		end,
		buys = list,
		policy = policy,
		milestones = {
			{
				name = "a",
				reached = function(s: PacingSim.State)
					return s.a >= 1
				end,
			},
			{
				name = "b",
				reached = function(s: PacingSim.State)
					return s.b >= 1
				end,
			},
		},
		sessionMinutes = 5,
		sessionsPerDay = 1,
		days = 1,
	})
end
local function itemA(): PacingSim.Buy
	return {
		name = "A",
		cost = function(s: PacingSim.State)
			return if s.a == 0 then 10 else nil
		end,
		buy = function(s: PacingSim.State)
			s.a += 1
		end,
	}
end
local function itemB(save: boolean?): PacingSim.Buy
	return {
		name = "B",
		save = save,
		cost = function(s: PacingSim.State)
			return if s.b == 0 then 15 else nil
		end,
		buy = function(s: PacingSim.State)
			s.b += 1
		end,
	}
end
local function seconds(result: PacingSim.Run, index: number): number
	return math.round((result.milestones[index].minutes or -1) * 60)
end
local cheap = trade("cheapest", { itemA(), itemB() }, 15)
check(seconds(cheap, 1) == 0 and seconds(cheap, 2) == 5, `cheapest buys A then B: {seconds(cheap, 1)}, {seconds(cheap, 2)}`)
local best = trade("value", { itemA(), itemB() }, 15)
check(seconds(best, 2) == 0 and seconds(best, 1) == 3, `value buys B then A: {seconds(best, 1)}, {seconds(best, 2)}`)
local path = trade("ordered", { itemB(), itemA() }, 12)
check(seconds(path, 2) == 3 and seconds(path, 1) == 6, `ordered waits for B: {seconds(path, 1)}, {seconds(path, 2)}`)
local saved = trade("cheapest", { itemA(), itemB(true) }, 12)
check(seconds(saved, 2) == 3 and seconds(saved, 1) == 6, `save holds A back: {seconds(saved, 1)}, {seconds(saved, 2)}`)
local unsaved = trade("cheapest", { itemA(), itemB() }, 12)
check(seconds(unsaved, 1) == 0 and seconds(unsaved, 2) == 7, `no save: {seconds(unsaved, 1)}, {seconds(unsaved, 2)}`)

-- B now costs 15 for +30: the optimizer saves for it (pays back in 15.5 s against A's 20), the casual player does not
local function bigB(): PacingSim.Buy
	return {
		name = "B",
		cost = function(s: PacingSim.State)
			return if s.b == 0 then 15 else nil
		end,
		buy = function(s: PacingSim.State)
			s.b += 10
		end,
	}
end
local casual = trade("cheapest", { itemA(), bigB() }, 0)
check(seconds(casual, 1) == 10 and seconds(casual, 2) == 18, `casual: {seconds(casual, 1)}, {seconds(casual, 2)}`)
local optimizer = trade("value", { itemA(), bigB() }, 0)
check(seconds(optimizer, 2) == 15 and seconds(optimizer, 1) == 16, `optimizer: {seconds(optimizer, 1)}, {seconds(optimizer, 2)}`)

-- when no buy raises income the optimizer buys cheapest first
local unlocks = PacingSim.simulate({
	policy = "value",
	init = function()
		return { cash = 0, x = false, y = false }
	end,
	income = function()
		return 1
	end,
	buys = {
		{
			name = "X",
			cost = function(s: PacingSim.State)
				return if s.x then nil else 5
			end,
			buy = function(s: PacingSim.State)
				s.x = true
			end,
		},
		{
			name = "Y",
			cost = function(s: PacingSim.State)
				return if s.y then nil else 3
			end,
			buy = function(s: PacingSim.State)
				s.y = true
			end,
		},
	},
	milestones = {
		{
			name = "x",
			reached = function(s: PacingSim.State)
				return s.x
			end,
		},
		{
			name = "y",
			reached = function(s: PacingSim.State)
				return s.y
			end,
		},
	},
	sessionMinutes = 1,
	sessionsPerDay = 1,
	days = 1,
})
check(seconds(unlocks, 2) == 3 and seconds(unlocks, 1) == 8, `unlocks: {seconds(unlocks, 1)}, {seconds(unlocks, 2)}`)

-- a second currency is spent from its own field
local gems = PacingSim.simulate({
	init = function()
		return { cash = 0, gems = 0, boost = 0 }
	end,
	income = function(s: PacingSim.State)
		return 1 + s.boost
	end,
	step = function(s: PacingSim.State, dt: number)
		s.gems += dt -- one gem a second
	end,
	buys = {
		{
			name = "Boost",
			currency = "gems",
			cost = function(s: PacingSim.State)
				return if s.boost == 0 then 30 else nil
			end,
			buy = function(s: PacingSim.State)
				s.boost = 1
			end,
		},
	},
	milestones = {
		{
			name = "boosted",
			reached = function(s: PacingSim.State)
				return s.boost == 1
			end,
		},
	},
	sessionMinutes = 1,
	sessionsPerDay = 1,
	days = 1,
})
check(seconds(gems, 1) == 30 and gems.state.cash == 30 + 30 * 2, `gems pay for gem items: {seconds(gems, 1)}, {gems.state.cash}`)

-- 6. Errors
local endless: PacingSim.Model = {
	init = function()
		return { cash = 0 }
	end,
	income = function()
		return 1
	end,
	buys = {
		{
			name = "Free",
			cost = function()
				return 0
			end,
			buy = function() end,
		},
	},
	milestones = {},
	sessionMinutes = 1,
	sessionsPerDay = 1,
	days = 1,
}
local ok, err = pcall(PacingSim.simulate, endless, nil)
check(not ok and has(tostring(err), "dearer"), "a buy that never gets dearer is reported: " .. tostring(err))
endless.buys = {
	{
		name = "Broken",
		cost = function()
			return 0 / 0
		end,
		buy = function() end,
	},
}
ok, err = pcall(PacingSim.simulate, endless, nil)
check(not ok and has(tostring(err), "Broken: cost is NaN"), "a NaN cost is reported: " .. tostring(err))
endless.buys = nil
local never = {
	name = "x",
	reached = function()
		return false
	end,
}
endless.milestones = { never, never }
ok, err = pcall(PacingSim.simulate, endless, nil)
check(not ok and has(tostring(err), "two milestones"), "duplicate milestone names are reported: " .. tostring(err))
endless.milestones = {}
endless.policy = "greedy"
ok, err = pcall(PacingSim.simulate, endless, nil)
check(not ok and has(tostring(err), "unknown policy"), "an unknown policy is reported: " .. tostring(err))
endless.policy = nil
endless.sessionMinutes = 13 * 60
endless.sessionsPerDay = 2
check(not pcall(PacingSim.simulate, endless, nil), "sessions longer than the day are rejected")

-- 7. Many runs: one roll a second at 1 in 600; median 416 rolls (6.9 min), p90 1381 (23 min)
local start = os.clock()
local lucky = PacingSim.simulateMany({
	init = function()
		return { cash = 0, hit = false }
	end,
	income = function()
		return 0
	end,
	step = function(s: PacingSim.State)
		if math.random() < 1 / 600 then
			s.hit = true
		end
	end,
	milestones = {
		{
			name = "hit",
			target = 7,
			reached = function(s: PacingSim.State)
				return s.hit
			end,
		},
		{
			name = "impossible",
			reached = function()
				return false
			end,
		},
	},
	sessionMinutes = 120,
	sessionsPerDay = 1,
	days = 1,
}, 4000)
local spread = lucky.milestones[1]
check(near(spread.median, 416 / 60, 0.08), `median {spread.median} vs {416 / 60}`)
check(near(spread.p90, 1381 / 60, 0.08), `p90 {spread.p90} vs {1381 / 60}`)
check(near(spread.p10, 64 / 60, 0.15), `p10 {spread.p10} vs {64 / 60}`)
check(spread.share > 0.999 and spread.day == 1, `share {spread.share}`)
check(lucky.milestones[2].share == 0 and lucky.milestones[2].median == nil, "an impossible milestone has no median")
check(has(PacingSim.report(lucky), "on target"), "many-run report verdict")
local manyTime = os.clock() - start

local same = PacingSim.simulateMany(constant(10), 50)
check(same.milestones[1].median == 10 and same.milestones[1].share == 1, "a model without chance is the same every run")

-- 8. Tables
local tiers = {
	{ name = "Rare", oneIn = 50 },
	{ name = "Mythic", oneIn = 25000 },
	{ name = "Secret", oneIn = 1000000 },
}
local odds = PacingSim.rngTable(tiers, { rollsPerMinute = 6, pity = { Mythic = 75000 } })
check(has(odds, "1 in 25,000") and has(odds, "roll 75,000: 5%"), "rng table odds and pity share")
check(has(odds, "1 in 1,000,000") and has(odds, "0.0001%"), "rng table small chances")
check(has(PacingSim.curve(one), "| 1 | 2 |"), "curve rows")

print(string.format("simulateMany 4000 runs: %.2f s", manyTime))
print(`PacingSim: {checks - failures}/{checks} checks passed`)
if failures > 0 then
	error(`{failures} checks failed`)
end
