# AGENTS.md

## Proyecto

Estamos construyendo `segitec-asistencia-rfid`, un sistema interno de asistencia para obras de SEGITEC.

## Reglas de producto

- SEGITEC necesita un sistema interno de asistencia para obras.
- No será el documento legal de asistencia; el libro físico sigue siendo el respaldo legal.
- El sistema sirve para control operativo, cálculo de horas, revisión de sábados trabajados, horas extra, horas faltadas y soporte para pago de sueldos.
- Usar Raspberry Pi como controlador principal.
- No usar Arduino como base principal.
- No usar QR.
- El único método de marcaje será RFID/NFC.
- El lector objetivo será PN532 13.56 MHz conectado a Raspberry Pi.
- Cada trabajador tendrá un tag RFID/NFC asociado a su chaqueta reflectante.
- La Raspberry debe arrancar automáticamente y quedar en modo listening.
- No debe haber login para marcar asistencia.
- Al leer un tag válido, debe sonar un buzzer y mostrar confirmación en pantalla.
- Cada marca debe guardarse primero en RAW local.
- Luego debe intentarse sincronizar con Google Sheets vía Google Apps Script.
- Si no hay internet, la marca queda guardada localmente y se sincroniza cuando vuelva la conexión.
- El RAW local debe conservar 3 meses de respaldo.
- El RAW local no debe ser editable desde la interfaz normal.
- Google Sheets será la base operativa: trabajadores, marcas sincronizadas, resumen mensual, sábados, ajustes del jefe y estado del equipo.
- El jefe podrá modificar horas finales y observaciones en Google Sheets, pero no debe modificar el RAW local.
- Google Sheets mensual se debe crear automáticamente por obra con el formato `SEGITEC - OBRA - Mes Año`.

## Reglas técnicas de esta etapa

- No implementar todavía pantalla, buzzer ni PN532 real.
- Usar lectura RFID simulada desde consola para validar flujo.
- Persistir RAW local con SQLite.
- Mantener el código simple, explícito y testeable.
- No envolver imports en bloques `try/catch`.
