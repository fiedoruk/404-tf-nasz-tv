"""Select an existing unique native group, then expose the owner's edit XML."""
import json
import hashlib
import time
import uuid
import sys

MODE = 'nasztv.favourites.mode'
OWNER = 'nasztv.favourites.owner'
LOCK = 'nasztv.favourites.lock'
ORIGIN = 'nasztv.favourites.origin'
SKIN = 'skin.arctic.zephyr.mod'
LIMIT = 3.0
MAX_GROUPS = 1000


class Refused(RuntimeError):
    pass


class Editor:
    def __init__(self, api, gui, monitor, clock=time.monotonic, persistence=None, profile_factory=None):
        self.api, self.gui, self.monitor, self.clock = api, gui, monitor, clock
        self.deadline = None
        self.home = None
        self.owns_mode = False
        self.origin = None
        self.initial_dialog = None
        self.opened_editor = False
        self.owner = None
        self.lock = None
        self.memento = None
        self.finished = False
        self.persistence = persistence
        self.profile_factory = profile_factory
        self.profile = None

    def prepare_profile(self):
        rows = self.groups()
        if self.profile_factory is not None:
            self.profile = self.call(self.profile_factory, rows)
        else:
            old = sys.dont_write_bytecode
            try:
                sys.dont_write_bytecode = True
                from portable_profile import resolve_runtime_profile
            finally:
                sys.dont_write_bytecode = old
            self.profile = self.call(resolve_runtime_profile, self.api, rows)

    def profile_key(self):
        profile = self.profile
        identity = [list(profile.identity), profile.group_path, str(profile.database),
                    str(profile.backup_dir), profile.package, profile.uid]
        # Bind every validated Profile field without exposing private paths in the memento.
        raw = json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def require_session_profile(self):
        if (self.memento['target'] != [self.profile.group_id, self.profile.group_name, self.profile.group_path]
                or self.memento['profile_key'] != self.profile_key()):
            raise Refused('session_target_changed')

    def call(self, function, *args, **kwargs):
        if self.deadline is not None and self.clock() >= self.deadline:
            raise Refused('deadline')
        if self.monitor.abortRequested():
            raise Refused('aborted')
        return function(*args, **kwargs)

    def rpc(self, method, params):
        raw = self.call(self.api.executeJSONRPC, json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}))
        if not isinstance(raw, str) or len(raw) > 65536:
            raise Refused('rpc_unknown')
        result = json.loads(raw)
        if not isinstance(result, dict) or 'error' in result or 'result' not in result:
            raise Refused('rpc_unknown')
        return result['result']

    def context(self, mode, dialog=None):
        self.lease()
        if self.call(self.home.getProperty, MODE) != mode:
            raise Refused('mode_cancelled')
        if self.call(self.gui.getCurrentWindowId) != self.origin:
            raise Refused('window_changed')
        current = self.call(self.gui.getCurrentWindowDialogId)
        if current != (9999 if dialog is None else dialog):
            raise Refused('dialog_changed')

    def lease(self):
        if self.owner is not None and self.call(self.home.getProperty, OWNER) != self.owner:
            raise Refused('owner_changed')
        if self.lock is not None and self.call(self.home.getProperty, LOCK) != self.lock:
            raise Refused('lock_changed')

    def claim_lock(self):
        if self.call(self.home.getProperty, LOCK):
            raise Refused('busy')
        self.lock = uuid.uuid4().hex
        self.call(self.home.setProperty, LOCK, self.lock)
        self.lease()

    def release_lock(self):
        if self.home is not None and self.lock is not None:
            try:
                if self.home.getProperty(LOCK) == self.lock:
                    self.home.clearProperty(LOCK)
            except Exception:
                pass

    def save_memento(self):
        self.lease()
        self.call(self.home.setProperty, ORIGIN, json.dumps(self.memento, ensure_ascii=False))

    def clear_session(self):
        if self.home.getProperty(OWNER) == self.owner:
            self.home.clearProperty(ORIGIN)
            self.home.clearProperty(OWNER)
            # mode belongs to the native XML onUnload after SendClick29.
        self.release_lock()

    def preflight(self):
        self.home = self.call(self.gui.Window, 10000)
        if self.call(self.home.getProperty, MODE):
            raise Refused('busy')
        if any(self.call(self.home.getProperty, key) for key in (OWNER, LOCK, ORIGIN)):
            raise Refused('unfinished_previous_session')
        self.origin = self.call(self.gui.getCurrentWindowId)
        if type(self.origin) is not int or self.origin not in (10000, 12005, 10700, 10060):
            raise Refused('origin_unsupported')
        self.initial_dialog = self.call(self.gui.getCurrentWindowDialogId)
        if (self.initial_dialog != 9999
                and not (self.origin == 12005 and self.initial_dialog == 10608)):
            raise Refused('initial_dialog_unsupported')
        self.context('', self.initial_dialog)
        version = self.rpc('Application.GetProperties', {'properties': ['version']})['version']
        if type(version.get('major')) is not int or version['major'] != 21:
            raise Refused('kodi_version')
        if self.call(self.api.getSkinDir) != SKIN:
            raise Refused('skin_id')
        skin = self.rpc('Addons.GetAddonDetails',
            {'addonid': SKIN, 'properties': ['version', 'enabled']})['addon']
        if skin.get('version') != '3.0.3' or skin.get('enabled') is not True:
            raise Refused('skin_version')
        self.context('', self.initial_dialog)

    def groups(self):
        data = self.rpc('PVR.GetChannelGroups', {'channeltype': 'tv'})
        rows, limits = data['channelgroups'], data['limits']
        if (not isinstance(rows, list) or len(rows) > MAX_GROUPS
                or any(type(limits.get(k)) is not int for k in ('start', 'end', 'total'))
                or limits['start'] != 0 or limits['end'] != limits['total']
                or len(rows) != limits['total']):
            raise Refused('catalogue_unknown')
        return rows

    @staticmethod
    def unique_group(rows, name):
        matches = [row for row in rows if isinstance(row, dict) and row.get('label') == name]
        if (len(matches) != 1 or type(matches[0].get('channelgroupid')) is not int
                or matches[0]['channelgroupid'] <= 0):
            raise Refused('group_missing_or_ambiguous')
        return matches[0]['channelgroupid']

    def capture_origin(self):
        rows = self.groups()
        if self.unique_group(rows, self.profile.group_name) != self.profile.group_id:
            raise Refused('local_group_id_changed')
        self.context('', self.initial_dialog)
        first = self.current_channel()
        name = self.call(self.api.getInfoLabel, 'VideoPlayer.ChannelGroup')
        if first is None or not isinstance(name, str) or not 0 < len(name) <= 256:
            raise Refused('origin_unknown')
        self.unique_group(rows, name)
        start = self.clock()
        while self.clock() - start < 0.55:
            self.context('', self.initial_dialog)
            self.pause()
        self.context('', self.initial_dialog)
        if (self.current_channel() != first
                or self.call(self.api.getInfoLabel, 'VideoPlayer.ChannelGroup') != name):
            raise Refused('origin_unstable')
        self.unique_group(self.groups(), name)
        self.memento = dict(schema=3, name=name, path=None, window=self.origin,
                            playerid=first[0], channelid=first[1],
                            target=[self.profile.group_id, self.profile.group_name, self.profile.group_path],
                            profile_key=self.profile_key())

    def pause(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0 or self.call(self.monitor.waitForAbort, min(0.05, remaining)):
            raise Refused('deadline_or_aborted')

    def wait_dialog(self, expected, mode, waiting=9999):
        while True:
            self.lease()
            if self.call(self.home.getProperty, MODE) != mode:
                raise Refused('mode_cancelled')
            if self.call(self.gui.getCurrentWindowId) != self.origin:
                raise Refused('window_changed')
            dialog = self.call(self.gui.getCurrentWindowDialogId)
            if dialog == expected:
                return
            if dialog != waiting:
                raise Refused('dialog_changed')
            self.pause()

    def dismiss_initial_osd(self):
        self.context('', self.initial_dialog)
        if self.initial_dialog == 10608:
            self.call(self.api.executebuiltin, 'Dialog.Close(10608)', True)
            self.wait_dialog(9999, '', waiting=10608)
        self.initial_dialog = 9999
        self.context('')

    def wait_check(self, predicate, mode):
        while True:
            self.context(mode, 10603)
            if self.call(predicate) is True:
                return
            self.pause()

    def info(self, label):
        value = self.call(self.api.getInfoLabel, label)
        if not isinstance(value, str):
            raise Refused('native_info_unknown')
        return value

    def native_count(self, number):
        value = self.info('Container(%d).NumItems' % number)
        if not value or not value.isascii() or not value.isdecimal() or int(value) > MAX_GROUPS:
            raise Refused('native_count_unknown')
        return int(value)

    def native_item(self, number, index, field):
        return self.info('Container(%d).ListItemAbsolute(%d).%s' % (number, index, field))

    def native_position(self, number):
        value = self.info('Container(%d).CurrentItem' % number)
        if not value or not value.isascii() or not value.isdecimal():
            raise Refused('native_position_unknown')
        position = int(value) - 1  # CurrentItem is one-based; ListItemAbsolute is zero-based.
        if not 0 <= position < self.native_count(number):
            raise Refused('native_position_unknown')
        return position

    def focus_control(self, window, number, mode, index=None):
        self.wait_check(lambda: self.call(self.api.getCondVisibility,
                        'Control.IsVisible(%d)' % number), mode)
        self.context(mode, 10603)
        command = ('SetFocus(%d)' % number if index is None
                   else 'SetFocus(%d,%d,absolute)' % (number, index))
        self.call(self.api.executebuiltin, command, True)
        self.wait_check(lambda: self.call(window.getFocusId) == number, mode)
        if index is not None:
            self.wait_check(lambda: self.native_position(number) == index, mode)

    @staticmethod
    def group_path(path):
        return (isinstance(path, str) and 0 < len(path) <= 1024
                and path.startswith('pvr://channels/tv/') and path.endswith('/')
                and '@' in path and not any(c in path for c in ('\n', '\r', '|', '?', '#')))

    def native_group(self, window, name, path, mode):
        size = self.native_count(13)
        if size == 0:
            raise Refused('native_groups_unknown')
        matches = []
        for index in range(size):
            self.context(mode, 10603)
            if self.native_item(13, index, 'Label') == name:
                actual = self.native_item(13, index, 'FileNameAndPath')
                if not self.group_path(actual) or (path is not None and actual != path):
                    raise Refused('native_group_path_changed')
                matches.append((index, actual))
        if len(matches) != 1:
            raise Refused('native_group_missing_or_ambiguous')
        return matches[0]

    def choose_group(self, window, name, path, mode):
        index, actual = self.native_group(window, name, path, mode)
        self.context(mode, 10603)
        self.focus_control(window, 13, mode, index)
        self.context(mode, 10603)
        if (self.native_item(13, index, 'Label') != name
                or self.native_item(13, index, 'FileNameAndPath') != actual):
            raise Refused('selection_changed')
        self.context(mode, 10603)
        self.call(self.api.executebuiltin, 'Action(Select,10603)', True)
        self.wait_check(lambda: self.info('Control.GetLabel(20)') == name, mode)
        return actual

    def current_channel(self):
        """Public PVR identity only; never request file/URI or read a native ListItem."""
        try:
            if self.call(self.api.getCondVisibility, 'Pvr.IsPlayingTv') is not True:
                return None
            players = self.rpc('Player.GetActivePlayers', {})
            if (not isinstance(players, list) or len(players) != 1
                    or players[0].get('type') != 'video'
                    or type(players[0].get('playerid')) is not int):
                return None
            pid = players[0]['playerid']
            item = self.rpc('Player.GetItem', {'playerid': pid, 'properties': ['channel']})['item']
            name = item.get('channel')
            if (pid < 0 or item.get('type') != 'channel' or type(item.get('id')) is not int
                    or item['id'] <= 0 or not isinstance(name, str) or not 0 < len(name) <= 256):
                return None
            return pid, item['id'], name
        except Exception:
            return None

    def current_focus(self, window):
        fallback = (11, None)
        # Keep time for mode/focus/readback. Optional scanning never owns another budget.
        if self.deadline - self.clock() < 0.8:
            return fallback
        identity = self.current_channel()
        if identity is None:
            return fallback
        matches = []
        for control_id in (11, 12):
            self.context('loading', 10603)
            try:
                size = self.native_count(control_id)
            except Exception:
                return fallback
            for index in range(size):
                if self.deadline - self.clock() < 0.4:
                    return fallback
                self.context('loading', 10603)
                if self.native_item(control_id, index, 'Label') == identity[2]:
                    matches.append((control_id, index))
        if (len(matches) != 1 or self.deadline - self.clock() < 0.4
                or self.current_channel() != identity):
            return fallback
        return matches[0]

    def edit(self):
        self.prepare_profile()
        self.context('', self.initial_dialog)
        self.capture_origin()
        self.dismiss_initial_osd()
        self.context('')
        self.claim_lock()
        self.context('')
        if any(self.call(self.home.getProperty, key) for key in (OWNER, ORIGIN)):
            raise Refused('session_claimed_during_preflight')
        self.owner = uuid.uuid4().hex
        self.call(self.home.setProperty, OWNER, self.owner)
        self.lease()
        self.save_memento()
        self.owns_mode = True
        self.call(self.home.setProperty, MODE, 'loading')
        self.context('loading')
        self.opened_editor = True
        self.call(self.api.executebuiltin, 'ActivateWindow(pvrgroupmanager)', False)
        self.wait_dialog(10603, 'loading')
        window = self.call(self.gui.Window, 10603)
        if self.call(window.getProperty, 'IsRadio') != '':
            raise Refused('native_not_tv')
        _, original_path = self.native_group(window, self.memento['name'], None, 'loading')
        self.memento['path'] = original_path
        self.save_memento()
        self.choose_group(window, self.profile.group_name, self.profile.group_path, 'loading')
        focus, selected = self.current_focus(window)
        self.context('loading', 10603)
        self.context('loading', 10603)
        self.call(self.home.setProperty, MODE, 'edit')
        self.focus_control(window, focus, 'edit', selected)
        self.context('edit', 10603)

    def notice(self, message):
        if self.clock() < self.deadline:
            self.call(self.call(self.gui.Dialog).notification, 'Ulubione', message,
                      time=5000, sound=False)

    def restore_and_close(self, mode):
        self.lease()
        desired = self.read_memberships()
        playing = self.call(self.api.getCondVisibility, 'Pvr.IsPlayingTv')
        if playing is True:
            current = self.current_channel()
            if current is None or current[:2] != (self.memento['playerid'], self.memento['channelid']):
                raise Refused('playback_changed_before_restore')
        elif playing is not False:
            raise Refused('playback_unknown_before_restore')
        self.call(self.home.setProperty, MODE, mode)
        self.context(mode, 10603)
        window = self.call(self.gui.Window, 10603)
        if self.call(window.getProperty, 'IsRadio') != '':
            raise Refused('native_not_tv')
        self.choose_group(window, self.memento['name'], self.memento['path'], mode)
        self.context(mode, 10603)
        self.prepare_profile()
        self.context(mode, 10603)
        self.require_session_profile()
        if self.read_memberships() != desired:
            raise Refused('memory_changed_before_save')
        # Native button29 ignores param1: PersistChanges, then Close. This also saves edits.
        self.call(self.api.executebuiltin, 'SendClick(10603,29)', True)
        self.finished = True
        try:
            origin_is_favourites = (self.memento['name'] == self.profile.group_name
                                    and self.memento['path'] == self.profile.group_path)
            if self.persistence is not None:
                self.persistence(desired, self.read_memberships, origin_is_favourites, self.profile)
            else:
                old = sys.dont_write_bytecode
                try:
                    sys.dont_write_bytecode = True
                    from persistence_runtime import persist_after_save
                finally:
                    sys.dont_write_bytecode = old
                persist_after_save(desired, self.read_memberships, origin_is_favourites, self.profile)
        except Exception:
            try:
                self.gui.Dialog().notification('Ulubione',
                    'Nie udało się trwale zapisać usunięcia. Lista może wrócić po ponownym uruchomieniu.',
                    time=7000, sound=False)
            finally:
                self.clear_session()
                self.home.clearProperty(MODE)
            return 'persistence_failed'
        self.clear_session()
        self.home.clearProperty(MODE)
        return 'finish_requested'

    def read_memberships(self, playing=False):
        if playing:
            value = self.call(self.api.getCondVisibility, 'Pvr.IsPlayingTv')
            if value is False: return 0
            current = self.current_channel()
            if value is not True or current is None: raise Refused('playing_unknown')
            return current[1]
        rows = self.groups()
        if self.unique_group(rows, self.profile.group_name) != self.profile.group_id:
            raise Refused('local_group_id_changed')
        data = self.rpc('PVR.GetChannels', {'channelgroupid': self.profile.group_id, 'properties': []})
        values, limits = data['channels'], data['limits']
        if (not isinstance(values, list) or not 0 <= len(values) <= 1000
                or limits != {'start':0,'end':len(values),'total':len(values)}):
            raise Refused('membership_unknown')
        ids = [row.get('channelid') for row in values if isinstance(row, dict)]
        if len(ids) != len(values) or any(type(x) is not int or x <= 0 for x in ids) or len(set(ids)) != len(ids):
            raise Refused('membership_ids_unknown')
        return tuple(sorted(ids))

    def read_session(self):
        self.home = self.call(self.gui.Window, 10000)
        self.owner = self.call(self.home.getProperty, OWNER)
        raw = self.call(self.home.getProperty, ORIGIN)
        if (len(self.owner) != 32 or any(c not in '0123456789abcdef' for c in self.owner)
                or not isinstance(raw, str) or not 0 < len(raw) <= 2048):
            raise Refused('memento_unknown')
        value = json.loads(raw)
        expected = {'schema', 'name', 'path', 'window', 'playerid', 'channelid', 'target', 'profile_key'}
        if (not isinstance(value, dict) or set(value) != expected or value['schema'] != 3
                or not isinstance(value['name'], str) or not 0 < len(value['name']) <= 256
                or (value['path'] is not None and not self.group_path(value['path']))
                or type(value['window']) is not int or value['window'] not in (10000,12005,10700,10060)
                or type(value['playerid']) is not int or value['playerid'] < 0
                or type(value['channelid']) is not int or value['channelid'] <= 0
                or not isinstance(value['target'], list) or len(value['target']) != 3
                or type(value['target'][0]) is not int or value['target'][0] <= 0
                or not isinstance(value['target'][1], str) or not 0 < len(value['target'][1]) <= 64
                or not self.group_path(value['target'][2])
                or not isinstance(value['profile_key'], str) or len(value['profile_key']) != 64
                or any(c not in '0123456789abcdef' for c in value['profile_key'])):
            raise Refused('memento_unknown')
        self.origin, self.memento = value['window'], value
        self.opened_editor = True
        self.lease()

    def removal_is_current(self, window):
        if self.memento['name'] != self.profile.group_name or self.memento['path'] != self.profile.group_path:
            return False
        playing = self.call(self.api.getCondVisibility, 'Pvr.IsPlayingTv')
        if playing is False:
            return False
        if playing is not True:
            raise Refused('playing_unknown')
        current = self.current_channel()
        if current is None:
            raise Refused('playing_unknown')
        item = self.rpc('Player.GetItem',
                        {'playerid': current[0], 'properties': ['mediapath']})['item']
        path = item.get('mediapath')
        if (item.get('type') != 'channel' or item.get('id') != current[1]
                or not isinstance(path, str) or not path.startswith('pvr://channels/tv/')
                or not path.endswith('.pvr') or any(c in path for c in ('?', '#', '|'))):
            raise Refused('playing_path_unknown')
        index = self.native_position(12)
        selected_path = self.native_item(12, index, 'FileNameAndPath')
        if (not isinstance(selected_path, str) or not selected_path.startswith(self.profile.group_path)
                or not selected_path.endswith('.pvr')):
            raise Refused('selected_channel_unknown')
        if self.current_channel() != current:
            raise Refused('playing_changed')
        return selected_path.rsplit('/', 1)[-1] == path.rsplit('/', 1)[-1]

    def owned_command(self, command):
        self.home = self.call(self.gui.Window, 10000)
        mode = self.call(self.home.getProperty, MODE)
        if self.call(self.gui.getCurrentWindowDialogId) != 10603:
            return 'not_opened'
        if not mode and not any(self.call(self.home.getProperty, k) for k in (OWNER,LOCK,ORIGIN)):
            if command in ('back', 'select'):
                action = 'Back' if command == 'back' else 'Select'
                self.call(self.api.executebuiltin, 'Action(%s,10603)' % action, True)
                return 'stock_forwarded'
            return 'not_opened'
        self.read_session()
        self.context(mode, 10603)
        if self.call(self.home.getProperty, LOCK):
            if command in ('back', 'finish') and mode == 'loading':
                self.call(self.home.setProperty, MODE, 'cancel')
                return 'cancel_requested'
            return 'busy'
        if mode not in ('edit', 'cancel'):
            return 'not_opened'
        self.prepare_profile()
        self.context(mode, 10603)
        self.require_session_profile()
        self.claim_lock()
        if command in ('finish', 'back'):
            return self.restore_and_close('saving' if command == 'finish' else 'cancel')
        if mode != 'edit':
            return 'not_opened'
        window = self.call(self.gui.Window, 10603)
        self.context('edit', 10603)
        focus = self.call(window.getFocusId)
        if focus in (8001,29):
            return self.restore_and_close('saving')
        if focus not in (11,12):
            raise Refused('edit_control_unknown')
        if self.info('Control.GetLabel(20)') != self.profile.group_name:
            raise Refused('group_context_changed')
        if focus == 12 and self.removal_is_current(window):
            self.notice('Najpierw przełącz na inny kanał. Potem usuń ten kanał z ulubionych.')
            return 'playing_channel_guard'
        self.context('edit', 10603)
        self.call(self.api.executebuiltin, 'Action(Select,10603)', True)
        return 'select_forwarded'

    def order(self):
        self.dismiss_initial_osd()
        self.context('')
        # User acknowledgement is interactive, outside the automatic 3-second wait.
        self.deadline = None
        dialog = self.call(self.gui.Dialog)
        accepted = self.call(dialog.yesno, 'Kolejność kanałów',
            'Kolejność jest wspólna we wszystkich listach. Zmiana wpłynie także na listę wszystkich kanałów. Otworzyć menedżer kanałów?')
        self.deadline = self.clock() + LIMIT
        self.context('')
        if accepted is not True:
            raise Refused('order_cancelled')
        self.call(self.api.executebuiltin, 'ActivateWindow(pvrchannelmanager)', False)
        self.wait_dialog(10604, '')

    def run(self, command):
        self.deadline = self.clock() + LIMIT
        try:
            if command in ('finish', 'back', 'select'):
                return self.owned_command(command)
            if command not in ('edit', 'order'):
                raise Refused('unknown_command')
            self.preflight()
            if command == 'edit':
                self.edit()
            else:
                self.order()
            return 'opened_' + command
        except Exception:
            # Never close after an unconfirmed restore or discard its memento.
            if self.owner is not None and self.home is not None:
                try:
                    if self.home.getProperty(OWNER) == self.owner:
                        if command == 'select':
                            pass  # Refuse only this action; retain the editable session.
                        elif self.opened_editor and self.gui.getCurrentWindowDialogId() == 10603:
                            self.home.setProperty(MODE, 'cancel')
                            if command == 'edit':
                                try:
                                    self.restore_and_close('cancel')
                                except Exception:
                                    pass  # A new explicit Back can retry with its own bounded budget.
                        elif not self.opened_editor:
                            self.clear_session()
                            self.home.clearProperty(MODE)
                        elif self.home.getProperty(MODE) in ('loading', 'edit', 'saving'):
                            self.home.setProperty(MODE, 'cancel')
                        # Once native UI was opened, an unexpected unload retains the memento.
                except Exception:
                    pass
            return 'not_opened'
        finally:
            self.release_lock()
