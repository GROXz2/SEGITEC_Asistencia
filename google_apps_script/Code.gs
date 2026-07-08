const SHEET_NAMES = {
  rawMarks: 'MARCAS_RAW_SYNC',
  equipmentStatus: 'ESTADO_EQUIPO',
  workers: 'TRABAJADORES',
  config: 'CONFIG',
};

const RAW_MARK_HEADERS = [
  'received_at',
  'raw_id',
  'tag_uid',
  'worker_id',
  'device_id',
  'obra',
  'marked_at',
  'created_at',
  'row_hash',
  'previous_hash',
  'sync_attempts',
  'last_sync_error',
];

const EQUIPMENT_STATUS_HEADERS = [
  'device_id',
  'obra',
  'last_seen',
  'status',
  'pending_marks',
  'firmware_version',
  'last_error',
];

const WORKERS_HEADERS = [
  'worker_id',
  'tag_uid',
  'name',
  'active',
  'obra',
];

const CONFIG_HEADERS = ['key', 'value'];

const DEFAULT_CONFIG_ROWS = [
  ['API_KEY', 'TEST_SECRET'],
  ['ACTIVE_MONTH_FILE_ID', ''],
  ['WORKERS_VERSION', '1'],
  ['DEFAULT_OBRA', 'OBRA DEMO'],
];

function doPost(e) {
  try {
    const payload = parseJsonBody_(e);
    verifyApiKey_(payload);

    if (payload.type === 'raw_mark') {
      return jsonResponse_(handleMark_(payload.payload || {}));
    }

    if (payload.type === 'heartbeat') {
      return jsonResponse_(handleHeartbeat_(payload.payload || {}));
    }

    return jsonResponse_({ ok: false, error: 'unsupported_type', type: payload.type }, 400);
  } catch (error) {
    return jsonResponse_({ ok: false, error: String(error.message || error) }, 400);
  }
}

function doGet(e) {
  try {
    const type = (e && e.parameter && e.parameter.type) || 'health';

    if (type === 'health') {
      return jsonResponse_(handleHealth_());
    }

    if (type === 'config') {
      return jsonResponse_({ ok: true, config: readConfig_() });
    }

    if (type === 'workers') {
      return jsonResponse_({ ok: true, workers: readWorkers_() });
    }

    return jsonResponse_({ ok: false, error: 'unsupported_type', type: type }, 400);
  } catch (error) {
    return jsonResponse_({ ok: false, error: String(error.message || error) }, 400);
  }
}

function handleMark_(payload) {
  const sheet = getOrCreateSheet_(SHEET_NAMES.rawMarks, RAW_MARK_HEADERS);
  const receivedAt = new Date().toISOString();

  sheet.appendRow([
    receivedAt,
    valueOrBlank_(payload.id),
    valueOrBlank_(payload.tag_uid),
    valueOrBlank_(payload.worker_id),
    valueOrBlank_(payload.device_id),
    valueOrBlank_(payload.obra),
    valueOrBlank_(payload.marked_at),
    valueOrBlank_(payload.created_at),
    valueOrBlank_(payload.row_hash),
    valueOrBlank_(payload.previous_hash),
    valueOrBlank_(payload.sync_attempts),
    valueOrBlank_(payload.last_sync_error),
  ]);

  return {
    ok: true,
    type: 'raw_mark',
    received_at: receivedAt,
    raw_id: valueOrBlank_(payload.id),
    row_hash: valueOrBlank_(payload.row_hash),
  };
}

function handleHeartbeat_(payload) {
  const sheet = getOrCreateSheet_(SHEET_NAMES.equipmentStatus, EQUIPMENT_STATUS_HEADERS);
  const deviceId = valueOrBlank_(payload.device_id);
  const lastSeen = valueOrBlank_(payload.last_seen) || new Date().toISOString();

  if (!deviceId) {
    throw new Error('payload.device_id is required');
  }

  const rowValues = [
    deviceId,
    valueOrBlank_(payload.obra),
    lastSeen,
    valueOrBlank_(payload.status) || 'online',
    valueOrBlank_(payload.pending_marks),
    valueOrBlank_(payload.firmware_version),
    valueOrBlank_(payload.last_error),
  ];

  const rowIndex = findRowByValue_(sheet, 1, deviceId);
  if (rowIndex > 0) {
    sheet.getRange(rowIndex, 1, 1, EQUIPMENT_STATUS_HEADERS.length).setValues([rowValues]);
  } else {
    sheet.appendRow(rowValues);
  }

  return {
    ok: true,
    type: 'heartbeat',
    device_id: deviceId,
    last_seen: lastSeen,
  };
}

function handleHealth_() {
  ensureBaseSheets_();
  return {
    ok: true,
    status: 'ok',
    service: 'segitec-asistencia-apps-script',
    checked_at: new Date().toISOString(),
  };
}

function verifyApiKey_(request) {
  const expectedApiKey = String(readConfig_().API_KEY || '');
  const receivedApiKey = String((request && request.api_key) || '');

  if (!expectedApiKey) {
    throw new Error('CONFIG API_KEY is empty');
  }

  if (receivedApiKey !== expectedApiKey) {
    throw new Error('invalid api_key');
  }

  return true;
}

function openSpreadsheet_() {
  return SpreadsheetApp.getActiveSpreadsheet();
}

function ensureBaseSheets_() {
  getOrCreateSheet_(SHEET_NAMES.rawMarks, RAW_MARK_HEADERS);
  getOrCreateSheet_(SHEET_NAMES.equipmentStatus, EQUIPMENT_STATUS_HEADERS);
  getOrCreateSheet_(SHEET_NAMES.workers, WORKERS_HEADERS);
  const configSheet = getOrCreateSheet_(SHEET_NAMES.config, CONFIG_HEADERS);
  seedDefaultConfig_(configSheet);
}

function getOrCreateSheet_(name, headers) {
  const spreadsheet = openSpreadsheet_();
  let sheet = spreadsheet.getSheetByName(name);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(name);
  }

  ensureHeaders_(sheet, headers);
  return sheet;
}

function ensureHeaders_(sheet, headers) {
  const range = sheet.getRange(1, 1, 1, headers.length);
  const currentHeaders = range.getValues()[0];
  const hasAnyHeader = currentHeaders.some(function (value) {
    return String(value || '').trim() !== '';
  });

  if (!hasAnyHeader) {
    range.setValues([headers]);
    sheet.setFrozenRows(1);
  }
}

function seedDefaultConfig_(sheet) {
  const existingConfig = readConfigFromSheet_(sheet);
  const rowsToAppend = DEFAULT_CONFIG_ROWS.filter(function (row) {
    return !Object.prototype.hasOwnProperty.call(existingConfig, row[0]);
  });

  if (rowsToAppend.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, rowsToAppend.length, CONFIG_HEADERS.length).setValues(rowsToAppend);
  }
}

function readConfig_() {
  const sheet = getOrCreateSheet_(SHEET_NAMES.config, CONFIG_HEADERS);
  seedDefaultConfig_(sheet);
  return readConfigFromSheet_(sheet);
}

function readConfigFromSheet_(sheet) {
  const lastRow = sheet.getLastRow();
  const config = {};

  if (lastRow < 2) {
    return config;
  }

  const values = sheet.getRange(2, 1, lastRow - 1, CONFIG_HEADERS.length).getValues();
  values.forEach(function (row) {
    const key = String(row[0] || '').trim();
    if (key) {
      config[key] = row[1];
    }
  });

  return config;
}

function readWorkers_() {
  const sheet = getOrCreateSheet_(SHEET_NAMES.workers, WORKERS_HEADERS);
  const lastRow = sheet.getLastRow();

  if (lastRow < 2) {
    return [];
  }

  const values = sheet.getRange(2, 1, lastRow - 1, WORKERS_HEADERS.length).getValues();
  return values
    .filter(function (row) {
      return row.some(function (value) {
        return String(value || '').trim() !== '';
      });
    })
    .map(function (row) {
      return {
        worker_id: row[0],
        tag_uid: row[1],
        name: row[2],
        active: row[3],
        obra: row[4],
      };
    });
}

function findRowByValue_(sheet, columnIndex, value) {
  const lastRow = sheet.getLastRow();

  if (lastRow < 2) {
    return -1;
  }

  const values = sheet.getRange(2, columnIndex, lastRow - 1, 1).getValues();
  for (let index = 0; index < values.length; index += 1) {
    if (String(values[index][0]) === String(value)) {
      return index + 2;
    }
  }

  return -1;
}

function parseJsonBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    throw new Error('missing JSON body');
  }

  return JSON.parse(e.postData.contents);
}

function jsonResponse_(body) {
  return ContentService
    .createTextOutput(JSON.stringify(body))
    .setMimeType(ContentService.MimeType.JSON);
}

function valueOrBlank_(value) {
  if (value === null || value === undefined) {
    return '';
  }

  return value;
}
