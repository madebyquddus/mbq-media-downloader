from pathlib import Path
root = Path(SPECPATH)
# External engines remain replaceable beside the executable; do not embed yt-dlp.
datas = [(str(root / 'assets'), 'assets')]
a = Analysis(['main.py'], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=[], excludes=['yt_dlp', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'], noarchive=False)
# Recent Qt uses Windows' native icuuc.dll. PATH can contain an unrelated ICU
# build with versioned exports; bundling that DLL prevents QtCore from loading.
# Leave the native Windows ICU API to the OS loader on supported Windows 10/11.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() != 'icuuc.dll'
              and not Path(entry[0]).name.lower().startswith('icudt')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MBQ Media Downloader',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon=str(root / 'assets' / 'icons' / 'mbq.ico'),
          version=str(root / 'assets' / 'windows-version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='MBQ Media Downloader')
