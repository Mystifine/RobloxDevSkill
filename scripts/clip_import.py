"""Blender clips into Studio as KeyframeSequences on the real rig: built, checked, audited and saved as upload-ready .rbxm files
(references/animation/blender.md, Into Studio). Python 3, standard library; Studio open, in Edit.

    python clip_import.py rbxanim CLIP.rbxanim ... --rig PATH     an R6 game's clip, or any Motor6D rig's (ClipImport.rbxanim)
    python clip_import.py rbxanim CLIP.rbxanim ... --r15 PATH     fake R6: read onto an R6, carried onto the R15 at every frame
                                                                   (R6OnR15.retarget, Thin = false), each leg planted on its
                                                                   IK target (R6OnR15.plantFeet), the joint policy checked
    python clip_import.py deltas CLIP.json ... --rig PATH [--feet A,B [--soles]] [--ignore R]   a bone rig's world deltas
                                                                   (blender_anim.deltas; ClipImport.deltas)

    PATH: the rig, dotted from game (ServerStorage.Rigs.Hero). Without one, a rig from a default HumanoidDescription is used:
          not the game's own body (a classic R15 stands at HipHeight 2, a default one at 2.19), so pass the game's rig.
    --out DIR        where <clip>.rbxm and <clip>.audit.txt go (default: a `clips` folder beside each source)
    --strip TEXT     a prefix to drop from the file names (EmberfangWalk -> Walk with --strip Emberfang)
    --priority P     Action, Core, Idle or Movement (default: Core for a loop, Action for a one-shot)
    --locomotion A,B clips the audit treats as in-place locomotion (default: the audit infers it)
    --held PART      fake R6: key the held item's joint (PART on a Motor6D from the hand) with the clip's Flick and Twist
                     channels (R6OnR15.keyHeld); the rig must hold the item
    --tip NAME       the attachment, part or bone whose fastest moment the first marker is checked against (a blade's tip)
    --feet A,B       the parts or bones that plant; --soles measures each one's sole as the floor point straight below it at
                     rest (the lowest visible part's bottom), for joints above the soles such as a creature's ankles
    --keep           leave the sequences in ServerStorage.__ClipImport for AnimationInspector.sheet; run `clean` later
    --studio NAME    which Studio, when several are open

A clip's sidecar .json (r6_rig.export) gives its Markers (seconds), Loop and the feet's IK targets; the first marker is checked
against the swing's fastest moment. Prints a line a clip (keys, policy findings, audit errors and warnings, KB) and the
findings; exit 1 when any clip has an error. One clip a Studio call: a long clip's keys are a few hundred KB of JSON."""
import argparse
import json
import os
from pathlib import Path
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio_mcp  # noqa: E402

FOLDER = '__ClipImport'

BUILD = r'''--@use ClipImport, R6OnR15, AnimationInspector
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local data = HttpService:JSONDecode(__DATA__)
local info = HttpService:JSONDecode(__INFO__)
local job = HttpService:JSONDecode(__JOB__)
local folder = game.ServerStorage:FindFirstChild("__FOLDER__")
if not folder then
	folder = Instance.new("Folder")
	folder.Name = "__FOLDER__"
	folder.Parent = game.ServerStorage
end
local function find(path: string?, kind: Enum.HumanoidRigType): Model
	if path and path ~= "" then
		local item: Instance = game
		for name in string.gmatch(path, "[^%.]+") do
			item = assert(item:FindFirstChild(name), "no " .. name .. " under " .. item:GetFullName())
		end
		assert(item:IsA("Model"), path .. " is not a Model")
		return item
	end
	local name = "__" .. kind.Name
	local made = folder:FindFirstChild(name)
	if not made then
		made = Players:CreateHumanoidModelFromDescription(Instance.new("HumanoidDescription"), kind)
		made.Name = name
		made.Parent = folder
	end
	return made :: Model
end
local old = folder:FindFirstChild(job.name)
if old then
	old:Destroy()
end
local loop = info.Loop == true
local priority = (Enum.AnimationPriority :: any)[job.priority or (if loop then "Core" else "Action")]
local report: { [string]: any } = { Policy = 0, Missing = {} }
local sequence: KeyframeSequence, rig: Model
if job.mode == "rbxanim" then
	if job.r15 then
		local seq, missing = ClipImport.rbxanim(find(nil, Enum.HumanoidRigType.R6), data, { Name = job.name, Loop = loop, Priority = priority, Parts = info.Parts })
		rig = find(job.r15, Enum.HumanoidRigType.R15)
		local map = R6OnR15.map(rig)
		sequence = R6OnR15.retarget(map, seq, { Name = job.name, Thin = false })
		seq:Destroy()
		sequence.Loop, sequence.Priority = loop, priority
		if info.Feet then
			report.FeetShort = R6OnR15.plantFeet(map, sequence, info)
		end
		if job.held and info.Channels and (info.Channels.Flick or info.Channels.Twist) then
			report.Held = R6OnR15.keyHeld(map, sequence, { Part = job.held, Flick = info.Channels.Flick or {}, Twist = info.Channels.Twist,
				Fps = info.Fps })
		end
		local findings, text = R6OnR15.check(map, sequence)
		report.Policy, report.PolicyText, report.Missing = #findings, text, missing
	else
		rig = find(job.rig, Enum.HumanoidRigType.R6)
		sequence, report.Missing = ClipImport.rbxanim(rig, data, { Name = job.name, Loop = loop, Priority = priority, Parts = info.Parts })
	end
else
	rig = find(job.rig, Enum.HumanoidRigType.R15)
	sequence, report.Fit = ClipImport.deltas(rig, data, { Name = job.name, Loop = loop, Priority = priority })
end
local markers = {}
for name, at in info.Markers or {} do
	AnimationInspector.setMarker(sequence, name, at)
	table.insert(markers, name)
end
table.sort(markers, function(a, b) return a == "Hit" and b ~= "Hit" or (a ~= "Hit" and b ~= "Hit" and a < b) end)
sequence.Parent = folder
local options: { [string]: any } = { Looped = loop, Markers = if #markers > 0 then markers else nil }
if job.feet then
	options.Feet = job.feet
	if job.soles then
		-- each foot's contact point: the floor straight below it at rest, the floor being the lowest visible part's bottom
		local ground = math.huge
		for _, part in rig:GetDescendants() do
			if part:IsA("BasePart") and part.Transparency < 1 then
				local c, h = part.CFrame, part.Size / 2
				ground = math.min(ground, c.Position.Y - math.abs(c.RightVector.Y) * h.X - math.abs(c.UpVector.Y) * h.Y - math.abs(c.LookVector.Y) * h.Z)
			end
		end
		local soles = {}
		for _, item in rig:GetDescendants() do
			if table.find(job.feet, item.Name) and (item:IsA("Bone") or item:IsA("BasePart")) then
				local at = if item:IsA("Bone") then item.WorldCFrame else (item :: BasePart).CFrame
				soles[item.Name] = at:PointToObjectSpace(Vector3.new(at.Position.X, ground, at.Position.Z))
			end
		end
		options.Soles = soles
	end
end
if job.ignore then
	options.Ignore = job.ignore
end
if job.tip then
	options.Tip = job.tip
end
if job.locomotion then
	options.Locomotion = true
end
report.Audit = AnimationInspector.audit(rig, sequence, options).Text
report.Keys = #sequence:GetKeyframes()
return HttpService:JSONEncode(report)
'''


def long_string(text):
    eq = '='
    while f']{eq}]' in text:
        eq += '='
    return f'[{eq}[{text}]{eq}]'


def rbxanim_data(path):
    """The .rbxanim's frames as compact JSON: { t, kfs = { { t, kf = { [part] = 12 numbers, or {12, style, direction} } } } }."""
    raw = json.loads(zlib.decompress(Path(path).read_bytes()))
    frames = []
    for frame in raw['kfs']:
        kf = {}
        for part, value in frame['kf'].items():
            numbers, *easing = value if isinstance(value[0], list) else (value,)
            numbers = [round(x, 6) for x in numbers]
            kf[part] = [numbers, *easing] if easing and easing != ['Linear', 'Out'] else numbers
        frames.append({'t': round(frame['t'], 6), 'kf': kf})
    return {'t': raw['t'], 'kfs': frames}


def sidecar(path):
    side = Path(path).with_suffix('.json')
    if Path(path).suffix == '.json':
        data = json.loads(side.read_text(encoding='utf-8'))
        return {'Loop': data.get('Loop', False), 'Markers': data.get('Markers', {})}
    return json.loads(side.read_text(encoding='utf-8')) if side.is_file() else {}


def build(s, studio, mode, path, a):
    name = Path(path).stem
    if a.strip and name.startswith(a.strip):
        name = name[len(a.strip):]
    data = rbxanim_data(path) if mode == 'rbxanim' else json.loads(Path(path).read_text(encoding='utf-8'))
    info = sidecar(path)
    job = {'mode': mode, 'name': name, 'rig': a.rig, 'r15': a.r15, 'priority': a.priority,
           'feet': a.feet.split(',') if a.feet else None, 'soles': a.soles, 'held': a.held, 'tip': a.tip, 'ignore': a.ignore.split(',') if a.ignore else None,
           'locomotion': name in (a.locomotion or '').split(',')}
    code = (BUILD.replace('__FOLDER__', FOLDER).replace('__DATA__', long_string(json.dumps(data, separators=(',', ':'))))
            .replace('__INFO__', long_string(json.dumps(info))).replace('__JOB__', long_string(json.dumps(job))))
    report = json.loads(studio_mcp.luau(s, studio, code, a.timeout))
    out = Path(a.out) if a.out else Path(path).parent / 'clips'
    out.mkdir(parents=True, exist_ok=True)
    size = studio_mcp.save(s, studio, f'ServerStorage.{FOLDER}.{name}', out / f'{name}.rbxm', a.timeout)
    (out / f'{name}.audit.txt').write_text((report.get('PolicyText') or '') + '\n\n' + report['Audit'], encoding='utf-8')
    lines = report['Audit'].splitlines()
    errors = [x.strip() for x in lines if 'ERROR' in x]
    warns = [x.strip() for x in lines if 'WARN' in x]
    extra = ''
    if report.get('Missing'):
        extra += f'; the rig lacks {report["Missing"]}'
    if report.get('Fit') is not None:
        extra += f'; fit {report["Fit"]:.4f} studs'
        if report['Fit'] > 0.05:
            errors.append(f'the bones sit {report["Fit"]:.3f} studs from the clip\'s rig: not the rig it was made on')
    if report.get('Held'):
        extra += f'; {job["held"]} keyed on {report["Held"]} keys'
    if report.get('FeetShort'):
        extra += f'; feet short of their targets by up to {report["FeetShort"]:.3f} studs'
    if report.get('Policy'):
        errors.append(f'{report["Policy"]} joint-policy findings (R6OnR15.check): see the audit file')
    print(f'{name}: {report["Keys"]} keys, {size // 1024} KB, policy {report.get("Policy", 0)}, {len(errors)} errors, '
          f'{len(warns)} warnings; markers {sorted(info.get("Markers", {}))}{extra}')
    for x in errors + warns:
        print('   ', x[:220])
    return not errors


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['rbxanim', 'deltas', 'clean'])
    ap.add_argument('files', nargs='*')
    ap.add_argument('--rig')
    ap.add_argument('--r15', nargs='?', const='')
    ap.add_argument('--out')
    ap.add_argument('--strip')
    ap.add_argument('--priority', choices=['Action', 'Core', 'Idle', 'Movement'])
    ap.add_argument('--locomotion')
    ap.add_argument('--feet')
    ap.add_argument('--soles', action='store_true')
    ap.add_argument('--held')
    ap.add_argument('--tip')
    ap.add_argument('--ignore')
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--studio', default=os.environ.get('STUDIO_ID'))
    ap.add_argument('--timeout', type=float, default=600)
    a = ap.parse_args(argv)
    s = studio_mcp.Server()
    try:
        studio = s.studio(a.studio)
        ok = True
        if a.mode != 'clean':
            for path in a.files:
                ok = build(s, studio, a.mode, path, a) and ok
        if a.mode == 'clean' or not a.keep:
            studio_mcp.luau(s, studio, f'''--@use AnimationInspector
pcall(AnimationInspector.clear)
local f = game.ServerStorage:FindFirstChild("{FOLDER}")
if f then f:Destroy() end
return "clean"''', a.timeout)
        return 0 if ok else 1
    finally:
        s.close()


if __name__ == '__main__':
    sys.exit(main())
