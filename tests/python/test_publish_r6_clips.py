"""Finding and uploading the default R6 clips, against a stand-in for Studio's MCP server and for Open Cloud. No request leaves the machine."""
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import publish_r6_clips as pub

USER, GROUP = '100', '200'


def asset(name, creator, asset_id, kind='Animation'):
    return {'name': name, 'assetId': asset_id, 'assetType': kind, 'creatorId': creator, 'source': 'inventory'}


class FakeServer:
    """Answers search_asset from a list of assets, as Studio's server does: by phrase, whoever created them. execute_luau answers
    the place's own owner (`place`; None: a reply with no JSON, as when Studio has no Edit DataModel)."""

    def __init__(self, assets, context=None, place='context'):
        self.assets, self.calls = assets, []
        self.context = context or {'creatorType': 'User', 'creatorId': USER, 'userId': USER}
        self.place = {k: v for k, v in self.context.items() if k != 'userId'} if place == 'context' else place

    def call(self, tool, args, timeout):
        if tool == 'execute_luau':
            assert args['code'] == pub.PLACE_OWNER and args['datamodel_type'] == 'Edit'
            return {'content': [{'type': 'text', 'text': json.dumps(self.place) if self.place is not None else 'error'}]}
        assert tool == 'search_asset'
        self.calls.append(args)
        phrase = args['query'].strip('"')
        results = [a for a in self.assets if phrase in a['name'] and a['assetType'] == args['assetType']]
        return {'content': [{'type': 'text', 'text': json.dumps({'status': 'success', 'results': results, 'context': self.context})}]}


def options(**over):
    base = dict(group=None, user=None, env_file=None, key_var='ROBLOX_CLOUD_API_KEY', manifest=None, timeout=1, dry_run=False)
    base.update(over)
    return SimpleNamespace(**base)


def run(a, names, server=None):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = pub.run(a, names, server, 'studio-id' if server else None)
    return code, json.loads(out.getvalue().strip().splitlines()[-1])


class Names(unittest.TestCase):
    def test_the_name_is_hard_coded_and_fits_roblox(self):
        self.assertEqual(pub.clip_name('walk'), 'RDSkill R6onR15 v1 walk')
        for clip in pub.clips():
            self.assertLessEqual(len(pub.clip_name(clip)), 50, clip)

    def test_a_new_set_gets_a_new_name(self):
        self.assertNotEqual(pub.clip_name('walk'), pub.clip_name('walk', 'v2'))

    def test_every_default_clip_has_a_file_and_no_other_does(self):
        source = (ROOT / 'scripts' / 'R6OnR15.luau').read_text(encoding='utf-8')
        names = re.findall(r'\{ Name = "(\w+)", Id = \d+', source)
        self.assertEqual(len(names), 23)
        self.assertEqual(sorted(names), pub.clips())

    def test_clips_were_saved_by_roblox(self):
        for path in pub.CLIPS.glob('*.rbxm'):
            self.assertEqual(path.read_bytes()[:8], b'<roblox!', path.name)


class Finding(unittest.TestCase):
    NAMES = {'walk': pub.clip_name('walk'), 'idle': pub.clip_name('idle')}

    def test_a_match_is_trusted_and_nothing_is_uploaded(self):
        server = FakeServer([asset(self.NAMES['walk'], USER, '1'), asset(self.NAMES['idle'], USER, '2')])
        with mock.patch.object(pub, 'upload') as upload:
            code, report = run(options(user=USER), self.NAMES, server)
        upload.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(report['ids'], {'walk': '1', 'idle': '2'})
        self.assertEqual((report['found'], report['uploaded'], report['missing']), (2, 0, []))

    def test_a_clip_owned_by_someone_else_is_not_found(self):
        hit = pub.match([asset(self.NAMES['walk'], GROUP, '9')], self.NAMES['walk'], ('user', USER))
        self.assertIsNone(hit)

    def test_only_the_exact_name_and_type_count(self):
        name = pub.clip_name('dance1')
        owner = ('user', USER)
        self.assertIsNone(pub.match([asset(name + 'b', USER, '1')], name, owner))
        self.assertIsNone(pub.match([asset(name, USER, '1', 'Model')], name, owner))
        self.assertEqual(pub.match([asset(name + 'b', USER, '1'), asset(name, USER, '2')], name, owner), '2')

    def test_the_query_is_an_exact_phrase_of_type_animation(self):
        args = pub.search_args('s', self.NAMES['walk'], ('user', USER))
        self.assertEqual((args['query'], args['assetType'], args['scope']), ('"RDSkill R6onR15 v1 walk"', 'Animation', 'user'))

    def test_a_group_owner_searches_that_group(self):
        args = pub.search_args('s', self.NAMES['walk'], ('group', GROUP))
        self.assertEqual((args['scope'], args['groupId']), ('group', GROUP))

    def test_the_owner_comes_from_the_open_place(self):
        self.assertEqual(pub.owner_of({'creatorType': 'Group', 'creatorId': GROUP, 'userId': USER}), ('group', GROUP))
        self.assertEqual(pub.owner_of({'creatorType': 'User', 'creatorId': USER, 'userId': '7'}), ('user', USER))

    def test_a_user_owned_place_can_report_creator_zero(self):
        self.assertEqual(pub.owner_of({'creatorType': 'User', 'creatorId': '0', 'userId': USER}), ('user', USER))

    def test_an_argument_overrides_the_place(self):
        self.assertEqual(pub.owner_of({'creatorType': 'User', 'creatorId': USER}, group=GROUP), ('group', GROUP))

    def test_the_place_owner_beats_the_search_context(self):
        # search_asset's context named the signed-in user for a group's place, and the first upload went to the wrong account.
        server = FakeServer([asset(self.NAMES['walk'], GROUP, '5'), asset(self.NAMES['idle'], GROUP, '6')],
                            {'creatorType': 'User', 'creatorId': USER, 'userId': USER}, {'creatorType': 'Group', 'creatorId': GROUP, 'placeId': '9'})
        code, report = run(options(), self.NAMES, server)
        self.assertEqual((code, report['owner'], report['ids']), (0, ['group', GROUP], {'walk': '5', 'idle': '6'}))
        self.assertTrue(all(c.get('groupId') == GROUP for c in server.calls))

    def test_an_unpublished_place_falls_back_to_the_search_context(self):
        for place in ({'creatorType': 'User', 'creatorId': '0', 'placeId': '0'}, None):
            server = FakeServer([asset(self.NAMES['walk'], USER, '1'), asset(self.NAMES['idle'], USER, '2')],
                                {'creatorType': 'User', 'creatorId': '0', 'userId': USER}, place)
            code, report = run(options(), self.NAMES, server)
            self.assertEqual((code, report['owner']), (0, ['user', USER]))

    def test_a_group_place_finds_clips_in_the_group(self):
        server = FakeServer([asset(self.NAMES['walk'], GROUP, '5'), asset(self.NAMES['idle'], GROUP, '6')], {'creatorType': 'Group', 'creatorId': GROUP, 'userId': USER})
        code, report = run(options(), self.NAMES, server)
        self.assertEqual((code, report['owner'], report['ids']), (0, ['group', GROUP], {'walk': '5', 'idle': '6'}))


class Uploading(unittest.TestCase):
    NAMES = {'walk': pub.clip_name('walk'), 'idle': pub.clip_name('idle')}

    def setUp(self):
        self.key = mock.patch.dict('os.environ', {'ROBLOX_CLOUD_API_KEY': 'not-a-real-key'})
        self.key.start()
        self.addCleanup(self.key.stop)

    def test_only_what_is_missing_goes_up(self):
        server = FakeServer([asset(self.NAMES['walk'], USER, '1')])
        with mock.patch.object(pub.upload_asset, 'upload', return_value=(0, {'assetId': '77'})) as send:
            code, report = run(options(user=USER), self.NAMES, server)
        self.assertEqual(code, 0)
        self.assertEqual(send.call_count, 1)
        request = send.call_args[0][0]
        self.assertEqual((request.type, request.name, request.user, request.group), ('Animation', self.NAMES['idle'], USER, None))
        self.assertTrue(send.call_args[0][1].endswith('idle.rbxm'))
        self.assertEqual(report['ids'], {'walk': '1', 'idle': '77'})
        self.assertEqual((report['found'], report['uploaded'], report['missing']), (1, 1, []))

    def test_it_stops_at_the_first_not_approved(self):
        server = FakeServer([])
        with mock.patch.object(pub.upload_asset, 'upload', return_value=(2, {'assetId': '77', 'moderation': 'Rejected'})) as send:
            code, report = run(options(user=USER), self.NAMES, server)
        self.assertEqual((code, send.call_count), (2, 1))
        self.assertEqual(len(report['missing']), 2)

    def test_no_key_reports_instead_of_failing_halfway(self):
        self.key.stop()
        self.addCleanup(self.key.start)
        server = FakeServer([asset(self.NAMES['walk'], USER, '1')])
        with mock.patch.dict('os.environ', {}, clear=True), mock.patch.object(pub.upload_asset, 'upload') as send:
            code, report = run(options(user=USER), self.NAMES, server)
        send.assert_not_called()
        self.assertEqual(code, 4)
        self.assertEqual((report['ids'], report['missing']), ({'walk': '1'}, ['idle']))
        self.assertIn('ROBLOX_CLOUD_API_KEY', report['note'])

    def test_a_dry_run_searches_and_sends_nothing(self):
        server = FakeServer([asset(self.NAMES['walk'], USER, '1')])
        with mock.patch.dict('os.environ', {}, clear=True):
            code, report = run(options(user=USER, dry_run=True), self.NAMES, server)
        self.assertEqual(code, 0)
        self.assertEqual(len(server.calls), 2)
        self.assertEqual(report['missing'], ['idle'])

    def test_the_manifest_is_kept_and_saves_the_query(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = str(Path(folder) / 'clips.json')
            with mock.patch.object(pub.upload_asset, 'upload', side_effect=[(0, {'assetId': '1'}), (0, {'assetId': '2'})]):
                run(options(user=USER, manifest=manifest), self.NAMES, FakeServer([]))
            again = FakeServer([])
            with mock.patch.object(pub.upload_asset, 'upload') as send:
                code, report = run(options(user=USER, manifest=manifest), self.NAMES, again)
            send.assert_not_called()
            self.assertEqual(again.calls, [])
            self.assertEqual((code, report['ids']), (0, {'idle': '1', 'walk': '2'}))

    def test_a_manifest_for_another_owner_does_not_count(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / 'clips.json'
            manifest.write_text(json.dumps({'walk': {'assetId': '1', 'name': self.NAMES['walk'], 'owner': GROUP}}))
            names = {'walk': self.NAMES['walk']}
            with mock.patch.object(pub.upload_asset, 'upload', return_value=(0, {'assetId': '2'})):
                _, report = run(options(user=USER, manifest=str(manifest)), names, FakeServer([]))
            self.assertEqual(report['ids'], {'walk': '2'})

    def test_without_studio_or_an_owner_it_stops(self):
        code, report = run(options(), self.NAMES)
        self.assertEqual(code, 1)
        self.assertIn('owner', report['note'])

    def test_the_uploader_accepts_animations_as_rbxm(self):
        source = (ROOT / 'scripts' / 'upload_asset.py').read_text(encoding='utf-8')
        self.assertIn("'Animation'", source)
        self.assertEqual(pub.upload_asset.TYPES['.rbxm'][1], 'model/x-rbxm')


if __name__ == '__main__':
    unittest.main()
