"""upload_asset.py: an asset that stays under review after its operation finishes. No network: the API is a fake."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('upload_asset', ROOT / 'scripts' / 'upload_asset.py')
ua = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ua)


class FakeApi:
    """Answers the upload, its operation and reads of the asset, whose states come one by one."""

    def __init__(self, first, later=()):
        self.first, self.later = first, list(later)
        self.posts, self.reads = 0, 0

    def __call__(self, key, method, url, body=None, headers=None):
        if method == 'POST':
            self.posts += 1
            return {'operationId': 'op1'}
        if '/operations/' in url:
            return {'done': True, 'response': {'assetId': '123', 'assetType': 'Audio', 'displayName': 'track', 'moderationResult': {'moderationState': self.first}}}
        self.reads += 1
        state = self.later.pop(0) if self.later else self.first
        return {'moderationResult': {'moderationState': state}}


class Reviewing(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.file = os.path.join(self.folder.name, 'track.mp3')
        Path(self.file).write_bytes(b'sound')
        self.manifest = os.path.join(self.folder.name, 'assets.json')

    def run_upload(self, api, timeout='300'):
        argv = ['upload_asset.py', self.file, '--user', '1', '--manifest', self.manifest, '--timeout', timeout]
        printed = io.StringIO()
        with mock.patch.object(ua, 'call', api), mock.patch.object(ua, 'read_key', return_value='key'), mock.patch.object(ua.time, 'sleep'), \
                mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(printed):
            code = ua.main()
        return code, printed.getvalue()

    def saved(self):
        return json.loads(Path(self.manifest).read_text(encoding='utf-8'))['track']

    def test_a_review_that_passes_is_waited_for_and_kept(self):
        api = FakeApi('Reviewing', ['Reviewing', 'Approved'])
        code, printed = self.run_upload(api)
        self.assertEqual(code, 0)
        self.assertEqual(api.reads, 2)
        self.assertIn('Approved', printed)
        self.assertEqual(self.saved()['moderation'], 'Approved')

    def test_a_review_that_outlasts_the_timeout_is_kept_and_never_sent_twice(self):
        api = FakeApi('Reviewing')
        code, _ = self.run_upload(api, timeout='0.05')
        self.assertEqual(code, 3)
        self.assertEqual(self.saved()['moderation'], 'Reviewing')
        self.assertEqual(self.saved()['assetId'], '123')
        again = FakeApi('Reviewing', ['Approved'])
        code, _ = self.run_upload(again)
        self.assertEqual(code, 0)
        self.assertEqual(again.posts, 0, 'asked again, not resent')
        self.assertEqual(self.saved()['moderation'], 'Approved')

    def test_a_rejection_exits_2_and_stays_out_of_the_manifest(self):
        code, _ = self.run_upload(FakeApi('Rejected'))
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.manifest))

    def test_a_failed_read_is_not_a_verdict(self):
        def refused(*_):
            raise SystemExit(1)

        with mock.patch.object(ua, 'call', refused), mock.patch.object(ua.time, 'sleep'):
            self.assertEqual(ua.settle('key', '123', 'Reviewing', ua.time.time() + 60), 'Reviewing')


if __name__ == '__main__':
    unittest.main()


class Refused(unittest.TestCase):
    """call(): a 403 is retried once after a pause (nothing went through); a second 403 fails."""

    def responses(self, codes):
        replies = list(codes)

        def opener(req, timeout=None):
            code = replies.pop(0)
            if code == 200:
                return contextlib.nullcontext(io.BytesIO(b'{"ok": true}'))
            raise ua.urllib.error.HTTPError(req.full_url, code, 'refused', {}, io.BytesIO(b'{"code":"PERMISSION_DENIED"}'))
        return opener

    def call(self, codes):
        waits = []
        with mock.patch.object(ua.urllib.request, 'urlopen', self.responses(codes)), \
                mock.patch.object(ua.time, 'sleep', waits.append), contextlib.redirect_stderr(io.StringIO()):
            result = ua.call('key', 'POST', 'https://example.invalid/assets', b'{}')
        return result, waits

    def test_a_refusal_is_retried_once_after_a_pause(self):
        result, waits = self.call([403, 200])
        self.assertEqual(result, {'ok': True})
        self.assertEqual(waits, [ua.FORBIDDEN_WAIT])

    def test_a_second_refusal_fails(self):
        with self.assertRaises(SystemExit):
            self.call([403, 403])

    def test_other_errors_are_not_retried(self):
        with self.assertRaises(SystemExit):
            self.call([500, 200])
