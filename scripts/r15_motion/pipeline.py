"""The R15 animation pipeline's Studio side, run from the shell. The motion itself is made in Blender (r15_rig.py): that writes
<project>/animation/baked/<clip>.json, and this takes it from there. No plugin: Studio MCP does the reading and writing.

  python pipeline.py dump                 dumps the real R15 from Studio to <project>/animation/r15_rig.json
  python pipeline.py import [A,B]         each baked clip to a KeyframeSequence in Studio (Edit): audit, round-trip check, and
                                          <project>/animation/clips/<clip>.rbxm; the audit text goes to animation/audit/
  python pipeline.py upload [A,B] --group ID (or --user ID)   uploads those (animation/clips.json holds the ids): same bytes are reused
  python pipeline.py bodies               audits the imported clips on tall, wide, Rthro and small avatars (import them first)
  python pipeline.py clean                removes what import left in Studio

Common: --project DIR (default: here), --studio NAME (needed when several Studios are open), --env-file (default <project>/.env).
"""
import argparse
import base64
import json
import os
import pathlib
import struct
import subprocess
import sys
import tempfile

TOOLS = pathlib.Path(__file__).resolve().parent
SKILL = TOOLS.parents[1]
ANIMATION = pathlib.Path("animation")  # set by main: <project>/animation
STUDIO = None
CHUNK = 60000  # bytes: base64 grows them by a third, and a reply is cut at about 100k characters
PARTS = [
    "Head", "UpperTorso", "LowerTorso",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
]


def studio(code: str, timeout: int = 300) -> str:
    with tempfile.TemporaryDirectory() as folder:
        script = pathlib.Path(folder) / "code.luau"
        result = pathlib.Path(folder) / "result.txt"
        script.write_text(code, encoding="utf-8")
        command = [sys.executable, str(SKILL / "scripts" / "studio_mcp.py"), "luau", str(script)]
        command += ["--output", str(result), "--timeout", str(timeout)] + (["--studio", STUDIO] if STUDIO else [])
        code_ = subprocess.call(command, stdout=subprocess.DEVNULL)
        text = result.read_text(encoding="utf-8") if result.exists() else ""
        if code_ != 0:
            raise SystemExit(f"Studio failed: {text[-2000:]}")
        return text


def decode(text: str):
    data = json.loads(text)
    return json.loads(data) if isinstance(data, str) else data


def dump() -> None:
    source = (TOOLS / "dump_rig.luau").read_text(encoding="utf-8")
    rig = decode(studio(source))
    rig["Meshes"] = {}
    for part in PARTS:
        one = decode(studio(source.replace('local ONLY = ""', f'local ONLY = "{part}"', 1)))
        rig["Meshes"][part] = one
        print(part, len(one.get("Verts", [])) // 3, "verts", len(one.get("Tris", [])) // 3, "tris", one.get("Error", ""))
    ANIMATION.mkdir(parents=True, exist_ok=True)
    (ANIMATION / "r15_rig.json").write_text(json.dumps(rig), encoding="utf-8")


def pack(joint: dict) -> dict:
    """A joint's keys as bytes: frame (u16), quaternion (4 x i16), offset (3 x i16, 1/4096 stud) when it has one."""
    frames, q, p = joint["F"], joint["Q"], joint["P"]
    out = bytearray()
    for i, f in enumerate(frames):
        v = q[i * 4 : i * 4 + 4]
        out += struct.pack("<H4h", f, *[max(-32767, min(32767, round(x * 32767))) for x in v])
        if p is not None:
            o = p[i * 3 : i * 3 + 3]
            out += struct.pack("<3h", *[max(-32767, min(32767, round(x * 4096))) for x in o])
    return {"N": len(frames), "O": p is not None, "D": base64.b64encode(bytes(out)).decode()}


def wanted(names: str | None, folder: pathlib.Path, suffix: str) -> list[pathlib.Path]:
    if names:
        return [folder / f"{n}{suffix}" for n in names.split(",")]
    return sorted(folder.glob(f"*{suffix}"))


def import_clips(names: str | None) -> int:
    clips, audit = ANIMATION / "clips", ANIMATION / "audit"
    clips.mkdir(parents=True, exist_ok=True)
    audit.mkdir(parents=True, exist_ok=True)
    source = (TOOLS / "import_clip.luau").read_text(encoding="utf-8")
    failed = 0
    for path in wanted(names, ANIMATION / "baked", ".json"):
        clip = json.loads(path.read_text(encoding="utf-8"))
        name = clip["Name"]
        slim = {k: clip.get(k) for k in ("Name", "Fps", "Loop", "Priority", "Markers", "Ignore", "Audit", "Check")}
        slim["Joints"] = {j: pack(d) for j, d in clip["Joints"].items()}
        code = source.replace("__CLIP__", json.dumps(slim, separators=(",", ":")))
        result = decode(studio(code, 600))
        (audit / f"{name}.txt").write_text(result["Audit"], encoding="utf-8")
        # the bytes, in pieces
        total = int(studio(f'''
local item = game:GetService("ServerStorage").R15ClipImports["{name}"]
return #buffer.tostring(game:GetService("SerializationService"):SerializeInstancesAsync({{ item }}))'''))
        raw = bytearray()
        while len(raw) < total:
            part = studio(_read_piece(name, len(raw)))
            part = json.loads(part) if part.startswith('"') else part
            raw += base64.b64decode(part)
        (clips / f"{name}.rbxm").write_bytes(bytes(raw))
        errors = [line for line in result["Audit"].splitlines() if "ERROR" in line]
        warns = [line for line in result["Audit"].splitlines() if "WARN" in line]
        failed += 1 if errors or result["Worst"] > 0.02 else 0
        print(f"{name}: {result['Keyframes']} keyframes, {result['Poses']} poses, {len(raw) // 1024} KB; round trip off by {result['Worst']:.4f} studs ({result['WorstAt']}); {len(errors)} errors, {len(warns)} warnings")
        for line in errors + warns:
            print("   ", line.strip()[:170])
    return failed


def _read_piece(name: str, at: int) -> str:
    return f'''
local item = game:GetService("ServerStorage").R15ClipImports["{name}"]
local data = buffer.tostring(game:GetService("SerializationService"):SerializeInstancesAsync({{ item }}))
local piece = string.sub(data, {at + 1}, {at + CHUNK})
local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local out = table.create(math.ceil(#piece / 3) * 4)
for i = 1, #piece, 3 do
	local a, b, c = string.byte(piece, i, i + 2)
	local n = a * 65536 + (b or 0) * 256 + (c or 0)
	for j = 3, 0, -1 do
		local index = bit32.band(bit32.rshift(n, j * 6), 63) + 1
		table.insert(out, string.sub(alphabet, index, index))
	end
	if not b then
		out[#out], out[#out - 1] = "=", "="
	elseif not c then
		out[#out] = "="
	end
end
return table.concat(out)'''


def upload(names: str | None, creator: list[str], env_file: str) -> int:
    files = [str(p) for p in wanted(names, ANIMATION / "clips", ".rbxm")]
    command = [sys.executable, str(SKILL / "scripts" / "upload_asset.py"), *files, *creator, "--type", "Animation"]
    command += ["--env-file", env_file, "--manifest", str(ANIMATION / "clips.json")]
    return subprocess.call(command)


def clean() -> None:
    print(studio('''
local folder = game:GetService("ServerStorage"):FindFirstChild("R15ClipImports")
if folder then folder:Destroy() end
for _, old in workspace:GetChildren() do
	if old.Name == "ClipImportRig" or old.Name == "AnimDumpRig" then old:Destroy() end
end
return "cleaned"'''))


def main() -> int:
    global ANIMATION, STUDIO
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["dump", "import", "upload", "bodies", "clean"])
    parser.add_argument("names", nargs="?")
    parser.add_argument("--project", default=".")
    parser.add_argument("--studio")
    parser.add_argument("--env-file")
    who = parser.add_mutually_exclusive_group()
    who.add_argument("--group")
    who.add_argument("--user")
    args = parser.parse_args()
    project = pathlib.Path(args.project).resolve()
    ANIMATION, STUDIO = project / "animation", args.studio
    if args.mode == "dump":
        dump()
    elif args.mode == "import":
        return 1 if import_clips(args.names) else 0
    elif args.mode == "upload":
        if not (args.group or args.user):
            parser.error("upload needs --group or --user: the experience's owner (references/safety/uploading.md)")
        creator = ["--group", args.group] if args.group else ["--user", args.user]
        return upload(args.names, creator, args.env_file or str(project / ".env"))
    elif args.mode == "bodies":
        print(studio((TOOLS / "check_bodies.luau").read_text(encoding="utf-8"), 600))
    else:
        clean()
    return 0


if __name__ == "__main__":
    sys.exit(main())
