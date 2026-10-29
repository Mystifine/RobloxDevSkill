--!strict
-- Pacing model for game design plans (references/game-economy.md): when a modeled player reaches each milestone, so a
-- plan's pacing table comes from arithmetic instead of guesses. Pure Luau, no Roblox APIs. Lune: copy this file beside
-- the model, require("./PacingSim"), `lune run model.luau`. It also runs in Studio or any Luau VM.
--
--   simulate(model, seed?)             one modeled player, session by session: when each milestone is first reached
--   simulateMany(model, runs?, seed?)  that over many seeds (default 200) for models with chance: p10, median, p90
--   report(result, tolerance?)         either result as a markdown table, each milestone judged slow, fast or on
--                                      target (within tolerance of its target; default 0.25 = 25%)
--   curve(run)                         income and balance at the end of each session, as a markdown table
--   rngTable(tiers, options)           per tier: chance with luck, median and p90 rolls and play time, share reaching pity
--   cost, totalCost, affordable        geometric cost ladders: one level, levels from..to-1, levels a budget buys
--   chance, rollsFor, hitShare         a 1-in-N outcome with luck: chance per roll, rolls until a share of players has
--                                      hit it (median about 0.69 N, p90 about 2.3 N), share that hit it within some rolls
--   duration(seconds)                  "40 s", "6.5 min", "35 min", "3.2 h"
--
-- A model is data plus functions over a flat state table (numbers and booleans):
--
--   local model = {
--       init = function() return { cash = 0, droppers = 0 } end,
--       income = function(s) return 1 + 2 * s.droppers end, -- cash per second of active play
--       buys = { { name = "Dropper", cost = function(s) return PacingSim.cost(10, 1.15, s.droppers) end,
--           buy = function(s) s.droppers += 1 end } },
--       milestones = { { name = "10 droppers", target = 5, reached = function(s) return s.droppers >= 10 end } },
--       sessionMinutes = 20, sessionsPerDay = 2, days = 7, offline = { rate = 0.25, capHours = 8 },
--   }
--   print(PacingSim.report(PacingSim.simulate(model)))
--
-- The player spends after every step (dt seconds of play). Policy "cheapest" (default, a casual player) buys the
-- cheapest affordable item. "value" (an optimizer) picks the buy that pays for itself soonest, counting the wait to
-- afford it, and saves for it; it tries each buy on a copy of the state, so buys must not roll dice (chance belongs in
-- step), and currencies other than the model's own still buy cheapest first. "ordered" buys the first available item
-- in list order and waits for it (a player following the game's goal arrow). An available buy marked save = true comes
-- first in its currency and is saved for. The gap between cheapest and value is how much allocation choices matter.
-- Targets and times are minutes of active play. Between sessions the player is away: offline earnings are paid, then
-- model.away runs.

local PacingSim = {}

export type State = { [string]: any }

export type Buy = {
	name: string,
	cost: (state: State) -> number?, -- nil while unavailable (locked or maxed)
	buy: (state: State) -> (),
	currency: string?, -- the state field it is paid from; default the model's currency
	save: boolean?, -- while available: bought before anything else in its currency, and saved for
}

export type Milestone = {
	name: string,
	reached: (state: State) -> boolean,
	target: number?, -- minutes of active play the design aims for
}

export type Clock = { active: number, day: number, session: number } -- active: seconds of play so far

export type Model = {
	init: () -> State,
	income: (state: State) -> number, -- currency per second of active play
	currency: string?, -- default "cash"
	buys: { Buy }?,
	policy: string?, -- "cheapest" (default), "value" or "ordered"
	step: ((state: State, dt: number, clock: Clock) -> ())?, -- rules for each step of play: rolls, timers, events
	away: ((state: State, seconds: number, clock: Clock) -> ())?, -- rules for time away: growth, hatching
	milestones: { Milestone },
	sessionMinutes: number?, -- default 20
	sessionsPerDay: number?, -- default 2
	days: number?, -- default 14
	offline: { rate: number, capHours: number }?, -- share of income paid for time away, up to a cap
	dt: number?, -- seconds per step, default 1
}

export type Reach = { name: string, target: number?, minutes: number?, day: number?, session: number? }
export type Session = { day: number, session: number, minutes: number, income: number, balance: number }
export type Run = { kind: "run", milestones: { Reach }, sessions: { Session }, state: State }
export type Spread = {
	name: string,
	target: number?,
	share: number, -- of the runs that reached it
	p10: number?, -- minutes; nil when fewer runs than that reached it
	median: number?,
	p90: number?,
	day: number?, -- median day it was reached
}
export type Many = { kind: "many", runs: number, milestones: { Spread } }
export type Tier = { name: string, oneIn: number }
export type RngOptions = { rollsPerMinute: number, luck: number?, pity: { [string]: number }? } -- pity: tier -> roll

type Purse = { currency: string, buys: { Buy }, main: boolean } -- main: paid in the model's own currency

local MAX_BUYS = 10000 -- in one step and currency; more means a buy that never gets dearer or runs out
local SUFFIXES = { "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc" }

-- Formatting

local function trim(text: string): string
	if string.find(text, ".", 1, true) then
		text = string.gsub(string.gsub(text, "0+$", ""), "%.$", "")
	end
	return text
end

-- 25000 -> "25,000"
local function group(n: number): string
	local text = string.format("%.0f", n)
	local sign, digits = string.match(text, "^(%-?)(%d+)$")
	if not digits then
		return text -- inf or nan
	end
	local grouped = string.reverse((string.gsub(string.reverse(digits), "(%d%d%d)", "%1,")))
	return (sign or "") .. (string.gsub(grouped, "^,", ""))
end

-- a probability as a percentage to two significant digits: "50%", "4.2%", "0.0042%"
local function percent(p: number): string
	local value = p * 100
	if value <= 0 then
		return "0%"
	end
	local decimals = math.max(0, 1 - math.floor(math.log10(value)))
	return trim(string.format("%." .. decimals .. "f", value)) .. "%"
end

-- 1234567 -> "1.23M"
local function short(n: number): string
	local size = math.abs(n)
	if size < 1000 or size ~= size or size == math.huge then
		return trim(string.format("%.1f", n))
	end
	local tier = math.floor(math.log10(size) / 3)
	if tier > #SUFFIXES then
		return string.format("%.2e", n)
	end
	return trim(string.format("%.2f", n / 10 ^ (3 * tier))) .. SUFFIXES[tier]
end

function PacingSim.duration(seconds: number): string
	if seconds ~= seconds or seconds == math.huge then
		return "never"
	elseif seconds < 60 then
		return `{math.round(seconds)} s`
	elseif seconds < 600 then
		return `{trim(string.format("%.1f", seconds / 60))} min`
	elseif seconds < 3600 then
		return `{math.round(seconds / 60)} min`
	elseif seconds < 360000 then
		return `{trim(string.format("%.1f", seconds / 3600))} h`
	end
	return `{group(seconds / 3600)} h`
end

-- Cost ladders

function PacingSim.cost(base: number, growth: number, level: number): number
	return base * growth ^ level
end

-- the sum of cost(level) over levels from .. to - 1
function PacingSim.totalCost(base: number, growth: number, from: number, to: number): number
	if to <= from then
		return 0
	elseif growth == 1 then
		return base * (to - from)
	end
	return base * (growth ^ to - growth ^ from) / (growth - 1)
end

-- how many levels, starting at `level`, a budget buys
function PacingSim.affordable(base: number, growth: number, level: number, budget: number): number
	assert(base > 0 and growth >= 1 and budget == budget, "affordable needs base > 0, growth >= 1 and a budget")
	if budget == math.huge then
		return math.huge
	elseif budget < PacingSim.cost(base, growth, level) then
		return 0
	end
	local n = if growth == 1
		then math.floor(budget / base)
		else math.floor(math.log(budget * (growth - 1) / PacingSim.cost(base, growth, level) + 1) / math.log(growth))
	-- the closed form can land one off at an exact boundary
	while n > 0 and PacingSim.totalCost(base, growth, level, level + n) > budget do
		n -= 1
	end
	while PacingSim.totalCost(base, growth, level, level + n + 1) <= budget do
		n += 1
	end
	return n
end

-- Chance

-- chance per roll of a 1-in-`oneIn` outcome, luck multiplying it (capped at certain)
function PacingSim.chance(oneIn: number, luck: number?): number
	return math.min(1, (luck or 1) / oneIn)
end

-- rolls until `share` (0 to 1) of players have hit it at least once
function PacingSim.rollsFor(oneIn: number, share: number, luck: number?): number
	local p = PacingSim.chance(oneIn, luck)
	if share <= 0 then
		return 0
	elseif p >= 1 then
		return 1
	elseif share >= 1 then
		return math.huge
	end
	return math.max(1, math.ceil(math.log(1 - share) / math.log(1 - p)))
end

-- share of players who have hit it at least once within `rolls`
function PacingSim.hitShare(oneIn: number, rolls: number, luck: number?): number
	return 1 - (1 - PacingSim.chance(oneIn, luck)) ^ rolls
end

-- Simulation

local function priceOf(item: Buy, state: State): number?
	local cost = item.cost(state)
	assert(cost == nil or cost == cost, `{item.name}: cost is NaN`)
	return cost
end

-- the buy the model's player makes next from `purse` and its price; nil while they buy nothing (or save)
local function choose(model: Model, policy: string, state: State, purse: Purse): (Buy?, number)
	local balance = state[purse.currency] or 0
	for _, item in purse.buys do
		local cost = if item.save then priceOf(item, state) else nil
		if cost ~= nil then
			return (if cost <= balance then item else nil), cost -- buy it, or save for it
		end
	end
	if policy == "ordered" then
		for _, item in purse.buys do
			local cost = priceOf(item, state)
			if cost ~= nil then
				return (if cost <= balance then item else nil), cost -- buy it, or wait for it
			end
		end
		return nil, 0
	elseif policy == "value" and purse.main then
		-- the buy that pays for itself soonest, counting the wait to afford it
		local now = model.income(state)
		local best: Buy?, bestCost, soonest = nil, 0, math.huge
		for _, item in purse.buys do
			local cost = priceOf(item, state)
			if cost ~= nil then
				local trial = table.clone(state)
				item.buy(trial)
				local gain = model.income(trial) - now
				local wait = if cost <= balance then 0 elseif now > 0 then (cost - balance) / now else math.huge
				if gain > 0 and wait + cost / gain < soonest then
					best, bestCost, soonest = item, cost, wait + cost / gain
				end
			end
		end
		if best then
			return (if bestCost <= balance then best else nil), bestCost
		end
		-- nothing raises income: buy as a casual player would
	end
	local cheapest: Buy?, low = nil, math.huge
	for _, item in purse.buys do
		local cost = priceOf(item, state)
		if cost ~= nil and cost <= balance and cost < low then
			cheapest, low = item, cost
		end
	end
	return cheapest, low
end

local function spend(model: Model, policy: string, state: State, purses: { Purse })
	for _, purse in purses do
		local bought = 0
		while true do
			local item, price = choose(model, policy, state, purse)
			if item == nil then
				break
			end
			bought += 1
			if bought > MAX_BUYS then
				error(`{MAX_BUYS} buys in {purse.currency} in one step: a buy must get dearer or run out`)
			end
			state[purse.currency] = (state[purse.currency] or 0) - price
			item.buy(state)
		end
	end
end

local function run(model: Model, seed: number, early: boolean): Run
	math.randomseed(seed)
	local currency = model.currency or "cash"
	local policy = model.policy or "cheapest"
	assert(policy == "cheapest" or policy == "value" or policy == "ordered", `unknown policy "{policy}"`)
	local dt = model.dt or 1
	local length = (model.sessionMinutes or 20) * 60
	local perDay = model.sessionsPerDay or 2
	local gap = 86400 / perDay - length -- seconds away between sessions
	assert(dt > 0 and length > 0 and gap >= 0, "dt and session length must be positive, and the sessions fit in a day")
	local offline, away, step = model.offline, model.away, model.step

	local purses: { Purse } = {}
	local byCurrency: { [string]: Purse } = {}
	local buys: { Buy } = model.buys or {}
	for _, item in buys do
		local name = item.currency or currency
		if not byCurrency[name] then
			byCurrency[name] = { currency = name, buys = {}, main = name == currency }
			table.insert(purses, byCurrency[name])
		end
		table.insert(byCurrency[name].buys, item)
	end

	local named: { [string]: boolean } = {}
	for _, milestone in model.milestones do
		assert(not named[milestone.name], `two milestones are named "{milestone.name}"`)
		named[milestone.name] = true
	end

	local state = model.init()
	state[currency] = state[currency] or 0
	local clock: Clock = { active = 0, day = 1, session = 1 }
	local found: { [string]: Reach } = {}
	local left = #model.milestones
	local function check()
		for _, milestone in model.milestones do
			if not found[milestone.name] and milestone.reached(state) then
				found[milestone.name] = {
					name = milestone.name,
					target = milestone.target,
					minutes = clock.active / 60,
					day = clock.day,
					session = clock.session,
				}
				left -= 1
			end
		end
	end

	local sessions: { Session } = {}
	spend(model, policy, state, purses)
	check()
	for day = 1, model.days or 14 do
		for session = 1, perDay do
			if early and left == 0 then
				break
			end
			clock.day, clock.session = day, session
			if day > 1 or session > 1 then
				if offline then
					state[currency] += offline.rate * model.income(state) * math.min(gap, offline.capHours * 3600)
				end
				if away then
					away(state, gap, clock)
				end
				spend(model, policy, state, purses)
				check()
			end
			local played = 0
			while played < length and not (early and left == 0) do
				local slice = math.min(dt, length - played)
				state[currency] += model.income(state) * slice
				played += slice
				clock.active += slice
				if step then
					step(state, slice, clock)
				end
				spend(model, policy, state, purses)
				check()
			end
			table.insert(sessions, {
				day = day,
				session = session,
				minutes = clock.active / 60,
				income = model.income(state),
				balance = state[currency],
			})
		end
	end

	local milestones: { Reach } = {}
	for _, milestone in model.milestones do
		table.insert(milestones, found[milestone.name] or { name = milestone.name, target = milestone.target })
	end
	return { kind = "run", milestones = milestones, sessions = sessions, state = state }
end

function PacingSim.simulate(model: Model, seed: number?): Run
	return run(model, seed or 1, false)
end

-- nearest rank over every run; a run that never reached it counts as never, so a rank past the reached ones is nil
local function rank(sorted: { number }, runs: number, q: number): number?
	return sorted[math.max(1, math.ceil(q * runs))]
end

function PacingSim.simulateMany(model: Model, runs: number?, seed: number?): Many
	local count = runs or 200
	local minutes: { [string]: { number } } = {}
	local days: { [string]: { number } } = {}
	for _, milestone in model.milestones do
		minutes[milestone.name], days[milestone.name] = {}, {}
	end
	for i = 1, count do
		for _, reach in run(model, (seed or 1) + i - 1, true).milestones do
			if reach.minutes and reach.day then
				table.insert(minutes[reach.name], reach.minutes)
				table.insert(days[reach.name], reach.day)
			end
		end
	end
	local spreads: { Spread } = {}
	for _, milestone in model.milestones do
		local times, when = minutes[milestone.name], days[milestone.name]
		table.sort(times)
		table.sort(when)
		table.insert(spreads, {
			name = milestone.name,
			target = milestone.target,
			share = #times / count,
			p10 = rank(times, count, 0.1),
			median = rank(times, count, 0.5),
			p90 = rank(times, count, 0.9),
			day = rank(when, count, 0.5),
		})
	end
	return { kind = "many", runs = count, milestones = spreads }
end

-- Reports

local function judge(target: number?, minutes: number?, tolerance: number): string
	if target == nil then
		return "-"
	elseif minutes == nil then
		return "not reached"
	elseif minutes > target * (1 + tolerance) then
		return "slow"
	elseif minutes < target * (1 - tolerance) then
		return "fast"
	end
	return "on target"
end

local function play(minutes: number?, missing: string): string
	return if minutes == nil then missing else PacingSim.duration(minutes * 60)
end

local function row(cells: { string }): string
	return "| " .. table.concat(cells, " | ") .. " |"
end

-- a markdown table: the header row, its rule, then the rows
local function markdown(header: { string }, rows: { { string } }): string
	local lines = { row(header), string.rep("|---", #header) .. "|" }
	for _, cells in rows do
		table.insert(lines, row(cells))
	end
	return table.concat(lines, "\n")
end

function PacingSim.report(result: Run | Many, tolerance: number?): string
	local within = tolerance or 0.25
	local rows: { { string } } = {}
	if result.kind == "run" then
		for _, reach in result.milestones do
			table.insert(rows, {
				reach.name,
				play(reach.target, "-"),
				play(reach.minutes, "not reached"),
				if reach.day then `day {reach.day}, session {reach.session}` else "-",
				judge(reach.target, reach.minutes, within),
			})
		end
		return markdown({ "Milestone", "Target", "Reached", "When", "Verdict" }, rows)
	end
	for _, spread in result.milestones do
		table.insert(rows, {
			spread.name,
			play(spread.target, "-"),
			play(spread.median, "-"),
			play(spread.p10, "-"),
			play(spread.p90, "-"),
			percent(spread.share),
			if spread.day then tostring(spread.day) else "-",
			judge(spread.target, spread.median, within),
		})
	end
	local reached = `Reached ({result.runs} runs)`
	return markdown({ "Milestone", "Target", "Median", "p10", "p90", reached, "Median day", "Verdict" }, rows)
end

function PacingSim.curve(result: Run): string
	local rows: { { string } } = {}
	for _, session in result.sessions do
		table.insert(rows, {
			tostring(session.day),
			tostring(session.session),
			PacingSim.duration(session.minutes * 60),
			short(session.income),
			short(session.balance),
		})
	end
	return markdown({ "Day", "Session", "Active play", "Income per second", "Balance" }, rows)
end

function PacingSim.rngTable(tiers: { Tier }, options: RngOptions): string
	local luck = options.luck or 1
	local function rolls(share: number, oneIn: number): string
		local n = PacingSim.rollsFor(oneIn, share, luck)
		return `{group(n)} ({PacingSim.duration(n / options.rollsPerMinute * 60)})`
	end
	local rows: { { string } } = {}
	for _, tier in tiers do
		local p = PacingSim.chance(tier.oneIn, luck)
		local pity = options.pity and options.pity[tier.name]
		table.insert(rows, {
			tier.name,
			`1 in {group(tier.oneIn)}`,
			percent(p),
			rolls(0.5, tier.oneIn),
			rolls(0.9, tier.oneIn),
			if pity then `roll {group(pity)}: {percent((1 - p) ^ (pity - 1))}` else "-",
		})
	end
	return markdown({ "Tier", "Odds", `Chance at luck x{luck}`, "Median", "p90", "Reach pity" }, rows)
end

return PacingSim
