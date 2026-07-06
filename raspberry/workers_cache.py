"""Local worker cache keyed by normalized RFID/NFC tag UID."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from raspberry.rfid import normalize_uid


@dataclass(frozen=True)
class Worker:
    id: str
    name: str
    tag_uid: str
    active: bool = True


class WorkersCache:
    """Loads and persists a small JSON worker cache for offline validation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._workers_by_tag: dict[str, Worker] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._workers_by_tag = {}
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        workers = [Worker(**item) for item in payload.get("workers", [])]
        self._workers_by_tag = {normalize_uid(worker.tag_uid): worker for worker in workers}

    def save(self) -> None:
        workers = [asdict(worker) for worker in self._workers_by_tag.values()]
        self.path.write_text(
            json.dumps({"workers": workers}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_by_tag(self, tag_uid: str) -> Worker | None:
        worker = self._workers_by_tag.get(normalize_uid(tag_uid))
        if worker is None or not worker.active:
            return None
        return worker

    def upsert(self, worker: Worker) -> None:
        normalized_uid = normalize_uid(worker.tag_uid)
        self._workers_by_tag[normalized_uid] = Worker(
            id=worker.id,
            name=worker.name,
            tag_uid=normalized_uid,
            active=worker.active,
        )
