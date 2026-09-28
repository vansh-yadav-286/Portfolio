/**
 * Portfolio contact-form backend (Google Apps Script + Google Sheets).
 *
 * Sheet columns (row 1):  ID | Name | Email | Message | Timestamp
 *
 * Endpoints (one Web App URL):
 *   POST  {action:"add", id, name, email, message, timestamp}   -> append a row (public, used by the contact form)
 *   GET   ?action=list&key=ADMIN_KEY                            -> all responses as JSON (admin only)
 *   POST  {action:"delete", id, key}                            -> delete one response (admin only)
 *   POST  {action:"deleteAll", key}                             -> delete every response (admin only)
 *
 * CORS: Apps Script web apps deployed with "Anyone" access answer browser fetch()
 * calls on their own. The frontend sends POST bodies as text/plain so the
 * browser skips the CORS preflight request, which Apps Script cannot handle.
 */

// Must be the same value as ADMIN_CONFIG.password in the portfolio's script.js.
// Reading and deleting responses requires it, so the sheet's data is not public.
const ADMIN_KEY = 'change-me-123';

const SHEET_NAME = 'Responses';
const HEADERS = ['ID', 'Name', 'Email', 'Message', 'Timestamp'];

function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.getRange('A:E').setNumberFormat('@'); // plain text so Sheets doesn't reformat timestamps/IDs
  }
  return sheet;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const sheet = getSheet_();

    if (body.action === 'add') {
      const name = String(body.name || '').trim();
      const email = String(body.email || '').trim();
      const message = String(body.message || '').trim();
      if (!name || !email || !message) return json_({ ok: false, error: 'Missing fields' });
      if (name.length > 200 || email.length > 200 || message.length > 5000) return json_({ ok: false, error: 'Field too long' });
      const id = String(body.id || Utilities.getUuid());
      const timestamp = String(body.timestamp || new Date().toISOString());
      sheet.appendRow([id, name, email, message, timestamp]);
      return json_({ ok: true });
    }

    // everything below is admin-only
    if (body.key !== ADMIN_KEY) return json_({ ok: false, error: 'Unauthorized' });

    if (body.action === 'delete') {
      const ids = sheet.getRange(1, 1, sheet.getLastRow(), 1).getValues();
      for (let i = ids.length - 1; i >= 1; i--) {
        if (String(ids[i][0]) === String(body.id)) sheet.deleteRow(i + 1);
      }
      return json_({ ok: true });
    }

    if (body.action === 'deleteAll') {
      if (sheet.getLastRow() > 1) sheet.deleteRows(2, sheet.getLastRow() - 1);
      return json_({ ok: true });
    }

    return json_({ ok: false, error: 'Unknown action' });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function doGet(e) {
  try {
    const params = (e && e.parameter) || {};
    if (params.action !== 'list') return json_({ ok: true, message: 'Portfolio responses API is running.' });
    if (params.key !== ADMIN_KEY) return json_({ ok: false, error: 'Unauthorized' });

    const rows = getSheet_().getDataRange().getValues().slice(1); // drop header row
    const responses = rows
      .filter((r) => r[0] !== '')
      .map((r) => ({
        id: String(r[0]),
        name: String(r[1]),
        email: String(r[2]),
        message: String(r[3]),
        timestamp: r[4] instanceof Date ? r[4].toISOString() : String(r[4])
      }));
    return json_({ ok: true, responses: responses });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}
