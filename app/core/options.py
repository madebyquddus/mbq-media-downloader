import re
import shlex
from pathlib import Path
from urllib.parse import urlparse

QUALITIES = [('Best Available', None), ('8K', 4320), ('4K', 2160), ('1440p', 1440), ('1080p', 1080), ('720p', 720), ('480p', 480), ('360p', 360)]
# Intentionally narrow: output, execution, config, plugin and postprocessor arguments
# cannot override the application's security and progress protocol.
CUSTOM = {'--limit-rate', '--retries', '--fragment-retries', '--socket-timeout',
          '--concurrent-fragments', '--proxy', '--user-agent', '--referer'}

def custom_args(text):
    tokens = shlex.split(text, posix=True)
    result = []
    while tokens:
        token = tokens.pop(0)
        option, sep, value = token.partition('=')
        if option not in CUSTOM:
            raise ValueError(f'Unsupported advanced option: {option}. Allowed: {", ".join(sorted(CUSTOM))}')
        if not sep:
            if not tokens or tokens[0].startswith('--'):
                raise ValueError(f'{option} requires a value')
            value = tokens.pop(0)
        if '\x00' in value or '\n' in value:
            raise ValueError('Invalid argument value')
        if option in {'--retries', '--fragment-retries', '--socket-timeout', '--concurrent-fragments'}:
            if not value.isdigit() or not 1 <= int(value) <= 1000:
                raise ValueError(f'{option} must be an integer between 1 and 1000')
        result.extend([option, value])
    return result

def urls(text):
    values = text.split()
    if not values:
        raise ValueError('Paste at least one URL.')
    for value in values:
        parsed = urlparse(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or '\x00' in value:
            raise ValueError('Use full http:// or https:// media URLs, one per line.')
    return list(dict.fromkeys(values))

def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value)).strip(' .')[:80] or 'Untitled'
    if value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        value = '_' + value
    return value

def validate_template(template):
    # Limit fields to names which cannot introduce untrusted path components.
    if len(template) > 200 or '/' in template or '\\' in template or '..' in template:
        raise ValueError('Filename template must be a filename, without directories or ..')
    remainder = re.sub(r'%\((title|id|ext|uploader|upload_date)\)(?:\.\d{1,3})?[Bs]', '', template)
    if '%' in remainder or re.search(r'[<>:"|?*\x00-\x1f]', remainder) or '%(ext)s' not in template:
        raise ValueError('Use title, id, ext, uploader or upload_date fields and include %(ext)s.')
    return template

def available_qualities(info):
    heights = {
        int(f.get('height'))
        for f in info.get('formats', [])
        if not f.get('has_drm')
        and f.get('vcodec') not in ('none', None)
        and isinstance(f.get('height'), (int, float))
        and f.get('height') > 0
    }

    if not heights:
        return ['Best Available']

    result = ['Best Available']

    for label, height in QUALITIES:
        if height is not None and height in heights:
            result.append(label)

    return result

def selector(quality, container, exact=''):
    if exact:
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+(?:\+[a-zA-Z0-9_.-]+)?', exact):
            raise ValueError('Choose one format ID or a video ID + audio ID.')
        return exact
    height = dict(QUALITIES).get(quality)
    cap = f'[height<={height}]' if height else ''
    if height is None:
        return 'bv+ba/b'
    if container == 'MP4':
        return f'bv{cap}[ext=mp4]+ba[ext=m4a]/b{cap}[ext=mp4]/bv{cap}+ba/b{cap}'
    if container == 'WebM':
        return f'bv{cap}[ext=webm]+ba[ext=webm]/b{cap}[ext=webm]/bv{cap}+ba/b{cap}'
    return f'bv{cap}+ba/b{cap}'

def download_args(job, ffmpeg):
    s = job['settings']
    folder = Path(s['folder']).expanduser().resolve()
    if job.get('playlist') and s['playlist_folders']:
        folder /= safe_name(job['playlist'])
    folder.mkdir(parents=True, exist_ok=True)
    template = validate_template(s['template'])
    if job.get('playlist'):
        template = f"{job.get('index', 1):03d} - " + template
    if len(str(folder)) > 140:
        raise ValueError('Download folder path is too long. Choose a shorter path (under 140 characters).')
    max_name = min(150, 240 - len(str(folder)))
    args = ['--no-playlist', '--windows-filenames', '--trim-filenames', str(max_name), '--no-overwrites',
            '--newline', '--no-quiet', '--progress', '--progress-delta', '0.3', '--encoding', 'utf-8',
            '--progress-template', 'download:MBQ_PROGRESS:%(progress)j',
            '--print', 'after_move:MBQ_FILE:%(filepath)j', '-o', str(folder / template)]
    if ffmpeg:
        args += ['--ffmpeg-location', str(Path(ffmpeg).parent)]
    if job['mode'] == 'Audio':
        args += ['-f', job.get('exact') or 'ba/b', '-x', '--audio-format', s['audio'].lower(), '--audio-quality', '0']
    else:
        args += ['-f', selector(job['quality'], s['container'], job.get('exact', '')),
                 '--merge-output-format', s['container'].lower(), '--remux-video', s['container'].lower()]
    if s['metadata']:
        args += ['--embed-metadata']
    if s['chapters']:
        args += ['--embed-chapters']
    if s['thumbnail']:
        args += ['--embed-thumbnail', '--convert-thumbnails', 'png']
    if s['write_subs'] or s['embed_subs']:
        args += ['--write-subs']
    if s['auto_subs']:
        args += ['--write-auto-subs']
    if s['embed_subs']:
        args += ['--embed-subs']
    args += ['--sub-langs', s['languages'] or 'en']
    if s['browser'] != 'None':
        args += ['--cookies-from-browser', s['browser'].lower()]
    args += custom_args(job.get('custom', ''))
    return args + ['--', job['url']]

def explain_error(details):
    text = details.lower()
    cases = [
        (('yt-dlp is missing',), 'yt-dlp engine is missing. Open Engine and click UPDATE yt-dlp to install it.'),
        (('ffmpeg', 'ffprobe'), 'FFmpeg/ffprobe is missing or processing failed. Check Engine and the selected output format.'),
        (('permission denied', 'no space left', 'disk full', 'winerror 5', 'unable to open for writing'), 'Disk/write error. Check free space and download-folder permissions.'),
        (('unsupported url', 'no suitable extractor'), 'Unsupported URL/site. Check the full URL or update yt-dlp.'),
        (('sign in', 'login', 'cookies', 'authentication'), 'Authentication required. Optionally use an existing browser login session in Settings.'),
        (('private', 'restricted', 'not available in your country'), 'Private or restricted media. Your account must have legitimate access.'),
        (('unavailable', 'removed', 'deleted', '404'), 'Media unavailable. It may have been removed or the URL may be incorrect.'),
        (('requested format', 'no video formats'), 'Format unavailable. Analyze again and select an available format.'),
        (('timed out', 'connection', 'resolve', 'network', '429'), 'Network failure or rate limit. Check connectivity, wait, and retry.'),
        (('extract', 'signature', 'nsig', 'javascript'), 'Extractor failure; yt-dlp may be outdated or a JavaScript runtime may be required. Update on Engine and see the log.'),
    ]
    for needles, message in cases:
        if any(n in text for n in needles):
            return message
    return 'Download failed. Check the technical details and update yt-dlp on Engine if the website changed.'
