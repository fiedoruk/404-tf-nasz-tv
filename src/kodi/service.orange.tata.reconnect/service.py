"""Kodi service entry point. Callbacks carry no media URLs or account data."""
import queue
import time
import os
import xbmc
import xbmcgui
from reconnect_adapter import Controller, KodiPort
from manifest_observer import FreshTail, ManifestWatch


class PlaybackReady:
    """Metadata scheduling signal only. Never controls playback or the reconnect queue."""
    KEY = 'nasztv.playback.ready_channel'

    def __init__(self, home, api):
        self.home, self.api = home, api
        self.clear()  # No bootstrap inference from an already playing item.

    def clear(self):
        try:
            self.home.clearProperty(self.KEY)
        except Exception:
            pass

    def av_started(self):
        try:
            if not (self.api.getCondVisibility('PVR.IsPlayingTV')
                    and self.api.getCondVisibility('Player.HasVideo')):
                self.clear()
                return
            name = self.api.getInfoLabel('VideoPlayer.ChannelName')
            if not name.strip() or name != self.api.getInfoLabel('VideoPlayer.ChannelName'):
                self.clear()
                return
            self.home.setProperty(self.KEY, name)
        except Exception:
            self.clear()


class Player(xbmc.Player):
    def __init__(self, events):
        super().__init__()
        self.events = events
        try:
            self.ready = PlaybackReady(xbmcgui.Window(10000), xbmc)
        except Exception:
            self.ready = None

    def emit(self, event):
        self.events.put((event, time.monotonic()))

    def onPlayBackStarted(self):
        self.emit("started")
        if self.ready:
            self.ready.clear()

    def onAVStarted(self):
        self.emit("av_started")
        if self.ready:
            self.ready.av_started()

    def onPlayBackStopped(self):
        self.emit("stopped")
        if self.ready:
            self.ready.clear()

    def onPlayBackPaused(self):
        self.emit("paused")

    def onPlayBackEnded(self):
        self.emit("ended")
        if self.ready:
            self.ready.clear()

    def onPlayBackResumed(self):
        self.emit("resumed")

    def onPlayBackError(self):
        self.emit("error")
        if self.ready:
            self.ready.clear()


if __name__ == "__main__":
    import xbmcvfs
    events = queue.Queue()
    player = Player(events)
    path = os.path.join(xbmcvfs.translatePath('special://logpath/'), 'kodi.log')
    watch = ManifestWatch(FreshTail(path))
    Controller(KodiPort(xbmc, xbmcgui, player), xbmc.Monitor(), events, manifest=watch).run()
