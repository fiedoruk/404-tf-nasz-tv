"""Approved, guarded membership-only transaction. Connection belongs to the caller."""
import unicodedata

SCHEMA = {
    'version': 'idVersion:INTEGER iCompressCount:INTEGER',
    'channels': 'idChannel:INTEGER iUniqueId:INTEGER bIsRadio:BOOL bIsHidden:BOOL bIsUserSetIcon:BOOL bIsUserSetName:BOOL bIsLocked:BOOL sIconPath:VARCHAR(255) sChannelName:VARCHAR(64) bIsVirtual:BOOL bEPGEnabled:BOOL sEPGScraper:VARCHAR(32) iLastWatched:INTEGER iClientId:INTEGER idEpg:INTEGER bHasArchive:BOOL iClientProviderUid:INTEGER bIsUserSetHidden:BOOL iLastWatchedGroupId:INTEGER sDateTimeAdded:VARCHAR(20)',
    'channelgroups': 'idGroup:INTEGER bIsRadio:BOOL iGroupType:INTEGER sName:VARCHAR(64) iLastWatched:INTEGER bIsHidden:BOOL iPosition:INTEGER iLastOpened:BIGINT_UNSIGNED iClientId:INTEGER bIsUserSetName:BOOL sClientName:VARCHAR(64) iClientPosition:INTEGER',
    'map_channelgroups_channels': 'idChannel:INTEGER idGroup:INTEGER iChannelNumber:INTEGER iSubChannelNumber:INTEGER iOrder:INTEGER iClientChannelNumber:INTEGER iClientSubChannelNumber:INTEGER',
}
MEMBER_COLUMNS = tuple(x.split(':')[0] for x in SCHEMA['map_channelgroups_channels'].split())


class Refused(RuntimeError):
    pass


def validate_identity(identity):
    if (not isinstance(identity, tuple) or len(identity) != 5
            or type(identity[0]) is not int or not 0 < identity[0] <= 2147483647
            or identity[1:3] != (0, 2) or identity[4] != -1
            or not isinstance(identity[3], str) or not 0 < len(identity[3]) <= 64):
        raise Refused('group_identity_unknown')
    return identity


def name_key(value):
    return unicodedata.normalize('NFC', value).strip().casefold() if isinstance(value, str) else None


def read_group_identity(conn, group_id, name):
    rows = conn.execute('SELECT idGroup,bIsRadio,iGroupType,sName,iClientId FROM channelgroups LIMIT 1001').fetchall()
    if len(rows) > 1000: raise Refused('db_groups_limit')
    return tuple(tuple(row) for row in rows if row[0] == group_id or name_key(row[3]) == name_key(name))


def validate_schema(conn):
    if conn.execute('SELECT idVersion FROM version').fetchall() != [(46,)]:
        raise Refused('schema_version')
    for table, description in SCHEMA.items():
        expected_schema = {a: b.replace('_',' ') for a,b in (x.split(':') for x in description.split())}
        info = conn.execute('PRAGMA table_info("'+table+'")').fetchall()
        actual = {r[1]: r[2].upper() for r in info}
        expected_pk = {'idChannel':1} if table=='channels' else {'idGroup':1} if table=='channelgroups' else {}
        if actual != expected_schema or {r[1]:r[5] for r in info if r[5]} != expected_pk:
            raise Refused('schema_drift')
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    if len(tables) > 64 or conn.execute("SELECT 1 FROM sqlite_master WHERE type='trigger'").fetchone():
        raise Refused('schema_side_effects')
    if any(conn.execute('PRAGMA foreign_key_list("'+t[0].replace('"','""')+'")').fetchone() for t in tables):
        raise Refused('schema_side_effects')
    indexes = conn.execute('PRAGMA index_list(map_channelgroups_channels)').fetchall()
    if not any(r[1]=='idx_idGroup_idChannel' and r[2]==1 for r in indexes):
        raise Refused('membership_index_unknown')
    if [r[2] for r in conn.execute('PRAGMA index_info(idx_idGroup_idChannel)')] != ['idGroup','idChannel']:
        raise Refused('membership_index_unknown')


def prune_stale_memberships(conn, desired_ids, expected_rows, *, playing_id,
                            origin_is_favourites, backup_rows, group_identity):
    """Delete extras only. expected_rows is a verified ordered preflight snapshot.

    backup_rows receives immutable (column_names, deleted_rows) BEFORE DELETE;
    True must mean durable backup completed. It must not use/commit this connection.
    playing_id=0 means caller verified no playing PVR; None/unknown is refused.
    Empty desired set deletes only this group's memberships, with the same guards.
    """
    identity = validate_identity(group_identity)
    group_id = identity[0]
    if (conn.in_transaction or type(origin_is_favourites) is not bool
            or type(playing_id) is not int or playing_id < 0 or not callable(backup_rows)):
        raise Refused('unknown_context_or_active_transaction')
    if (not isinstance(desired_ids, (list, tuple, set, frozenset)) or not 0 <= len(desired_ids) <= 1000
            or any(type(x) is not int or x <= 0 for x in desired_ids)
            or len(set(desired_ids)) != len(desired_ids)):
        raise Refused('desired_unknown')
    wanted = set(desired_ids)
    if (not isinstance(expected_rows, (list, tuple)) or not 0 <= len(expected_rows) <= 1000
            or any(not isinstance(r, (list, tuple)) or len(r) != 7 for r in expected_rows)):
        raise Refused('snapshot_unknown')
    expected = tuple(tuple(r) for r in expected_rows)
    old_timeout = conn.execute('PRAGMA busy_timeout').fetchone()[0]
    columns = ','.join(MEMBER_COLUMNS)
    read_rows = lambda: tuple(conn.execute('SELECT '+columns+' FROM map_channelgroups_channels WHERE idGroup=? ORDER BY idChannel', (group_id,)))
    read_identity = lambda: read_group_identity(conn, group_id, identity[3])
    try:
        conn.execute('PRAGMA busy_timeout=250')
        conn.execute('BEGIN IMMEDIATE')
        validate_schema(conn)
        if read_identity() != (identity,) or read_rows() != expected:
            raise Refused('identity_or_membership_drift')
        existing = {r[0] for r in expected}
        if not wanted <= existing:
            raise Refused('missing_desired_membership')
        known = conn.execute('SELECT idChannel,bIsRadio FROM channels WHERE idChannel IN ('+','.join('?'*len(existing))+')', tuple(existing)).fetchall() if existing else []
        if {r[0] for r in known} != existing or any(r[1] != 0 for r in known):
            raise Refused('unknown_or_non_tv_channel')
        deleted = tuple(r for r in expected if r[0] not in wanted)
        if origin_is_favourites and any(r[0] == playing_id for r in deleted):
            raise Refused('current_playing_removal')
        if deleted and backup_rows(MEMBER_COLUMNS, deleted) is not True:
            raise Refused('backup_not_confirmed')
        if not conn.in_transaction or read_rows() != expected or read_identity() != (identity,):
            raise Refused('changed_during_backup')
        for row in deleted:
            result = conn.execute('DELETE FROM map_channelgroups_channels WHERE idGroup=? AND idChannel=?', (group_id, row[0]))
            if result.rowcount != 1:
                raise Refused('delete_count')
        if read_rows() != tuple(r for r in expected if r[0] in wanted) or read_identity() != (identity,):
            raise Refused('readback_failed')
        conn.commit()
        return {'deleted_rows': deleted, 'remaining_ids': tuple(sorted(wanted)), 'scope': 'membership_only'}
    except Exception:
        if conn.in_transaction:
            try:
                conn.rollback()
            except Exception:
                raise Refused('rollback_failed_state_unknown') from None
        raise
    finally:
        conn.execute('PRAGMA busy_timeout='+str(int(old_timeout)))
