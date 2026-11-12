import os
import unittest
from unittest.mock import patch
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, QRect
from PySide6.QtTest import QTest
from app.core.storage import Store, downloads_dir, data_dir
from app.ui.window import MainWindow
from test_core import test_directory

class BrandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_downloads_default_and_custom_folder_preserved(self):
        with test_directory() as root:
            store = Store(root)
            self.assertEqual(store.settings['folder'], downloads_dir())
            store.save_settings({'folder':str(Path(root)/'custom')})
            store.db.close()
            store = Store(root)
            self.assertEqual(store.settings['folder'], str(Path(root)/'custom'))
            store.db.close()

    def test_cards_select_output_and_available_quality(self):
        with test_directory() as root, patch.dict(os.environ, {'MBQ_DATA_DIR':root}):
            window = MainWindow()
            info = {'id':'cards','title':'Card selection fixture','formats':[
                {'format_id':'v','height':720,'width':1280,'fps':30,'vcodec':'h264','acodec':'none','url':'https://example.test/video'},
                {'format_id':'a','vcodec':'none','acodec':'aac','url':'https://example.test/audio'}]}
            window.add_media(info, 'https://example.test/watch')
            self.assertEqual([c.choice for c in window.format_cards], ['Best Available','720p'])
            window.format_cards[1].click()
            self.assertEqual(window.quality.currentText(), '720p')
            window.mode_buttons['Audio'].click()
            next(c for c in window.format_cards if c.choice == 'Opus').click()
            self.assertEqual(window.output.currentText(), 'Opus')
            self.assertIn('Opus', window.selection_summary.text())
            window.mode_buttons['Video'].click()
            window.container_buttons['MKV'].click()
            self.assertEqual(window.output.currentText(), 'MKV')
            self.assertNotIn('1080p', [c.choice for c in window.format_cards])
            window.store.save_settings({'motion':False})
            window.apply_motion()
            self.assertFalse(window.canvas.timer.isActive())
            self.assertFalse(window.pages.motion)
            window.close()
            deadline = __import__('time').monotonic() + 25
            while window.workers and __import__('time').monotonic() < deadline:
                self.app.processEvents()
                __import__('time').sleep(.02)
            self.app.processEvents()
            import logging
            logging.shutdown()
            logging.getLogger().handlers.clear()

    def test_mbq_data_directory_initialization(self):
        with test_directory() as root, patch.dict(os.environ, {
                'LOCALAPPDATA':root, 'MBQ_DATA_DIR':''}):
            path = data_dir()
            self.assertEqual(path, Path(root) / 'MBQDownloader')
            self.assertTrue(path.is_dir())
            store = Store(path)
            self.assertTrue((path / 'history.sqlite3').exists())
            store.db.close()
    def test_theme_persistence_and_download_footer_with_many_cards(self):
        with test_directory() as root, patch.dict(os.environ, {'MBQ_DATA_DIR':root}):
            window = None
            try:
                window = MainWindow()
                window.resize(1000,740)
                window.show()
                info = {'id':'many','title':'Many quality fixture','formats':[
                    {'format_id':str(h),'height':h,'width':int(h*16/9),'fps':25,
                     'vcodec':'h264','acodec':'none','url':'https://example.test/video'}
                    for h in (2160,1440,1080,720,480,360)]}
                window.add_media(info,'https://example.test/watch')
                window.next_analysis()
                QTest.qWait(300)
                self.assertEqual(len(window.format_cards),7)
                self.assertEqual(len({c.accent.name() for c in window.format_cards}),7)
                self.assertEqual([c.choice for c in window.format_cards if c.best], ['Best Available'])
                window.canvas.frame.emit(3.0)
                self.assertEqual(window.format_cards[0].phase,3.0)
                self.assertTrue(all(c.phase == 0 for c in window.format_cards[1:]))

                for theme in ('Light','Dark'):
                    window.set_theme(theme)
                    window.nav.setCurrentRow(5)
                    QTest.qWait(300)
                    self.assertIsNone(window.pages.currentWidget().graphicsEffect())
                    window.nav.setCurrentRow(0)
                    QTest.qWait(300)

                    b = window.download_button
                    self.assertTrue(b.isVisible() and b.isEnabled())
                    self.assertIsNone(b.graphicsEffect())
                    rect = QRect(b.mapTo(window,QPoint()),b.size())
                    self.assertTrue(window.rect().contains(rect))

                    # Inspect the button itself, not the main-window background.
                    pixel = b.grab().toImage().pixelColor(
                        b.width() // 4, b.height() // 2
                    )
                    self.assertGreater(pixel.blue(),pixel.red()+30)
                    self.assertEqual(window.canvas.light, theme=='Light')

                    saved = Store(root)
                    try:
                        self.assertEqual(saved.settings['theme'],theme)
                    finally:
                        saved.db.close()

                window.store.save_settings({'motion':False})
                window.apply_motion()
                self.assertFalse(window.canvas.timer.isActive())
                self.assertEqual(window.format_cards[0].phase,0.0)

            finally:
                if window is not None:
                    window.close()
                    deadline = __import__('time').monotonic() + 25
                    while window.workers and __import__('time').monotonic() < deadline:
                        self.app.processEvents()
                        __import__('time').sleep(.02)

                    self.app.processEvents()
                    if not window.workers:
                        window.close()
                        self.app.processEvents()

                # Close file handlers before test_directory removes its files.
                import logging
                logging.shutdown()
                logging.getLogger().handlers.clear()
