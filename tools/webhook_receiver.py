"""Local demo receiver: verifies HMAC/timestamp and deduplicates event IDs.

Run from project root: python tools/webhook_receiver.py
Receipts are persisted in an ignored SQLite file, with a localhost-only JSON view.
"""
import hashlib
import hmac
import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
DATABASE = ROOT / 'webhook_receipts.sqlite3'

def initialize():
    with sqlite3.connect(DATABASE) as db:
        db.execute('CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, received_at TEXT, payload TEXT)')

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != '/receipts': return self.respond(404, {'detail': 'Use /receipts.'})
        with sqlite3.connect(DATABASE) as db:
            rows = db.execute('SELECT id, received_at, payload FROM receipts ORDER BY received_at DESC LIMIT 50').fetchall()
        self.respond(200, {'receipts': [{'id': r[0], 'received_at': r[1], 'event': json.loads(r[2])} for r in rows]})

    def do_POST(self):
        if self.path != '/alerts': return self.respond(404, {'detail': 'Use /alerts.'})
        secret = os.getenv('WEBHOOK_SECRET', '')
        if not secret: return self.respond(503, {'detail': 'WEBHOOK_SECRET não configurado.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 64_000: raise ValueError()
            body = self.rfile.read(length)
            timestamp = self.headers.get('X-RiskOps-Timestamp', '')
            if abs(time.time() - int(timestamp)) > 300: raise ValueError()
            expected = 'sha256=' + hmac.new(secret.encode(), timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, self.headers.get('X-RiskOps-Signature', '')):
                return self.respond(401, {'detail': 'Assinatura inválida.'})
            data = json.loads(body)
            if not isinstance(data, dict): raise ValueError()
            event_id = data['id']
            if event_id != self.headers.get('Idempotency-Key') or not isinstance(event_id, str): raise ValueError()
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            return self.respond(400, {'detail': 'Evento inválido ou timestamp fora da janela.'})
        with sqlite3.connect(DATABASE) as db:
            result = db.execute('INSERT OR IGNORE INTO receipts VALUES (?, ?, ?)',
                (event_id, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), body.decode('utf-8')))
        self.respond(200, {'accepted': True, 'duplicate': result.rowcount == 0, 'id': event_id})

if __name__ == '__main__':
    initialize()
    print('Receptor local: http://127.0.0.1:9001/receipts (Ctrl+C para encerrar)', flush=True)
    try: HTTPServer(('127.0.0.1', 9001), Handler).serve_forever()
    except KeyboardInterrupt: pass
