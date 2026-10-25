"""Optional AZR integration, invoked from this add-on's setup menu.

Copyright (c) 2026 Tomasz Fiedoruk. MIT.
Installs the separately licensed AZR integration after explicit consent.
Does not modify the Kodi database. The editor itself performs database writes.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read(path):
    if path.is_symlink() or path.parent.is_symlink():
        raise RuntimeError('Symlink refused')
    if not path.exists(): return None
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise RuntimeError('Unexpected file')
    return path.read_bytes()


def write(path, data):
    fd, name = tempfile.mkstemp(prefix='.nasztv-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def apply(skin, keymaps, state_dir, payload, rollback=False):
    for directory in (skin, skin/'1080i', keymaps, state_dir):
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError('Expected existing real directory')
    manifest = ET.fromstring(read(skin/'addon.xml'))
    if (manifest.get('id'), manifest.get('version')) != ('skin.arctic.zephyr.mod','3.0.3'):
        raise RuntimeError('AZR 3.0.3 required')
    targets = {'group': skin/'1080i/DialogPVRGroupManager.xml',
               'osd': skin/'1080i/DialogPVRChannelsOSD.xml',
               'keymap': keymaps/'zzz-nasztv-favourites.xml'}
    baseline = {'group':'2d33895f3089f849422e4fa864314f54164c6c283d5622638d15725e526ef8e8',
                'osd':'8e5f795919e065a6a00079ef511ef68f0a7cad2a92193a7bccdd70389d5b93ad',
                'keymap':None}
    lock = state_dir/'operation.lock'
    fd = os.open(lock, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    os.close(fd)
    try:
        state_path = state_dir/'installation.json'
        raw = read(state_path)
        current = {name: read(path) for name,path in targets.items()}
        if raw is None:
            if rollback: raise RuntimeError('No installation record')
            if {n:digest(v) for n,v in current.items()} != baseline:
                raise RuntimeError('Unknown AZR baseline; no changes made')
            desired = {'group':read(payload/'1080i/DialogPVRGroupManager.xml'),
                       'osd':read(payload/'1080i/DialogPVRChannelsOSD.xml'),
                       'keymap':read(payload/'zzz-nasztv-favourites.xml')}
            for data in desired.values(): ET.fromstring(data)
            for n,data in current.items():
                if data is not None: write(state_dir/(n+'.before'),data)
            state = {'schema':1, 'skin':str(skin), 'keymaps':str(keymaps),
                     'before':baseline,'after':{n:digest(v) for n,v in desired.items()}}
            for n,data in desired.items(): write(state_dir/(n+'.after'),data)
            write(state_path,(json.dumps(state,sort_keys=True)+'\n').encode())
        else:
            state = json.loads(raw)
            if (state.get('schema') != 1 or state.get('skin') != str(skin)
                    or state.get('keymaps') != str(keymaps) or state.get('before') != baseline):
                raise RuntimeError('Installation identity mismatch')
        suffix = 'before' if rollback else 'after'
        desired = {}
        for n in targets:
            if digest(current[n]) not in (state['before'][n],state['after'][n]):
                raise RuntimeError('Later user changes found; restore manually')
            desired[n] = read(state_dir/(n+'.'+suffix)) if state[suffix][n] is not None else None
            if digest(desired[n]) != state[suffix][n]: raise RuntimeError('Backup mismatch')
        for n,path in targets.items():
            if read(path) != current[n]: raise RuntimeError('Concurrent change')
            if desired[n] is None:
                if path.exists(): path.unlink()
            else: write(path,desired[n])
            if read(path) != desired[n]: raise RuntimeError('Write mismatch')
    finally: lock.unlink()


def main(rollback=False):
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcvfs
    home = xbmcgui.Window(10000)
    if any(home.getProperty('nasztv.favourites.'+n) for n in ['lock','mode','origin','owner']):
        raise RuntimeError('Close the editor first')
    if not xbmcgui.Dialog().yesno('Ulubione — eksperyment',
        'Cofnąć integrację?' if rollback else
        'Edytor zapisuje bazę Kodi. Zachowaj kopię profilu. Przygotować integrację AZR i prywatny katalog kopii?'):
        return
    addon = xbmcaddon.Addon('script.nasztv.favourites')
    addon_path = Path(xbmcvfs.translatePath(addon.getAddonInfo('path')))
    sys.path.insert(0,str(addon_path))
    from portable_profile import process_package
    uid = os.getuid()
    package, _ = process_package(Path('/proc/self/cmdline').read_bytes()[:257], uid)
    private = Path('/data/user')/str(uid//100000)/package/'files'
    if not private.is_dir() or private.is_symlink() or private.stat().st_uid != uid:
        raise RuntimeError('Unknown private application directory')
    for name in ['nasztv-favourites-backups','nasztv-favourites-integration']:
        folder = private/name
        folder.mkdir(mode=0o700,exist_ok=True)
        if folder.is_symlink() or folder.stat().st_uid != uid or folder.stat().st_mode & 0o777 != 0o700:
            raise RuntimeError('Private directory must be owned and mode 0700')
    skin = Path(xbmcvfs.translatePath('special://home/addons/skin.arctic.zephyr.mod'))
    keymaps = Path(xbmcvfs.translatePath('special://profile/keymaps'))
    apply(skin,keymaps,private/'nasztv-favourites-integration',
          Path(__file__).resolve().parent/'resources/azr',rollback)
    xbmc.executebuiltin('Action(reloadkeymaps)')
    xbmc.executebuiltin('ReloadSkin()')
    xbmcgui.Dialog().ok('Ulubione','Integracja cofnięta. Dane listy zachowano.' if rollback
        else 'Gotowe. Utwórz lokalną grupę Moje ulubione przed uruchomieniem edytora.')


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        import xbmcgui
        xbmcgui.Dialog().ok('Ulubione — zatrzymano',str(exc))
