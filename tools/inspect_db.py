"""Inspect SEGITEC local RAW SQLite marks without the sqlite3 CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from raspberry.raw_store import RawStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lista marcas RAW locales desde SQLite")
    parser.add_argument(
        "--db",
        default="data/segitec_asistencia.db",
        help="Ruta a la base SQLite local",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Cantidad máxima de marcas a mostrar",
    )
    parser.add_argument(
        "--pending-only",
        action="store_true",
        help="Mostrar solo marcas pendientes de sincronización",
    )
    parser.add_argument(
        "--validate-chain",
        action="store_true",
        help="Validar la cadena row_hash/previous_hash",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"No existe la base SQLite: {db_path}")

    store = RawStore(db_path)
    marks = store.list_pending(limit=args.limit) if args.pending_only else store.list_marks(limit=args.limit)

    if not marks:
        print("No hay marcas RAW para mostrar.")
    else:
        print("id | marked_at | tag_uid | worker_id | obra | synced | attempts | previous_hash | row_hash | last_sync_error")
        for mark in marks:
            print(
                " | ".join(
                    [
                        str(mark.id),
                        mark.marked_at,
                        mark.tag_uid,
                        mark.worker_id or "",
                        mark.obra,
                        "sí" if mark.synced else "no",
                        str(mark.sync_attempts),
                        mark.previous_hash or "",
                        mark.row_hash,
                        mark.last_sync_error or "",
                    ]
                )
            )

    if args.validate_chain:
        is_valid, error = store.validate_hash_chain()
        if is_valid:
            print("Cadena hash RAW: OK")
        else:
            raise SystemExit(f"Cadena hash RAW: ERROR - {error}")


if __name__ == "__main__":
    main()
