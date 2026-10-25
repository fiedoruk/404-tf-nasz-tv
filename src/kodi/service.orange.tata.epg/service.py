"""Kodi-owned metadata refresher. Does not read EPG contents or account data."""
import json
import os
from pathlib import Path
import tempfile
import time
import xbmc
import xbmcaddon
import xbmcvfs
from epg_schedule import CHECK, attempted, plan, stale

EPG = "special://profile/addon_data/plugin.video.orange_go/tata/epg.xml"
EXPORT = "RunPlugin(plugin://plugin.video.orange_go/?mode=exportTataPvr)"


def log(message):
    xbmc.log("[service.orange.tata.epg] " + message, xbmc.LOGWARNING)


def mtime():
    return xbmcvfs.Stat(EPG).st_mtime() if xbmcvfs.exists(EPG) else None


def enabled():
    request = {"jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails",
               "params": {"addonid": "plugin.video.orange_go", "properties": ["enabled"]}}
    reply = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    return reply.get("result", {}).get("addon", {}).get("enabled") is True


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".attempt-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    monitor = xbmc.Monitor()
    path = Path(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))) / "attempt.json"
    if monitor.waitForAbort(30):
        return
    first_check = True
    while not monitor.abortRequested():
        next_check = time.monotonic() + CHECK
        try:
            now, before = time.time(), mtime()
            if first_check:
                status = "stale" if stale(now, before) else "fresh"
                xbmc.log("[service.orange.tata.epg] Service started; XMLTV " + status, xbmc.LOGINFO)
                first_check = False
            if stale(now, before):
                state = json.loads(path.read_text()) if path.exists() else {}
                ready, adjusted = plan(now, state)
                if not ready and adjusted != state:
                    save(path, adjusted)
                if ready and enabled():
                    save(path, attempted(now))  # Persist before invoking the export.
                    xbmc.executebuiltin(EXPORT)
                    if monitor.waitForAbort(120):
                        return
                    after = mtime()
                    if after == before or stale(time.time(), after):
                        log("Export did not produce a changed, fresh XMLTV timestamp within 120s")
        except Exception as exc:
            log("Refresh check failed: " + type(exc).__name__)
        if monitor.waitForAbort(max(0, next_check - time.monotonic())):
            return


if __name__ == "__main__":
    main()
