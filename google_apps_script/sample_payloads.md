# Payloads de ejemplo

Reemplazar `WEB_APP_URL` por la URL publicada del Web App de Google Apps Script.

## raw_mark

```bash
curl -X POST "WEB_APP_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "TEST_SECRET",
    "type": "raw_mark",
    "payload": {
      "id": 1,
      "tag_uid": "04AABBCCDD",
      "worker_id": "demo-001",
      "device_id": "pc-simulado-obra-demo-01",
      "obra": "OBRA DEMO",
      "marked_at": "2026-07-06T20:17:04.287481+00:00",
      "synced": false,
      "sync_attempts": 1,
      "last_sync_error": "google.enabled=false; marca queda pendiente en modo dry-run",
      "created_at": "2026-07-06T20:17:04.287481+00:00",
      "row_hash": "abc123",
      "previous_hash": null
    }
  }'
```

Respuesta esperada:

```json
{
  "ok": true,
  "type": "raw_mark",
  "received_at": "2026-07-06T20:18:00.000Z",
  "raw_id": 1,
  "row_hash": "abc123"
}
```

## heartbeat

```bash
curl -X POST "WEB_APP_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "TEST_SECRET",
    "type": "heartbeat",
    "payload": {
      "device_id": "pc-simulado-obra-demo-01",
      "obra": "OBRA DEMO",
      "last_seen": "2026-07-06T20:20:00.000000+00:00",
      "status": "online",
      "pending_marks": 0,
      "firmware_version": "local-mvp-python",
      "last_error": ""
    }
  }'
```

Respuesta esperada:

```json
{
  "ok": true,
  "type": "heartbeat",
  "device_id": "pc-simulado-obra-demo-01",
  "last_seen": "2026-07-06T20:20:00.000000+00:00"
}
```

## health

```bash
curl "WEB_APP_URL?type=health"
```

Respuesta esperada:

```json
{
  "ok": true,
  "status": "ok",
  "service": "segitec-asistencia-apps-script",
  "checked_at": "2026-07-06T20:21:00.000Z"
}
```
