# Google Apps Script real para SEGITEC Asistencia

Esta carpeta contiene la primera versión mínima de API real en Google Apps Script para sincronizar marcas RAW desde la Raspberry/PC hacia Google Sheets.

## Alcance de esta etapa

Incluye:

- Recepción de marcas RAW por `POST`.
- Registro en la pestaña `MARCAS_RAW_SYNC`.
- Recepción de heartbeat por `POST`.
- Actualización de estado en `ESTADO_EQUIPO`.
- Endpoints `GET` para `health`, `config` y `workers`.
- Creación automática de pestañas base si no existen.

No incluye todavía:

- Creación mensual automática de archivos.
- Resumen mensual de horas.
- Integración con PN532 real.
- Pantalla, buzzer ni servicio `systemd` en Raspberry Pi.

## Instalación manual

1. Crear manualmente un Google Sheet para la obra o ambiente de pruebas.
2. Abrir el Google Sheet.
3. Ir a **Extensions > Apps Script**.
4. Crear o abrir el archivo `Code.gs` del proyecto Apps Script.
5. Copiar y pegar el contenido de `google_apps_script/Code.gs`.
6. Guardar el proyecto.
7. Ejecutar manualmente `handleHealth_()` una vez desde el editor para autorizar permisos y crear las pestañas base:
   - `MARCAS_RAW_SYNC`
   - `ESTADO_EQUIPO`
   - `TRABAJADORES`
   - `CONFIG`
8. En la pestaña `CONFIG`, configurar la fila `API_KEY` con una clave secreta propia. No usar `TEST_SECRET` en producción.
9. Publicar el script como Web App:
   - **Deploy > New deployment**.
   - Tipo: **Web app**.
   - Execute as: el usuario dueño del Sheet.
   - Who has access: según el ambiente de prueba definido por SEGITEC.
10. Copiar la URL del Web App (`.../exec`).
11. Pegar esa URL en `config.yaml`:

```yaml
google:
  enabled: true
  api_url: "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
  timeout_seconds: 10
```

## Pestañas creadas

### `MARCAS_RAW_SYNC`

Columnas:

- `received_at`
- `raw_id`
- `tag_uid`
- `worker_id`
- `device_id`
- `obra`
- `marked_at`
- `created_at`
- `row_hash`
- `previous_hash`
- `sync_attempts`
- `last_sync_error`

### `ESTADO_EQUIPO`

Columnas:

- `device_id`
- `obra`
- `last_seen`
- `status`
- `pending_marks`
- `firmware_version`
- `last_error`

### `TRABAJADORES`

Por ahora se usa como fuente simple para `GET ?type=workers`.

Columnas iniciales:

- `worker_id`
- `tag_uid`
- `name`
- `active`
- `obra`

### `CONFIG`

Formato clave/valor:

- `API_KEY`
- `ACTIVE_MONTH_FILE_ID`
- `WORKERS_VERSION`
- `DEFAULT_OBRA`
