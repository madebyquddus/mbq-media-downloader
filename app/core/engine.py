import hashlib
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile
from pathlib import Path
from app.core.storage import data_dir

if getattr(sys, 'frozen', False):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parents[2]

CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def find_tool(name):
    suffix = '.exe' if os.name == 'nt' else ''
    locations = [data_dir() / 'tools' / name / (name + suffix), ROOT / 'tools' / name / (name + suffix),
                 ROOT / 'tools' / 'ffmpeg' / (name + suffix), ROOT / 'tools' / 'ffmpeg' / 'bin' / (name + suffix)]

    for path in locations:
        if path.is_file():
            return str(path)
    return shutil.which(name)

def engine_command():
    runtime = []
    for name in ('deno', 'node'):
        path = find_tool(name)
        if path:
            runtime = ['--js-runtimes', f'{name}:{path}']
            break
    tool = find_tool('yt-dlp')
    if tool:
        return [tool, '--ignore-config', '--no-plugin-dirs'] + runtime
    if not getattr(sys, 'frozen', False):
        import importlib.util
        if importlib.util.find_spec('yt_dlp'):
            return [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-plugin-dirs'] + runtime
    raise RuntimeError('yt-dlp is missing. Click UPDATE yt-dlp on Engine to install the official Windows engine.')

def check_engine():
    lines = [f'Application: 1.2.0 | Python: {sys.version.split()[0]}', f'Data: {data_dir()}']
    for name in ('yt-dlp', 'ffmpeg', 'ffprobe'):
        try:
            cmd = engine_command() + ['--version'] if name == 'yt-dlp' else [find_tool(name) or name, '-version']
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20, creationflags=CREATE_FLAGS)
            if result.returncode:
                raise RuntimeError(result.stderr.strip())
            lines.append(f'{name}: {result.stdout.splitlines()[0]}')
            if name != 'yt-dlp':
                lines.append(f'  {find_tool(name)}')
        except Exception as exc:
            lines.append(f'{name}: MISSING / unavailable — {exc}')
    runtime = find_tool('deno') or find_tool('node')
    lines.append(f'JavaScript runtime: {runtime}' if runtime else 'JavaScript runtime: not found. Install Deno for full YouTube support.')
    return '\n'.join(lines)

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'MBQDownloader/1.2'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()

def update_engine():
    if os.name != 'nt':
        raise RuntimeError('The built-in installer targets Windows x64. Update your source install with python -m pip install -U yt-dlp.')
    # Pin the binary and checksum to the same release to avoid a latest-release race.
    release = json.loads(fetch('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest'))
    assets = {a['name']: a['browser_download_url'] for a in release['assets']}
    binary = fetch(assets['yt-dlp_win.zip'])
    checksums = fetch(assets['SHA2-256SUMS']).decode('utf-8')
    expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1].lstrip('*') == 'yt-dlp_win.zip')
    if hashlib.sha256(binary).hexdigest() != expected:
        raise RuntimeError('Official release checksum mismatch. Existing engine was preserved.')
    parent = data_dir() / 'tools'
    parent.mkdir(parents=True, exist_ok=True)
    folder = parent / 'yt-dlp'
    staging = parent / ('yt-dlp-stage-' + uuid.uuid4().hex)
    backup = parent / ('yt-dlp-backup-' + uuid.uuid4().hex)
    staging.mkdir()
    try:
        with zipfile.ZipFile(io.BytesIO(binary)) as archive:
            for entry in archive.infolist():
                target = (staging / entry.filename).resolve()
                if not target.is_relative_to(staging.resolve()) or ':' in entry.filename:
                    raise RuntimeError('Unsafe path in official engine archive. Installation aborted.')
            archive.extractall(staging)
        result = subprocess.run([str(staging / 'yt-dlp.exe'), '--version'], capture_output=True, timeout=30, creationflags=CREATE_FLAGS)
        if result.returncode:
            raise RuntimeError('The downloaded official engine could not run. Existing engine was preserved.')
        (staging / 'SOURCE.txt').write_text(f"Official yt-dlp {release['tag_name']} unpackaged Windows x64 release\n{assets['yt-dlp_win.zip']}\nSHA256: {expected}\n", 'utf-8')
        if folder.exists():
            folder.rename(backup)
        try:
            staging.rename(folder)
        except OSError:
            if backup.exists():
                backup.rename(folder)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    logging.info('Installed official yt-dlp %s', release['tag_name'])
    return f"Installed yt-dlp {release['tag_name']} with verified SHA-256. Restart waiting downloads to use it."
