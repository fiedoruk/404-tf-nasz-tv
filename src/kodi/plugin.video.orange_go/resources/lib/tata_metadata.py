# OrangeGo derivative; modified by Tomasz Fiedoruk on 2026-10-25. GPL-2.0; upstream author lg. See NOTICE.txt.
"""Small, credential-free channel metadata cache; never performs network I/O."""

import json
import os
import tempfile

MAX_CACHE_BYTES = 512 * 1024


def _text(value, limit=256):
    return value.strip()[:limit] if isinstance(value, str) else ''


def save_channels(path, channels):
    """Write only public channel fields; failure must not affect channel listing."""
    temporary = None
    try:
        entries = {}
        for channel in channels:
            cid = channel.get('channelExtId')
            if not isinstance(cid, (str, int)) or isinstance(cid, bool):
                continue
            cid = str(cid).strip()[:128]
            if not cid:
                continue
            entries[cid] = {
                'name': _text(channel.get('name')),
                'logo_signature': _text(channel.get('logoSignature'), 1024),
                'category': _text(channel.get('category')),
            }
        payload = json.dumps({'schema': 1, 'channels': entries}, ensure_ascii=False)
        if len(payload.encode('utf-8')) > MAX_CACHE_BYTES:
            return False
        fd, temporary = tempfile.mkstemp(prefix='channel-metadata-', suffix='.tmp',
                                         dir=os.path.dirname(path))
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(payload)
        os.replace(temporary, path)
        return True
    except (OSError, TypeError, ValueError, AttributeError):
        return False
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass


def get_channel(path, cid, logo_base, fallback_icon, live=True):
    """Resolve a label without fetching channels or EPG on the playback path."""
    cid = str(cid).strip()[:128] if cid is not None else ''
    entry = {}
    try:
        with open(path, encoding='utf-8') as handle:
            raw = handle.read(MAX_CACHE_BYTES + 1)
        if len(raw.encode('utf-8')) <= MAX_CACHE_BYTES:
            cache = json.loads(raw)
            if cache.get('schema') == 1:
                entry = cache.get('channels', {}).get(cid, {})
        if not isinstance(entry, dict):
            entry = {}
    except (OSError, TypeError, ValueError, AttributeError):
        entry = {}
    name = _text(entry.get('name')) or ('Kanał ' + cid if cid else 'Orange TV')
    signature = _text(entry.get('logo_signature'), 1024)
    category = _text(entry.get('category'))
    return {
        'channel_id': cid,
        'name': name,
        'logo': logo_base + signature if signature else fallback_icon,
        'plot': ('Telewizja na żywo' if live else 'Archiwum kanału')
                + (' · ' + category if category else ''),
        'is_live': live,
    }
