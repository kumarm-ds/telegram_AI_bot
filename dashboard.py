"""Read-only public dashboard for demo conversation logs; serves on Railway PORT."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from html import escape
from datetime import datetime, timezone
import csv
import io
import os

CSS = """body{font-family:system-ui,Arial,sans-serif;max-width:1200px;margin:36px auto;padding:0 18px;color:#182333;background:#f7f9fc}h1{margin-bottom:5px}small,.muted{color:#637083}.panel{background:white;border:1px solid #e3e8f0;border-radius:12px;padding:18px;margin:16px 0}input,button{font:inherit;padding:9px;border:1px solid #bbc7d8;border-radius:7px}button{background:#173c74;color:white;cursor:pointer}table{border-collapse:collapse;width:100%;background:white}th,td{text-align:left;padding:11px;border-bottom:1px solid #e5e9f0;vertical-align:top}th{background:#eef2f8}.msg{white-space:pre-wrap;overflow-wrap:anywhere;max-width:650px}.pager a{margin-right:15px}a{color:#1453a1} .pill{font-size:12px;background:#edf2fa;border-radius:5px;padding:3px 7px}"""

def page_html(rows, total, page, q, user):
    body = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Telegram Bot Conversation Logs</title><style>', CSS, '</style></head><body>']
    body += ['<h1>Telegram Bot — Conversation Logs</h1><small>Read-only demo dashboard · Times shown in UTC · Refresh to see new messages</small>']
    body += ['<div class="panel"><form action="/" method="get"><label>Search message <input name="q" value="', escape(q, quote=True), '" placeholder="warranty, model, error..."></label> &nbsp; <label>User ID <input name="user" value="', escape(user, quote=True), '" placeholder="optional"></label> <button type="submit">Filter</button></form><p>', str(total), ' matching log entries · Page ', str(page), '</p><a href="/export.csv">Export all logs as CSV</a></div>']
    body += ['<div class="panel" style="overflow-x:auto"><table><thead><tr><th>UTC time</th><th>User ID</th><th>Sender</th><th>Event</th><th>Message</th></tr></thead><tbody>']
    for row in rows:
        _, ts, uid, sender, event, message = row
        body += ['<tr><td>', escape(ts), '</td><td>', escape(str(uid)), '</td><td><span class="pill">', escape(sender), '</span></td><td>', escape(event), '</td><td class="msg">', escape(message), '</td></tr>']
    if not rows:
        body += ['<tr><td colspan="5">No conversation logs found yet.</td></tr>']
    body += ['</tbody></table></div><div class="pager">']
    from urllib.parse import urlencode
    if page > 1:
        body += ['<a href="/?', urlencode({'q': q, 'user': user, 'page': page-1}), '">← Previous</a>']
    if page * 50 < total:
        body += ['<a href="/?', urlencode({'q': q, 'user': user, 'page': page+1}), '">Next →</a>']
    body += ['</div></body></html>']
    return ''.join(body).encode('utf-8')

def run_dashboard(store):
    port = int(os.environ.get('PORT', '8080'))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == '/health':
                self.send_response(200); self.end_headers(); self.wfile.write(b'OK'); return
            if parsed.path == '/export.csv':
                data = io.StringIO()
                writer = csv.writer(data)
                writer.writerow(['id', 'utc_time', 'user_id', 'sender', 'event', 'message'])
                writer.writerows(store.get_logs(limit=1000000))
                payload = data.getvalue().encode('utf-8-sig')
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="conversation_logs.csv"')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers(); self.wfile.write(payload); return
            if parsed.path != '/':
                self.send_error(404); return
            params = parse_qs(parsed.query)
            q = params.get('q', [''])[0][:200]
            user = params.get('user', [''])[0][:30]
            try: page = max(1, min(100000, int(params.get('page', ['1'])[0])))
            except ValueError: page = 1
            rows, total = store.search_logs(q, user, page=page, page_size=50)
            payload = page_html(rows, total, page, q, user)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers(); self.wfile.write(payload)
        def log_message(self, format, *args):
            pass
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()
