import tempfile
import unittest
import contextlib
import shutil
import uuid
import os
from pathlib import Path
from app.core.options import available_qualities, custom_args, download_args, safe_name, selector, urls, validate_template
from app.core.storage import Store, DEFAULTS, media_key

@contextlib.contextmanager
def test_directory():
    # Plain mkdir also works under restricted Windows desktop sandboxes which
    # reject Python's 0o700 TemporaryDirectory ACL.
    base = Path(os.environ.get('MBQ_TEST_ROOT', str(Path(tempfile.gettempdir()) / 'MBQTests')))
    root = base / ('test-' + uuid.uuid4().hex[:8])
    root.mkdir(parents=True)
    try:
        yield str(root)
    finally:
        shutil.rmtree(root)

class CoreTests(unittest.TestCase):
    def test_command_injection_and_override_blocked(self):
        for args in ['--exec calc.exe', '--config-location bad.conf', '--plugin-dirs evil', '-o ../evil', '--print x', '--enable-file-urls', 'https://example.com']:
            with self.assertRaises(ValueError):
                custom_args(args)
        self.assertEqual(custom_args('--limit-rate 5M --retries=10'), ['--limit-rate', '5M', '--retries', '10'])
        self.assertEqual(custom_args('--user-agent "test; calc.exe"'), ['--user-agent', 'test; calc.exe'])

    def test_filename_safety(self):
        self.assertEqual(safe_name('../../CON'), '_.._CON')
        self.assertEqual(safe_name('CON'), '_CON')
        for template in ['../%(title)s.%(ext)s', 'C:\\%(title)s.%(ext)s', '%(bad)s.%(ext)s', '%(title)s']:
            with self.assertRaises(ValueError):
                validate_template(template)
        self.assertEqual(validate_template(DEFAULTS['template']), DEFAULTS['template'])

    def test_real_formats_and_best(self):
        self.assertEqual(available_qualities({'formats':[{'height':720,'vcodec':'h264'}, {'height':2160,'vcodec':'vp9','has_drm':True}]}), ['Best Available','720p'])
        self.assertEqual(selector('Best Available','MP4'), 'bv+ba/b')
        self.assertIn('[height<=1080]', selector('1080p','MKV'))
        with self.assertRaises(ValueError):
            selector('Best Available', 'MKV', '137;calc')

    def test_urls(self):
        self.assertEqual(urls('https://vimeo.com/123 https://vimeo.com/123'), ['https://vimeo.com/123'])
        for value in ['--exec', 'file:///C:/secret', 'javascript:alert(1)', '']:
            with self.assertRaises(ValueError):
                urls(value)

    def test_persistence_and_flat_archive(self):
        with test_directory() as directory:
            store = Store(directory)
            store.save_settings({'concurrency':3})
            info = {'id':'abc','extractor_key':'Youtube'}
            store.record(dict(info=info,title='Test',url='https://example.com',quality='720p',status='Completed',file='test.mp4'))
            self.assertTrue(store.downloaded({'id':'abc','ie_key':'Youtube'}))
            self.assertEqual(len(store.history('Test')), 1)
            store.db.close()
            store = Store(directory)
            self.assertEqual(store.settings['concurrency'],3)
            store.clear_history()
            self.assertFalse(store.downloaded(info))
            store.db.close()

    def test_playlist_arguments(self):
        with test_directory() as directory:
            settings = DEFAULTS | {'folder':directory}
            job = dict(settings=settings,quality='Best Available',mode='Video',url='https://example.com',playlist='../CON',index=3)
            args = download_args(job, 'C:/ffmpeg/ffmpeg.exe')
            template = args[args.index('-o') + 1]
            self.assertIn('003 - ', template)
            self.assertEqual(Path(template).parent.parent, Path(directory).resolve())
            self.assertEqual(args[-2:], ['--','https://example.com'])

if __name__ == '__main__':
    unittest.main()
