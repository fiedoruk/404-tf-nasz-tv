# OrangeGo derivative; modified by Tomasz Fiedoruk on 2026-10-25. GPL-2.0; upstream author lg. See NOTICE.txt.
"""Fixed Nasz TV bridge in Orange's reusable invocation; no Kodi I/O on import."""
import importlib.util
import os
import sys

GUI_ID = 'script.nasztv.gui'
GUI_VERSION = '0.1.9'
ACTIONS = ('cycle', 'help', 'back', 'details')


def _dispatch(gui, vfs):
    name = '_nasztv_dispatch_' + GUI_VERSION.replace('.', '_')
    if name not in sys.modules:
        path = os.path.join(vfs.translatePath(gui.getAddonInfo('path')), 'dispatch.py')
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not callable(module.serial_handle):
            raise ValueError('invalid_dispatcher')
        sys.modules[name] = module
    return sys.modules[name]


def _details_ready(home, api):
    if (home.getProperty('nasztv.hud.mode') != '2'
            or home.getProperty('nasztv.hud.help') == '1'
            or home.getProperty('nasztv.details.busy') == '1'
            or not api.getCondVisibility('PVR.IsPlayingTV')
            or not api.getCondVisibility('VideoPlayer.HasEpg')
            or not api.getCondVisibility('Window.IsActive(fullscreenvideo)')
            or api.getCondVisibility('Player.Caching')):
        return False
    current = tuple(api.getInfoLabel('VideoPlayer.' + key)
                    for key in ('ChannelName', 'StartTime', 'NextStartTime'))
    if not current[0] or home.getProperty('nasztv.playback.ready_channel') != current[0]:
        return False
    requested = tuple(home.getProperty('nasztv.details.request_' + key)
                      for key in ('channel_name', 'now_start', 'next_start'))
    return (current != requested
            and (not api.getInfoLabel('VideoPlayer.Plot')
                 or not api.getInfoLabel('VideoPlayer.NextPlot')))


def run(action, home, api, addons, vfs, notify):
    """No login, arbitrary paths or commands. GUI remains the only input logic."""
    if action not in ACTIONS:
        return 'invalid_action'
    try:
        gui = addons.Addon(GUI_ID)
        if gui.getAddonInfo('version') != GUI_VERSION:
            raise ValueError('gui_version')
    except Exception:
        if action != 'details':
            notify('Nakładka Nasz TV wymaga zgodnej aktualizacji.')
        return 'gui_unavailable'
    try:
        if action == 'details':
            if not _details_ready(home, api):
                return 'inactive'
            from .tata_details import load_for_current
            return load_for_current(home, api)  # Its own nonblocking lock, not dispatch.lock.
        profile = vfs.translatePath(gui.getAddonInfo('profile'))
        _dispatch(gui, vfs).serial_handle(action, home, api, profile)
        return 'handled'
    except Exception as exc:
        api.log('[NaszTV adapter] unavailable: ' + type(exc).__name__, api.LOGWARNING)
        return 'error'
