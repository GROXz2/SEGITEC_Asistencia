"""Synchronization clients for Google Apps Script."""

from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

import requests

from raspberry.raw_store import RawMark, RawStore


class SyncClient(Protocol):
    def send_mark(self, mark: RawMark) -> None:
        """Send a mark to the remote service or raise an exception."""


class GoogleAppsScriptSyncClient:
    """HTTP client that posts RAW marks to a Google Apps Script endpoint."""

    def __init__(self, url: str, api_key: str, *, timeout_seconds: int = 10) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def send_mark(self, mark: RawMark) -> None:
        response = requests.post(
            self.url,
            json={"api_key": self.api_key, "type": "raw_mark", "payload": asdict(mark)},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()


class DryRunSyncClient:
    """Client used when Google sync is disabled; it never marks rows as synced."""

    def send_mark(self, mark: RawMark) -> None:
        raise RuntimeError("google.enabled=false; marca queda pendiente en modo dry-run")


def build_sync_client(*, enabled: bool, api_url: str, api_key: str, timeout_seconds: int = 10) -> SyncClient:
    """Build the configured sync client."""

    if not enabled:
        return DryRunSyncClient()
    if not api_url:
        raise ValueError("google.api_url es obligatorio cuando google.enabled=true")
    if not api_key:
        raise ValueError("google.api_key es obligatorio cuando google.enabled=true")
    return GoogleAppsScriptSyncClient(api_url, api_key, timeout_seconds=timeout_seconds)


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
