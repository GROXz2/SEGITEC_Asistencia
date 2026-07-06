"""Synchronization placeholders for Google Apps Script."""

from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

import requests

from raspberry.raw_store import RawMark, RawStore


class SyncClient(Protocol):
    def send_mark(self, mark: RawMark) -> None:
        """Send a mark to the remote service or raise an exception."""


class GoogleAppsScriptSyncClient:
    """Minimal Google Apps Script HTTP client.

    The Apps Script endpoint contract will be completed in a later stage. For
    now this client posts the RAW mark as JSON and expects a successful HTTP
    status code.
    """

    def __init__(self, url: str, *, timeout_seconds: int = 10) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    def send_mark(self, mark: RawMark) -> None:
        response = requests.post(
            self.url,
            json={"type": "raw_mark", "payload": asdict(mark)},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()


class NoopSyncClient:
    """Development client that accepts marks without network access."""

    def send_mark(self, mark: RawMark) -> None:
        return None


def sync_pending_marks(raw_store: RawStore, client: SyncClient, *, limit: int = 100) -> int:
    """Try to sync pending marks and return the number synchronized."""

    synced_count = 0
    for mark in raw_store.list_pending(limit=limit):
        try:
            client.send_mark(mark)
        except Exception as exc:  # noqa: BLE001 - store any sync failure reason.
            raw_store.record_sync_failure(mark.id, str(exc))
            continue
        raw_store.mark_synced(mark.id)
        synced_count += 1
    return synced_count
