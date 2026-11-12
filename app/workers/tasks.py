import json
import logging
import os
import subprocess
import threading
import signal
from collections import deque
from PySide6.QtCore import QThread, Signal
from app.core.engine import CREATE_FLAGS, engine_command, find_tool
from app.core.options import download_args, explain_error


def _windows_process_tree(root_pid):
    """Return root_pid and descendants using the Windows Toolhelp snapshot API."""
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    MAX_PATH = 260

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ('dwSize', wintypes.DWORD),
            ('cntUsage', wintypes.DWORD),
            ('th32ProcessID', wintypes.DWORD),
            ('th32DefaultHeapID', ctypes.c_size_t),
            ('th32ModuleID', wintypes.DWORD),
            ('cntThreads', wintypes.DWORD),
            ('th32ParentProcessID', wintypes.DWORD),
            ('pcPriClassBase', wintypes.LONG),
            ('dwFlags', wintypes.DWORD),
            ('szExeFile', wintypes.WCHAR * MAX_PATH),
        ]

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return [int(root_pid)]

    children = {}
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)

    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            children.setdefault(int(entry.th32ParentProcessID), []).append(int(entry.th32ProcessID))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    result = []
    stack = [int(root_pid)]
    seen = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        result.append(pid)
        stack.extend(children.get(pid, ()))
    return result


def _windows_suspend_resume(pid, suspend):
    """Suspend or resume one process with NtSuspendProcess/NtResumeProcess."""
    import ctypes

    PROCESS_SUSPEND_RESUME = 0x0800
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    ntdll = ctypes.WinDLL('ntdll')

    handle = kernel32.OpenProcess(
        PROCESS_SUSPEND_RESUME | PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        int(pid),
    )
    if not handle:
        return False

    try:
        func = ntdll.NtSuspendProcess if suspend else ntdll.NtResumeProcess
        status = func(handle)
        return status == 0
    finally:
        kernel32.CloseHandle(handle)


def _pause_process_tree(pid):
    if os.name == 'nt':
        # Suspend children first, then the yt-dlp parent.
        pids = _windows_process_tree(pid)
        changed = False
        for child_pid in reversed(pids):
            changed = _windows_suspend_resume(child_pid, True) or changed
        return changed

    try:
        os.kill(pid, signal.SIGSTOP)
        return True
    except OSError:
        return False


def _resume_process_tree(pid):
    if os.name == 'nt':
        # Resume parent first, then descendants.
        pids = _windows_process_tree(pid)
        changed = False
        for child_pid in pids:
            changed = _windows_suspend_resume(child_pid, False) or changed
        return changed

    try:
        os.kill(pid, signal.SIGCONT)
        return True
    except OSError:
        return False


class FunctionWorker(QThread):
    result = Signal(object)
    error = Signal(str, str)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn
    def run(self):
        try:
            self.result.emit(self.fn())
        except Exception as exc:
            logging.exception('Background operation failed')
            self.error.emit(explain_error(str(exc)), str(exc))

class ProcessWorker(QThread):
    event = Signal(object)
    result = Signal(object)
    error = Signal(str, str)
    def __init__(self, mode, payload, parent=None):
        super().__init__(parent)
        self.mode, self.payload = mode, payload
        self.cancelled = threading.Event()
        self.paused = threading.Event()
        self.process = None
        self.lock = threading.Lock()

    def pause(self):
        """Pause the current yt-dlp/FFmpeg process tree without cancelling it."""
        if self.cancelled.is_set() or self.isFinished():
            return False
        self.paused.set()
        with self.lock:
            process = self.process
        if process and process.poll() is None:
            _pause_process_tree(process.pid)
        return True

    def resume(self):
        """Resume a process tree previously paused with pause()."""
        if self.cancelled.is_set() or self.isFinished():
            return False
        was_paused = self.paused.is_set()
        self.paused.clear()
        with self.lock:
            process = self.process
        if process and process.poll() is None:
            _resume_process_tree(process.pid)
        return was_paused

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.process and self.process.poll() is None:
                # Kill FFmpeg children too; no shell and only a process ID we own.
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'], capture_output=True, creationflags=CREATE_FLAGS)
                else:
                    self.process.terminate()

    def run(self):
        details = deque(maxlen=100)
        try:
            cmd = engine_command()
            if self.mode in ('analyze', 'channel_profile'):
                cmd += ['--flat-playlist', '--dump-single-json', '--skip-download', '--encoding', 'utf-8', '--socket-timeout', '20', '--retries', '2']
                if self.payload.get('browser', 'None') != 'None':
                    cmd += ['--cookies-from-browser', self.payload['browser'].lower()]
                if self.mode == 'channel_profile':
                    cmd += ['--playlist-end', '1']
                cmd += ['--', self.payload['url']]

            elif self.mode == 'channel':
                cmd += ['--flat-playlist', '--dump-json', '--skip-download', '--encoding', 'utf-8', '--socket-timeout', '20', '--retries', '2']
                if self.payload.get('browser', 'None') != 'None':
                    cmd += ['--cookies-from-browser', self.payload['browser'].lower()]
                cmd += ['--', self.payload['url']]

            else:
                ffmpeg = find_tool('ffmpeg')
                if not ffmpeg or not find_tool('ffprobe'):
                    raise RuntimeError('FFmpeg/ffprobe missing. Install both on Engine before downloading.')
                cmd += download_args(self.payload, ffmpeg)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            with self.lock:
                if self.cancelled.is_set():
                    self.event.emit({'status': 'Cancelled'})
                    return
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace', env=env, creationflags=CREATE_FLAGS, shell=False)
            if self.paused.is_set() and self.process.poll() is None:
                _pause_process_tree(self.process.pid)
            metadata = None
            output = None
            channel_count = 0
            for raw in self.process.stdout:
                line = raw.strip()
                if self.cancelled.is_set():
                    break
                if line.startswith('MBQ_PROGRESS:'):
                    try:
                        progress = json.loads(line[len('MBQ_PROGRESS:'):])
                        self.event.emit({'status': 'Downloading' if progress.get('status') == 'downloading' else 'Processing', 'progress': progress})
                    except ValueError:
                        logging.warning('Unrecognized progress: %s', line[:500])
                elif line.startswith('MBQ_FILE:'):
                    output = json.loads(line[len('MBQ_FILE:'):])
                elif self.mode == 'channel' and line.startswith('{'):
                    try:
                        entry = json.loads(line)
                        channel_count += 1
                        self.event.emit({
                            'status': 'Channel item',
                            'entry': entry,
                            'count': channel_count
                        })
                    except ValueError:
                        details.append(line)
                        logging.warning('Invalid channel JSON: %s', line[:500])

                elif self.mode in ('analyze', 'channel_profile') and line.startswith('{'):
                    metadata = json.loads(line)
                else:
                    details.append(line)
                    logging.info('%s', line)
                    if '[Merger]' in line:
                        self.event.emit({'status': 'Merging'})
                    elif any(marker in line for marker in ('[ExtractAudio]', '[Metadata]', '[Embed', '[VideoRemuxer]', '[ThumbnailsConvertor]')):
                        self.event.emit({'status': 'Processing'})
            self.process.stdout.close()
            code = self.process.wait()
            if self.cancelled.is_set():
                self.event.emit({'status': 'Cancelled'})
            elif code:
                raise RuntimeError('\n'.join(details) or f'Engine exit code {code}')
            elif self.mode in ('analyze', 'channel_profile'):
                if not metadata:
                    raise RuntimeError('Extractor returned no metadata. Update yt-dlp and see log.')
                self.result.emit(metadata)
            elif self.mode == 'channel':
                self.result.emit({'count': channel_count, 'complete': True})
            elif output and os.path.isfile(output):
                self.result.emit(output)
            else:
                raise RuntimeError('Engine finished but did not report an existing output file. See the log for processing errors.')
        except Exception as exc:
            if self.cancelled.is_set():
                self.event.emit({'status': 'Cancelled'})
            else:
                logging.exception('Engine operation failed')
                self.error.emit(explain_error(str(exc)), str(exc))
