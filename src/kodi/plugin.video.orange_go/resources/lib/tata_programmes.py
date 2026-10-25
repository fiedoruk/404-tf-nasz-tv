# OrangeGo derivative; modified by Tomasz Fiedoruk on 2026-10-25. GPL-2.0; upstream author lg. See NOTICE.txt.
"""Public programme index from already fetched EPG. Import has no I/O or Kodi dependency."""
import json
from datetime import datetime, timezone
import math
import re
import unicodedata
from .tata_pvr import text


def build_index(channels, epg):
    selected = {}
    for c in channels:
        if not isinstance(c, dict):
            continue
        cid = str(c.get('channelExtId', ''))
        features = c.get('playFeatures', {})
        otg = features.get('otg', {}) if isinstance(features, dict) else {}
        if (cid.isascii() and cid.isdecimal() and c.get('isSubscribed') is True
                and isinstance(otg, dict) and otg.get('isChannelAllowed') is True):
            selected.setdefault(cid, {'name': text(c.get('name')), 'programmes': {}})
    for guide in epg.values():
        for row in guide:
            if not isinstance(row, dict):
                continue
            entry = selected.get(str(row.get('channelExtId', '')))
            if entry is None or not isinstance(row.get('programs'), list):
                continue
            for p in row['programs']:
                if not isinstance(p, dict):
                    continue
                pid, title = p.get('programExtId'), text(p.get('name'))
                if isinstance(pid, bool) or not isinstance(pid, (str, int)) or not str(pid) or len(str(pid)) > 256:
                    continue
                try:
                    if isinstance(p['startTimeUtc'], bool) or isinstance(p['endTimeUtc'], bool):
                        continue
                    start, end = float(p['startTimeUtc']), float(p['endTimeUtc'])
                    if not title or not math.isfinite(start) or not math.isfinite(end) or end <= start:
                        continue
                    datetime.fromtimestamp(start, timezone.utc)
                    datetime.fromtimestamp(end, timezone.utc)
                except (KeyError, ValueError, TypeError, OverflowError, OSError):
                    continue
                entry['programmes'][(str(pid), start, end)] = {
                    'id': str(pid), 'title': title, 'start': start, 'end': end}
    for entry in selected.values():
        entry['programmes'] = sorted(entry['programmes'].values(), key=lambda p: (p['start'], p['id']))
    return json.dumps({'schema': 1, 'channels': selected}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def normal(value):
    return ' '.join(unicodedata.normalize('NFKC', value).split()) if isinstance(value, str) else ''


def channel_id(metadata, name):
    channels = metadata.get('channels', {})
    for strip_hd in (False, True):
        def key(value):
            value = normal(value).casefold()
            return re.sub(r'\s+hd$', '', value) if strip_hd else value
        hits = [cid for cid, row in channels.items() if isinstance(row, dict) and key(row.get('name')) == key(name)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None
    return None


def now_next(index, cid, now):
    rows = index.get('channels', {}).get(cid, {}).get('programmes', [])
    current = [p for p in rows if p['start'] <= now < p['end']]
    if len(current) != 1:
        return None
    following = [p for p in rows if p['start'] >= current[0]['end']]
    return {'now': current[0], 'next': min(following, key=lambda p: p['start']) if following else None}
