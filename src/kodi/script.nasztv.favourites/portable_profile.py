"""Narrow Kodi21/schema46 profile, discovered identity and Android own-path checks."""
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from typing import NamedTuple
import unicodedata
from urllib.parse import quote

from prune_memberships import Refused, validate_identity, validate_schema, name_key, read_group_identity

POLICY_FILE = Path(__file__).with_name('profile.json')
BACKUP_NAME = 'nasztv-favourites-backups'


class Policy(NamedTuple):
    name: str
    path: str
    kodi_major: int
    database_schema: int


class Profile(NamedTuple):
    identity: tuple
    group_path: str
    database: Path
    backup_dir: Path
    package: str
    uid: int

    @property
    def group_id(self): return self.identity[0]

    @property
    def group_name(self): return self.identity[3]


def validate_policy(value):
    if (not isinstance(value, dict) or set(value) != {'group_name','group_path','kodi_major','database_schema'}
            or type(value['kodi_major']) is not int or value['kodi_major'] != 21
            or type(value['database_schema']) is not int or value['database_schema'] != 46):
        raise Refused('profile_contract')
    name = value['group_name']
    if (not isinstance(name, str) or not 0 < len(name) <= 64 or name != name.strip()
            or unicodedata.normalize('NFC', name) != name
            or any(ord(c) < 32 or ord(c) == 127 or c in '/\\@%?#|' for c in name)):
        raise Refused('profile_name')
    path = 'pvr://channels/tv/' + quote(name, safe='') + '@-1/'
    if value['group_path'] != path:
        raise Refused('profile_path')
    return Policy(name, path, 21, 46)


def load_policy():
    if POLICY_FILE.is_symlink(): raise Refused('profile_symlink')
    raw = POLICY_FILE.read_bytes()
    if len(raw) > 2048: raise Refused('profile_size')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise Refused('profile_duplicate_key')
            result[key] = value
        return result
    return validate_policy(json.loads(raw, object_pairs_hook=unique))


def discover_group(conn, rows, policy):
    """A public RPC id is evidence to cross-check, never permission to mutate."""
    validate_schema(conn)
    if not isinstance(rows, list) or len(rows) > 1000:
        raise Refused('rpc_groups_unknown')
    rpc_matches = [r for r in rows if isinstance(r, dict) and isinstance(r.get('label'), str)
                   and name_key(r['label']) == name_key(policy.name)]
    if (len(rpc_matches) != 1 or rpc_matches[0]['label'] != policy.name
            or type(rpc_matches[0].get('channelgroupid')) is not int):
        raise Refused('rpc_group_missing_alias_or_ambiguous')
    expected = validate_identity((rpc_matches[0]['channelgroupid'], 0, 2, policy.name, -1))
    if read_group_identity(conn, expected[0], policy.name) != (expected,):
        raise Refused('db_group_identity_or_alias')
    return expected


def process_package(raw, uid):
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= 256 or b'\0' not in raw
            or type(uid) is not int or not 10000 <= uid <= 2147483647
            or not 10000 <= uid % 100000 <= 19999):
        raise Refused('process_identity_unknown')
    package, rest = raw.split(b'\0', 1)
    if rest.strip(b'\0') or not re.fullmatch(rb'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){1,8}', package):
        raise Refused('process_package_unknown')
    return package.decode('ascii'), uid // 100000


def owned(path, uid, directory, mode=None):
    info = path.lstat()
    predicate = stat.S_ISDIR if directory else stat.S_ISREG
    if not predicate(info.st_mode) or info.st_uid != uid or (mode is not None and stat.S_IMODE(info.st_mode) != mode):
        raise Refused('owned_path_unknown')


def storage_paths(database_value, package, uid, schema):
    """Only derived Android aliases; never accept a configured arbitrary backup path."""
    user = uid // 100000
    app = Path('/data/user') / str(user) / package
    files = app / 'files'
    owned(app, uid, True); owned(files, uid, True)
    canonical = files.resolve(strict=True)
    allowed = {files}
    if user == 0: allowed.add(Path('/data/data') / package / 'files')
    if canonical not in allowed: raise Refused('private_base_alias')
    backup = files / BACKUP_NAME
    owned(backup, uid, True, 0o700)
    if backup.resolve(strict=True) != canonical / BACKUP_NAME:
        raise Refused('backup_alias')
    if not isinstance(database_value, str): raise Refused('database_path')
    database = Path(database_value)
    if (not database.is_absolute()
            or str(database) != database_value or '..' in database.parts
            or database.name != 'TV%d.db' % schema):
        raise Refused('database_path')
    external = Path('/storage/emulated') / str(user) / 'Android/data' / package / 'files'
    bases = {files: canonical, canonical: canonical, external: external,
             Path('/sdcard/Android/data') / package / 'files': external,
             Path('/storage/self/primary/Android/data') / package / 'files': external}
    expected = None
    for alias, resolved in bases.items():
        try: relative = database.relative_to(alias)
        except ValueError: continue
        parts = relative.parts
        if (parts == ('.kodi','userdata','Database','TV%d.db' % schema)
                or (len(parts) == 6 and parts[:3] == ('.kodi','userdata','profiles')
                    and parts[-2:] == ('Database','TV%d.db' % schema))):
            expected = resolved / relative
            break
    if expected is None or database.resolve(strict=True) != expected:
        raise Refused('database_alias_or_outside_app')
    owned(database, uid, False)
    if database.parent.is_symlink(): raise Refused('database_parent_symlink')
    return expected, canonical / BACKUP_NAME


def rpc(api, method, params):
    raw = api.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}))
    if not isinstance(raw, str) or len(raw) > 65536: raise Refused('rpc_unknown')
    result = json.loads(raw)
    if not isinstance(result, dict) or 'error' in result or 'result' not in result:
        raise Refused('rpc_unknown')
    return result['result']


def resolve_runtime_profile(api, groups=None):
    import xbmcvfs
    policy = load_policy()
    version = rpc(api, 'Application.GetProperties', {'properties':['version']})['version']
    if type(version.get('major')) is not int or version['major'] != policy.kodi_major:
        raise Refused('kodi_version')
    if api.getCondVisibility('System.Platform.Android') is not True:
        raise Refused('android_required')
    uid = os.getuid()
    with open('/proc/self/cmdline', 'rb') as handle: raw = handle.read(257)
    package, _ = process_package(raw, uid)
    database, backup = storage_paths(xbmcvfs.translatePath('special://database/TV%d.db' % policy.database_schema),
                                      package, uid, policy.database_schema)
    if groups is None:
        data = rpc(api, 'PVR.GetChannelGroups', {'channeltype':'tv'})
        groups = data.get('channelgroups')
        if not isinstance(groups, list) or data.get('limits') != {'start':0,'end':len(groups),'total':len(groups)}:
            raise Refused('rpc_groups_incomplete')
    conn = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=0.25)
    try:
        if conn.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise Refused('journal_mode_changed')
        identity = discover_group(conn, groups, policy)
    finally: conn.close()
    return Profile(identity, policy.path, database, backup, package, uid)
