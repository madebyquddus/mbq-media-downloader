import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import QStandardPaths

def downloads_dir():
    return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation) or str(Path.home() / 'Downloads')

DEFAULTS = dict(folder=downloads_dir(), quality='Best Available', motion=True, theme='Dark',
    container='MP4', audio='MP3', languages='en', metadata=True, thumbnail=False,
    embed_subs=False, write_subs=False, auto_subs=False, chapters=True,
    playlist_folders=True, skip=True, browser='None', concurrency=2,
    template='%(title).120B [%(id)s].%(ext)s')

def data_dir():
    override = os.environ.get('MBQ_DATA_DIR') or os.environ.get('TANGI_DATA_DIR')
    parent = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    path = Path(override or parent / 'MBQDownloader')
    first_launch = not path.exists()
    path.mkdir(parents=True, exist_ok=True)
    legacy = parent / 'TangiYTDownloader'
    if first_launch and not override and legacy.exists():
        import shutil
        for filename in ('settings.json', 'queue.json'):
            if (legacy / filename).is_file():
                shutil.copy2(legacy / filename, path / filename)
        if (legacy / 'history.sqlite3').is_file():
            from contextlib import closing
            with closing(sqlite3.connect(f'file:{(legacy / "history.sqlite3").as_posix()}?mode=ro', uri=True)) as source:
                with closing(sqlite3.connect(path / 'history.sqlite3')) as target:
                    source.backup(target)
    return path

class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root else data_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'history.sqlite3')
        self.db.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, media_key TEXT, title TEXT, url TEXT, source TEXT, date TEXT, file TEXT, quality TEXT, status TEXT)')
        self.db.execute('CREATE INDEX IF NOT EXISTS media_index ON history(media_key,status)')
        self.db.commit()
        self.settings = DEFAULTS.copy()
        try:
            self.settings.update(json.loads((self.root / 'settings.json').read_text('utf-8')))
        except (OSError, ValueError):
            pass
        if self.settings['folder'] == str(Path.home() / 'Downloads' / 'Tangi'):
            self.settings['folder'] = downloads_dir()

    def save_settings(self, settings):
        self.settings.update(settings)
        path = self.root / 'settings.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.settings, indent=2), 'utf-8')
        temp.replace(path)

    def record(self, job):
        info = job['info']
        self.db.execute('INSERT INTO history(media_key,title,url,source,date,file,quality,status) VALUES(?,?,?,?,?,?,?,?)',
            (media_key(info), job['title'], job['url'], info.get('extractor_key', info.get('extractor', '')),
             datetime.now(timezone.utc).isoformat(timespec='seconds'), job.get('file', ''), job['quality'], job['status']))
        self.db.commit()

    def downloaded(self, info):
        return bool(self.db.execute("SELECT 1 FROM history WHERE media_key=? AND status='Completed' LIMIT 1", (media_key(info),)).fetchone())

    def history(self, search=''):
        return self.db.execute('SELECT title,url,source,date,file,quality,status FROM history WHERE title LIKE ? OR url LIKE ? ORDER BY id DESC', ('%' + search + '%', '%' + search + '%')).fetchall()

    def clear_history(self):
        self.db.execute('DELETE FROM history')
        self.db.commit()

def media_key(info):
    return str(info.get('extractor_key') or info.get('ie_key') or info.get('extractor') or 'generic').lower() + ':' + str(info.get('id') or info.get('webpage_url') or info.get('url'))
