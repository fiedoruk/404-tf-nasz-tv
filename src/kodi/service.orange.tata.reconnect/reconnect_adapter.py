"""Kodi adapter: existing network recovery plus exact manifest-error evidence."""

import ipaddress
import json
import queue
import time

from reconnect_state import CHANNEL_IDS, ReconnectState, StopGate, eligible_item
from manifest_observer import manifest_binding


def local_network(xbmc):
    try:
        address = ipaddress.ip_address(xbmc.getIPAddress())
        return not (address.is_unspecified or address.is_loopback)
    except (ValueError, RuntimeError):
        return None


class KodiPort:
    def __init__(self, xbmc, gui, player):
        self.xbmc, self.gui, self.player = xbmc, gui, player
        self._identity = None  # Scalars only; never retain a native ListItem.
        self._manifest = None
        self._manifest_binding = None
        self._manifest_read = False

    def invalidate_identity(self):
        self._identity = None
        self._manifest = None
        self._manifest_binding = None
        self._manifest_read = False

    def manifest_state(self, force=False):
        """Raw URL lives only in this expression; never returned or logged."""
        if force or not self._manifest_read:
            self._manifest = None
            self._manifest_binding = None
            self._manifest_read = True
            try:
                self._manifest_binding = manifest_binding(self.player.getPlayingFile())
                self._manifest = self._manifest_binding[0] if self._manifest_binding is not None else None
            except Exception:
                pass
        try:
            progress = self.player.getTime()
        except Exception:
            progress = None
        return self._manifest, progress

    def current_binding(self):
        return self._manifest_binding

    def orange_identity(self, player_id, channel_id, force):
        key = (player_id, channel_id)
        if force or self._identity is None or self._identity[0] != key:
            self.invalidate_identity()
            item = self.player.getPlayingItem()
            cid = item.getProperty("orangego.channel_id")
            live = item.getProperty("orangego.is_live") == "true"
            current = self.rpc("Player.GetItem", {"playerid": player_id, "properties": []})["item"]
            if (current.get("type") != "channel" or type(current.get("id")) is not int
                    or current["id"] != channel_id):
                raise ValueError("channel_changed_during_identity_read")
            self._identity = (key, cid if cid in CHANNEL_IDS else None, live)
        return self._identity[1:]

    def rpc(self, method, params=None):
        request = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            request["params"] = params
        reply = json.loads(self.xbmc.executeJSONRPC(json.dumps(request)))
        if not isinstance(reply, dict) or "error" in reply or "result" not in reply:
            raise RuntimeError("rpc_unavailable")
        return reply["result"]

    def snapshot(self, force_identity=False):
        result = dict(network=None, identity=None, fullscreen=False,
                      post_window=False, stopped=None, player_id=None)
        try:
            result["network"] = local_network(self.xbmc)
            window = self.gui.getCurrentWindowId()
            clear = (self.gui.getCurrentWindowDialogId() == 9999
                     and not self.xbmc.getCondVisibility("Window.IsVisible(videoosd)")
                     and not self.xbmc.getCondVisibility("Window.IsVisible(pvrosdchannels)"))
            result["fullscreen"] = window == 12005 and clear
            result["post_window"] = window in (12005, 10060, 10700) and clear
            active = self.rpc("Player.GetActivePlayers")
            if not isinstance(active, list) or any(not isinstance(p, dict) for p in active):
                raise ValueError("players_unknown")
            result["stopped"] = not active
            if len(active) != 1 or active[0].get("type") != "video":
                self.invalidate_identity()
                return result
            pid = active[0].get("playerid")
            if type(pid) is not int or pid < 0:
                raise ValueError("player_unknown")
            result["player_id"] = pid
            props = self.rpc("Player.GetProperties", {"playerid": pid, "properties": ["speed"]})
            current = self.rpc("Player.GetItem", {"playerid": pid, "properties": []})["item"]
            channel = current.get("id") if current.get("type") == "channel" else None
            speed = props.get("speed")
            playing = type(speed) in (int, float) and speed == 1
            pvr = self.xbmc.getCondVisibility("Pvr.IsPlayingTv")
            video = self.xbmc.getCondVisibility("Player.HasVideo")
            if (type(channel) is not int or channel <= 0 or not playing
                    or pvr is not True or video is not True or result["network"] is None):
                self.invalidate_identity()
                return result
            cid, live = self.orange_identity(pid, channel, force_identity)
            result["identity"] = eligible_item(
                cid, channel, live=live, pvr=pvr, video=video,
                paused=not playing, fullscreen=True)
            return result
        except Exception:
            self.invalidate_identity()
            return dict(network=None, identity=None, fullscreen=False,
                        post_window=False, stopped=None, player_id=None)

    def stop(self, player_id):
        if self.rpc("Player.Stop", {"playerid": player_id}) != "OK":
            raise RuntimeError("stop_unavailable")

    def stopping_context(self, result):
        result["network"] = local_network(self.xbmc)
        window = result["window_id"] = self.gui.getCurrentWindowId()
        dialog = result["dialog_id"] = self.gui.getCurrentWindowDialogId()
        result["video_osd"] = self.xbmc.getCondVisibility("Window.IsVisible(videoosd)")
        result["channel_list"] = self.xbmc.getCondVisibility("Window.IsVisible(pvrosdchannels)")
        clear = dialog == 9999 and not result["video_osd"] and not result["channel_list"]
        result["post_window"] = window in (12005, 10060, 10700) and clear

    def stopping_snapshot(self, candidate, player_id):
        """Teardown can retain PVR active flags after getPlayingItem stops working."""
        result = dict(network=None, post_window=False, stopped=None, same_or_stopped=False,
                      error=None, window_id=None, dialog_id=None,
                      active_kind="unknown", actual_playing=None,
                      video_osd=None, channel_list=None)
        stage = "context"
        try:
            self.stopping_context(result)
            stage = "active_players"
            active = self.rpc("Player.GetActivePlayers")
            if not isinstance(active, list) or any(not isinstance(p, dict) for p in active):
                raise ValueError("players_unknown")
            same_player = (len(active) == 1 and active[0].get("type") == "video"
                           and active[0].get("playerid") == player_id)
            result["active_kind"] = "none" if not active else "video" if same_player else "other"
            stage = "actual_playing"
            actual = result["actual_playing"] = self.player.isPlaying()
            if type(actual) is not bool:
                raise ValueError("playback_unknown")
            result["stopped"] = not active and not actual
            if not active:
                result["same_or_stopped"] = not actual
                if actual:
                    result["error"] = "post_stop_state_disagreement"
            elif same_player and not actual:
                # Known closing state: still wait for active=[] and the Stop callback.
                result["same_or_stopped"] = True
            elif same_player:
                stage = "channel_identity"
                current = self.rpc("Player.GetItem", {"playerid": player_id, "properties": []})["item"]
                result["same_or_stopped"] = current.get("type") == "channel" and current.get("id") == candidate[1]
        except Exception:
            result["error"] = "post_stop_" + stage + "_unknown"
        return result

    def open_channel(self, channel_id):
        if self.rpc("Player.Open", {"item": {"channelid": channel_id}}) != "OK":
            raise RuntimeError("open_unavailable")

    def log(self, code):
        self.xbmc.log("[service.orange.tata.reconnect] " + code, self.xbmc.LOGINFO)


class Controller:
    def __init__(self, port, monitor, events, clock=time.monotonic, manifest=None):
        self.port, self.monitor, self.events, self.clock = port, monitor, events, clock
        self.state = ReconnectState()
        self.manifest = manifest

    def drain(self, gate=None):
        changed = False
        while True:
            try:
                event, when = self.events.get_nowait()
            except queue.Empty:
                return changed
            changed = True
            self.port.invalidate_identity()
            if self.manifest is not None:
                self.manifest.on_event()
            if gate is not None:
                gate.on_event(event, when)
                if event == "stopped" and not gate.cancelled:
                    continue
            self.state.on_event(event)

    def recover(self, candidate, manifest_source=None, signaled_at=None):
        # Recheck ownership after the five-second interval, before spending Stop.
        fresh = self.port.snapshot(force_identity=True)
        source_ok = True
        if manifest_source is not None:
            source_ok = (fresh['identity'] == candidate and fresh['network'] is True
                         and fresh['fullscreen'] is True
                         and self.port.manifest_state(force=True)[0] == manifest_source
                         and signaled_at is not None and 0 <= self.clock() - signaled_at <= 2)
        if (self.drain() or self.monitor.abortRequested() or fresh["network"] is not True
                or not fresh["fullscreen"] or fresh["identity"] != candidate or not source_ok):
            self.port.log("cancelled_before_stop")
            return
        gate = StopGate(self.clock())
        current = {}
        stop_rpc_ms = read_ms = confirmation_ms = None

        def timings():
            return dict(elapsed_ms=round((self.clock() - gate.started) * 1000),
                        stop_rpc_ms=stop_rpc_ms, post_read_ms=read_ms,
                        stop_callback_ms=(round((gate.ack_at - gate.started) * 1000)
                                          if gate.ack_at is not None else None),
                        confirmation_ms=confirmation_ms)

        stage = "stop_rpc_failed"
        self.port.log("one_attempt_stop_requested")
        try:
            self.port.stop(fresh["player_id"])
            stop_rpc_ms = round((self.clock() - gate.started) * 1000)
            stage = "post_stop_read_failed"
            while self.clock() < gate.deadline:
                if self.monitor.waitForAbort(min(0.1, max(0, gate.deadline - self.clock()))):
                    gate.cancel("service_abort")
                    break
                self.drain(gate)
                read_started = self.clock()
                current = self.port.stopping_snapshot(candidate, fresh["player_id"])
                if (not current.get("error") and current["stopped"] is True
                        and current["same_or_stopped"] is True and current["network"] is True
                        and current["post_window"] is True and self.clock() <= gate.deadline):
                    # A fresh guard may only narrow permission; never overwrite an earlier veto.
                    self.port.stopping_context(current)
                read_ms = round((self.clock() - read_started) * 1000)
                self.drain(gate)
                if current.get("error"):
                    gate.cancel(current["error"])
                observed_at = self.clock()
                ready = gate.ready(observed_at, stopped=current["stopped"],
                                   network=current["network"], window_ok=current["post_window"],
                                   same_or_stopped=current["same_or_stopped"])
                if self.monitor.abortRequested():
                    gate.cancel("service_abort")
                if gate.cancelled:
                    break
                if ready:
                    decision_at = self.clock()  # After the last synchronous SDK guard.
                    if decision_at > gate.deadline:
                        gate.cancel("player_stop_timeout")
                        break
                    confirmation_ms = round((decision_at - gate.started) * 1000)
                    stage = "open_rpc_failed"
                    self.port.open_channel(candidate[1])
                    self.port.log("one_attempt_open_requested " + json.dumps(timings(), sort_keys=True))
                    return
        except Exception:
            gate.cancel(stage)
        finally:
            self.state.last = self.state.pending = self.state.since = None
        if not gate.cancelled:
            gate.cancel("stop_ack_timeout" if not gate.ack else "player_stop_timeout")
        diagnostics = {key: current.get(key) for key in (
            "window_id", "dialog_id", "network", "active_kind", "actual_playing",
            "video_osd", "channel_list")}
        diagnostics.update(reason=gate.reason, stop_ack=gate.ack)
        diagnostics.update(timings())
        self.port.log("cancelled_after_stop_no_retry " + json.dumps(diagnostics, sort_keys=True))

    def tick(self):
        self.drain()
        current = self.port.snapshot()
        if self.drain():
            current["identity"] = None  # Callback raced the snapshot: discard it.
        item = current["identity"] if current["fullscreen"] else None
        candidate = self.state.step(self.clock(), current["network"], item)
        if candidate is not None:
            self.recover(candidate)
            return
        if self.manifest is not None:
            source, progress = (self.port.manifest_state()
                                if current['identity'] is not None else (None, None))
            binding = self.port.current_binding() if source is not None else None
            if self.drain():
                current['identity'] = None
            now = self.clock()
            if self.manifest.observe(now, current, source, progress, binding=binding):
                self.port.log('manifest_419_episode_qualified')
                self.recover(current['identity'], manifest_source=source, signaled_at=now)

    def run(self):
        self.port.log("service_started_local_network_and_manifest identity_cache=v1 manifest_watch=v2 stop_gate=v2")
        while not self.monitor.abortRequested():
            try:
                self.tick()
            except Exception:
                self.state.on_event("unknown_state")
                if self.manifest is not None:
                    self.manifest.on_event()
                self.port.log("unknown_state_pending_cancelled")
            if self.monitor.waitForAbort(2):
                return
