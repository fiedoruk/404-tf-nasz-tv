# OrangeGo derivative; modified by Tomasz Fiedoruk on 2026-10-25. GPL-2.0; upstream author lg. See NOTICE.txt.
"""Local M3U/XMLTV export. No Kodi, HTTP, credentials or DRM implementation."""

from datetime import datetime, timezone
import os
import tempfile
from urllib.parse import quote, urlencode
from xml.etree import ElementTree as ET

# Stable first eight numbers and resolver URLs preserve existing PVR favourites.
CHANNEL_IDS = ('14135', '14999', '14171', '14137', '14190', '14014', '14233', '15049')
# Owner's news selection supplements the provider category; it grants no access.
EXTRA_NEWS_IDS = ('14429',)  # Zero, confirmed in the entitled catalogue 2026-10-24.


class ExportError(ValueError):
    pass


def text(value, limit=2048):
    if not isinstance(value, str):
        return ''
    # XML 1.0 control characters and M3U line breaks must not become markup.
    return ''.join(c if ord(c) >= 32 and not 0xD800 <= ord(c) <= 0xDFFF
                   and ord(c) not in (0xFFFE, 0xFFFF) else ' ' for c in value).strip()[:limit]


def render(channels, epg, logo_base):
    """Export the entitled live catalogue, with favourites first and native news grouping."""
    if not isinstance(channels, list) or not isinstance(epg, dict) or not epg:
        raise ExportError('invalid_snapshot')
    selected = {}
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        cid = str(channel.get('channelExtId', ''))
        if not cid.isascii() or not cid.isdecimal() or channel.get('isSubscribed') is not True:
            continue
        features = channel.get('playFeatures', {})
        otg = features.get('otg', {}) if isinstance(features, dict) else {}
        if not isinstance(otg, dict) or otg.get('isChannelAllowed') is not True:
            continue
        name, signature = text(channel.get('name')), text(channel.get('logoSignature'), 1024)
        if not name or not signature:
            raise ExportError('invalid_channel_metadata')
        groups = []
        if cid in CHANNEL_IDS:
            groups.append('Ulubione taty')
        if channel.get('category') == 'Informacje' or cid in EXTRA_NEWS_IDS:
            groups.append('Informacyjne')
        # No artificial category for the rest: Kodi's native All includes every row.
        selected.setdefault(cid, (name, logo_base + quote(signature, safe=''), ';'.join(groups)))
    if not selected:
        raise ExportError('empty_channels')

    programmes = {cid: {} for cid in selected}
    for guide in epg.values():
        if not isinstance(guide, list):
            raise ExportError('invalid_epg_snapshot')
        for row in guide:
            if not isinstance(row, dict):
                continue
            cid = str(row.get('channelExtId', ''))
            if cid not in selected:
                continue
            if not isinstance(row.get('programs'), list):
                continue
            for programme in row['programs']:
                if not isinstance(programme, dict):
                    continue
                try:
                    start_value, stop_value = programme['startTimeUtc'], programme['endTimeUtc']
                    if isinstance(start_value, bool) or isinstance(stop_value, bool):
                        continue
                    start = datetime.fromtimestamp(float(start_value), timezone.utc)
                    stop = datetime.fromtimestamp(float(stop_value), timezone.utc)
                    title = text(programme.get('name'))
                    if not title or stop <= start:
                        continue
                except (KeyError, TypeError, ValueError, OverflowError, OSError):
                    continue
                key = (start, stop, title)
                programmes[cid][key] = text(programme.get('description'), 16384)
    if not any(programmes.values()):
        raise ExportError('empty_epg')

    m3u = ['#EXTM3U']
    tv = ET.Element('tv', {'generator-info-name': 'Orange Go Tata local'})
    order = [cid for cid in CHANNEL_IDS if cid in selected]
    order.extend(cid for cid in selected if cid not in CHANNEL_IDS)
    extra_number = len(CHANNEL_IDS)
    for cid in order:
        if cid in CHANNEL_IDS:
            number = CHANNEL_IDS.index(cid) + 1
        else:
            extra_number += 1
            number = extra_number
        name, logo, groups = selected[cid]
        m3u.append('#EXTINF:-1 tvg-id="%s" tvg-chno="%s" tvg-logo="%s" group-title="%s",%s'
                   % (cid, number, logo, groups, name))
        m3u.append('plugin://plugin.video.orange_go/?' + urlencode({'mode': 'playSource', 'cid': cid, 'tata_pvr': '1'}))
        channel = ET.SubElement(tv, 'channel', {'id': cid})
        ET.SubElement(channel, 'display-name', {'lang': 'pl'}).text = name
        ET.SubElement(channel, 'icon', {'src': logo})
    for cid in order:
        for (start, stop, title), description in sorted(programmes.get(cid, {}).items()):
            programme = ET.SubElement(tv, 'programme', {
                'channel': cid, 'start': start.strftime('%Y%m%d%H%M%S +0000'),
                'stop': stop.strftime('%Y%m%d%H%M%S +0000')})
            ET.SubElement(programme, 'title', {'lang': 'pl'}).text = title
            if description:
                ET.SubElement(programme, 'desc', {'lang': 'pl'}).text = description
    return ('\n'.join(m3u) + '\n').encode('utf-8'), ET.tostring(tv, encoding='utf-8', xml_declaration=True)


def _stage(directory, data):
    fd, path = tempfile.mkstemp(prefix='.tata-pvr-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        return path
    except Exception:
        os.unlink(path)
        raise


def publish(directory, m3u, xml, index=None):
    """Stage complete files, atomically replace each; roll back ordinary write failures."""
    files = {'epg.xml': xml, 'channels.m3u': m3u}
    if index is not None:
        files['programme-index.json'] = index
    staged, previous, replaced = {}, {}, []
    os.makedirs(directory, exist_ok=True)
    try:
        for name, data in files.items():
            path = os.path.join(directory, name)
            try:
                with open(path, 'rb') as handle:
                    previous[name] = handle.read()
            except FileNotFoundError:
                previous[name] = None
            staged[name] = _stage(directory, data)
        for name in files:
            os.replace(staged[name], os.path.join(directory, name))
            replaced.append(name)
    except OSError:
        rollback_failed = False
        for name in reversed(replaced):
            path = os.path.join(directory, name)
            restore = None
            try:
                if previous[name] is None:
                    os.unlink(path)
                else:
                    restore = _stage(directory, previous[name])
                    os.replace(restore, path)
            except OSError:
                rollback_failed = True
            finally:
                if restore and os.path.exists(restore):
                    os.unlink(restore)
        raise ExportError('publish_rollback_failed' if rollback_failed else 'publish_failed') from None
    finally:
        for path in staged.values():
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
