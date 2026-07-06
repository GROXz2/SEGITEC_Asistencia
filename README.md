# segitec-asistencia-rfid

Sistema interno de asistencia RFID/NFC para obras de SEGITEC.

> Este sistema es una herramienta operativa para control de asistencia, cálculo de horas, revisión de sábados trabajados, horas extra, horas faltadas y soporte para pago de sueldos. No reemplaza el libro físico de asistencia, que sigue siendo el respaldo legal.

## Objetivo

Registrar marcas de entrada/salida en obra mediante tags RFID/NFC asociados a la chaqueta reflectante de cada trabajador. La Raspberry Pi opera como controlador principal, arranca automáticamente y queda en modo escucha sin requerir login para marcar asistencia.

## Decisiones de arquitectura

- Controlador principal: Raspberry Pi.
- Método de marcaje único: RFID/NFC.
- Lector objetivo: PN532 13.56 MHz conectado a Raspberry Pi.
- Persistencia local inicial: SQLite para RAW local de marcas.
- Sincronización operativa: Google Sheets mediante Google Apps Script.
- Respaldo legal: libro físico de asistencia.
- Respaldo local RAW: conservación mínima de 3 meses.
- RAW local: no editable desde la interfaz normal.

## Flujo operativo

1. La Raspberry Pi inicia automáticamente el servicio.
2. El sistema carga configuración y caché local de trabajadores.
3. El lector queda en modo listening esperando tags RFID/NFC.
4. Al detectar un tag válido:
   - se registra primero la marca RAW local en SQLite;
   - se muestra confirmación en pantalla y suena buzzer (pendiente para etapa futura);
   - se intenta sincronizar la marca con Google Apps Script.
5. Si no hay internet o falla la sincronización, la marca queda pendiente localmente.
6. Cuando vuelve la conectividad, el servicio reintenta sincronizar marcas pendientes.
7. Google Sheets funciona como base operativa para trabajadores, marcas sincronizadas, resúmenes mensuales, sábados, ajustes del jefe y estado del equipo.
8. El jefe puede modificar horas finales y observaciones en Google Sheets, pero no el RAW local.

## Google Sheets

El sistema debe crear automáticamente una planilla mensual por obra con el formato:

```text
SEGITEC - OBRA - Mes Año
```

## Estructura inicial

```text
raspberry/
  main.py            # Flujo inicial con lectura RFID simulada por consola
  raw_store.py       # Persistencia SQLite de marcas RAW
  sync_service.py    # Placeholder de sincronización con Google Apps Script
  workers_cache.py   # Caché local de trabajadores

tests/
  test_raw_store.py  # Tests básicos de persistencia RAW
```

## Ejecución local de desarrollo

1. Crear entorno virtual e instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copiar configuración de ejemplo:

```bash
cp config.example.yaml config.yaml
```

3. Ejecutar flujo simulado:

```bash
python -m raspberry.main --config config.yaml
```

4. Ejecutar tests:

```bash
pytest
```
