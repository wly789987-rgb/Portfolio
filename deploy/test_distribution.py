import io
from pathlib import Path
import subprocess
import tarfile
import unittest


class DistributionTests(unittest.TestCase):
    def test_server_scripts_keep_unix_newlines_in_windows_archive(self):
        root = Path(__file__).resolve().parent.parent
        content = subprocess.check_output(
            ['git', '-c', 'core.autocrlf=true', 'archive', '--format=tar',
             'HEAD', 'deploy/setup-server.sh', 'deploy/release.py'], cwd=root)
        with tarfile.open(fileobj=io.BytesIO(content)) as archive:
            for name in ('deploy/setup-server.sh', 'deploy/release.py'):
                data = archive.extractfile(name).read()
                self.assertNotIn(b'\r', data, name + ' must use LF in the shipped archive')
                self.assertTrue(data.startswith(b'#!'), name)


if __name__ == '__main__':
    unittest.main()
