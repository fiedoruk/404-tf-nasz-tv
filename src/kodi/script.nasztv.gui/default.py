"""RunScript(script.nasztv.gui,install|rollback|cycle|help|back|up|down|reset)."""
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from dispatch import serial_handle, reset


def main():
    command = sys.argv[1] if len(sys.argv) == 2 else "install" if len(sys.argv) == 1 else "invalid"
    home = xbmcgui.Window(10000)
    addon = xbmcaddon.Addon("script.nasztv.gui")
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if command == "details":
        import importlib
        import types
        from pathlib import Path
        # Separate invocation: no network under the input dispatcher lock.
        try:
            orange = xbmcaddon.Addon('plugin.video.orange_go')
            if orange.getAddonInfo('version') not in ('1.0.12', '1.0.13', '1.0.14', '1.0.15'):
                raise RuntimeError('Description module version is not qualified')
            library = Path(xbmcvfs.translatePath(orange.getAddonInfo('path'))) / 'resources/lib'
            package = types.ModuleType('_nasztv_orange_lib')
            package.__path__ = [str(library)]
            sys.modules[package.__name__] = package
            module = importlib.import_module(package.__name__ + '.tata_details')
            module.load_for_current(home, xbmc)
        except Exception as exc:
            # Consume this trigger without exposing account data or creating a retry loop.
            for key, label in [('channel_name', 'ChannelName'), ('now_start', 'StartTime'),
                               ('next_start', 'NextStartTime')]:
                home.setProperty('nasztv.details.request_' + key, xbmc.getInfoLabel('VideoPlayer.' + label))
            home.setProperty('nasztv.details.status', 'error')
            xbmc.log('[script.nasztv.gui] details unavailable: ' + type(exc).__name__, xbmc.LOGWARNING)
        return
    if command not in ("install", "rollback"):
        try:
            serial_handle(command, home, xbmc, profile)
        except (ValueError, OSError, ImportError) as exc:
            xbmc.log("[script.nasztv.gui] " + str(exc), xbmc.LOGERROR)
        return
    import json
    from pathlib import Path
    from install import InstallError, run
    profile = Path(profile)
    try:
        skin = Path(xbmcvfs.translatePath("special://skin/"))
        if command == "rollback":
            # Rollback must also work after the owner switches to Estuary.
            state = json.loads((profile / "state.json").read_text())
            skin = Path(state["skin_path"])
        report = run(command, Path(xbmcvfs.translatePath("special://profile/keymaps/")),
                     skin, profile,
                     Path(xbmcvfs.translatePath(addon.getAddonInfo("path"))))
        reset(home)
        home.clearProperty("osdinfo")
        home.clearProperty("osdshowinfo")
        xbmc.executebuiltin("Action(reloadkeymaps)")
        xbmc.executebuiltin("ReloadSkin()")
        xbmc.log("[script.nasztv.gui] " + command + ": " + report["status"], xbmc.LOGINFO)
    except (InstallError, OSError, ValueError, KeyError) as exc:
        xbmc.log("[script.nasztv.gui] " + str(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Nasz TV", "Nie zmieniono nieznanej konfiguracji. Sprawdź dziennik.",
                                      xbmcgui.NOTIFICATION_ERROR)


if __name__ == "__main__":
    main()
