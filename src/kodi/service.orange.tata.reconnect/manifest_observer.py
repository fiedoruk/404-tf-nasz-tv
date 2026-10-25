"""HOST candidate: bounded private log filtering, no Kodi/player/network actions.

Only counters, timestamps and health escape the reader. URL digests are kept
inside the owning process; do not serialize them or raw exceptions.
"""
import datetime
import hashlib
import math
import os
import re
import time
from urllib.parse import urlsplit

MAX_URL = 4096
MAX_LINE = 8192
MAX_READ = 16384
FRESH_SECONDS = 15
HEADER = re.compile(
    rb"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
    rb"T:\d+\s+error <general>: AddOnLog: inputstream\.adaptive: "
    rb"Download failed, HTTP error 419: (https://[^\s]+)$")


def manifest_digest(value):
    """Strict identity: preserve the complete URL, including query and ticket."""
    if not isinstance(value, str) or not 0 < len(value) <= MAX_URL:
        return None
    try:
        raw = value.encode('ascii')
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.fragment or '|' in value
                or any(c <= 32 or c == 127 for c in raw)
                or not parsed.path.endswith('.mpd')):
            return None
        return hashlib.sha256(raw).digest()
    except (ValueError, UnicodeError):
        return None


def manifest_binding(value):
    """Three RAM-only digests: full URL, raw path+whole raw query, authority."""
    full = manifest_digest(value)
    if full is None:
        return None
    parsed = urlsplit(value)
    resource = b'https\0' + parsed.path.encode('ascii') + b'\0' + parsed.query.encode('ascii')
    return (full, hashlib.sha256(resource).digest(),
            hashlib.sha256(parsed.netloc.encode('ascii')).digest())


def valid_binding(binding, expected):
    return (type(binding) is tuple and len(binding) == 3
            and all(type(part) is bytes and len(part) == 32 for part in binding)
            and binding[0] == expected)


def match_error(line, expected, floor, wall_now):
    """Return only event time; never return a line, URL or digest."""
    if not isinstance(expected, bytes) or len(expected) != 32 or len(line) > MAX_LINE:
        return None
    match = HEADER.fullmatch(line.rstrip(b'\r'))
    if not match:
        return None
    try:
        occurred = datetime.datetime.strptime(
            match[1].decode('ascii'), '%Y-%m-%d %H:%M:%S.%f').timestamp()
        if occurred < floor or not 0 <= wall_now - occurred <= FRESH_SECONDS:
            return None
        actual = manifest_digest(match[2].decode('ascii'))
        return occurred if actual is not None and actual == expected else None
    except (ValueError, UnicodeError, OverflowError, OSError):
        return None


def match_bound_error(line, expected, binding, floor, wall_now):
    """A full request digest identifies one candidate inside the current source."""
    if not valid_binding(binding, expected) or len(line) > MAX_LINE:
        return None
    match = HEADER.fullmatch(line.rstrip(b'\r'))
    if not match:
        return None
    try:
        request = manifest_binding(match[2].decode('ascii'))
    except (ValueError, UnicodeError):
        return None
    if request is None:
        return None
    same_full = request[0] == expected
    authority_alias = request[1] == binding[1] and request[2] != binding[2]
    if not (same_full or authority_alias):
        return None
    occurred = match_error(line, request[0], floor, wall_now)
    return (occurred, request[0]) if occurred is not None else None


class FreshTail:
    """Read only appended records, with a 64-byte RAM hash checking the boundary.

    Every rebase discards the first new completed line, even if complete. This
    deliberately avoids interpreting a line that started before the EOF mark.
    Historical boundary bytes are hashed only, never parsed as events.
    """
    def __init__(self, path):
        self.path = path
        self.file_id = None
        self.offset = 0
        self.anchor = None
        self.pending = b''
        self.skip = True
        self.generation = 0

    @staticmethod
    def _id(stat):
        return stat.st_dev, stat.st_ino

    @staticmethod
    def _anchor(handle, offset):
        count = min(64, offset)
        handle.seek(offset - count)
        data = handle.read(count)
        return hashlib.sha256(data).digest() if len(data) == count else None

    def _reset(self, handle, stat):
        self.generation += 1
        self.file_id = self._id(stat)
        self.offset = stat.st_size
        self.anchor = self._anchor(handle, self.offset)
        self.pending = b''
        self.skip = True

    def poll(self, expected, floor, wall_now, binding=None):
        """Times for strict callers, (time, request digest) for bound callers."""
        try:
            with open(self.path, 'rb') as handle:
                stat = os.fstat(handle.fileno())
                if (self.file_id != self._id(stat) or stat.st_size < self.offset
                        or stat.st_size - self.offset > MAX_READ
                        or self.anchor != self._anchor(handle, self.offset)):
                    self._reset(handle, stat)
                    return False, self.generation, ()
                handle.seek(self.offset)
                data = handle.read(min(MAX_READ, stat.st_size - self.offset))
                if len(data) != stat.st_size - self.offset:
                    self._reset(handle, os.fstat(handle.fileno()))
                    return False, self.generation, ()
                self.offset += len(data)
                self.anchor = self._anchor(handle, self.offset)
                after = os.fstat(handle.fileno())
                if self._id(os.stat(self.path)) != self.file_id or after.st_size < self.offset:
                    self.file_id = None
                    self.pending = b''
                    self.generation += 1
                    return False, self.generation, ()
                rows = (self.pending + data).split(b'\n')
                self.pending = rows.pop()
                if len(self.pending) > MAX_LINE or any(len(row) > MAX_LINE for row in rows):
                    self._reset(handle, after)
                    return False, self.generation, ()
                times = []
                uncertain = False
                for row in rows:
                    if self.skip:
                        self.skip = False
                        continue
                    occurred = (match_error(row, expected, floor, wall_now) if binding is None
                                else match_bound_error(row, expected, binding, floor, wall_now))
                    if occurred is not None:
                        times.append(occurred)
                    elif HEADER.fullmatch(row.rstrip(b'\r')):
                        # A foreign/stale/unclassifiable 419 is never quiet-time proof.
                        uncertain = True
                return not uncertain, self.generation, () if uncertain else tuple(times)
        except (OSError, ValueError):
            self.file_id = None
            self.anchor = None
            self.pending = b''
            self.generation += 1
            return False, self.generation, ()


class ErrorWindow:
    """Evidence only, no retry budget or permission to control a player."""
    def __init__(self):
        self.context = None
        self.seen = []

    def reset(self):
        self.context, self.seen = None, []

    def observe(self, *, healthy, generation, source, times, wall_now, eligible, target=None):
        context = (generation, source, target)
        if (healthy is not True or eligible is not True
                or not isinstance(source, bytes) or len(source) != 32):
            self.reset()
            return False
        if context != self.context:
            self.context, self.seen = context, []
        self.seen = [t for t in self.seen if 0 <= wall_now - t <= FRESH_SECONDS]
        for occurred in times:
            if 0 <= wall_now - occurred <= FRESH_SECONDS and occurred not in self.seen:
                self.seen.append(occurred)
        self.seen = self.seen[-2:]
        return len(self.seen) >= 2


class ManifestWatch:
    """One 419 attempt, then 10min cooldown and 2min software progress.

    Time progression is the native player's media clock, not decoded frames or
    physical TV proof. Unknown/stalled time, reader gaps and callbacks erase
    stability. Own AVStarted never clears this budget. The existing network
    outage policy has its separate budget and is not governed by this cooldown.
    """
    COOLDOWN = 600
    STABLE = 120
    MAX_GAP = 6

    def __init__(self, reader, wall_clock=time.time):
        self.reader, self.wall_clock = reader, wall_clock
        self.floor = wall_clock()
        self.errors = ErrorWindow()
        self.spent = False
        self.cooldown_until = 0
        self.stable_since = None
        self.last_sample = None
        self.context = None

    def on_event(self):
        self.floor = self.wall_clock()
        self.reader.file_id = None  # Next poll rebases at EOF, never replays history.
        self.reader.pending = b''
        self.errors.reset()
        self.stable_since = self.last_sample = self.context = None

    def observe(self, now, current, source, media_time, binding=None):
        wall_now = self.wall_clock()
        eligible = (current.get('network') is True and current.get('fullscreen') is True
                    and current.get('identity') is not None
                    and type(source) is bytes and len(source) == 32
                    and (binding is None or valid_binding(binding, source)))
        media_context = (current.get('identity'), current.get('player_id'), source)
        if self.context is not None and media_context != self.context[:3]:
            # A missed callback must not let bytes from the previous context count.
            self.floor = wall_now
            self.reader.file_id = None
            self.reader.pending = b''
        if binding is None:
            healthy, generation, times = self.reader.poll(source, self.floor, wall_now)
        else:
            healthy, generation, times = self.reader.poll(source, self.floor, wall_now, binding=binding)
        context = media_context + (generation,)
        if context != self.context:
            self.errors.reset()
            self.stable_since = self.last_sample = None
            self.context = context
        if binding is None:
            ready = self.errors.observe(healthy=healthy, generation=generation, source=source,
                                        times=times, wall_now=wall_now, eligible=eligible)
        else:
            # Target changes reset only the pair, never the 419 attempt budget.
            target = self.errors.context[2] if self.errors.context is not None else None
            ready = False
            for record in times or ((None, target),):
                occurred, target = record
                ready = self.errors.observe(
                    healthy=healthy, generation=generation, source=source,
                    times=() if occurred is None else (occurred,), target=target,
                    wall_now=wall_now, eligible=eligible)
        if not eligible or healthy is not True:
            self.stable_since = self.last_sample = None
            return False
        if ready and not self.spent:
            self.spent = True  # Spend before any SDK call, including a failed guard.
            self.cooldown_until = now + self.COOLDOWN
            self.errors.reset()
            self.stable_since = self.last_sample = None
            return True
        if times or type(media_time) not in (int, float) or not math.isfinite(media_time):
            self.stable_since = self.last_sample = None
            return False
        if self.last_sample is None:
            self.stable_since = now
        else:
            previous, position = self.last_sample
            elapsed = now - previous
            advance = media_time - position
            if not (0 < elapsed <= self.MAX_GAP and 0.5 * elapsed <= advance <= 2 * elapsed):
                self.stable_since = now
        self.last_sample = (now, media_time)
        if (self.spent and now >= self.cooldown_until and self.stable_since is not None
                and now - self.stable_since >= self.STABLE):
            self.spent = False
            self.errors.reset()
        return False
