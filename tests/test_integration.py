import functools
import http.server
import os
import shutil
import subprocess
import threading
import time
import unittest
import uuid
import tempfile
from pathlib import Path
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from app.core.engine import CREATE_FLAGS, find_tool
from app.core.storage import DEFAULTS
from app.workers.tasks import ProcessWorker

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        cls.root = None
        cls.old_data = os.environ.get('MBQ_DATA_DIR')
        cls.server = None
        cls.thread = None
        try:
            base = Path(os.environ.get('MBQ_TEST_ROOT', str(Path(tempfile.gettempdir()) / 'MBQTests')))
            cls.root = base / ('it-' + uuid.uuid4().hex[:8])
            cls.root.mkdir(parents=True)
            os.environ['MBQ_DATA_DIR'] = str(cls.root / 'data')

            cls.ffmpeg = find_tool('ffmpeg')
            cls.ffprobe = find_tool('ffprobe')
            if not cls.ffmpeg or not cls.ffprobe:
                raise unittest.SkipTest('Install FFmpeg and ffprobe to run integration tests.')

            subprocess.run([cls.ffmpeg, '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                'testsrc=size=320x180:rate=24', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                '-t', '2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(cls.root / 'sample.mp4')],
                check=True, creationflags=CREATE_FLAGS)
            subprocess.run([cls.ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(cls.root / 'sample.mp4'),
                '-c:v', 'libvpx-vp9', '-c:a', 'libopus', str(cls.root / 'sample.webm')],
                check=True, creationflags=CREATE_FLAGS)
            subprocess.run([cls.ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(cls.root / 'sample.mp4'),
                '-c', 'copy', '-f', 'dash', 'manifest.mpd'], check=True,
                creationflags=CREATE_FLAGS, cwd=cls.root)

            # Exceed yt-dlp's initial transfer burst so cancellation remains deterministic.
            shutil.copy2(cls.root / 'sample.mp4', cls.root / 'cancel.mp4')
            with (cls.root / 'cancel.mp4').open('ab') as sample:
                sample.write(b'\0' * (5 * 1024 * 1024))

            handler = functools.partial(QuietHandler, directory=str(cls.root))
            cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
            cls.thread.start()
            cls.url = f'http://127.0.0.1:{cls.server.server_port}/sample.mp4'
        except BaseException:
            cls._cleanup_class_resources()
            raise

    @classmethod
    def _cleanup_class_resources(cls):
        if cls.server is not None:
            if cls.thread is not None and cls.thread.is_alive():
                cls.server.shutdown()
            cls.server.server_close()
            cls.server = None
        if cls.thread is not None:
            cls.thread.join(timeout=5)
            cls.thread = None
        if cls.old_data is None:
            os.environ.pop('MBQ_DATA_DIR', None)
        else:
            os.environ['MBQ_DATA_DIR'] = cls.old_data
        if cls.root is not None:
            shutil.rmtree(cls.root, ignore_errors=True)
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        try:
            cls._cleanup_class_resources()
        finally:
            super().tearDownClass()

    def run_worker(self, mode, payload, cancel_after=None):
        loop = QEventLoop()
        worker = ProcessWorker(mode, payload)
        results, errors, events = [], [], []
        worker.result.connect(results.append)
        worker.error.connect(lambda msg, detail: errors.append((msg, detail)))
        worker.event.connect(events.append)
        worker.finished.connect(loop.quit)
        timeout = QTimer()
        timeout.setSingleShot(True)
        timeout.timeout.connect(worker.cancel)
        timeout.start(45000)
        if cancel_after is not None:
            QTimer.singleShot(cancel_after, worker.cancel)
        worker.start()
        loop.exec()
        worker.wait(10000)
        timeout.stop()
        self.assertFalse(worker.isRunning())
        return results, errors, events

    def test_real_analysis_video_and_audio(self):
        results, errors, _ = self.run_worker('analyze', dict(url=self.url, browser='None'))
        self.assertFalse(errors, errors)
        info = results[0]
        self.assertTrue(info['formats'])
        self.assertFalse(any((self.root / 'downloads').glob('*')))
        for mode, output in [('Video', 'MP4'), ('Video', 'MKV'), ('Video', 'WebM'), ('Audio', 'MP3'), ('Audio', 'M4A'), ('Audio', 'Opus'), ('Audio', 'WAV')]:
            settings = DEFAULTS | {'folder':str(self.root / 'downloads' / output), 'audio':output if mode == 'Audio' else 'MP3',
                                   'container':output if mode == 'Video' else 'MP4'}
            job = dict(url=self.url.replace('sample.mp4', 'sample.webm') if output == 'WebM' else self.url,
                       settings=settings, mode=mode, quality='Best Available', playlist='', exact='')
            files, errors, events = self.run_worker('download', job)
            self.assertFalse(errors, errors)
            self.assertTrue(files, (mode, output, events))
            self.assertEqual(Path(files[0]).suffix.lower(), '.' + output.lower())
            self.assertGreater(Path(files[0]).stat().st_size, 100)
            probe = subprocess.run([find_tool('ffprobe'), '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', files[0]], capture_output=True, text=True, creationflags=CREATE_FLAGS)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertGreater(float(probe.stdout.strip()), 1)
            self.assertTrue(any(e.get('progress') for e in events))

    def test_cancel_active_process(self):
        job = dict(url=self.url.replace('sample.mp4', 'cancel.mp4'), settings=DEFAULTS | {'folder':str(self.root / 'cancel')},
                   mode='Video', quality='Best Available', custom='--limit-rate 1K')
        files, errors, events = self.run_worker('download', job, cancel_after=1000)
        self.assertFalse(files)
        self.assertFalse(errors)
        self.assertTrue(any(e.get('status') == 'Cancelled' for e in events))

    def test_real_dash_video_audio_merge(self):
        job = dict(url=self.url.replace('sample.mp4', 'manifest.mpd'),
                   settings=DEFAULTS | {'folder':str(self.root / 'merged'), 'container':'MKV'},
                   mode='Video', quality='Best Available')
        files, errors, events = self.run_worker('download', job)
        self.assertFalse(errors, errors)
        self.assertTrue(files)
        self.assertTrue(any(e['status'] == 'Merging' for e in events), events)
        probe = subprocess.run([find_tool('ffprobe'), '-v', 'error', '-show_entries', 'stream=codec_type',
            '-of', 'csv=p=0', files[0]], capture_output=True, text=True, creationflags=CREATE_FLAGS)
        self.assertIn('video', probe.stdout)
        self.assertIn('audio', probe.stdout)

    def test_useful_unavailable_error(self):
        results, errors, events = self.run_worker('analyze', dict(url=self.url.replace('sample.mp4', 'missing.mp4')))
        self.assertFalse(results)
        self.assertTrue(errors)
        self.assertIn('unavailable', errors[0][0].lower())

    def test_gui_queue_and_history(self):
        from app.ui.window import MainWindow
        results, errors, _ = self.run_worker('analyze', dict(url=self.url))
        self.assertFalse(errors, errors)
        window = MainWindow()
        try:
            window.show()
            window.folder.setText(str(self.root / 'gui-output'))
            window.save_settings()
            window.add_media(results[0], self.url)
            self.assertTrue(window.current_info['formats'])
            self.assertGreater(window.formats_table.rowCount(), 0)
            window.enqueue()
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline and (
                window.workers or not window.jobs or
                window.jobs[0]['status'] not in ('Completed', 'Failed')
            ):
                self.app.processEvents()
                time.sleep(0.02)
            self.assertTrue(window.jobs, 'Enqueue should create a queue job')
            self.assertEqual(window.jobs[0]['status'], 'Completed', window.jobs[0].get('details'))
            self.assertTrue(Path(window.jobs[0]['file']).is_file())

            window.refresh_history()
            self.assertGreater(window.history_table.rowCount(), 0)
            window.enqueue()
            self.assertEqual(len(window.jobs), 1, 'Archive should skip the same completed media')

            completed_ids = {job['id'] for job in window.jobs if job['status'] == 'Completed'}
            self.assertTrue(completed_ids)
            window.clear_completed()
            self.assertFalse(any(job['status'] == 'Completed' for job in window.jobs))
            self.assertTrue(completed_ids.isdisjoint(window.queue_cards))
        finally:
            window.close()
            self.app.processEvents()

if __name__ == '__main__':
    unittest.main()
