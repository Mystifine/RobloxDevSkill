"""Upload one file through Open Cloud (references/assets.md, Uploading) and wait for moderation.

  python upload_asset.py FILE [FILE ...] (--group ID | --user ID) [--manifest assets.json] [--type Decal|Model|Audio] [--name NAME]
                         [--description TEXT] [--env-file .env] [--key-var ROBLOX_CLOUD_API_KEY] [--timeout 300] [--dry-run]

Prints one JSON line a file: assetId, assetType, displayName, moderation (Approved, Rejected, ...) and the operation id.
Exit codes: 0 approved, 1 a failed request, 2 not approved, 3 still pending after --timeout.

- Several files go in order and stop at the first that is not approved, so nothing more is sent after a rejection.
- --manifest keeps each file's result by its stem with its hash: a file already approved at the same hash is reused, not resent, so a
  batch can be rerun after any change. It holds ids only, never the key.

- The creator is the experience's owner (references/assets.md says how to find it).
- The key comes from the environment (--key-var) or the --env-file (KEY=VALUE lines) and is never printed.
- The type follows the extension: .png .jpg .jpeg .bmp .tga a Decal (its image id: InsertService:LoadAsset in Studio),
  .fbx .obj .gltf .glb .rbxm a Model, .mp3 .ogg .wav .flac Audio. Tested with .png Decals and .fbx Models.
- --dry-run prints the request without the key and sends nothing."""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

API = 'https://apis.roblox.com/assets/v1'
TYPES = {'.png': ('Decal', 'image/png'), '.jpg': ('Decal', 'image/jpeg'), '.jpeg': ('Decal', 'image/jpeg'),
         '.bmp': ('Decal', 'image/bmp'), '.tga': ('Decal', 'image/tga'), '.fbx': ('Model', 'model/fbx'),
         '.obj': ('Model', 'model/obj'), '.gltf': ('Model', 'model/gltf+json'), '.glb': ('Model', 'model/gltf-binary'),
         '.rbxm': ('Model', 'model/x-rbxm'), '.mp3': ('Audio', 'audio/mpeg'), '.ogg': ('Audio', 'audio/ogg'),
         '.wav': ('Audio', 'audio/wav'), '.flac': ('Audio', 'audio/flac')}


def read_key(var, env_file):
    if os.environ.get(var):
        return os.environ[var].strip()
    if env_file:
        for line in open(env_file, encoding='utf-8'):
            name, _, value = line.strip().partition('=')
            if name.strip() == var:
                return value.strip().strip('"\'')
    sys.exit(f'no API key: set {var} or pass --env-file with a {var}= line')


def call(key, method, url, body=None, headers=None):
    # Polling is safe to repeat, so a dropped connection is retried there: one reset ended a long batch. A POST
    # is not, since it may have gone through: it fails, and a rerun of the batch decides.
    for attempt in range(5 if method == 'GET' else 1):
        req = urllib.request.Request(url, data=body, method=method, headers={'x-api-key': key, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            print(f'HTTP {e.code} {method} {url}: {e.read().decode(errors="replace")[:800]}', file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f'{method} {url}: {e.reason}', file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('file', nargs='+')
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument('--group', help='group id (the experience is group-owned)')
    who.add_argument('--user', help='user id (the experience is user-owned)')
    ap.add_argument('--type', choices=['Decal', 'Model', 'Audio'])
    ap.add_argument('--name')
    ap.add_argument('--description', default='')
    ap.add_argument('--env-file')
    ap.add_argument('--key-var', default='ROBLOX_CLOUD_API_KEY')
    ap.add_argument('--timeout', type=float, default=300)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--manifest', help='JSON of results by file stem: what is approved at the same hash is reused')
    a = ap.parse_args()
    if len(a.file) > 1 and a.name:
        ap.error('--name goes with one file')
    done = json.load(open(a.manifest, encoding='utf-8')) if a.manifest and os.path.exists(a.manifest) else {}
    for path in a.file:
        stem = os.path.splitext(os.path.basename(path))[0]
        with open(path, 'rb') as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        if done.get(stem, {}).get('sha256') == sha and done[stem].get('moderation') == 'Approved':
            print(json.dumps({**done[stem], 'reused': True}))
            continue
        code, record = upload(a, path)
        if record and code == 0 and a.manifest and not a.dry_run:
            done[stem] = {**record, 'sha256': sha}
            with open(a.manifest, 'w', encoding='utf-8') as f:
                json.dump(done, f, indent=2)
        if code:
            return code
    return 0


def upload(a, path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in TYPES:
        sys.exit(f'unsupported file type {ext}: ' + ' '.join(sorted(TYPES)))
    kind, content_type = TYPES[ext]
    creator = {'groupId': str(a.group)} if a.group else {'userId': str(a.user)}
    request = {'assetType': a.type or kind, 'displayName': a.name or os.path.splitext(os.path.basename(path))[0],
               'description': a.description, 'creationContext': {'creator': creator}}
    if a.dry_run:
        print(json.dumps({'request': request, 'contentType': content_type, 'bytes': os.path.getsize(path)}))
        return 0, None
    key = read_key(a.key_var, a.env_file)
    b = uuid.uuid4().hex
    head = (f'--{b}\r\nContent-Disposition: form-data; name="request"\r\nContent-Type: application/json\r\n\r\n'
            f'{json.dumps(request)}\r\n--{b}\r\nContent-Disposition: form-data; name="fileContent"; '
            f'filename="{os.path.basename(path)}"\r\nContent-Type: {content_type}\r\n\r\n')
    with open(path, 'rb') as f:
        body = head.encode() + f.read() + f'\r\n--{b}--\r\n'.encode()
    op = call(key, 'POST', API + '/assets', body, {'Content-Type': f'multipart/form-data; boundary={b}'})
    op_id = op.get('operationId') or op.get('path', '').split('/')[-1]
    end = time.time() + a.timeout
    while time.time() < end:
        res = call(key, 'GET', f'{API}/operations/{op_id}')
        if res.get('done'):
            r = res.get('response', {})
            state = r.get('moderationResult', {}).get('moderationState')
            record = {'assetId': r.get('assetId'), 'assetType': r.get('assetType'), 'displayName': r.get('displayName'),
                      'moderation': state, 'operation': op_id, 'error': res.get('error')}
            print(json.dumps(record))
            return (0 if state in ('Approved', 'MODERATION_STATE_APPROVED') else 2), record
        time.sleep(3)
    print(json.dumps({'operation': op_id, 'moderation': 'pending', 'poll': f'{API}/operations/{op_id}'}))
    return 3, None


if __name__ == '__main__':
    sys.exit(main())
