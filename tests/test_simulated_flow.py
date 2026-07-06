from __future__ import annotations

from threading import Thread

from tools.fake_apps_script_server import FakeAppsScriptHandler, ThreadingHTTPServer
from raspberry.main import process_simulated_uid
from raspberry.raw_store import RawStore
from raspberry.rfid import normalize_uid
from raspberry.sync_service import DryRunSyncClient, GoogleAppsScriptSyncClient, sync_pending_marks
from raspberry.workers_cache import Worker, WorkersCache


def test_uid_normalizes_common_manual_formats():
    assert normalize_uid(" 04:aa-bb cc_dd ") == "04AABBCCDD"
    assert normalize_uid("0x04aabbccdd") == "04AABBCCDD"


def test_mark_stays_pending_when_google_disabled(tmp_path):
    store = RawStore(tmp_path / "raw.sqlite3")
    mark = store.add_mark(
        tag_uid="04AABBCCDD",
        worker_id="demo-001",
        device_id="pc-test",
        obra="OBRA DEMO",
    )

    synced = sync_pending_marks(store, DryRunSyncClient())

    stored = store.get_mark(mark.id)
    assert synced == 0
    assert stored.synced is False
    assert stored.sync_attempts == 1
    assert "google.enabled=false" in (stored.last_sync_error or "")


def test_process_simulated_uid_saves_raw_first_and_normalized(tmp_path):
    store = RawStore(tmp_path / "raw.sqlite3")
    workers = WorkersCache(tmp_path / "workers.json")
    workers.upsert(Worker(id="demo-001", name="Trabajador Demo", tag_uid="04:aa:bb:cc:dd"))
    workers.save()

    mark_id, synced, worker_label = process_simulated_uid(
        uid="04-aa-bb-cc-dd",
        raw_store=store,
        workers_cache=workers,
        sync_client=DryRunSyncClient(),
        device_id="pc-test",
        obra="OBRA DEMO",
    )

    mark = store.get_mark(mark_id)
    assert synced == 0
    assert worker_label == "Trabajador Demo"
    assert mark.tag_uid == "04AABBCCDD"
    assert mark.synced is False


def test_sync_mark_against_fake_apps_script_server(tmp_path):
    FakeAppsScriptHandler.received_marks = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAppsScriptHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        store = RawStore(tmp_path / "raw.sqlite3")
        mark = store.add_mark(
            tag_uid="04AABBCCDD",
            worker_id="demo-001",
            device_id="pc-test",
            obra="OBRA DEMO",
        )
        client = GoogleAppsScriptSyncClient(f"http://127.0.0.1:{port}/exec", timeout_seconds=2)

        synced = sync_pending_marks(store, client)

        assert synced == 1
        assert store.get_mark(mark.id).synced is True
        assert FakeAppsScriptHandler.received_marks[0]["payload"]["tag_uid"] == "04AABBCCDD"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
