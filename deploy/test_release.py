import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('release', Path(__file__).with_name('release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
SHA = 'a' * 40


def bundle(extra=(), omit=()):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name in ('index.html', 'app.js', 'style.css', 'assets/example.txt'):
            if name in omit:
                continue
            data = b'example content'
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        for entry, data in extra:
            archive.addfile(entry, io.BytesIO(data) if data is not None else None)
    stream.seek(0)
    return stream


class ArchiveTests(unittest.TestCase):
    def extract(self, stream):
        with tempfile.TemporaryDirectory() as tmp:
            release.unpack(stream, Path(tmp))

    def test_valid_site(self):
        self.extract(bundle())

    def test_required_file(self):
        with self.assertRaisesRegex(ValueError, 'Missing or empty'):
            self.extract(bundle(omit=('app.js',)))

    def test_path_traversal_and_unexpected_paths(self):
        for name in ('../outside', '/etc/passwd', 'assets/../../outside',
                     'assets/./file', 'assets\\outside', '.git/config', 'release.json'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.extract(bundle(((tarfile.TarInfo(name), b''),)))

    def test_links_and_duplicates(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE):
            entry = tarfile.TarInfo('assets/link')
            entry.type = kind
            entry.linkname = '/etc/passwd'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.extract(bundle(((entry, None),)))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.extract(bundle(((tarfile.TarInfo('index.html'), b''),)))

    def test_total_size_limit(self):
        original = release.MAX_TOTAL
        try:
            release.MAX_TOTAL = 1
            with self.assertRaisesRegex(ValueError, 'size limit'):
                self.extract(bundle())
        finally:
            release.MAX_TOTAL = original


@unittest.skipIf(os.name == 'nt', 'Atomic directory symlink replacement requires Linux; run CI')
class SwitchingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        old = self.base / 'releases' / 'manual-old'
        old.mkdir(parents=True)
        (old / 'release.json').write_text(json.dumps({'release_id': 'manual-old', 'commit': 'manual-import'}))
        self.old = old
        try:
            (self.base / 'current').symlink_to(old, target_is_directory=True)
        except OSError as error:
            self.skipTest('This host cannot create directory symlinks: ' + str(error))

    def healthy(self, record, base):
        current = release.release_target(base, 'current')
        self.assertEqual(json.loads((current / 'release.json').read_text()), record)

    def test_deploy_then_rollback(self):
        result = release.deploy(self.base, SHA, bundle(), self.healthy)
        self.assertEqual(result['commit'], SHA)
        deployed = release.release_target(self.base, 'current')
        self.assertEqual(release.release_target(self.base, 'previous'), self.old)
        release.rollback(self.base, health=self.healthy)
        self.assertEqual(release.release_target(self.base, 'current'), self.old)
        release.rollback(self.base, SHA, self.healthy)
        self.assertEqual(release.release_target(self.base, 'current'), deployed)

    def test_failed_health_restores_current(self):
        def failure(record, base):
            raise RuntimeError('simulated Nginx failure')
        with self.assertRaisesRegex(RuntimeError, 'Nginx failure'):
            release.deploy(self.base, SHA, bundle(), failure)
        self.assertEqual(release.release_target(self.base, 'current'), self.old)
        self.assertFalse((self.base / 'previous').exists())

    def test_invalid_archive_keeps_current_and_cleans_staging(self):
        with self.assertRaises(ValueError):
            release.deploy(self.base, SHA, bundle(omit=('index.html',)), self.healthy)
        self.assertEqual(release.release_target(self.base, 'current'), self.old)
        self.assertEqual(list(self.base.glob('incoming-*')), [])

    def test_invalid_or_unknown_revision(self):
        for revision in ('main; rm -rf /', '../outside', 'shortsha'):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                release.deploy(self.base, revision, bundle(), self.healthy)
        with self.assertRaisesRegex(ValueError, 'has not been deployed'):
            release.rollback(self.base, 'b' * 40, self.healthy)
        self.assertEqual(release.release_target(self.base, 'current'), self.old)

    def test_symlink_outside_releases_is_rejected(self):
        (self.base / 'previous').symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'outside'):
            release.rollback(self.base, health=self.healthy)


if __name__ == '__main__':
    unittest.main()
