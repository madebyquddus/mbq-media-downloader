# MBQ Media Downloader 1.2 — historical verification record

**Record date:** 5 October 2026  
**Status:** Historical development record; the checks below have not been rerun
against this release-candidate source archive.

The original development record states that the application was built and
tested on Windows 11 x64 using Python 3.13.9, PySide6 6.11.2,
PyInstaller 6.22.3, yt-dlp 2026.08.19, FFmpeg/ffprobe 9.0.2 and
Node.js 24.14.1. These are recorded historical environment details, not
current compatibility guarantees.

## Historical automated checks

The original record reports 18 unittest cases passing. That result is not
being represented as a verified result for the current source snapshot.
The release candidate's test suite must be rerun before publication.

The recorded test coverage included:

- Command/argument override rejection and safe argument arrays.
- URL, filename and output-template validation; Windows reserved names.
- Available quality derivation and Best Available selection.
- Native format-card selection and GUI layout/theme behavior.
- Persistent settings, queue and SQLite history.
- Playlist folder and numbered filename construction.
- Real metadata extraction and media downloads/conversions from a local HTTP server.
- FFprobe validation, DASH merging and cancellation behavior.
- GUI enqueue, download completion, history/archive and completed-queue cleanup.
- Verified updater installation, checksum rejection and archive traversal rejection.

## Historical manual checks

The original record reports syntax/import checks, GUI inspection in Light and
Dark themes, and a live metadata-only provider check. These checks are
historical and have not been independently repeated for this archive.

## Packaging model in this source snapshot

`MBQ.spec` builds a **PyInstaller onedir folder distribution** named
`MBQ Media Downloader`. The executable is:

```powershell
dist\MBQ Media Downloader\MBQ Media Downloader.exe
```

This is not a single-file executable or an installer.

The current spec includes the `assets` directory and packages the Python
application and PySide6 runtime through PyInstaller. It explicitly excludes
`yt_dlp`, `PySide6.QtWebEngineCore` and `PySide6.QtWebEngineWidgets`.
The `tools/ffmpeg`, `tools/node` and `tools/yt-dlp` directories in this source
archive are placeholders; they do not contain those runtime binaries.
Users must provide the external engines as described in `README.md`.

The current build script copies the project MIT `LICENSE`, third-party
notices, available supporting documentation, and the `tools` directory into
the distribution folder. It does not download or bundle FFmpeg, Node.js or
yt-dlp. If you add third-party binaries to `tools/` before building, you
become their distributor and must satisfy the applicable upstream license
and redistribution requirements.

## Release verification still required

Before publishing a new release, run the test suite against the exact source
being released, build from a clean environment, and test the resulting folder
distribution on a Windows account where the installation directory is not
writable. Confirm that downloads, engine discovery, updates and user-data
writes work in that environment. Record the actual commands, environment,
test counts and results after execution; do not reuse this historical report
as evidence of a current successful run.

The application executable is not represented as code-signed. Provider
compatibility can change independently of the application.
