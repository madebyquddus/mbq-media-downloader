import hashlib
import io
import json
import os
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from test_core import test_directory
from app.core.engine import update_engine

class UpdateTests(unittest.TestCase):
    def make_release(self, filename='yt-dlp.exe'):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr(filename, b'engine-test')
            archive.writestr('_internal/dependency.dll', b'dependency-test')
        binary = stream.getvalue()
        manifest = hashlib.sha256(binary).hexdigest() + '  yt-dlp_win.zip\n'
        release = json.dumps({'tag_name':'test', 'assets':[
            {'name':'yt-dlp_win.zip','browser_download_url':'https://example.test/binary'},
            {'name':'SHA2-256SUMS','browser_download_url':'https://example.test/checksum'}]}).encode()
        return {'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest':release,
                'https://example.test/binary':binary,'https://example.test/checksum':manifest.encode()}

    def test_verified_update_and_dependencies(self):
        with test_directory() as root, patch.dict(os.environ, {'MBQ_DATA_DIR':root}):
            responses = self.make_release()
            with patch('app.core.engine.fetch', side_effect=responses.__getitem__), patch('app.core.engine.subprocess.run') as run:
                run.return_value.returncode = 0
                self.assertIn('verified', update_engine())
            self.assertEqual((Path(root)/'tools/yt-dlp/yt-dlp.exe').read_bytes(), b'engine-test')
            self.assertTrue((Path(root)/'tools/yt-dlp/_internal/dependency.dll').is_file())

    def test_bad_checksum_preserves_engine(self):
        with test_directory() as root, patch.dict(os.environ, {'MBQ_DATA_DIR':root}):
            target = Path(root)/'tools/yt-dlp'
            target.mkdir(parents=True)
            (target/'yt-dlp.exe').write_bytes(b'old')
            responses = self.make_release()
            responses['https://example.test/checksum'] = b'bad  yt-dlp_win.zip'
            with patch('app.core.engine.fetch', side_effect=responses.__getitem__):
                with self.assertRaisesRegex(RuntimeError, 'checksum'):
                    update_engine()
            self.assertEqual((target/'yt-dlp.exe').read_bytes(), b'old')

    def test_archive_traversal_rejected(self):
        with test_directory() as root, patch.dict(os.environ, {'MBQ_DATA_DIR':root}):
            responses = self.make_release('../escape.exe')
            with patch('app.core.engine.fetch', side_effect=responses.__getitem__):
                with self.assertRaisesRegex(RuntimeError, 'Unsafe path'):
                    update_engine()
            self.assertFalse((Path(root)/'tools/escape.exe').exists())
