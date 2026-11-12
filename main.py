import sys
import json
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from app.ui.window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName('MBQ DOWNLOADER')
    app.setApplicationVersion('1.2.0')
    app.setOrganizationName('MadeByQuddus')
    resources = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    app.setWindowIcon(QIcon(str(resources / 'assets' / 'icons' / 'mbq.ico')))
    window = MainWindow()
    window.show()
    if '--smoke-test' in sys.argv:
        def finish_test():
            report = window.store.root / 'smoke-test.json'
            window.grab().save(str(window.store.root / 'smoke-test.png'))
            report.write_text(json.dumps({'gui': 'launched', 'pages': window.pages.count(),
                'engine': window.engine_status.toPlainText()}, indent=2), 'utf-8')
            window.close()
        QTimer.singleShot(8000, finish_test)
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
