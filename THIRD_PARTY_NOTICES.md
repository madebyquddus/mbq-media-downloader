# Third-party components

This source repository contains no third-party runtime binaries. It uses the
components listed below; users provide the external engines unless they
independently bundle them. Each component retains its own upstream license.
The MBQ Media Downloader application source is released under the MIT
License (see `LICENSE`).

- **Python** — Python Software Foundation License.
  https://docs.python.org/3/license.html

- **PySide6 / Qt** — LGPLv3 (or commercial licensing, as applicable).
  https://doc.qt.io/qtforpython-6/licenses.html
  https://www.qt.io/licensing/
  The source application uses the PySide6 Python bindings. A PyInstaller
  onedir build collects PySide6/Qt runtime libraries into the distribution.
  A packaged build must therefore be reviewed as a redistribution of those
  components, not merely as a user-side `pip install`. Before distributing
  a packaged build, include the applicable upstream LGPL and Qt license and
  notice materials from the exact PySide6/Qt versions used. Verify compliance
  with the applicable LGPL terms, including user rights concerning
  replacement or relinking of covered libraries. This project does not
  intentionally modify Qt or PySide6.

- **yt-dlp** — Unlicense for the project source; official executable
  distributions may include components under additional licenses.
  https://github.com/yt-dlp/yt-dlp#licensing
  The application's built-in update action retrieves yt-dlp at the user's
  request at runtime; this source distribution does not ship yt-dlp.

- **FFmpeg** — licensing depends on the build selected by the user.
  https://ffmpeg.org/legal.html
  https://www.gyan.dev/ffmpeg/builds/
  Some commonly used Windows builds are GPLv3. Anyone redistributing such
  a build must meet the applicable GPL requirements, including providing
  corresponding source and license notices. Users who bundle and redistribute
  FFmpeg are responsible for verifying the exact build's terms.

- **Node.js** — MIT License and included third-party licenses.
  https://github.com/nodejs/node/blob/main/LICENSE

- **Deno** — MIT License.
  https://github.com/denoland/deno/blob/main/LICENSE.md

- **PyInstaller** — GPLv2-or-later with a bootloader exception for
  distributing applications built with PyInstaller.
  https://pyinstaller.org/en/stable/license.html
  Retain applicable PyInstaller license and bootloader notices with packaged
  distributions as required by the upstream terms.

## Responsibility

The application does not circumvent DRM, paywalls, or access controls.
Users are responsible for:

- installing or bundling third-party tools in accordance with their licenses;
- downloading only media they are authorized to access; and
- complying with applicable service terms, copyright rules and laws.

## PyInstaller builds

A build made with `build.ps1` / `MBQ.spec` contains PySide6/Qt runtime
libraries and PyInstaller runtime files. It may also contain tools placed in
`tools/`. The build script copies this project's `LICENSE` and this notice
file, but it cannot automatically establish that all upstream license texts
and notices are present. Before redistribution, add and verify the materials
required for the exact versions and binaries included. This is particularly
important for Qt/PySide6 LGPL compliance and GPL-licensed FFmpeg builds.
Do not bundle a binary unless its redistribution terms and any
corresponding-source obligations have been verified.
