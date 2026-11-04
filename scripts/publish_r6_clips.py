"""Roblox's default R6 clips on R15, on the account that owns the experience (references/animation/r6-default-set.md). Finds each clip
by its hard-coded name, trusts any match, and uploads only what is missing. Prints the ids for R6OnR15.wire.

  python publish_r6_clips.py [--group ID | --user ID] [--studio NAME] [--no-studio] [--env-file .env] [--key-var NAME]
                             [--manifest r6_clips.json] [--set v1] [--timeout 300] [--dry-run]

A clip's name is `RDSkill R6onR15 <set> <clip>`, for example `RDSkill R6onR15 v1 walk`.

- Owner: --group or --user, else the open place's own game.CreatorType and game.CreatorId (read with execute_luau: search_asset's
  context can name the signed-in user for a group's place), else that context for a place never published. Printed to stderr
  before any search or upload. An animation plays only in experiences owned by its creator, so a clip under that name owned by
  anyone else does not count as found.
- Finding: Studio's MCP server (search_asset, exact phrase, type Animation). Open Cloud cannot list private animations by name, so
  without Studio only --manifest says what exists.
- Uploading: Open Cloud through upload_asset.py, one at a time, stopping at the first not approved. Needs the project's key.
- Output: a line per upload, then last one JSON object: owner, found, uploaded, ids ({clip: asset id}), missing. Exit codes: 0 every clip has an id, 1 a failed
  request, 2 not approved, 3 still pending after --timeout, 4 clips are missing and there is no key to upload them with."""
import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio_mcp
import upload_asset

CLIPS = Path(__file__).resolve().parent.parent / 'assets' / 'r6-on-r15' / 'clips'
SET = 'v1'  # changes only when the clips' data does; an old name always means the old data


def clip_name(clip, clip_set=SET):
    return f'RDSkill R6onR15 {clip_set} {clip}'


def clips():
    return sorted(p.stem for p in CLIPS.glob('*.rbxm'))


PLACE_OWNER = ('local HttpService = game:GetService("HttpService") return HttpService:JSONEncode({ creatorType = game.CreatorType.Name, '
               'creatorId = tostring(game.CreatorId), placeId = tostring(game.PlaceId) })')


def place_owner(server, studio):
    """The open place's own CreatorType and CreatorId, or {} when Studio cannot say (no Edit DataModel, an error reply)."""
    try:
        res = server.call('execute_luau', {'studio_id': studio, 'code': PLACE_OWNER, 'datamodel_type': 'Edit'}, 60)
        place = json.loads(res['content'][0]['text'])
    except (KeyError, IndexError, TypeError, ValueError, SystemExit):
        return {}
    return place if isinstance(place, dict) and str(place.get('creatorId', '0')) != '0' else {}


def owner_of(context, group=None, user=None):
    """(kind, id) of the account that must own the clips: the arguments, else the place's owner as `context` gives it."""
    if group:
        return 'group', str(group)
    if user:
        return 'user', str(user)
    if context.get('creatorType') == 'Group' and str(context.get('creatorId', '0')) != '0':
        return 'group', str(context['creatorId'])
    # A user-owned place can report creator 0; its owner is then the signed-in user.
    who = str(context.get('creatorId', '0'))
    return 'user', who if who != '0' else str(context.get('userId', '0'))


def search_args(studio, name, owner):
    args = {'studio_id': studio, 'query': f'"{name}"', 'assetType': 'Animation', 'maxResults': 20}
    if owner and owner[0] == 'group':
        args.update(scope='group', groupId=owner[1])
    else:
        args['scope'] = 'user'
    return args


def match(results, name, owner):
    """The asset id under exactly this name with this owner, or None. A user's inventory also holds other creators' animations."""
    for item in results:
        if item.get('name') == name and item.get('assetType') == 'Animation' and str(item.get('creatorId')) == owner[1]:
            return str(item['assetId'])
    return None


def search(server, studio, name, owner):
    res = server.call('search_asset', search_args(studio, name, owner), 60)
    return json.loads(res['content'][0]['text'])


def find(server, studio, names, owner, group=None, user=None):
    """Looks up each {clip: name} one by one (a search returns at most 20). Returns the owner and {clip: id} for those found."""
    found = {}
    for clip, name in names.items():
        reply = search(server, studio, name, owner)
        if owner is None:
            owner = owner_of(reply.get('context') or {}, group, user)
            if owner[0] == 'group':  # the first search ran in the user's scope
                reply = search(server, studio, name, owner)
        hit = match(reply.get('results') or [], name, owner)
        if hit:
            found[clip] = hit
    return owner, found


def upload(clip, name, owner, a):
    request = SimpleNamespace(group=owner[1] if owner[0] == 'group' else None, user=owner[1] if owner[0] == 'user' else None,
                              type='Animation', name=name, description="Roblox's default R6 animation, on an R15 rig (RDSkill).",
                              env_file=a.env_file, key_var=a.key_var, timeout=a.timeout, dry_run=a.dry_run)
    return upload_asset.upload(request, str(CLIPS / f'{clip}.rbxm'))


def has_key(a):
    if os.environ.get(a.key_var):
        return True
    if a.env_file and os.path.exists(a.env_file):
        return any(line.strip().partition('=')[0].strip() == a.key_var for line in Path(a.env_file).read_text(encoding='utf-8').splitlines())
    return False


def run(a, names, server=None, studio=None):
    done = json.loads(Path(a.manifest).read_text(encoding='utf-8')) if a.manifest and os.path.exists(a.manifest) else {}
    owner = (('group', str(a.group)) if a.group else ('user', str(a.user))) if (a.group or a.user) else None
    # The manifest is this run's own record, so a clip it holds for this owner needs no query.
    ids = {c: str(e['assetId']) for c, e in done.items() if c in names and e.get('name') == names[c] and owner and e.get('owner') == owner[1]}
    queried = 0
    if server and len(ids) < len(names):
        if owner is None:
            place = place_owner(server, studio)
            owner = owner_of(place) if place else None
        wanted = {c: n for c, n in names.items() if c not in ids}
        owner, hits = find(server, studio, wanted, owner, a.group, a.user)
        ids.update(hits)
        queried = len(hits)
    if owner:
        print(f'owner: {owner[0]} {owner[1]}', file=sys.stderr)
    report = {'owner': list(owner) if owner else None, 'found': queried, 'uploaded': 0, 'ids': ids, 'missing': sorted(set(names) - set(ids))}
    if report['missing'] and not owner:
        print(json.dumps({**report, 'note': 'no owner: pass --group or --user, or open the place in Studio'}))
        return 1
    if report['missing'] and not a.dry_run and not has_key(a):
        print(json.dumps({**report, 'note': f'{len(report["missing"])} clips need uploading: set {a.key_var} or pass --env-file'}))
        return 4
    for clip in report['missing'][:]:
        code, record = upload(clip, names[clip], owner, a)
        if a.dry_run:
            continue
        if code:
            print(json.dumps(report))
            return code
        ids[clip] = str(record['assetId'])
        report['missing'].remove(clip)
        report['uploaded'] += 1
        if a.manifest:
            done[clip] = {'assetId': ids[clip], 'name': names[clip], 'owner': owner[1]}
            with open(a.manifest, 'w', encoding='utf-8') as f:
                json.dump(done, f, indent=2)
    print(json.dumps(report))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    who = ap.add_mutually_exclusive_group()
    who.add_argument('--group', help='group id, when a group owns the experience')
    who.add_argument('--user', help='user id, when a user owns the experience')
    ap.add_argument('--studio', default=os.environ.get('STUDIO_ID'), help='place name part or studio id')
    ap.add_argument('--no-studio', action='store_true', help='skip the search: only --manifest says what exists')
    ap.add_argument('--env-file')
    ap.add_argument('--key-var', default='ROBLOX_CLOUD_API_KEY')
    ap.add_argument('--manifest', help='JSON of what this tool uploaded, kept across runs')
    ap.add_argument('--set', default=SET, dest='clip_set')
    ap.add_argument('--timeout', type=float, default=300)
    ap.add_argument('--dry-run', action='store_true', help='searches for real, then prints each upload without sending it')
    a = ap.parse_args()
    names = {c: clip_name(c, a.clip_set) for c in clips()}
    server = studio = None
    if not a.no_studio:
        try:
            server = studio_mcp.Server()
            studio = server.studio(a.studio)
        except (SystemExit, OSError) as e:
            print(f'Studio is not reachable ({e}): only --manifest can say what exists', file=sys.stderr)
            server = None
    try:
        return run(a, names, server, studio)
    finally:
        if server:
            server.close()


if __name__ == '__main__':
    sys.exit(main())
