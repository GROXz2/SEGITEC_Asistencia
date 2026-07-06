"""Initial console-simulated RFID flow for Raspberry Pi."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from raspberry.raw_store import RawStore
from raspberry.sync_service import GoogleAppsScriptSyncClient, NoopSyncClient, sync_pending_marks
from raspberry.workers_cache import WorkersCache


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def build_sync_client(config: dict[str, Any]):
    sync_config = config.get("sync", {})
    url = sync_config.get("google_apps_script_url", "")
    if not url or "REEMPLAZAR" in url:
        return NoopSyncClient()
    return GoogleAppsScriptSyncClient(
        url,
        timeout_seconds=int(sync_config.get("timeout_seconds", 10)),
    )


def run(config_path: str | Path) -> None:
    config = load_config(config_path)
    device = config.get("device", {})
    storage = config.get("storage", {})

    device_id = device.get("id", "raspberry-unknown")
    obra = device.get("obra", "OBRA SIN CONFIGURAR")
    raw_store = RawStore(storage.get("raw_db_path", "data/raw_marks.sqlite3"))
    workers_cache = WorkersCache(storage.get("workers_cache_path", "data/workers_cache.json"))
    sync_client = build_sync_client(config)

    retention_days = int(storage.get("raw_retention_days", 90))
    raw_store.purge_older_than(retention_days=retention_days)

    print("SEGITEC asistencia RFID - modo simulado")
    print("Ingrese UID RFID/NFC y presione Enter. Escriba 'salir' para terminar.")

    while True:
        tag_uid = input("RFID UID> ").strip()
        if tag_uid.lower() in {"salir", "exit", "quit"}:
            break
        if not tag_uid:
            continue

        worker = workers_cache.get_by_tag(tag_uid)
        raw_mark = raw_store.add_mark(
            tag_uid=tag_uid,
            worker_id=worker.id if worker else None,
            device_id=device_id,
            obra=obra,
        )
        worker_label = worker.name if worker else "TAG NO REGISTRADO"
        print(f"Marca RAW guardada #{raw_mark.id}: {worker_label} ({tag_uid})")

        synced = sync_pending_marks(raw_store, sync_client)
        print(f"Sincronización intentada. Marcas sincronizadas: {synced}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SEGITEC asistencia RFID simulada")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Ruta al archivo YAML de configuración",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.config)
