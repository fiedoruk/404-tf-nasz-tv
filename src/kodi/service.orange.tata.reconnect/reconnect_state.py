"""Pure intent gate. Emits a candidate once; never controls Kodi itself."""

# Explicit Orange IDs from the 209-channel export of 2026-10-24. Not PVR IDs,
# a numeric range, or entitlement evidence. All live/PVR/source guards still apply.
CHANNEL_IDS = frozenset((
    "14003", "14004", "14005", "14006", "14007", "14008", "14009", "14010", "14011", "14014",
    "14015", "14016", "14027", "14028", "14029", "14038", "14039", "14063", "14066", "14072",
    "14079", "14106", "14108", "14118", "14119", "14120", "14121", "14123", "14130", "14132",
    "14134", "14135", "14137", "14138", "14139", "14146", "14151", "14152", "14153", "14154",
    "14155", "14156", "14157", "14158", "14160", "14161", "14162", "14163", "14164", "14166",
    "14167", "14169", "14170", "14171", "14173", "14174", "14175", "14176", "14177", "14178",
    "14180", "14181", "14182", "14185", "14187", "14188", "14189", "14190", "14193", "14194",
    "14196", "14197", "14198", "14199", "14200", "14208", "14209", "14210", "14211", "14212",
    "14215", "14217", "14218", "14219", "14222", "14223", "14224", "14229", "14230", "14232",
    "14233", "14237", "14239", "14240", "14241", "14242", "14248", "14249", "14250", "14252",
    "14255", "14256", "14257", "14258", "14259", "14260", "14262", "14265", "14271", "14272",
    "14277", "14281", "14282", "14283", "14284", "14286", "14287", "14288", "14289", "14290",
    "14291", "14292", "14293", "14294", "14296", "14297", "14298", "14299", "14300", "14301",
    "14306", "14307", "14308", "14324", "14328", "14329", "14330", "14331", "14332", "14333",
    "14334", "14335", "14336", "14340", "14341", "14343", "14345", "14347", "14348", "14350",
    "14352", "14355", "14358", "14359", "14360", "14380", "14381", "14383", "14384", "14385",
    "14386", "14391", "14392", "14396", "14397", "14398", "14400", "14401", "14402", "14403",
    "14404", "14405", "14406", "14407", "14408", "14409", "14410", "14411", "14412", "14413",
    "14414", "14415", "14416", "14417", "14418", "14419", "14421", "14422", "14423", "14424",
    "14425", "14426", "14427", "14428", "14429", "14430", "14432", "14498", "14999", "15014",
    "15019", "15021", "15031", "15033", "15036", "15037", "15044", "15049", "15055",
))


def eligible_item(cid, channel_id, *, live, pvr, video, paused, fullscreen):
    if (cid in CHANNEL_IDS and type(channel_id) is int and channel_id > 0
            and live is True and pvr is True and video is True
            and paused is False and fullscreen is True):
        return (cid, channel_id)
    return None


class ReconnectState:
    def __init__(self):
        self.online = None
        self.last = None
        self.pending = None
        self.since = None
        self.used = False

    def on_event(self, event):
        """Callbacks cancel pending work, including pause→resume between polls."""
        self.last = self.pending = self.since = None
        if event == "av_started":
            self.used = False

    def step(self, now, online, item):
        if type(online) is not bool:
            self.online = None
            self.on_event("unknown_network")
            return None
        if self.pending is not None and item != self.pending:
            self.on_event("item_or_ui_changed")
        if self.online is True and online is False:
            self.pending = item if item is not None and item == self.last and not self.used else None
            self.since = None
        self.online, self.last = online, item
        if self.pending is None:
            return None
        if not online:
            self.since = None
        elif self.since is None:
            self.since = now
        elif now - self.since >= 5:
            candidate = self.pending
            self.pending = self.since = None
            self.used = True
            return candidate
        return None


class StopGate:
    """One Stop callback within2s; fresh confirmation within4s total, never4s after ACK."""
    def __init__(self, started):
        self.started = started
        self.ack_deadline = started + 2
        self.deadline = started + 4
        self.ack = False
        self.ack_at = None
        self.cancelled = False
        self.reason = None

    def cancel(self, reason):
        if not self.cancelled:
            self.reason = reason
        self.cancelled = True

    def on_event(self, event, when):
        if (event == "stopped" and not self.ack and not self.cancelled
                and self.started <= when <= self.ack_deadline):
            self.ack = True
            self.ack_at = when
        else:
            if event == "stopped":
                reason = "duplicate_stop" if self.ack else "stop_callback_outside_window"
            else:
                reason = "callback_" + (event if event in (
                    "started", "av_started", "paused", "ended", "resumed", "error") else "other")
            self.cancel(reason)

    def ready(self, now, *, stopped, network, window_ok, same_or_stopped):
        if now > self.deadline:
            self.cancel("stop_ack_timeout" if not self.ack else "player_stop_timeout")
        elif not self.ack and now > self.ack_deadline:
            self.cancel("stop_ack_timeout")
        elif network is not True:
            self.cancel("network_lost" if network is False else "network_unknown")
        elif window_ok is not True:
            self.cancel("window_or_dialog_disallowed")
        elif stopped is None:
            self.cancel("player_state_unknown")
        elif same_or_stopped is not True:
            self.cancel("different_player_or_channel")
        return not self.cancelled and self.ack and stopped is True
