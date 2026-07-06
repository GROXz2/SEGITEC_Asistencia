from datetime import UTC, datetime, timedelta

from raspberry.raw_store import RawStore


def test_add_mark_persists_raw_mark(tmp_path):
    store = RawStore(tmp_path / "raw.sqlite3")

    mark = store.add_mark(
        tag_uid="04AABBCCDD",
        worker_id="trabajador-1",
        device_id="raspberry-1",
        obra="OBRA DEMO",
        marked_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    )

    stored = store.get_mark(mark.id)
    assert stored.tag_uid == "04AABBCCDD"
    assert stored.worker_id == "trabajador-1"
    assert stored.device_id == "raspberry-1"
    assert stored.obra == "OBRA DEMO"
    assert stored.synced is False
    assert stored.sync_attempts == 0


def test_pending_marks_and_mark_synced(tmp_path):
    store = RawStore(tmp_path / "raw.sqlite3")
    first = store.add_mark(
        tag_uid="TAG-1",
        worker_id=None,
        device_id="raspberry-1",
        obra="OBRA DEMO",
    )
    store.add_mark(
        tag_uid="TAG-2",
        worker_id=None,
        device_id="raspberry-1",
        obra="OBRA DEMO",
    )

    assert [mark.id for mark in store.list_pending()] == [first.id, first.id + 1]

    store.mark_synced(first.id)

    assert [mark.id for mark in store.list_pending()] == [first.id + 1]
    assert store.get_mark(first.id).synced is True


def test_record_sync_failure_increments_attempts(tmp_path):
    store = RawStore(tmp_path / "raw.sqlite3")
    mark = store.add_mark(
        tag_uid="TAG-1",
        worker_id=None,
        device_id="raspberry-1",
        obra="OBRA DEMO",
    )

    store.record_sync_failure(mark.id, "sin internet")
    store.record_sync_failure(mark.id, "timeout")

    failed = store.get_mark(mark.id)
    assert failed.sync_attempts == 2
    assert failed.last_sync_error == "timeout"


def test_purge_older_than_deletes_old_marks(tmp_path):
    store = RawStore(tmp_path / "raw.sqlite3")
    old_mark = store.add_mark(
        tag_uid="OLD",
        worker_id=None,
        device_id="raspberry-1",
        obra="OBRA DEMO",
        marked_at=datetime.now(UTC) - timedelta(days=100),
    )
    new_mark = store.add_mark(
        tag_uid="NEW",
        worker_id=None,
        device_id="raspberry-1",
        obra="OBRA DEMO",
        marked_at=datetime.now(UTC),
    )

    deleted = store.purge_older_than(retention_days=90)

    assert deleted == 1
    assert store.get_mark(new_mark.id).tag_uid == "NEW"
    assert [mark.id for mark in store.list_pending()] == [new_mark.id]

    try:
        store.get_mark(old_mark.id)
    except KeyError:
        pass
    else:
        raise AssertionError("old mark should have been purged")
