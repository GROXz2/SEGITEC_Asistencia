# segitec-asistencia-rfid

Sistema interno de asistencia RFID/NFC para obras de SEGITEC.

> Este sistema es una herramienta operativa para control de asistencia, cálculo de horas, revisión de sábados trabajados, horas extra, horas faltadas y soporte para pago de sueldos. No reemplaza el libro físico de asistencia, que sigue siendo el respaldo legal.

## Objetivo

Registrar marcas de entrada/salida en obra mediante tags RFID/NFC asociados a la chaqueta reflectante de cada trabajador. La Raspberry Pi será el controlador principal en producción, pero esta etapa queda preparada para probar el flujo completo desde un PC Windows o Linux sin Raspberry, PN532, pantalla ni buzzer.

## Decisiones de arquitectura

- Controlador principal futuro: Raspberry Pi.
- Método de marcaje único: RFID/NFC.
- Lector objetivo futuro: PN532 13.56 MHz conectado a Raspberry Pi.
- Modo disponible en esta etapa: `rfid.mode=simulated`, con UID ingresado manualmente por consola.
- Persistencia local inicial: SQLite en `data/segitec_asistencia.db`.
- Cada marca se guarda primero como RAW local antes de intentar sincronizar.
- Sincronización operativa futura: Google Sheets mediante Google Apps Script.
- Si `google.enabled=false`, no se llama a Google y las marcas quedan pendientes en modo dry-run.
- Si `google.enabled=true`, el sistema intenta enviar cada marca pendiente a `google.api_url`.
- Respaldo local RAW: conservación de 3 meses, configurada como `raw_retention_days: 90`.
- RAW local: no editable desde la interfaz normal.

## Datos de prueba

El proyecto incluye trabajadores falsos, sin datos reales, en:

```text
data/workers_demo.json
```

UIDs útiles para probar:

```text
04AABBCCDD  -> Trabajador Demo Uno
04DDEEFF00  -> Trabajadora Demo Dos
0411223344  -> Trabajador Demo Inactivo (debe aparecer como TAG NO REGISTRADO)
```

También puedes escribir los UIDs con espacios, guiones o `:`; el sistema los normaliza a hexadecimal en mayúsculas.

## Estructura

```text
raspberry/
  main.py            # Flujo con lectura RFID simulada por consola
  raw_store.py       # Persistencia SQLite de marcas RAW
  rfid.py            # Normalización de UID/tag RFID
  sync_service.py    # Sincronización dry-run o HTTP con Google Apps Script
  workers_cache.py   # Caché local de trabajadores falsos

data/
  workers_demo.json  # Trabajadores falsos para pruebas locales

tools/
  fake_apps_script_server.py  # Servidor HTTP local que simula Google Apps Script
  inspect_db.py              # Inspector Python de RAW SQLite sin sqlite3 CLI

tests/
  test_raw_store.py
  test_simulated_flow.py
```

## Preparación en Windows o Linux

### 1. Crear entorno virtual

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Crear configuración local

```bash
cp config.example.yaml config.yaml
```

En Windows PowerShell:

```powershell
Copy-Item config.example.yaml config.yaml
```

## Ejecutar tests

```bash
pytest
```

## Ejecutar una marca simulada sin Google

Deja `google.enabled: false` en `config.yaml` y ejecuta el modo interactivo:

```bash
python -m raspberry.main --config config.yaml
```

Luego ingresa un UID, por ejemplo:

```text
RFID UID> 04:AA:BB:CC:DD
```

Para pruebas rápidas desde PC también puedes registrar una sola marca y salir automáticamente con `--simulate-tag`:

```bash
python -m raspberry.main --config config.yaml --simulate-tag 04:AA:BB:CC:DD
```

En Windows PowerShell:

```powershell
python -m raspberry.main --config config.yaml --simulate-tag 04:AA:BB:CC:DD
```

La marca se guarda primero en `data/segitec_asistencia.db`, no se intenta conectar a Google y queda pendiente con un error dry-run controlado.

## Levantar servidor falso de Google Apps Script

En una terminal:

```bash
python tools/fake_apps_script_server.py --host 127.0.0.1 --port 8000
```

En otra terminal, edita `config.yaml`:

```yaml
google:
  enabled: true
  api_url: "http://127.0.0.1:8000/exec"
  timeout_seconds: 10
```

Luego ejecuta el simulador:

```bash
python -m raspberry.main --config config.yaml
```

Cada UID ingresado se guardará como RAW local y luego se enviará al servidor falso.

## Revisar la base SQLite

La base local se crea automáticamente en:

```text
data/segitec_asistencia.db
```

No necesitas instalar el ejecutable `sqlite3`. El proyecto incluye un inspector Python:

```bash
python tools/inspect_db.py --db data/segitec_asistencia.db
```

En Windows PowerShell:

```powershell
python tools/inspect_db.py --db data/segitec_asistencia.db
```

Para ver solo pendientes:

```bash
python tools/inspect_db.py --db data/segitec_asistencia.db --pending-only
```

En Windows PowerShell:

```powershell
python tools/inspect_db.py --db data/segitec_asistencia.db --pending-only
```

Para validar la cadena de integridad RAW (`previous_hash` -> `row_hash`):

```bash
python tools/inspect_db.py --db data/segitec_asistencia.db --validate-chain
```

En Windows PowerShell:

```powershell
python tools/inspect_db.py --db data/segitec_asistencia.db --validate-chain
```

## Siguiente etapa: Google Apps Script real

La carpeta `google_apps_script/` contiene la primera API mínima para recibir marcas RAW reales en Google Sheets mediante Google Apps Script.

Incluye:

- `Code.gs` con endpoints `doPost(e)` y `doGet(e)`.
- Escritura de marcas en `MARCAS_RAW_SYNC`.
- Actualización de heartbeat en `ESTADO_EQUIPO`.
- Lectura básica de `CONFIG` y `TRABAJADORES`.
- Ejemplos de payload en `google_apps_script/sample_payloads.md`.

Esta etapa todavía no implementa creación mensual automática, resumen mensual de horas, PN532 real, pantalla, buzzer ni servicio `systemd` en Raspberry Pi.
