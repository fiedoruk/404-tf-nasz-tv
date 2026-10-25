# OrangeGo derivative; modified by Tomasz Fiedoruk on 2026-10-25. GPL-2.0; upstream author lg. See NOTICE.txt.
"""On-demand public programme descriptions. No Kodi imports or I/O at import time."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from .tata_programmes import channel_id, normal, now_next
from .tata_pvr import text

PREFIX = 'nasztv.details.'
MODE = 'nasztv.hud.mode'
MAX_BODY = 2 * 1024 * 1024
FIELDS = ('channel_name', 'now_title', 'now_start', 'now_end', 'now_plot',
          'next_title', 'next_start', 'next_end', 'next_plot')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'


class DetailError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


class KodiAPI:
    def __init__(self, api=None):
        if api is None:
            import xbmc
            api = xbmc
        import xbmcaddon
        import xbmcvfs
        self.api = api
        self.addon = xbmcaddon.Addon('plugin.video.orange_go')
        self.profile = Path(xbmcvfs.translatePath(self.addon.getAddonInfo('profile')))

    def label(self, name):
        return self.api.getInfoLabel(name)

    def playing(self):
        return self.api.getCondVisibility('PVR.IsPlayingTV')

    def now(self):
        return time.time()

    def fetch_detail(self, pid):
        keys = ('logged', 'ci', 'ca', 'Token', 'TokenId', 'hhTech', 'householdExtId')
        values = {k: self.addon.getSetting(k) for k in keys}
        if values['logged'] != 'true' or not all(values[k].strip() for k in keys[1:5]):
            raise DetailError('auth_missing')
        if any('\n' in v or '\r' in v for v in values.values()):
            raise DetailError('invalid_session')
        odi = {'dev_type': 'web_otf', 'app_version': '1.21.1', 'web_native': UA,
               'hh_tech': values['hhTech'], 'serial_number': 'FIREFOX_WEB_TERMINAL_1' + values['householdExtId'], 'offer': ''}
        cookies = {'AnalyticsData': values['ca'], 'I12': values['ci'], 'Token': values['Token'],
                   'TokenId': values['TokenId'], 'Authenticated': 'true'}
        headers = {'Origin': 'https://tvgo.orange.pl', 'Referer': 'https://tvgo.orange.pl/',
                   'User-Agent': UA, 'OtvDeviceInfo2': urllib.parse.urlencode(odi),
                   'Accept': 'application/json;ver=1', 'Accept-Encoding': 'identity',
                   'Cookie': '; '.join(k + '=' + v for k, v in cookies.items())}
        url = 'https://tvgo.orange.pl/gpapi2/core/tvguide/details?' + urllib.parse.urlencode(
            {'programExtId': pid, 'deviceCat': 'otg'})
        started = time.monotonic()
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(urllib.request.Request(url, headers=headers), timeout=5) as response:
                if response.status != 200 or int(response.headers.get('Content-Length', 0)) > MAX_BODY:
                    raise DetailError('response_failed')
                data = bytearray()
                while not response.isclosed():
                    remaining = 5 - (time.monotonic() - started)
                    if remaining <= 0:
                        raise DetailError('timeout')
                    response.fp.raw._sock.settimeout(remaining)
                    chunk = response.read1(min(65536, MAX_BODY + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > MAX_BODY:
                        raise DetailError('response_too_large')
                value = json.loads(data.decode('utf-8'))
                if not isinstance(value, dict) or value.get('errCode') or value.get('error'):
                    raise DetailError('api_error')
                return value
        except urllib.error.HTTPError as error:
            error.close()
            raise DetailError('http_error') from None
        except Exception:
            raise DetailError('unavailable') from None


def _read(path, limit, optional=False):
    try:
        with open(path, 'rb') as handle:
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise ValueError('size')
        result = json.loads(data.decode('utf-8'))
        if not isinstance(result, dict):
            raise ValueError('schema')
        return result
    except (OSError, ValueError, UnicodeError):
        if optional:
            return {}
        raise


def _hm(epoch):
    return datetime.datetime.fromtimestamp(epoch).strftime('%H:%M')


def _normal_hm(value):
    """Compare Kodi's h:mm/HH:mm only; keep raw labels for GUI identity guards."""
    if not isinstance(value, str):
        return None
    parts = value.strip().split(':')
    if (len(parts) != 2 or len(parts[0]) not in (1, 2) or len(parts[1]) != 2
            or any(c not in '0123456789' for part in parts for c in part)):
        return None
    hour, minute = map(int, parts)
    return '%02d:%02d' % (hour, minute) if hour < 24 and minute < 60 else None


class _PublicFiles:
    """Parsed public files reused only inside one load_for_current invocation."""
    def __init__(self, profile):
        self.paths = (Path(profile) / 'channel-metadata.json', Path(profile) / 'tata/programme-index.json')
        self.fingerprints = None
        self.data = None

    def _stat(self):
        values = []
        for path in self.paths:
            stat = path.stat()
            values.append((stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_size))
        return tuple(values)

    def read(self):
        before = self._stat()
        if self.data is not None and self.fingerprints == before:
            data = self.data
        else:
            data = (_read(self.paths[0], 512 * 1024), _read(self.paths[1], 8 * 1024 * 1024))
        after = self._stat()
        if before != after:
            raise ValueError('public_snapshot_changed')  # Fail closed; no read retry loop.
        self.fingerprints, self.data = after, data
        return data


def _snapshot(home, api, public_files=None):
    if home.getProperty(MODE) != '2' or not api.playing():
        return None
    metadata, index = (public_files or _PublicFiles(api.profile)).read()
    if metadata.get('schema') != 1 or index.get('schema') != 1:
        return None
    name = api.label('VideoPlayer.ChannelName')
    cid = channel_id(metadata, name)
    selected = now_next(index, cid, api.now()) if cid else None
    if selected is None:
        return None
    labels = {'channel_name': name}
    for role, p in selected.items():
        base = 'VideoPlayer.' + ('Next' if role == 'next' else '')
        if p is not None:
            expected = (normal(p['title']), _hm(p['start']), _hm(p['end']))
            actual = (normal(api.label(base + 'Title')), _normal_hm(api.label(base + 'StartTime')),
                      _normal_hm(api.label(base + 'EndTime')))
            if expected != actual:
                return None
        for field, suffix in (('title', 'Title'), ('start', 'StartTime'), ('end', 'EndTime'), ('plot', 'Plot')):
            labels[role + '_' + field] = text(api.label(base + suffix), 16384) if p is not None else ''
    identity = (cid, normal(name), tuple((role, p['id'], p['title'], p['start'], p['end'])
                                       for role, p in selected.items() if p is not None))
    return identity, selected, labels


def _key(cid, p):
    return hashlib.sha256(json.dumps([cid, p['id'], p['start'], p['end']], separators=(',', ':')).encode()).hexdigest()


def _publish(home, labels, status):
    home.setProperty(PREFIX + 'status', 'loading')
    for field in FIELDS:
        home.setProperty(PREFIX + field, labels.get(field, ''))
    home.setProperty(PREFIX + 'status', status)


def _request_identity(api):
    return tuple(api.label('VideoPlayer.' + field) for field in ('ChannelName', 'StartTime', 'NextStartTime'))


def _cache_write(path, records):
    records = dict(sorted(records.items(), key=lambda item: item[1]['used'], reverse=True)[:32])
    fd, tmp = tempfile.mkstemp(prefix='.details-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump({'schema': 1, 'records': records}, handle, ensure_ascii=False, separators=(',', ':'))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_for_current(home, api=None):
    """Call after GUI dispatch lock is released. api may be xbmc or an injected HOST bridge."""
    if home.getProperty(MODE) != '2':
        return 'inactive'
    try:
        api = api if api is not None and hasattr(api, 'fetch_detail') else KodiAPI(api)
    except Exception:
        _publish(home, {}, 'error')
        return 'error'
    profile = Path(api.profile) / 'tata'
    try:
        profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(profile / 'details.lock', 'a+b') as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 'busy'
            try:
                home.setProperty(PREFIX + 'busy', '1')
                request_identity = _request_identity(api)
                if (home.getProperty(MODE) != '2' or not api.playing()
                        or request_identity != _request_identity(api)):
                    return 'cache_only'
                for key, value in zip(('request_channel_name', 'request_now_start', 'request_next_start'), request_identity):
                    home.setProperty(PREFIX + key, value)
                public_files = _PublicFiles(api.profile)
                initial = _snapshot(home, api, public_files)
                if initial is None:
                    if home.getProperty(MODE) == '2' and api.playing():
                        _publish(home, {}, 'empty')
                    return 'empty'
                identity, selected, labels = initial
                if request_identity != tuple(labels[key] for key in ('channel_name', 'now_start', 'next_start')):
                    return 'cache_only'
                cache_path = profile / 'details-cache.json'
                cached = _read(cache_path, 1024 * 1024, optional=True)
                records = cached.get('records', {}) if cached.get('schema') == 1 else {}
                now = api.now()
                records = {k: v for k, v in records.items() if isinstance(v, dict)
                           and isinstance(v.get('expires'), (int, float)) and v['expires'] > now
                           and isinstance(v.get('plot'), str) and isinstance(v.get('used'), (int, float))}
                _publish(home, labels, 'loading')
                failed = False
                for role, p in selected.items():
                    if p is None or labels[role + '_plot']:
                        continue  # Native Plot is always first; never fetch it again.
                    key = _key(identity[0], p)
                    if key in records:
                        labels[role + '_plot'] = text(records[key]['plot'], 16384)
                        records[key]['used'] = now
                        continue
                    if home.getProperty(MODE) != '2' or normal(api.label('VideoPlayer.ChannelName')) != normal(labels['channel_name']):
                        break
                    try:
                        detail = api.fetch_detail(p['id'])
                        if (str(detail.get('programExtId')) != p['id']
                                or str(detail.get('channelExtId')) != identity[0]
                                or detail.get('startTimeUtc') != p['start'] or detail.get('endTimeUtc') != p['end']):
                            raise DetailError('identity_mismatch')
                        series = detail.get('series', {})
                        plot = text(series.get('episodeDescription'), 16384) if isinstance(series, dict) else ''
                        plot = plot or text(detail.get('description'), 16384)
                        labels[role + '_plot'] = plot
                        records[key] = {'plot': plot, 'expires': p['end'] + 900 if plot else now + 300, 'used': now}
                    except Exception:
                        failed = True
                        records[key] = {'plot': '', 'expires': now + 300, 'used': now}
                        break  # No retries or second request after failure/auth error.
                try:
                    _cache_write(cache_path, records)
                except OSError:
                    pass  # Cache write failure must not interrupt playback or discard valid text.
                final = _snapshot(home, api, public_files)
                if final is None or final[0] != identity:
                    return 'cache_only'
                for role in ('now', 'next'):
                    labels[role + '_plot'] = final[2][role + '_plot'] or labels[role + '_plot']
                status = 'ready' if labels['now_plot'] or labels['next_plot'] else 'error' if failed else 'empty'
                _publish(home, labels, status)
                return status
            finally:
                try:
                    home.clearProperty(PREFIX + 'busy')
                finally:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    except Exception:
        if home.getProperty(MODE) == '2' and api.playing():
            _publish(home, {}, 'error')
        return 'error'
