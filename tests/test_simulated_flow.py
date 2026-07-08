from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as BaseThreadingHTTPServer
from threading import Thread

from tools.fake_apps_script_server import FakeAppsScriptHandler, ThreadingHTTPServer
from raspberry.main import _build_sync_client_from_config, process_simulated_uid, run
from raspberry.raw_store import RawStore
from raspberry.rfid import normalize_uid
from raspberry.sync_service import DryRunSyncClient, GoogleAppsScriptSyncClient, build_sync_client, sync_pending_marks
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
        client = GoogleAppsScriptSyncClient(f"http://127.0.0.1:{port}/exec", "TEST_SECRET", timeout_seconds=2)

        synced = sync_pending_marks(store, client)

        assert synced == 1
        assert store.get_mark(mark.id).synced is True
        assert FakeAppsScriptHandler.received_marks[0]["api_key"] == "TEST_SECRET"
        assert FakeAppsScriptHandler.received_marks[0]["type"] == "raw_mark"
        assert FakeAppsScriptHandler.received_marks[0]["payload"]["tag_uid"] == "04AABBCCDD"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_sync_does_not_mark_synced_when_response_ok_false(tmp_path):
    class RejectingHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": false, "error": "invalid api_key"}')

        def log_message(self, format: str, *args) -> None:  # noqa: A002 - inherited signature.
            return

    server = BaseThreadingHTTPServer(("127.0.0.1", 0), RejectingHandler)
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
        client = GoogleAppsScriptSyncClient(f"http://127.0.0.1:{port}/exec", "TEST_SECRET", timeout_seconds=2)

        synced = sync_pending_marks(store, client)

        stored = store.get_mark(mark.id)
        assert synced == 0
        assert stored.synced is False
        assert stored.sync_attempts == 1
        assert "invalid api_key" in (stored.last_sync_error or "")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_sync_records_error_when_apps_script_rejects_api_key(tmp_path):
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
        client = GoogleAppsScriptSyncClient(f"http://127.0.0.1:{port}/exec", "BAD_SECRET", timeout_seconds=2)

        synced = sync_pending_marks(store, client)

        stored = store.get_mark(mark.id)
        assert synced == 0
        assert stored.synced is False
        assert stored.sync_attempts == 1
        assert "invalid api_key" in (stored.last_sync_error or "")
        assert FakeAppsScriptHandler.received_marks[0]["api_key"] == "BAD_SECRET"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_sync_records_error_when_response_is_not_json(tmp_path):
    class TextHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not json")

        def log_message(self, format: str, *args) -> None:  # noqa: A002 - inherited signature.
            return

    server = BaseThreadingHTTPServer(("127.0.0.1", 0), TextHandler)
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
        client = GoogleAppsScriptSyncClient(f"http://127.0.0.1:{port}/exec", "TEST_SECRET", timeout_seconds=2)

        synced = sync_pending_marks(store, client)

        stored = store.get_mark(mark.id)
        assert synced == 0
        assert stored.synced is False
        assert stored.sync_attempts == 1
        assert "no es JSON válido" in (stored.last_sync_error or "")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_google_sync_requires_api_key_when_enabled():
    try:
        build_sync_client(enabled=True, api_url="http://127.0.0.1:8000/exec", api_key="")
    except ValueError as exc:
        assert "google.api_key es obligatorio" in str(exc)
    else:
        raise AssertionError("Expected missing google.api_key to raise ValueError")


def test_build_sync_client_from_config_reads_api_key():
    client = _build_sync_client_from_config(
        {
            "google": {
                "enabled": True,
                "api_url": "http://127.0.0.1:8000/exec",
                "api_key": "CONFIG_SECRET",
            }
        }
    )

    assert isinstance(client, GoogleAppsScriptSyncClient)
    assert client.api_key == "CONFIG_SECRET"


def test_run_with_simulate_tag_saves_one_mark_and_exits(tmp_path, capsys):
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "raw.sqlite3"
    workers_path = tmp_path / "workers.json"
    workers = WorkersCache(workers_path)
    workers.upsert(Worker(id="demo-001", name="Trabajador Demo", tag_uid="04:aa:bb:cc:dd"))
    workers.save()
    config_path.write_text(
        f"""
device:
  id: "pc-test"
  obra: "OBRA DEMO"
storage:
  raw_db_path: "{db_path}"
  workers_cache_path: "{workers_path}"
  raw_retention_days: 90
google:
  enabled: false
rfid:
  mode: "simulated"
""",
        encoding="utf-8",
    )

    run(config_path, simulate_tag="04-aa-bb-cc-dd")

    output = capsys.readouterr().out
    store = RawStore(db_path)
    marks = store.list_marks()
    assert len(marks) == 1
    assert marks[0].tag_uid == "04AABBCCDD"
    assert marks[0].row_hash
    assert "Marca RAW guardada #1" in output
