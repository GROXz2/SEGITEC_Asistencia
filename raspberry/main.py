"""Console-simulated RFID flow for local PC and Raspberry development."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from raspberry.raw_store import RawStore
from raspberry.rfid import normalize_uid
from raspberry.sync_service import build_sync_client, sync_pending_marks
from raspberry.workers_cache import WorkersCache


SUPPORTED_RFID_MODES = {"simulated", "simulated_console"}


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def _build_sync_client_from_config(config: dict[str, Any]):
    google_config = config.get("google", {})
    legacy_sync_config = config.get("sync", {})
    return build_sync_client(
        enabled=bool(google_config.get("enabled", False)),
        api_url=str(google_config.get("api_url") or legacy_sync_config.get("google_apps_script_url") or ""),
        timeout_seconds=int(google_config.get("timeout_seconds", legacy_sync_config.get("timeout_seconds", 10))),
    )


def process_simulated_uid(
    *,
    uid: str,
    raw_store: RawStore,
    workers_cache: WorkersCache,
    sync_client,
    device_id: str,
    obra: str,
) -> tuple[int, int, str]:
    """Normalize, store, and try to sync one simulated RFID/NFC UID."""

    tag_uid = normalize_uid(uid)
    worker = workers_cache.get_by_tag(tag_uid)
    raw_mark = raw_store.add_mark(
        tag_uid=tag_uid,
        worker_id=worker.id if worker else None,
        device_id=device_id,
        obra=obra,
    )
    synced = sync_pending_marks(raw_store, sync_client)
    worker_label = worker.name if worker else "TAG NO REGISTRADO"
    return raw_mark.id, synced, worker_label


def run(config_path: str | Path, simulate_tag: str | None = None) -> None:
    config = load_config(config_path)
    device = config.get("device", {})
    storage = config.get("storage", {})
    rfid = config.get("rfid", {})

    rfid_mode = rfid.get("mode", "simulated")
    if rfid_mode not in SUPPORTED_RFID_MODES:
        raise ValueError("En esta etapa solo está disponible rfid.mode=simulated")

    device_id = device.get("id", "raspberry-unknown")
    obra = device.get("obra", "OBRA SIN CONFIGURAR")
    raw_store = RawStore(storage.get("raw_db_path", "data/segitec_asistencia.db"))
    workers_cache = WorkersCache(storage.get("workers_cache_path", "data/workers_demo.json"))
    sync_client = _build_sync_client_from_config(config)

    retention_days = int(storage.get("raw_retention_days", 90))
    raw_store.purge_older_than(retention_days=retention_days)

    print("SEGITEC asistencia RFID - modo simulated")

    if simulate_tag is not None:
        mark_id, synced, worker_label = process_simulated_uid(
            uid=simulate_tag,
            raw_store=raw_store,
            workers_cache=workers_cache,
            sync_client=sync_client,
            device_id=device_id,
            obra=obra,
        )
        print(f"Marca RAW guardada #{mark_id}: {worker_label} ({normalize_uid(simulate_tag)})")
        print(f"Sincronización intentada. Marcas sincronizadas: {synced}")
        return

    print("Ingrese UID RFID/NFC y presione Enter. Escriba 'salir' para terminar.")

    while True:
        typed_uid = input("RFID UID> ").strip()
        if typed_uid.lower() in {"salir", "exit", "quit"}:
            break
        if not typed_uid:
            continue

        try:
            mark_id, synced, worker_label = process_simulated_uid(
                uid=typed_uid,
                raw_store=raw_store,
                workers_cache=workers_cache,
                sync_client=sync_client,
                device_id=device_id,
                obra=obra,
            )
        except ValueError as exc:
            print(f"UID inválido: {exc}")
            continue
        print(f"Marca RAW guardada #{mark_id}: {worker_label} ({normalize_uid(typed_uid)})")
        print(f"Sincronización intentada. Marcas sincronizadas: {synced}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SEGITEC asistencia RFID simulada")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Ruta al archivo YAML de configuración",
    )
    parser.add_argument(
        "--simulate-tag",
        help="UID RFID/NFC para registrar una marca directa sin modo interactivo",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.config, simulate_tag=args.simulate_tag)
